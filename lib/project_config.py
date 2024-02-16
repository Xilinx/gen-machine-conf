#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT


import os
import re
import yaml
import common_utils
import logging
import glob

logger = logging.getLogger('Gen-Machineconf')


start_menu = '''
mainmenu "PetaLinux System Configuration"
config SUBSYSTEM_TYPE_LINUX
        bool
        default y
        select SYSTEM_{0}

config SYSTEM_{0}
        bool "{0} Configuration"
        help
          {0} Configuration for petalinux project.
          All these config options will be in {1}/config
'''

socvariant_menu = '''
config SUBSYSTEM_VARIANT_{0}{1}
        bool
        default y
        help
'''

Kconfig_sdt = '''
config SUBSYSTEM_SDT_FLOW
        bool
        default y
        help
'''

Kconfig_plnx = '''
config SUBSYSTEM_DISTRO_PETALINUX
        bool
        default y
        help
'''

Kconfig_multitarget = '''
config YOCTO_BBMC_{0}
        bool "{1}"
        default {2}
'''

SocVariantDict = {
    'zynqmp': {'xczu.+cg': 'cg', 'xczu.+dr': 'dr', 'xczu.+eg': 'eg',
               'xczu.+ev': 'ev', 'xck26': 'ev', 'xck24': 'eg'},
    'versal': {'xcvm.+': 'prime', 'xcvc.+': 'ai-core', 'xcve.+': 'ai-edge',
               'xcvn.+': 'net', 'xcvp.+': 'premium', 'xcvh.+': 'hbm'
               }
}


def DetectSocVariant(device_id):
    soc_variant = ''
    for platform in SocVariantDict.keys():
        for id_fromdict in SocVariantDict[platform].keys():
            if re.search(id_fromdict, device_id):
                soc_variant = SocVariantDict[platform][id_fromdict]
    return soc_variant


def DetectSocFamily(proc_type):
    soc_family = ''
    if re.search('.*a78.*', proc_type) or re.search('.*a72.*', proc_type):
        return 'versal'
    elif re.search('.*a53.*', proc_type):
        return 'zynqmp'
    elif re.search('.*a9.*', proc_type):
        return 'zynq'
    elif re.search('microblaze', proc_type):
        return 'microblaze'
    return proc_type


def GenMachineScriptsPath():
    scriptpath = os.path.dirname(__file__)
    genscriptspath = os.path.join(os.path.dirname(scriptpath),
                                  'gen-machine-scripts')
    return genscriptspath


def ConvertMCTargetsToKconfig(bbmctargets, multiconfig_min):
    multiconfig_str = 'menu "Multiconfig Targets"'
    for target in bbmctargets:
        enable = 'n'
        if target in multiconfig_min:
            enable = 'y'
        multiconfig_str += Kconfig_multitarget.format(
            target.upper().replace('-', '_'), target, enable)
    multiconfig_str += 'endmenu'
    return multiconfig_str


def GenKconfigProj(soc_family, soc_variant, output, petalinux,
                   system_conffile, bbmctargets='', multiconfig_min=''):
    genmachine_scripts = GenMachineScriptsPath()
    project_cfgdir = os.path.join(output, 'configs')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    template_cfgfile = os.path.join(
        genmachine_scripts, 'configs/config_%s' % soc_family)
    Kconfig_files = glob.glob(os.path.join(
                        genmachine_scripts, 'configs', 'Kconfig.*'))

    if not os.path.isfile(Kconfig_syshw):
        raise Exception('%s is not found in tool' % file_path)

    if not os.path.isfile(system_conffile):
        common_utils.CopyFile(template_cfgfile, system_conffile)

    Kconfig_BBMCTargets = ''
    if bbmctargets:
        Kconfig_BBMCTargets = ConvertMCTargetsToKconfig(
            bbmctargets, multiconfig_min)

    for Kconfig_file in Kconfig_files:
        common_utils.CopyFile(Kconfig_file, project_cfgdir)
        common_utils.ReplaceStrFromFile(
                    os.path.join(project_cfgdir, os.path.basename(Kconfig_file)),
                    'source ./Kconfig.', 'source %s/Kconfig.' % project_cfgdir)
        common_utils.ReplaceStrFromFile(
                    os.path.join(project_cfgdir, os.path.basename(Kconfig_file)),
                    '@@multiconfigmenustr@@', Kconfig_BBMCTargets)

    Kconfig_soc_family = soc_family.upper()
    Kconfig_str = start_menu.format(Kconfig_soc_family, output)
    if soc_variant:
        Kconfig_soc_variant = soc_variant.upper()
        Kconfig_str += socvariant_menu.format(
            Kconfig_soc_family, Kconfig_soc_variant)
    if Kconfig_BBMCTargets:
        Kconfig_str += Kconfig_sdt
    if petalinux:
        Kconfig_str += Kconfig_plnx
    Kconfig_str += '\nsource %s/Kconfig.main\n' % project_cfgdir

    with open(Kconfig, 'w') as kconfig_f:
        kconfig_f.write(Kconfig_str)
    kconfig_f.close()


