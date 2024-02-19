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
import glob
import project_config
import post_process_config
import rootfs_config
import multiconfigs
import yocto_machine
import plnx_machine
import update_buildconf
import kconfig_syshw

logger = logging.getLogger('Gen-Machineconf')


def GetProcNameFromCpuInfo(cpuinfo_dict):
    for cpukey in cpuinfo_dict.keys():
        if re.findall('.*cortexa78.*|.*cortexa72.*|.*cortexa53.*|microblaze', cpukey):
            return cpukey


def CpuInfoToDict(cpu_info):
    cpu_info_dict = {}
    for _cpu in cpu_info.splitlines():
        if not _cpu.startswith('#') or _cpu.startswith('['):
            cpu, core, domain, cpu_name, os_hint = _cpu.split(' ', 4)
            # cpu_name is unique so using it as key
            cpu_info_dict[cpu_name] = {'cpu': cpu, 'core': core,
                                       'domain': domain, 'os_hint': os_hint}
    return cpu_info_dict


def GenSdtSystemHwFile(genmachine_scripts, Kconfig_syshw, proc_type, hw_file, output):
    logger.info('Generating Kconfig for the project')
    sdtipinfo_schema = os.path.join(
        genmachine_scripts, 'data', 'sdt_ipinfo.yaml')
    ipinfo_schema = os.path.join(
        genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(output, 'petalinux_config.yaml')

    multiconfigs.RunLopperSubcommand(output, output, hw_file,
                                     'petalinuxconfig_xlnx %s %s' % (proc_type,
                                                                     sdtipinfo_schema))
    logger.debug('Generating System HW file')
    kconfig_syshw.GenKconfigSysHW(plnx_syshw_file, ipinfo_schema, Kconfig_syshw)
    if not os.path.exists(Kconfig_syshw):
        raise Exception('Failed to Generate Kconfig_syshw File')


def ParseSDT(args):
    if args.hw_flow == 'xsct':
        raise Exception('Invalide HW source Specified for System-Device-Tree.')
    config_dtsdir = os.path.join(args.config_dir, 'dts')
    multiconfig_dir = os.path.join(args.config_dir, 'multiconfig')
    machine_include_dir = os.path.join(args.config_dir, 'machine', 'include')
    for dirpath in [multiconfig_dir, machine_include_dir]:
        common_utils.CreateDir(dirpath)

    logger.info('Getting Platform info from HW file')
    # Get machinefile name, device-id and model
    machine_info = multiconfigs.RunLopperUsingDomainFile(['lop-machine-name.dts'],
                                                         args.output, args.output,
                                                         args.hw_file, '')[0]
    local_machine_conf, device_id, model = machine_info.strip().split(' ', 2)

    if not args.machine:
        args.machine = local_machine_conf

    if not args.psu_init_path:
        args.psu_init_path = args.hw_description

    # Update FPGA path
    if not args.fpga:
        args.fpga = os.path.dirname(args.hw_file)

    # Generate CPU list
    cpu_info = multiconfigs.RunLopperUsingDomainFile(['lop-xilinx-id-cpus.dts'],
                                                     args.output, args.output,
                                                     args.hw_file, '')[0]
    cpu_info_dict = CpuInfoToDict(cpu_info)

    # Get proc name
    proc_type = GetProcNameFromCpuInfo(cpu_info_dict)
    if not args.soc_family:
        args.soc_family = project_config.DetectSocFamily(proc_type)
    else:
        logger.debug('Using the soc_family specified by user:%s' % args.soc_family)

    if not args.soc_variant:
        args.soc_variant = project_config.DetectSocVariant(device_id)
    else:
        logger.debug('Using the soc_variant specified by user:%s' % args.soc_variant)

    MCObject = multiconfigs.CreateMultiConfigFiles(
        args, cpu_info_dict, file_names_only=True)
    multiconfig_targets, multiconfig_min = MCObject.ParseCpuDict()

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
    plnx_syshw_file = os.path.join(args.output, 'petalinux_config.yaml')
    system_conffile = os.path.join(args.output, 'config')

    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False):
        # When multiple xsa/sdt files configured with same memory ip with different
        # size offsets mconf/conf will use the old configs instead of new
        # to fix that removing old MEMORY related configs from sysconfig
        # for the first time with every new XSA configured.
        common_utils.RemoveConfigs('CONFIG_SUBSYSTEM_MEMORY_', system_conffile)

    project_config.PrintSystemConfiguration(args, model, device_id, cpu_info_dict)

    # Generate Kconfig.syshw only when hw_file changes
    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file) or \
            not os.path.exists(Kconfig_syshw):
        GenSdtSystemHwFile(genmachine_scripts, Kconfig_syshw,
                           proc_type, args.hw_file, args.output)
    
    project_config.GenKconfigProj(args.soc_family, args.soc_variant,
                                  args.output, args.petalinux, system_conffile,
                                  multiconfig_targets, multiconfig_min)

    # Update the sysconfig with command line arguments
    # to reflect in menuconfig/config
    project_config.PreProcessSysConf(args, system_conffile, multiconfig_targets)
    common_utils.RunMenuconfig(Kconfig, system_conffile,
                               True if args.menuconfig == 'project' else False,
                               args.output, 'project')
    post_process_config.PostProcessSysConf(
        args, system_conffile, ipinfo_file, plnx_syshw_file)
    # In case machine name updated in config
    cfg_machine = common_utils.GetConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                                     system_conffile)
    if cfg_machine:
        args.machine = cfg_machine
    # In case dts_path updated in config
    cfg_dtspath = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DT_XSCT_WORKSPACE',
                                                     system_conffile)
    if cfg_dtspath:
        args.dts_path = os.path.expandvars(cfg_dtspath)
    else:
        args.dts_path = args.machine
    
    if not os.path.isabs(args.dts_path):
        args.dts_path = os.path.join(config_dtsdir, args.dts_path)
    else:
        args.dts_path = os.path.realpath(args.dts_path)


    if args.petalinux:
        rootfs_config.GenRootfsConfig(args, system_conffile)

    MultiConfDict = {}
    GenMultiConf = True
    # Dont re-trigger the multiconfigs if no changes in project file
    if common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False) and \
            common_utils.ValidateHashFile(args.output, 'SYSTEM_CONF', system_conffile, update=False) and \
            os.path.exists(args.dts_path) and \
            os.path.exists(plnx_syshw_file):
        GenMultiConf = False
    
    args.bbconf_dir = os.path.join(machine_include_dir, args.machine)
    common_utils.CreateDir(args.bbconf_dir)
    common_utils.CreateDir(args.dts_path)
    if GenMultiConf:
        MCObject = multiconfigs.CreateMultiConfigFiles(args, cpu_info_dict,
                                                       system_conffile=system_conffile)
        MultiConfDict = MCObject.ParseCpuDict()

    if args.petalinux:
        # Layers should be added before generating machine conf files
        update_buildconf.AddUserLayers(args)

    machine_conf_file = yocto_machine.GenerateYoctoMachine(
        args, system_conffile, plnx_syshw_file, MultiConfDict)

    update_buildconf.GenSdtConf(args.localconf,
                                machine_conf_file, multiconfig_targets,
                                system_conffile, args.petalinux)

    if args.petalinux:
        plnx_conf_file = plnx_machine.GeneratePlnxConfig(
            args, machine_conf_file)
        update_buildconf.UpdateLocalConf(
            args, plnx_conf_file, machine_conf_file)


