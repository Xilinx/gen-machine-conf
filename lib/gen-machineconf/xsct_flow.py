#!/usr/bin/env python3

# Copyright (C) 2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import logging
import os
import common_utils
import sys
import shutil
import project_config
import post_process_config
import rootfs_config
import plnx_machine
import yocto_machine
import update_buildconf
import re
import subprocess

logger = logging.getLogger('Gen-Machineconf')


def AddXsctUtilsPath(xsct_tool):
    if xsct_tool:
        if not os.path.isdir(xsct_tool):
            raise Exception('XSCT_TOOL path not found: %s' % xsct_tool)
        else:
            os.environ["PATH"] += os.pathsep + os.path.join(xsct_tool, 'bin')
    else:
        if not common_utils.HaveBitbake():
            raise Exception('No --xsct-tool specified or bitbake command found '
                         'to get XILINX_SDK_TOOLCHAIN')

        try:
            xilinx_xsct_tool = common_utils.GetBitbakeVars(['XILINX_SDK_TOOLCHAIN'])['XILINX_SDK_TOOLCHAIN']
        except KeyError:
            raise Exception('Unable to get XILINX_SDK_TOOLCHAIN path, please verify meta-xilinx-tools layer is available.')

        if xilinx_xsct_tool and not os.path.isdir(xilinx_xsct_tool):
            logger.info('Installing xsct...')
            common_utils.RunBitbakeCmd('xsct-native')

        if xilinx_xsct_tool and not os.path.isdir(xilinx_xsct_tool):
            raise Exception('Looking for xsct in "%s" but the path does not exist. '
                         'Use --xsct-tool option to specify the SDK_XSCT path' % xilinx_xsct_tool)
        elif xilinx_xsct_tool:
            os.environ["PATH"] += os.pathsep + xilinx_xsct_tool + '/bin'

    xsct_exe = common_utils.check_tool('xsct', None, 'xsct command not found')
    logger.debug('Using xsct from : %s' % xsct_exe)


def GetSocInfo(hw_file):
    genmachine_scripts = project_config.GenMachineScriptsPath()
    cmd = 'xsct -sdx -nodisp %s get_soc_info %s' % \
        (os.path.join(genmachine_scripts, 'hw-description.tcl'),
         hw_file)

    stdout, stderr = common_utils.RunCmd(cmd, os.getcwd(), shell=True)
    proc_type = ''
    for line in stdout.splitlines():
        try:
            line = line.decode('utf-8')
        except AttributeError:
            pass
        if re.search('{.+proc_name.+}', line):
            import json
            line_dict = json.loads(line)
            proc_type = line_dict['proc_name']
    return proc_type


def GetDeviceId(plnx_syshw_file):
    device_id = ''
    with open(plnx_syshw_file, 'r') as fp:
        lines = fp.readlines()
        for line in lines:
            if line.startswith('device_id:'):
                device_id = line.split(':')[1]
                break
    return device_id.strip()


def GenXsctSystemHwFile(genmachine_scripts,
                        Kconfig_syshw, hw_file, output):
    logger.info('Generating Kconfig for project')
    cmd = 'xsct -sdx -nodisp %s/hw-description.tcl plnx_gen_hwsysconf %s %s' % \
        (genmachine_scripts, hw_file, Kconfig_syshw)
    logger.debug('Generating System HW file')
    common_utils.RunCmd(cmd, output, shell=True)
    if not os.path.exists(Kconfig_syshw):
        raise Exception('Failed to Generate Kconfig_syshw File')


def GetFlashInfo(genmachine_scripts, output, system_conffile, hw_file):
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    flashinfo_file = os.path.join(output, 'flash_parts.txt')
    # No need to run if system conf file(config) is doesnot change
    if common_utils.ValidateHashFile(output, 'SYSTEM_CONF', system_conffile, update=False) and \
            os.path.exists(flashinfo_file):
        return 0

    with open(flashinfo_file, 'w') as fp:
        pass
    cmd = 'xsct -sdx -nodisp %s get_flash_width_parts %s %s %s %s' % \
        (os.path.join(genmachine_scripts, 'petalinux_hsm.tcl'),
         system_conffile, ipinfo_file, hw_file,
         flashinfo_file)
    common_utils.RunCmd(cmd, output, shell=True)


