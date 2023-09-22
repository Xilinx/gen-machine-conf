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


def GenKconfigProj(soc_family, soc_variant, output,
                   system_conffile, bbmctargets='', multiconfig_min=''):
    genmachine_scripts = GenMachineScriptsPath()
    project_cfgdir = os.path.join(output, 'configs')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    template_cfgfile = os.path.join(
        genmachine_scripts, 'configs/config_%s' % soc_family)
    Kconfig_part = os.path.join(genmachine_scripts, 'configs', 'Kconfig.part')

    for file_path in [Kconfig_part, Kconfig_syshw]:
        if not os.path.isfile(file_path):
            logger.error('%s is not found in tool' % file_path)
            sys.exit(255)

    if not os.path.isfile(system_conffile):
        common_utils.CopyFile(template_cfgfile, system_conffile)

    Kconfig_soc_family = soc_family.upper()
    Kconfig_str = start_menu.format(Kconfig_soc_family, output)
    if soc_variant:
        Kconfig_soc_variant = soc_variant.upper()
        Kconfig_str += socvariant_menu.format(
            Kconfig_soc_family, Kconfig_soc_variant)

    Kconfig_BBMCTargets = ''
    if bbmctargets:
        Kconfig_str += Kconfig_sdt
        Kconfig_BBMCTargets = ConvertMCTargetsToKconfig(
            bbmctargets, multiconfig_min)

    with open(Kconfig_part, 'r', encoding='utf-8') as kconfig_part_f:
        kconfig_part_data = kconfig_part_f.read()
    kconfig_part_f.close()
    kconfig_part_data = kconfig_part_data.replace(
        'source ./Kconfig.syshw', 'source %s' % Kconfig_syshw)
    kconfig_part_data = kconfig_part_data.replace(
        '@@multiconfigmenustr@@', Kconfig_BBMCTargets)
    Kconfig_str += kconfig_part_data
    with open(Kconfig, 'w') as kconfig_f:
        kconfig_f.write(Kconfig_str)
    kconfig_f.close()


def PreProcessSysConf(args, system_conffile):
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