def register_commands(subparsers):
    parser_sdt = subparsers.add_parser('parse-sdt',
                                       help='Parse System devicet-tree file and generate Yocto/PetaLinux configurations.',
                                       usage='%(prog)s [--hw-description'
                                       ' <PATH_TO_SDTDIR>] [other options]'
                                       )
    parser_sdt.add_argument('-g', '--gen-pl-overlay', choices=['full', 'dfx'],
                            help='Generate pl overlay for full, dfx configuration using xlnx_overlay_dt lopper script')
    parser_sdt.add_argument('-d', '--domain-file', metavar='<domain_file>',
                            help='Path to domain file (.yaml/.dts)', type=os.path.realpath)
    parser_sdt.add_argument('-p', '--psu-init-path', metavar='<psu_init_path>',
                            help='Path to psu_init files, defaults to system_dts path', type=os.path.realpath)
    parser_sdt.add_argument('-i', '--fpga', metavar='<pdi path>',
                            help='Path to pdi file', type=os.path.realpath)
    parser_sdt.add_argument('-l', '--localconf', metavar='<config_file>',
                            help='Write local.conf changes to this file', type=os.path.realpath)
    parser_sdt.add_argument('--multiconfigfull', action='store_true',
                            help='Generate/Enable Full set of multiconfig .conf and .dts files. Default is minimal)')
    parser_sdt.add_argument('--dts-path', metavar='<dts_path>',
                            help='Absolute path or subdirectory of conf/dts to place DTS files in (usually auto detected from DTS)')

    parser_sdt.set_defaults(func=ParseSDT)
