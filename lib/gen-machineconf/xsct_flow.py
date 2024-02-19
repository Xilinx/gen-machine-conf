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
import re
import project_config
import post_process_config
import rootfs_config
import yocto_machine
import plnx_machine
import update_buildconf
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

    def gatherHWInfo(hw_file):
        nonlocal Kconfig_syshw
        nonlocal plnx_syshw_file
        nonlocal project_cfgdir
        nonlocal genmachine_scripts

        hw_info = {}

        logger.info('Getting Platform info from HW file')

        if args.machine:
            logger.debug('Using the machine specified by user:%s' % args.machine)
            hw_info['machine'] = args.machine

        if args.soc_family:
            logger.debug('Using the soc_family specified by user:%s' % args.soc_family)
            hw_info['soc_family'] = args.soc_family

        if args.soc_variant:
            logger.debug('Using the soc_variant specified by user:%s' % args.soc_variant)
            hw_info['soc_variant'] = args.soc_variant

        # Generate Kconfig.syshw only when hw_file changes
        if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file) or \
            not os.path.exists(Kconfig_syshw):

            if not args.soc_family:
                hw_info['proc_type'] = GetSocInfo(args.hw_file)
                hw_info['soc_family'] = project_config.DetectSocFamily(hw_info['proc_type'])

            template_cfgfile = os.path.join(
                genmachine_scripts, 'configs', 'config_%s' % hw_info['soc_family'])

            if not os.path.isfile(template_cfgfile):
                raise Exception('Unsupported soc_family: %s' % hw_info['soc_family'])

            GenXsctSystemHwFile(genmachine_scripts, Kconfig_syshw,
                                args.hw_file, args.output)

        import yaml

        with open(plnx_syshw_file, 'r') as fp:
            syshw_data = yaml.safe_load(fp)

        if 'machine' not in hw_info:
            hw_info['machine'] = None

        hw_info['device_id'] = syshw_data['device_id']

        hw_info['model'] = ''

        processor = syshw_data['processor']
        if 'proc_type' not in hw_info:
            hw_info['proc_type'] = processor[list(processor.keys())[0]]['ip_name']
        if 'soc_family' not in hw_info:
            hw_info['soc_family'] = project_config.DetectSocFamily(hw_info['proc_type'])
        if 'soc_variant' not in hw_info:
            hw_info['soc_variant'] = project_config.DetectSocVariant(hw_info['device_id'])

        return hw_info


    #### Setup:

    AddXsctUtilsPath(args.xsct_tool)

    genmachine_scripts = project_config.GenMachineScriptsPath()

    project_cfgdir = os.path.join(args.output, 'configs')
    common_utils.CreateDir(project_cfgdir)

    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    system_conffile = os.path.join(args.output, 'config')


    #### Gather:
    hw_info = gatherHWInfo(args.hw_file)

    if hw_info['machine']:
        args.machine = hw_info['machine']
    args.soc_family = hw_info['soc_family']
    args.soc_variant = hw_info['soc_variant']

    project_config.PrintSystemConfiguration(args, None, hw_info['device_id'], None)

    #### Generate Kconfig:
    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False):
        # When multiple xsa/sdt files configured with same memory ip with different
        # size offsets mconf/conf will use the old configs instead of new
        # to fix that removing old MEMORY related configs from sysconfig
        # for the first time with every new XSA configured.
        common_utils.RemoveConfigs('CONFIG_SUBSYSTEM_MEMORY_', system_conffile)

    project_config.GenKconfigProj(args.soc_family, args.soc_variant,
                                  args.output, args.petalinux, system_conffile)
    # Update the sysconfig with command line arguments
    # to reflect in menuconfig/config
    project_config.PreProcessSysConf(args, system_conffile)
    common_utils.RunMenuconfig(Kconfig, system_conffile,
                               True if args.menuconfig == 'project' else False,
                               args.output, 'project')

    #### Process the configuration:
    post_process_config.PostProcessSysConf(
        args, system_conffile, ipinfo_file, plnx_syshw_file)

    # In case machine name updated in config
    cfg_machine = common_utils.GetConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                                     system_conffile)
    if cfg_machine:
        args.machine = cfg_machine

    if args.petalinux:
        GetFlashInfo(genmachine_scripts, args.output,
                     system_conffile, args.hw_file)
        rootfs_config.GenRootfsConfig(args, system_conffile)

    #### Generate the configuration:
    if args.petalinux:
        # Layers should be added before generating machine conf files
        update_buildconf.AddUserLayers(args)

    machine_conf_file = yocto_machine.GenerateYoctoMachine(
        args, system_conffile, plnx_syshw_file)

    update_buildconf.GenLocalConf(args.localconf,
                                machine_conf_file, None,
                                system_conffile, args.petalinux)

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

    parser_xsa.add_argument('-l', '--localconf', metavar='<config_file>',
                            help='Write local.conf changes to this file', type=os.path.realpath)

    parser_xsa.set_defaults(func=ParseXsa)
