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
            logger.error('Unable to create directory at %s' % dirpath)
            sys.exit(255)


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
    if check_tool('mconf') and check_tool('conf'):
        pass
    elif native_sysroot:
        if not os.path.isdir(native_sysroot):
            logger.error('Native sysroot path doesnot exists: %s'
                         % native_sysroot)
            sys.exit(255)
        else:
            for bindir in ['bin', 'sbin', os.path.join('usr', 'bin'), os.path.join('usr', 'sbin')]:
                os.environ["PATH"] = os.path.join(
                    native_sysroot, bindir) + os.pathsep + os.environ['PATH']
    else:
        mconf_provides = "kconfig-frontends-native"
        if not check_tool('bitbake',
                   'No --native-sysroot specified or bitbake command found '
                   'to get kconfig-frontends sysroot path'):
            sys.exit(255)
        command = "bitbake -e %s" % (mconf_provides)
        logger.info('Getting kconfig-frontends sysroot path...')
        stdout, stderr = RunCmd(command, os.getcwd(), shell=True)
        sysroot_path = ''
        sysroot_destdir = ''
        staging_bindir_native = ''
        native_package_path_suffix = ''
        for line in stdout.splitlines():
            if line.startswith('SYSROOT_DESTDIR'):
                sysroot_destdir = line.split('=')[1].replace('"', '')
            elif line.startswith('STAGING_BINDIR_NATIVE'):
                staging_bindir_native = line.split('=')[1].replace('"', '')
            elif line.startswith('NATIVE_PACKAGE_PATH_SUFFIX'):
                native_package_path_suffix = line.split(
                    '=')[1].replace('"', '')
        sysroot_path = '%s%s%s' % (sysroot_destdir, staging_bindir_native,
                                   native_package_path_suffix)
        scripts = ['mconf', 'conf']
        not_found = False
        for script in scripts:
            if not os.path.isfile(os.path.join(sysroot_path, script)):
                not_found = True
            elif os.path.isfile(os.path.join(sysroot_path, script)) and not \
                    os.access(os.path.join(sysroot_path, script), os.X_OK):
                not_found = True
        if not_found:
            logger.debug('INFO: Running CMD: bitbake %s' % mconf_provides)
            subprocess.check_call(["bitbake", mconf_provides])
        os.environ["PATH"] += os.pathsep + sysroot_path

    conf_exe = shutil.which('mconf')
    if not conf_exe:
        logger.error('mconf/conf command not found')
        sys.exit(255)
    else:
        logger.debug('Using conf/mconf from : %s' % conf_exe)


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


def check_tool(tool, failed_msg=None):
    '''Check the tool exists in PATH variable'''
    tool = tool.lower()
    tool_path = shutil.which(tool)
    if not tool_path:
        if failed_msg:
            logger.error(failed_msg)
        return None
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


def GetLopperUtilsPath():
    lopper = check_tool('lopper',
                   'Unable to find find lopper, please source the prestep '
                   'environment to get lopper sysroot path. See README-setup '
                   'in meta-xilinx layer for more details.')
    if not lopper:
        sys.exit(255)
    lopper_dir = os.path.dirname(lopper)
    lops_dir = glob.glob(os.path.join(os.path.dirname(lopper_dir),
                                      'lib', 'python*', 'site-packages', 'lopper', 'lops'))[0]
    embeddedsw = os.path.join(os.path.dirname(
        lopper_dir), 'share', 'embeddedsw')

    return lopper, lopper_dir, lops_dir, embeddedsw
