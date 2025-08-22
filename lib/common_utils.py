#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import argparse
import os
import sys
import logging
import importlib
import importlib.machinery
import importlib.util
import glob
import subprocess
import shutil
import re
import yaml
import time

logger = logging.getLogger('Gen-Machineconf')

# Common bitbake variable
Bitbake = None

# Reference from OE-Core
def load_plugins(plugins, pluginpath):
    def load_plugin(name):
        logger.debug('Loading plugin %s' % name)
        spec = importlib.machinery.PathFinder.find_spec(
            name, path=[pluginpath])
        if spec:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

    def plugin_name(filename):
        return os.path.splitext(os.path.basename(filename))[0]

    known_plugins = [plugin_name(p.__name__) for p in plugins]
    logger.debug('Loading plugins from %s...' % pluginpath)
    for fn in glob.glob(os.path.join(pluginpath, '*.py')):
        logger.debug(fn)
        name = plugin_name(fn)
        if name != '__init__' and name not in known_plugins:
            plugin = load_plugin(name)
            if hasattr(plugin, 'plugin_init'):
                plugin.plugin_init(plugins)
            plugins.append(plugin)


TemplateYamlData = {}

def ReadTemplateYaml(yamlfile):
    '''
    Reads the specified YAML file and stores the contents into the global TemplateYamlData.
    '''
    if not yamlfile:
        return
    if not os.path.isfile(yamlfile):
        raise Exception('Specified yaml file doesnot exists: %s' % yamlfile)
    global TemplateYamlData
    TemplateYamlData = ReadYaml(yamlfile) or {}


def AddYamlDefaultValues(arg=None, default=None):
    '''
    Looks for a matching argument in the YAML 'args' list and sets default value accordingly.
    '''
    global TemplateYamlData
    TemplateYamlDataArgs = TemplateYamlData.get('args', [])
    for yamlarg in TemplateYamlDataArgs or []:
        if isinstance(yamlarg, str):
            yamlarg = yamlarg.split()
        index, value = ContainsAny(arg, yamlarg)
        if value is not None:
            # Safely get the next value if it exists
            next_value = yamlarg[index + 1] if index + 1 < len(yamlarg) else ''

            if not next_value or next_value.startswith('-'):
                return True
            return next_value
    return default


def GenCPUNames(cluster: str, cpu:str, cpumask_hex: str):
    """
    Generates a list of CPU names based on the cluster name, CPU string, and CPU mask.
    Args:
        cluster (str): The name of the CPU cluster, expected to match the pattern 'cpus_<type>[_<number>]'.
        cpu (str): A string representing CPU identifiers, typically comma-separated and may include ranges.
        cpumask_hex (str or int): A hexadecimal string or integer representing the CPU mask.
    Returns:
        list[str]: A list of CPU names in the format '<cpu_prefix><cpu_type>_<core_index>' for each core enabled in the mask.
        If the cluster name does not match the expected pattern, returns an empty string.
    """
    match = re.match(r'cpus_(\w+?)(?:_\d+)?$', cluster)
    if not match:
        return ''
    cpu_split = cpu.split(',')
    if len(cpu_split) > 1:
        cpu_prefix = cpu_split[1].split('-')[0]
    else:
        cpu_prefix = cpu_split[0].split('-')[0]
    cpu_type = match.group(1)
    if isinstance(cpumask_hex, int):
        cpumask = cpumask_hex
    else:
        cpumask = int(str(cpumask_hex), 16)
    bit_positions = [i for i in range(cpumask.bit_length()) if cpumask & (1 << i)]
    # Generate cpunames like cortex<type>_<core_index>
    cpunames = [f"{cpu_prefix}{cpu_type}_{i}" for i in bit_positions]

    return cpunames


def GetDomainName(proc_name: str, cpu: str, os_hint: str, yaml_file: str):
    """
    Retrieves the domain name for a given processor name, CPU, and OS hint from a YAML configuration file.
    Args:
        proc_name (str): The name of the processor to search for.
        cpu (str): The CPU identifier used for generating CPU names.
        os_hint (str): The operating system type to match.
        yaml_file (str): Path to the YAML file containing domain configurations.
    Returns:
        str or None: The domain name if found, otherwise None.
    """
    try:
        yaml_content = ReadYaml(yaml_file)
        if not yaml_content or 'domains' not in yaml_content:
            return None
        schema = yaml_content['domains']
        for subsystem in schema:
            os_type = schema[subsystem].get('os,type', '')
            for cpu_dict in schema[subsystem].get('cpus', []):
                cluster = cpu_dict.get('cluster', '')
                cpumask = cpu_dict.get('cpumask', '')
                cpunames = GenCPUNames(cluster, cpu, cpumask)
                if proc_name.endswith(tuple(cpunames)):
                    if not os_type:
                        logger.warning(f'OS type not defined for domain {subsystem} (proc_name: {proc_name}), skipping entry.')
                        return None
                    elif os_type.lower() == os_hint:
                        logger.debug(f'Found domain name {subsystem} for proc_name {proc_name} with os type {os_type}')
                        return subsystem
    except Exception as e:
        raise Exception(f"Error in GetDomainName: {e}")
    return None