def ParseXsa(args):
    if args.hw_flow == 'sdt':
        raise Exception('Invalide HW source Specified for XSCT Flow.')
    AddXsctUtilsPath(args.xsct_tool)
    if not args.soc_family:
        logger.info('Getting Platform info from HW file')
        proc_type = GetSocInfo(args.hw_file)
        args.soc_family = project_config.DetectSocFamily(proc_type)
    else:
        logger.debug('Using the soc_family specified by user:%s' % args.soc_family)
    
    genmachine_scripts = project_config.GenMachineScriptsPath()

    project_cfgdir = os.path.join(args.output, 'configs')
    common_utils.CreateDir(project_cfgdir)
    template_cfgfile = os.path.join(
        genmachine_scripts, 'configs', 'config_%s' % args.soc_family)

    if not os.path.isfile(template_cfgfile):
        raise Exception('Unsupported soc_family: %s' % args.soc_family)

    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    system_conffile = os.path.join(args.output, 'config')

    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False):
        # When multiple xsa/sdt files configured with same memory ip with different
        # size offsets mconf/conf will use the old configs instead of new
        # to fix that removing old MEMORY related configs from sysconfig
        # for the first time with every new XSA configured.
        common_utils.RemoveConfigs('CONFIG_SUBSYSTEM_MEMORY_', system_conffile)

    # Generate Kconfig.syshw only when hw_file changes
    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file) or \
            not os.path.exists(Kconfig_syshw):
        GenXsctSystemHwFile(genmachine_scripts, Kconfig_syshw,
                            args.hw_file, args.output)

    if not args.soc_variant:
        device_id = GetDeviceId(plnx_syshw_file)
        args.soc_variant = project_config.DetectSocVariant(device_id)
    else:
        logger.debug('Using the soc_variant specified by user:%s' % args.soc_variant)

    project_config.GenKconfigProj(args.soc_family, args.soc_variant,
                                  args.output, args.petalinux, system_conffile)
    # Update the sysconfig with command line arguments
    # to reflect in menuconfig/config
    project_config.PreProcessSysConf(args, system_conffile)
    common_utils.RunMenuconfig(Kconfig, system_conffile,
                               True if args.menuconfig == 'project' else False,
                               args.output, 'project')
    post_process_config.PostProcessSysConf(
        args, system_conffile, ipinfo_file, plnx_syshw_file)

    if args.petalinux:
        GetFlashInfo(genmachine_scripts, args.output,
                     system_conffile, args.hw_file)
        rootfs_config.GenRootfsConfig(args, system_conffile)

    if args.petalinux:
        # Layers should be added before generating machine conf files
        update_buildconf.AddUserLayers(args)

    machine_conf_file = yocto_machine.GenerateYoctoMachine(
        args, system_conffile, plnx_syshw_file)
    if args.petalinux:
        plnx_conf_file = plnx_machine.GeneratePlnxConfig(
            args, machine_conf_file)
        update_buildconf.UpdateLocalConf(
            args, plnx_conf_file, machine_conf_file)


def register_commands(subparsers):
    parser_xsa = subparsers.add_parser('parse-xsa',
                                       help='Parse xsa file and generate Yocto/PetaLinux configurations.',
                                       usage='%(prog)s [--hw-description'
                                       ' <PATH_TO_XSA>/<xsa_name>.xsa] [other options]'
                                       )
    parser_xsa.add_argument('--xsct-tool', metavar='[XSCT_TOOL_PATH]',
                            help='Vivado or Vitis XSCT path to use xsct commands')

    parser_xsa.set_defaults(func=ParseXsa)
