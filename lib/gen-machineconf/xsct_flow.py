#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
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

logger = logging.getLogger('Gen-Machineconf')


def AddXsctUtilsPath(xsct_tool):
    if xsct_tool:
        if not os.path.isdir(xsct_tool):
            logger.error('XSCT_TOOL path not found: %s' % xsct_tool)
            sys.exit(255)
        else:
            os.environ["PATH"] += os.pathsep + os.path.join(xsct_tool, 'bin')
    else:
        common_utils.check_tool('bitbake',
                                'No --xsct-tool specified or bitbake command found '
                                'to get XILINX_SDK_TOOLCHAIN')
        command = "bitbake -e"
        logger.info('Getting XILINX_SDK_TOOLCHAIN path...')
        stdout, stderr = common_utils.RunCmd(
            command, os.getcwd(), shell=True)
        xilinx_xsct_tool = ''
        for line in stdout.splitlines():
            try:
                line = line.decode('utf-8')
            except AttributeError:
                pass
            if line.startswith('XILINX_SDK_TOOLCHAIN'):
                xilinx_xsct_tool = line.split('=')[1].replace('"', '')
        if xilinx_xsct_tool and not os.path.isdir(xilinx_xsct_tool):
            logger.error('XILINX_SDK_TOOLCHAIN set to "%s" is doesn\'t exists'
                         ' please set a valid one, or' % xilinx_xsct_tool)
            logger.error(
                'Use --xsct-tool option to specify the SDK_XSCT path')
            sys.exit(255)
        elif xilinx_xsct_tool:
            os.environ["PATH"] += os.pathsep + xilinx_xsct_tool + '/bin'

    xsct_exe = shutil.which('xsct')
    if not xsct_exe:
        logger.error('xsct command not found')
        sys.exit(255)
    else:
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
        logger.error('Failed to Generate Kconfig_syshw File')
        sys.exit(255)


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
        logger.error('Invalide HW source Specified for XSCT Flow.')
        sys.exit(255)
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
        logger.error('Unsupported soc_family: %s' % args.soc_family)
        sys.exit(255)

    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')

    # Generate Kconfig.syshw only when hw_file changes
    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file) or \
            not os.path.exists(Kconfig_syshw):
        GenXsctSystemHwFile(genmachine_scripts, Kconfig_syshw,
                            args.hw_file, args.output)
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    system_conffile = os.path.join(args.output, 'config')
    
    if not args.soc_variant:
        device_id = GetDeviceId(plnx_syshw_file)
        args.soc_variant = project_config.DetectSocVariant(device_id)
    else:
        logger.debug('Using the soc_variant specified by user:%s' % args.soc_variant)

    project_config.GenKconfigProj(args.soc_family, args.soc_variant,
                                  args.output, system_conffile)
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

    machine_conf_file = yocto_machine.GenerateYoctoMachine(
        args, system_conffile, plnx_syshw_file)
    if args.petalinux:
        plnx_conf_file = plnx_machine.GeneratePlnxConfig(
            args, machine_conf_file)
        update_buildconf.AddUserLayers(args)
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