class AppendArgWithSpace(argparse.Action):
    """
    Custom argparse Action that appends arguments with a space separator.
    """
    def __call__(self, _parser, namespace, values, _option_string=None):
        """
        Appends the provided value to the existing argument value with a space.
        """
        current = getattr(namespace, self.dest, None)
        if current:
            setattr(namespace, self.dest, current + " " + values)
        else:
            setattr(namespace, self.dest, values)


def ContainsAny(search_items, target_list):
    '''
    Returns the index and value of the first item in target_list that exists in search_items.
    '''
    if isinstance(search_items, str):
        search_items = search_items.split()
    for i, item in enumerate(target_list):
        if item in search_items:
            return i, item
    return None, None


def CreateDir(dirpath):
    '''Creates Directory'''
    if not os.path.exists(dirpath):
        try:
            os.makedirs(dirpath, exist_ok=True)
        except IOError:
            raise Exception('Unable to create directory at %s' % dirpath)


def CreateFile(filepath):
    '''Creates a empty File'''
    if not os.path.isfile(filepath):
        with open(filepath, 'w') as f:
            pass


def RenameDir(indir, outdir):
    '''Rename the Directory'''
    if os.path.exists(indir):
        shutil.move(indir, outdir)


def RenameFile(infile, outfile):
    '''Rename File'''
    if os.path.exists(infile):
        os.rename(infile, outfile)


def RemoveDir(dirpath):
    '''Remove Directory'''
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)


def RemoveFile(filepath):
    '''Remove file'''
    if os.path.exists(filepath):
        os.remove(filepath)


def CopyDir(indir, outdir, exclude=''):
    '''Copy Directory to Directory
    Using tar command to copy dirs which is twice
    faster than shutil.copytree and support exclude option'''
    if os.path.exists(indir):
        if not os.path.exists(outdir):
            CreateDir(outdir)
        copycmd = "tar --xattrs --xattrs-include='*' --exclude='%s' \
                -cf - -S -C %s -p . | tar --xattrs --xattrs-include='*' \
                -xf - -C %s" % (exclude, indir, outdir)
        RunCmd(copycmd, os.getcwd(), shell=True)


def CopyFile(infile, dest, follow_symlinks=False):
    '''Copy File to Dir'''
    if os.path.isfile(infile):
        shutil.copy2(infile, dest, follow_symlinks=follow_symlinks)


def RunCmd(command, out_dir, extraenv=None,
           failed_msg='', shell=False, checkcall=False):
    '''Run Shell commands from python'''
    command = command.split() if not shell else command
    logger.debug(command)
    env = os.environ.copy()
    if extraenv:
        for k in extraenv:
            env[k] = extraenv[k]
    if checkcall:
        subprocess.check_call(
            command, env=extraenv, cwd=out_dir, shell=shell)
        return
    else:
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env, shell=shell,
                                   executable='/bin/bash',
                                   cwd=out_dir)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception('\n%s\n%s\n%s' %
                            (stdout.decode('utf-8'),
                             stderr.decode('utf-8'),
                             failed_msg))
        else:
            if not stdout is None:
                stdout = stdout.decode("utf-8")
            if not stderr is None:
                stderr = stderr.decode("utf-8")
        logger.debug('\n%s\n%s\n%s' % (stdout, stderr, failed_msg))
        return stdout, stderr