def ApplyConfValue(string, system_conffile):
    string = string.strip()
    if string.startswith('#'):
        conf = string.replace('#', '').split()[0]
        value = 'disable'
    else:
        conf = string.split('=')[0]
        value = 'y'
        if len(string.split('=')) == 2:
            value = string.split('=')[1]
    if conf and value:
        common_utils.UpdateConfigValue(conf, value, system_conffile)


def PreProcessSysConf(args, system_conffile, mctargets=[]):
    if args.machine:
        common_utils.UpdateConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                       '"%s"' % args.machine, system_conffile)
    if args.require_machine:
        common_utils.UpdateConfigValue('CONFIG_YOCTO_INCLUDE_MACHINE_NAME',
                                       '"%s"' % args.require_machine, system_conffile)
    if args.machine_overrides:
        common_utils.UpdateConfigValue('CONFIG_YOCTO_ADD_OVERRIDES',
                                       '"%s"' % args.machine_overrides, system_conffile)
    if hasattr(args, 'dts_path') and args.dts_path:
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_DT_XSCT_WORKSPACE',
                                       '"%s"' % args.dts_path, system_conffile)

    # Read the args.multiconfigfull and enable full target set
    if hasattr(args, 'multiconfigfull') and args.multiconfigfull:
        for mctarget in mctargets:
            cfgtarget = 'CONFIG_YOCTO_BBMC_%s' % mctarget.upper().replace('-', '_')
            common_utils.UpdateConfigValue(cfgtarget, 'y', system_conffile)

    # Read the args.gen_pl_overlay and update sysconfig
    if hasattr(args, 'gen_pl_overlay') and args.gen_pl_overlay:
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_FPGA_MANAGER',
                                        'y', system_conffile)
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_PL_DT_OVERLAY_%s' %
                args.gen_pl_overlay.replace('-','_').upper(), 'y', system_conffile)

    # Read the configs from CLI and update system conf file
    for config in args.add_config:
        # Default assume macro stars with CONFIG_ else file
        if os.path.isfile(config):
            with open(config, 'r') as file_data:
                lines = file_data.readlines()
            for line in lines:
                ApplyConfValue(line, system_conffile)
        elif config.strip().replace('#', '').startswith('CONFIG_'):
            ApplyConfValue(config, system_conffile)
        else:
            logger.warning('Unable to detect config type: %s. Using CONFIG_%s' % (
                            config, config))
            ApplyConfValue('CONFIG_%s' % config, system_conffile)


def PrintSystemConfiguration(args, model, device_id, cpu_info_dict=None):
    cpumap = {'pmu-microblaze': 'zynqmp-pmu', 'pmc-microblaze': 'versal-plm',
              'psm-microblaze': 'versal-psm', 'xlnx,microblaze': 'microblaze'
              }
    logger.debug('Hardware Configuration:')
    if model:
        logger.debug('MODEL       = "%s"' % model)
    logger.debug('MACHINE     = "%s"' % args.machine)
    logger.debug('DEVICE_ID   = "%s"' % device_id)
    logger.debug('SOC_FAMILY  = "%s"' % args.soc_family)
    logger.debug('SOC_VARIANT = "%s"' % args.soc_variant)
    if cpu_info_dict:
        logger.debug('CPUs:')
        for cpu in cpu_info_dict.keys():
            _cpu = cpu_info_dict[cpu].get('cpu')
            _cpu = cpumap.get(_cpu, _cpu)
            logger.debug('\t= %s %s %s' % (
                cpu, _cpu.replace(',', ' '),
                cpu_info_dict[cpu].get('core')))
