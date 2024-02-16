#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

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

logger = logging.getLogger('Gen-Machineconf')


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
        runCmd(copycmd, os.getcwd(), shell=True)


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

    try:
        recipe_staging_dir = GetBitbakeVars(['STAGING_DIR_NATIVE'], recipe)['STAGING_DIR_NATIVE']
    except TypeError:
        recipe_staging_dir = None
    except KeyError:
        recipe_staging_dir = None
    except Exception as e:
        raise Exception("Unable to get required sysroot path.\n%s" % e)

    if not recipe_staging_dir:
        raise Exception("Unable to get required %s sysroot path" % recipe)

    if not os.path.exists(recipe_staging_dir):
        # Make sure the sysroot is available to us
        logger.info('Constructing %s recipe sysroot...' % recipe)

        RunBitbakeCmd(recipe, "addto_recipe_sysroot")

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


def check_tool(tool, recipe=None, failed_msg=None):
    '''Check the tool exists in PATH variable'''
    tool = tool.lower()
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


def GetLopperUtilsPath():
    lopper = check_tool('lopper',
                   'esw-conf-native',
                   'Unable to find lopper, please ensure this is in your '
                   'environment or lopper can be built by bitbake. See README-setup '
                   'in meta-xilinx layer for more details.')

    lopper_dir = os.path.dirname(lopper)
    lops_dir = glob.glob(os.path.join(os.path.dirname(lopper_dir),
                                      'lib', 'python*', 'site-packages', 'lopper', 'lops'))[0]
    if not os.path.isdir(lops_dir):
        raise Exception("The lopper 'lops' are missing.")

    embeddedsw = os.path.join(os.path.dirname(
        lopper_dir), 'share', 'embeddedsw')

    if not os.path.isdir(embeddedsw):
        raise Exception("The embeddedsw configuration files are missing.")

    return lopper, lopper_dir, lops_dir, embeddedsw


def HaveBitbake():
    '''If bitbake is available, return True'''

    if HaveBitbake.have_bitbake == None:
        # Check if we can load bitbake, if so we can augment the plugin path
        HaveBitbake.have_bitbake = False
        try:
            import bb.tinfoil
            HaveBitbake.have_bitbake = True
        except:
            pass

    return HaveBitbake.have_bitbake

def InitBitbake(recipes=False):
    '''Initialize Bitbake (tinfoil) for use as a helper tool, you must shutodwn after you are done!'''
    logger.debug('Initialize tinfoil...')

    if HaveBitbake():
        if not HaveBitbake.tinfoil:
            HaveBitbake.tinfoil = bb.tinfoil.Tinfoil(tracking=False)
            HaveBitbake.tinfoil.prepare(config_only=not recipes, quiet=2)
            HaveBitbake.tinfoil_recipe = recipes
        else:
            if recipes and HaveBitbake.tinfoil_recipe == False:
                HaveBitbake.tinfoil.parse_recipes()
                HaveBitbake.tinfoil_recipe = True

# Default
HaveBitbake.have_bitbake = None

HaveBitbake.tinfoil = None
HaveBitbake.tinfoil_recipe = False

def GetBitbakeVars(variables, recipe=None):
    '''Return back the values of bitbake variables with an optional recipe'''
    logger.debug('Getting bitbake variables %s' % ' '.join(variables))

    if not HaveBitbake():
        logger.debug('No bitbake found skip getting %s' % ''.join(variables))
        if isinstance(variables, dict):
            return {}
        else:
            return None

    result = None
    if recipe:
        InitBitbake(True)
        d = HaveBitbake.tinfoil.parse_recipe(recipe)
    else:
        InitBitbake(False)
        d = HaveBitbake.tinfoil.config_data

    if isinstance(variables, list):
        result = {}
        for each_var in variables:
            result[each_var] = d.getVar(each_var)
    else:
        result = d.getVar(variables)

    # How to process a recipe specific variable?
    return result

def RunBitbakeCmd(recipe, task=None):
    '''Return back the values of bitbake variables with an optional recipe'''
    logger.debug('Building %s and task %s' % (recipe, task))

    if not HaveBitbake():
        raise Exception('No bitbake found cannot build %s' % ''.join(recipe))

    InitBitbake(True)

    return HaveBitbake.tinfoil.build_targets(recipe, task)

def ShutdownBitbake():
    if HaveBitbake() and HaveBitbake.tinfoil:
        HaveBitbake.tinfoil.shutdown()
        HaveBitbake.tinfoil = None
        HaveBitbake.tinfoil_recipe = False
