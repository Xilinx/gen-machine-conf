#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import argparse
import os
import logging
import importlib.machinery
import importlib.util
import glob
import subprocess
import shutil
import re
import time
import yaml_utils
import bitbake_utils

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


def ExpandFilePath(filepath):
    '''Expand environment variables, bitbake variables and resolve to real path.'''
    filepath = os.path.expandvars(filepath)
    filepath = bitbake_utils.Bitbake.expand(filepath)
    filepath = os.path.realpath(filepath)
    return filepath


def RunCmd(command, out_dir, extraenv=None,
           failed_msg='External command failed', shell=False, checkcall=False):
    '''Run Shell commands from python'''
    command = command.split() if not shell else command
    logger.debug('Command: %s' % command)
    env = os.environ.copy()
    if extraenv:
        for k in extraenv:
            env[k] = extraenv[k]
    if checkcall:
        subprocess.check_call(
            command, env=env, cwd=out_dir, shell=shell)
        return
    else:
        try:
            process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env, shell=shell,
                                   executable='/bin/bash',
                                   cwd=out_dir)

            stdout, stderr = process.communicate()

            if not stdout is None:
                stdout = stdout.decode("utf-8")
            if not stderr is None:
                stderr = stderr.decode("utf-8")

            rc = process.returncode

            logger.debug('\nstdout: %s\nstderr: %s\nrc: %s\n' % (stdout or "(blank)", stderr or "(blank)", rc))
        except FileNotFoundError:
            raise Exception('File Not Found: env:%s\ncommand: %s' %
                            (env,
                             command))

        if rc != 0:
            raise Exception('%s\nenv:%s\ncommand: %s\nstdout: %s\nstderr: %s\nrc: %s\n' %
                            (failed_msg,
                             env,
                             command,
                             stdout or "(blank)",
                             stderr or "(blank)",
                             rc))

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
        try:
            for entry in os.listdir(os.path.join(native_sysroot, 'usr', 'bin')):
                special_bin_dir = os.path.join(native_sysroot, 'usr', 'bin', entry)
                if os.path.isdir(special_bin_dir) and entry.endswith('-native') and entry != 'python3-native':
                    os.environ["PATH"] = special_bin_dir + os.pathsep + os.environ['PATH']
        except FileNotFoundError as e:
            logger.warning('Expected directory or file not found: %s' % (str(e)))

        for bindir in ['sbin', 'usr/sbin', 'bin', 'usr/bin']:
            add_path = os.path.join(native_sysroot, bindir)
            # Skip paths already in the PATH
            if add_path in os.environ["PATH"].split(':'):
                continue
            os.environ["PATH"] = add_path + os.pathsep + os.environ['PATH']

    logger.debug("PATH=%s" % os.environ["PATH"])

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

    with open(filename, 'w') as file_data:
        for line in lines:
            if re.search('# %s is not set' % macro, line) or re.search('%s=' % macro, line):
                continue
            file_data.write(line)
        if value == 'disable':
            file_data.write('# %s is not set\n' % macro)
        else:
            file_data.write('%s=%s\n' % (macro, value))


def RemoveConfigs(macro, filename):
    # Remove configs from file if given macro match
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
    with open(filename, 'w') as file_data:
        for line in lines:
            if line.startswith(macro):
                continue
            file_data.write(line)


def GetConfigValue(macro, filename, Type='bool', end_macro='=y'):
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
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
    if not failed_msg:
        if recipe:
            failed_msg = "The tool %s is required but not found.  This is usually built with the bitbake target of %s." % (tool, recipe)
            if bitbake_utils.Bitbake.disabled:
                failed_msg += "  However, bitbake is unavailable."
        else:
            failed_msg = "The tool %s is required but not found.  You may have to install this tool into your environment." % (tool)
    tool = tool.lower()
    if skip_path:
        tool_path = ''
    else:
        tool_path = shutil.which(tool)
    if not tool_path:
        if recipe:
            try:
                bitbake_utils.FindNativeSysroot(recipe)
            except Exception as e:
                failed_msg += "\n" + str(e)

        tool_path = shutil.which(tool)
        if not tool_path:
            raise Exception(failed_msg)
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
        with open(fpath, encoding='utf-8') as f:
            s = f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 encoding which can handle any byte sequence
        try:
            with open(fpath, encoding='latin-1') as f:
                s = f.read()
        except Exception as e:
            logger.warning(f"Failed to read file {fpath}: {e}")
            return

    s = s.replace(search_str, replace_str)

    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(s)
    except UnicodeEncodeError:
        # Write with the same encoding we successfully read with
        with open(fpath, 'w', encoding='latin-1') as f:
            f.write(s)


def AddStrToFile(filename, string, mode='w'):
    '''Add string or line into the given file '''
    with open(filename, mode) as file_f:
        file_f.write(string)


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
    lopper_err_msg  = "Be sure that meta-virtualization, meta-xilinx-core, and meta-xilinx-standalone "
    lopper_err_msg += "(and their dependencies) are part of your build configuration.  This may also "
    lopper_err_msg += "mean your build's tmp directory is corrupted.  Often removing it will fix the issue."

    if bitbake_utils.Bitbake.disabled:
        lopper_err_msg = "Bitbake is unavailable to build lopper and related components."

    try:
        lopper = check_tool('lopper', 'esw-conf-native', "The tool lopper is required but not found.  This is usually built as a dependency to the bitbake target of esw-conf-native.")
    except Exception as e:
        if not bitbake_utils.Bitbake.disabled:
            raise Exception(str(e) + "  " + lopper_err_msg)
        else:
            raise e

    lopper, lopper_dir, lops_dir, embeddedsw = CheckLopperUtilsPaths(lopper)

    '''Check if lopper from PATH have all required directories, if not construct the sysroot'''
    if (lops_dir and not os.path.isdir(lops_dir)) or (embeddedsw and not os.path.isdir(embeddedsw)):
        logger.warning("The lopper 'lops' or 'embeddedsw configuration' files in your path are not correct, Trying to get recipe sysroot using bitbake.")
        try:
            lopper = check_tool('lopper', 'esw-conf-native', lopper_err_msg, skip_path=True)
        except Exception as e:
            if not bitbake_utils.Bitbake.disabled:
                raise Exception(str(e) + "  " + lopper_err_msg)
            else:
                raise e
        lopper, lopper_dir, lops_dir, embeddedsw = CheckLopperUtilsPaths(lopper)

    if (lops_dir and not os.path.isdir(lops_dir)):
        raise Exception("The lopper 'lops'  in your path is not correct.  " + lopper_err_msg)

    embeddedsw = os.path.join(os.path.dirname(lopper_dir), 'share', 'embeddedsw')

    if embeddedsw and not os.path.isdir(embeddedsw):
        raise Exception("The esw-conf configuration files are missing.  " + lopper_err_msg)

    return lopper, lopper_dir, lops_dir, embeddedsw