# Check mconf utilities
def AddNativeSysrootPath(native_sysroot):
    '''Add a native-sysroot to the PATH'''
    if not native_sysroot:
       return

    native_sysroot = os.path.abspath(native_sysroot)

    # Note the PATH setting following poky/scripts/oe-run-native
    if not os.path.isdir(native_sysroot):
        raise Exception('Native sysroot path does not exists: %s'
                     % native_sysroot)
    else:
        # This list is BACKWARDS of oe-run-native, ensures we get the same final order
        # Skip python3-native, as this breaks subsequent calls to bitbake
        for entry in os.listdir(os.path.join(native_sysroot, 'usr', 'bin')):
            special_bin_dir = os.path.join(native_sysroot, 'usr', 'bin', entry)
            if os.path.isdir(special_bin_dir) and entry.endswith('-native') and entry != 'python3-native':
                os.environ["PATH"] = special_bin_dir + os.pathsep + os.environ['PATH']

        for bindir in ['sbin', 'usr/sbin', 'bin', 'usr/bin']:
            add_path = os.path.join(native_sysroot, bindir)
            # Skip paths already in the PATH
            if add_path in os.environ["PATH"].split(':'):
                continue
            os.environ["PATH"] = add_path + os.pathsep + os.environ['PATH']

    logger.debug("PATH=%s" % os.environ["PATH"])


def FindNativeSysroot(recipe):
    '''Based on oe-find-native-sysroot, purpose is to find a recipes sysroot'''
    if not recipe:
        return ""

    # That has already been done, don't repeat!
    if recipe in FindNativeSysroot.recipe_list:
        return

    recipe_staging_dir = None
    try:
        recipe_staging_dir = Bitbake.getVar('STAGING_DIR_NATIVE', recipe)
    except TypeError:
        recipe_staging_dir = None
    except KeyError:
        recipe_staging_dir = None
    except Exception as e:
        raise Exception("Unable to get required %s sysroot path.\nError: %s" % (recipe, e))

    if not recipe_staging_dir:
        raise Exception("Unable to get required %s sysroot path" % recipe)

    if recipe and not os.path.exists(recipe_staging_dir):
        # Make sure the sysroot is available to us
        logger.info('Constructing %s recipe sysroot...' % recipe)

        Bitbake.runBitbakeCmd(recipe, "addto_recipe_sysroot")

        if not recipe_staging_dir:
            raise Exception("Unable to get %s sysroot path after building" % recipe)

    AddNativeSysrootPath(recipe_staging_dir)

    FindNativeSysroot.recipe_list.append(recipe)

# Default
FindNativeSysroot.recipe_list = []

def RunMenuconfig(Kconfig, cfgfile, ui, out_dir, component):
    if not ui:
        logger.info('Silentconfig %s' % (component))
        cmd = 'yes "" | env KCONFIG_CONFIG=%s conf %s' % (cfgfile, Kconfig)
        logger.debug('Running CMD: %s' % cmd)
        status, stdout = subprocess.getstatusoutput(cmd)
        logger.debug(stdout)
        if status != 0:
            logger.error('Failed to silentconfig %s' % component)
            raise Exception(stdout)
    else:
        logger.info('Menuconfig %s' % (component))
        cmd = 'env KCONFIG_CONFIG=%s mconf -s %s' % (cfgfile, Kconfig)
        logger.debug('Running CMD: %s' % cmd)
        try:
            subprocess.check_call(cmd.split(), cwd=out_dir)
        except subprocess.CalledProcessError as e:
            if e.returncode != 0:
                logger.error('Failed to Menuconfig %s' % component)
                raise Exception


def UpdateConfigValue(macro, value, filename):
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()

    with open(filename, 'w') as file_data:
        for line in lines:
            if re.search('# %s is not set' % macro, line) or re.search('%s=' % macro, line):
                continue
            file_data.write(line)
        if value == 'disable':
            file_data.write('# %s is not set\n' % macro)
        else:
            file_data.write('%s=%s\n' % (macro, value))
    file_data.close()


def RemoveConfigs(macro, filename):
    # Remove configs from file if given macro match
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()
    with open(filename, 'w') as file_data:
        for line in lines:
            if line.startswith(macro):
                continue
            file_data.write(line)
    file_data.close()


def GetConfigValue(macro, filename, Type='bool', end_macro='=y'):
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()
    value = ''
    if Type == 'bool':
        for line in lines:
            line = line.strip()
            if line.startswith(macro + '='):
                value = line.replace(macro + '=', '').replace('"', '')
                break
    elif Type == 'choice':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value = line.replace(macro, '').replace(end_macro, '')
                break
    elif Type == 'choicelist':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value += ' ' + line.replace(macro, '').replace(end_macro, '')
    elif Type == 'asterisk':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and re.search(end_macro, line):
                value = line.split('=')[1].replace('"', '')
                break
    return value


