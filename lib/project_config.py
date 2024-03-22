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
import multiconfigs

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


def GenKconfigProj(args, system_conffile, hw_info):
    genmachine_scripts = GenMachineScriptsPath()
    project_cfgdir = os.path.join(args.output, 'configs')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    template_cfgfile = os.path.join(
        genmachine_scripts, 'configs/config_%s' % args.soc_family)
    Kconfig_files = glob.glob(os.path.join(
                        genmachine_scripts, 'configs', 'Kconfig.*'))

    if not os.path.isfile(Kconfig_syshw):
        raise Exception('%s is not found in tool' % file_path)

    if not os.path.isfile(system_conffile):
        common_utils.CopyFile(template_cfgfile, system_conffile)

    if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file):
        # When multiple xsa/sdt files configured with same memory ip with different
        # size offsets mconf/conf will use the old configs instead of new
        # to fix that removing old MEMORY related configs from sysconfig
        # for the first time with every new XSA configured.
        common_utils.RemoveConfigs('CONFIG_SUBSYSTEM_MEMORY_', system_conffile)

    if 'cpu_info_dict' in hw_info:
        MCObject = multiconfigs.CreateMultiConfigFiles(
            args, hw_info['cpu_info_dict'], file_names_only=True)
        bbmctargets, multiconfig_min = MCObject.ParseCpuDict()
    else:
        bbmctargets = ''
        multiconfig_min = ''

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

    Kconfig_soc_family = args.soc_family.upper()
    Kconfig_str = start_menu.format(Kconfig_soc_family, args.output)
    if args.soc_variant:
        Kconfig_soc_variant = args.soc_variant.upper()
        Kconfig_str += socvariant_menu.format(
            Kconfig_soc_family, Kconfig_soc_variant)
    if Kconfig_BBMCTargets:
        Kconfig_str += Kconfig_sdt
    if args.petalinux:
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


def PreProcessSysConf(args, system_conffile, hw_info):
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
    if hasattr(args, 'multiconfigfull') and args.multiconfigfull \
       and 'cpu_info_dict' in hw_info:
        MCObject = multiconfigs.CreateMultiConfigFiles(
            args, hw_info['cpu_info_dict'], file_names_only=True)
        mctargets, _ = MCObject.ParseCpuDict()

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

def GenerateConfiguration(args, hw_info, system_conffile, plnx_syshw_file, mctargets=[]):
    import yocto_machine
    import update_buildconf

    logger.info('Generating configuration files')

    MultiConfDict = {}
    GenMultiConf = True
    # Dont re-trigger the multiconfigs if no changes in project file
    if common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False) and \
            common_utils.ValidateHashFile(args.output, 'SYSTEM_CONF', system_conffile, update=False) and \
            os.path.exists(plnx_syshw_file) and \
            (hasattr(args, 'dts_path') and os.path.exists(args.dts_path)):
        GenMultiConf = False

    if GenMultiConf and 'cpu_info_dict' in hw_info:
        if hasattr(args, 'dts_path') and args.dts_path:
            common_utils.CreateDir(args.dts_path)

        multiconfig_dir = os.path.join(args.config_dir, 'multiconfig')
        machine_include_dir = os.path.join(args.config_dir, 'machine', 'include')
        for dirpath in [multiconfig_dir, machine_include_dir]:
            common_utils.CreateDir(dirpath)

        args.bbconf_dir = os.path.join(machine_include_dir, args.machine)
        common_utils.CreateDir(args.bbconf_dir)

        MCObject = multiconfigs.CreateMultiConfigFiles(args, hw_info['cpu_info_dict'],
                                                       system_conffile=system_conffile)
        MultiConfDict = MCObject.ParseCpuDict()

    if args.petalinux:
        # Layers should be added before generating machine conf files
        update_buildconf.AddUserLayers(args)

    machine_conf_file = yocto_machine.GenerateYoctoMachine(
        args, system_conffile, plnx_syshw_file, MultiConfDict)

    if args.petalinux:
        import plnx_machine

        plnx_conf_file = plnx_machine.GeneratePlnxConfig(
            args, machine_conf_file)
        update_buildconf.UpdateLocalConf(
            args, plnx_conf_file, machine_conf_file)

    update_buildconf.GenLocalConf(args.localconf,
                                  machine_conf_file,
                                  system_conffile, args.petalinux)