def GetFileHashValue(filename):
    import mmap
    import hashlib
    method = hashlib.sha256()
    with open(filename, "rb") as f:
        try:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                for chunk in iter(lambda: mm.read(8192), b''):
                    method.update(chunk)
        except ValueError:
            # You can't mmap() an empty file so silence this exception
            pass
    return method.hexdigest()


def ValidateHashFile(output, macro, infile, update=True):
    statistics_file = os.path.join(output, '.statistics')
    old_hashvalue = GetConfigValue(macro, statistics_file)
    new_hashvalue = GetFileHashValue(infile)
    if old_hashvalue != new_hashvalue:
        if update:
            UpdateConfigValue(macro, new_hashvalue, statistics_file)
        return False
    return True


def check_tool(tool, recipe=None, failed_msg=None, skip_path=False):
    '''Check the tool exists in PATH variable'''
    tool = tool.lower()
    if skip_path:
        tool_path = ''
    else:
        tool_path = shutil.which(tool)
    if not tool_path:
        if recipe:
            try:
                FindNativeSysroot(recipe)
            except Exception as e:
                failed_msg += "\n" + str(e)

        tool_path = shutil.which(tool)
        if not tool_path:
            if failed_msg:
                raise Exception(failed_msg)
            raise Exception('%s is required but not found in the path' % tool)
    return tool_path


def convert_dictto_lowercase(data_dict):
    if isinstance(data_dict, dict):
        return {k.lower(): convert_dictto_lowercase(v) for k, v in data_dict.items()}
    elif isinstance(data_dict, (list, set, tuple)):
        t = type(data_dict)
        return t(convert_dictto_lowercase(o) for o in data_dict)
    elif isinstance(data_dict, str):
        return data_dict.lower()
    else:
        return data_dict


def ReplaceStrFromFile(fpath, search_str, replace_str):
    '''Replace the string with string in the file
    replace with replace_str if found in file.
    '''
    try:
        with open(fpath) as f:
            s = f.read()
            s = s.replace(search_str, replace_str)
    except UnicodeDecodeError:
        pass
    with open(fpath, 'w') as f:
        f.write(s)


def AddStrToFile(filename, string, mode='w'):
    '''Add string or line into the given file '''
    with open(filename, mode) as file_f:
        file_f.write(string)


def ReadYaml(yamlfile):
    with open(yamlfile, 'r') as yaml_fd:
        try:
            return yaml.safe_load(yaml_fd)
        except yaml.YAMLError as exc:
            raise Exception(exc)


def GetFilesFromDir(dirpath, file_ext=''):
    '''Search the nested directories for the file ext if provided'''
    FilesList = []
    for path, dirs, files in os.walk(dirpath):
        for _file in files:
            if file_ext and _file.endswith(file_ext):
                FilesList.append(os.path.join(path, _file))
            if not file_ext:
                FilesList.append(os.path.join(path, _file))
    return FilesList


def CheckLopperUtilsPaths(lopper):
    lopper_dir = os.path.dirname(lopper)
    _lops_dir = glob.glob(os.path.join(os.path.dirname(lopper_dir),
                                      'lib', 'python*', 'site-packages', 'lopper', 'lops'))
    lops_dir = ''
    if _lops_dir:
        lops_dir = _lops_dir[0]

    embeddedsw = os.path.join(os.path.dirname(lopper_dir), 'share', 'embeddedsw')

    return lopper, lopper_dir, lops_dir, embeddedsw


def GetLopperUtilsPath():
    lopper_err_msg = 'Unable to find lopper, please ensure this is in your '
    lopper_err_msg += 'environment or lopper can be built by bitbake. See README.building.md '
    lopper_err_msg += 'in meta-xilinx layer for more details.'

    lopper = check_tool('lopper', 'esw-conf-native', lopper_err_msg)

    lopper, lopper_dir, lops_dir, embeddedsw = CheckLopperUtilsPaths(lopper)

    '''Check if lopper from PATH have all required directories, if not construct the sysroot'''
    if (lops_dir and not os.path.isdir(lops_dir)) or not os.path.isdir(embeddedsw):
        logger.warning("The lopper 'lops' or 'embeddedsw configuration' files are missing, Trying to get recipe sysroot using bitbake")
        lopper = check_tool('lopper', 'esw-conf-native', lopper_err_msg, skip_path=True)
        lopper, lopper_dir, lops_dir, embeddedsw = CheckLopperUtilsPaths(lopper)

    if not os.path.isdir(lops_dir):
        raise Exception("The lopper 'lops' are missing.")

    embeddedsw = os.path.join(os.path.dirname(lopper_dir), 'share', 'embeddedsw')

    if not os.path.isdir(embeddedsw):
        raise Exception("The embeddedsw configuration files are missing.")

    return lopper, lopper_dir, lops_dir, embeddedsw

def startBitbake(disabled=False):
    global Bitbake
    if not Bitbake:
        Bitbake = bitbake(disabled=disabled)
        if not disabled:
            try:
                Bitbake.initialize()
            except Exception:
                logger.warning("Bitbake is not available, some functionality may be reduced.")
                Bitbake.shutdown()
                Bitbake.disabled = True
        else:
            logger.info("Bitbake is not available, some functionality may be reduced.")

class FetchError(Exception):
    """Fetch exception transfered from bitbake"""
    def __init__(self, message, url = None):
        if url:
            msg = "Fetcher failure for URL: '%s'. %s" % (url, message)
        else:
            msg = "Fetcher failure: %s" % message
        Exception.__init__(self, msg)
        self.args = (message, url)

class bitbake():
    disabled = False
    tinfoil = None
    tinfoilPrepared = False
    recipes_parsed = False
    prepare_args = None

    def __init__(self, config_only=False, prefile=[], disabled=False):
        if disabled:
            self.disabled = True
        else:
            try:
                import bb.tinfoil
            except Exception as e:
                self.disabled = True

        self.prepare_args = { 'config_only':config_only , 'prefile':prefile }

    def __del__(self):
        self.shutdown()

    # Typlical flow:
    #  initilize
    #  prepare
    #  parse_recipes (optional)
    #  getVar/setVar
    #
    # Bitbake commands:
    #  initialize
    #  prepare
    #  runBitbakeCmd
    #
    # Component Download:
    #  initialize
    #  prepare


    def initialize(self):
        if self.disabled:
            raise Exception("Bitbake is not available")

        self.tinfoil = bb.tinfoil.Tinfoil(tracking=False)
        self.tinfoilPrepared = False

    def shutdown(self):
        logger.debug('Shutting down bitbake')

        if self.tinfoil:
            # No recovery if we can't shutdown, just accept any exceptions
            try:
                self.tinfoil.shutdown()
            except:
                pass
            time.sleep(3)

        self.tinfoil = None
        self.tinfoilPrepared = False
        self.recipes_parsed = False
        # Do NOT reset prepare_args!

    def prepare(self, config_only=False, prefile=[]):
        logger.debug('Prepare bitbake')

        self.prepare_args = { 'config_only':config_only , 'prefile':prefile }

        if self.disabled:
            return

        if self.tinfoilPrepared == True:
            logger.info('Configuration change, restarting bitbake')
            self.shutdown()

        if not self.tinfoil:
            self.initialize()

        self.tinfoilConfig = bb.tinfoil.TinfoilConfigParameters(config_only=config_only, quiet=2, prefile=prefile)
        self.tinfoil.prepare(config_only=config_only, quiet=2, config_params=self.tinfoilConfig)
        self.tinfoilPrepared = True
        self.recipes_parsed = False

    def prepare_again(self):
        logger.debug('Prepare bitbake again (configuration change)')

        if self.disabled:
            return

        if self.prepare_args:
            self.prepare(config_only=self.prepare_args['config_only'], prefile=self.prepare_args['prefile'])
        else:
            self.prepare()

    def parse_recipes(self):
        logger.debug('Bitbake parsing recipes')

        if self.disabled:
            return

        if not self.tinfoilPrepared:
            self.prepare_again()
        if not self.recipes_parsed:
            # Emulate self.parse_recipes, but with our config
            #self.tinfoil.parse_recipes()
            # run_actions requires config_only set to False
            self.prepare_args['config_only'] = False
            self.tinfoilConfig = bb.tinfoil.TinfoilConfigParameters(config_only=self.prepare_args['config_only'], quiet=2, prefile=self.prepare_args['prefile'])
            try:
                self.tinfoil.run_actions(config_params=self.tinfoilConfig)
            except bb.tinfoil.TinfoilUIException as e:
                # Something went very wrong, shutdown bitbake and disable it
                self.shutdown()
                self.disabled = True
                raise Exception("Bitbake failed tinfoil.run_actions: %s" % e)
            self.tinfoil.recipes_parsed = True
            self.recipes_parsed = True

    def expand(self, variable, recipe=None):
       '''Return back the expanded values of bitbake variables with an optional recipe'''
       if self.disabled:
           return variable

       logger.debug('Expanding bitbake variable %s from %s' % (variable, recipe))

       d = None
       try:
           if recipe:
               if not self.recipes_parsed:
                   self.parse_recipes()
               d = self.tinfoil.parse_recipe(recipe)
           else:
               if not self.tinfoilPrepared:
                   self.prepare()
               d = self.tinfoil.config_data
       except:
           # Something went wrong in bitbake, we accept that and return 'variable'
           return variable
       return d.expand(variable)

    def getVar(self, variable, recipe=None):
      '''Return back the values of bitbake variables with an optional recipe'''
      if self.disabled:
          return None

      logger.debug('Getting bitbake variable %s from %s' % (variable, recipe))

      d = None
      try:
          if recipe:
              if not self.recipes_parsed:
                  self.parse_recipes()
              d = self.tinfoil.parse_recipe(recipe)
          else:
              if not self.tinfoilPrepared:
                  self.prepare()
              d = self.tinfoil.config_data
      except:
          # Something went wrong in bitbake, we accept that and return 'nothing'
          return None

      return d.getVar(variable)

    def setVar(self, variable, value):
        '''Set a bitbake variable. Note: this can NOT be used to set something that effects recipe parsing!'''
        logger.debug('Set bitbake variable %s to %s' % (variable, value))

        if self.disabled:
            return

        if not self.tinfoilPrepared:
            self.prepare()
        d = self.tinfoil.config_data

        d.setVar(variable, value)

    def runBitbakeCmd(self, recipe, task=None):
        '''Run a bitbake command.  Note there is a bug that the prefile isn't evaluated prior to parsing if parse_recipes has been run.'''
        '''This may require us to shutdown bitbake, and reconfigure WITHOUT recipe_parsed!'''
        logger.debug('Running bitbake recipe %s (task %s)' % (recipe, task))

        if self.disabled:
            raise Exception("Bitbake is unavailable to build task %s from recipe %s" % (task, recipe))

        return self.tinfoil.build_targets(recipe, task)

    def fetchAndUnpackURI(self, uri):
        ''' Use bb.fetch2.Fetch to download the specified URL's
        and unpack to TOPDIR/hw-description if bitbake found.'''
        if self.disabled:
            return Exception("Bitbake is unavailable to run fetch and download.")

        if os.path.exists(uri):
            # Add file:// prefix if its local file
            uri = 'file://%s' % os.path.abspath(uri)

        if not self.tinfoilPrepared:
            self.prepare_again()

        d = self.tinfoil.config_data
        localdata = d.createCopy()

        # BB_STRICT_CHECKSUM - To skip the checksum for network files
        localdata.setVar('BB_STRICT_CHECKSUM', 'ignore')
        # PREMIRRORS,MIRRORS - Skip fetching from MIRRORS
        #localdata.setVar('PREMIRRORS', '')
        #localdata.setVar('MIRRORS', '')
        try:
            fetcher = bb.fetch2.Fetch([uri], localdata)
            fetcher.download()

            # Unpack to hw-description
            hw_dir = os.path.join(localdata.getVar('TOPDIR'), '.hw-description')
            RemoveDir(hw_dir)
            CreateDir(hw_dir)
            fetcher.unpack(hw_dir)
        except bb.fetch2.FetchError as e:
            raise FetchError(message=e, url=uri)
        hw_dir_root = hw_dir
        # Get the S from url if exists, Helps if the specified path or url has multiple
        # SDT/XSA directories user can specify sub source directory. similar to
        # S variable in bb files.
        s_dir = ''
        localpath = ''
        for url in fetcher.urls:
            s_dir = fetcher.ud[url].parm.get('S') or ''
            localpath = fetcher.ud[url].localpath
            if url.startswith("file:///"):
                # If the file can't be unpacked or refers to a directory
                # then it will be in the same directory stucture as the
                # original file:// URL.  hw_dir = ${WORKDIR}
                base_sdir = os.path.dirname(uri[8:])
                maybe_s_dir = os.path.join(base_sdir, s_dir)
                if os.path.exists(os.path.join(hw_dir, maybe_s_dir)):
                    s_dir = maybe_s_dir
            elif url.startswith("git://"):
                s_dir = os.path.join('git', s_dir)

        if s_dir:
            hw_dir = os.path.join(hw_dir, s_dir)

        return hw_dir, hw_dir_root, uri, s_dir, localpath
