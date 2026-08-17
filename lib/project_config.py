#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT


import os
import re
import yaml
import common_utils
import yaml_utils
import lopper_utils
import logging
import glob
import multiconfigs

logger = logging.getLogger('Gen-Machineconf')


start_menu = '''
mainmenu "System Configuration"
config SUBSYSTEM_TYPE_LINUX
        bool
        default y
        select SYSTEM_{0}

config SYSTEM_{0}
        bool "{0} Configuration"
        help
          {0} Configuration for the project.
          All these config options will be in {1}/config
'''

socvariant_menu = '''
config SUBSYSTEM_VARIANT_{0}{1}
        bool
        default y
        help
'''

mbv_xlen_menu = '''
config SUBSYSTEM_MICROBLAZE_V_XLEN_{0}
        bool
        default y
        help
          Auto-detected MicroBlaze-V register width (XLEN={0}).
'''

Kconfig_sdt = '''
config SUBSYSTEM_SDT_FLOW
        bool
        default y
        help
'''

Kconfig_multitarget_dtsi = '''
config YOCTO_BBMC_{0}_DTSI
        string "DTSI path for {1} (optional)"
        default ""
        {2}
        help
         The specified files shall be directly merged into the domain DTS.
         Includes are applied in their listed order.

         Specify multiple files using space separation.
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


def DetectSocFamily(proc_type, device_id=''):
    soc_family = ''
    if re.search('.*a78.*', proc_type):
        if proc_type.startswith('psx_'):
            return 'versal'
        return 'versal-2ve-2vm'
    elif re.search('.*a72.*', proc_type):
        if device_id.startswith('xc2vp'):
            return 'versal-2vp'
        return 'versal'
    elif re.search('.*a53.*', proc_type):
        return 'zynqmp'
    elif re.search('.*a9.*', proc_type):
        return 'zynq'
    elif re.search('microblaze_riscv', proc_type):
        return 'microblaze-v'
    return proc_type


def GenMachineScriptsPath():
    scriptpath = os.path.dirname(__file__)
    genscriptspath = os.path.join(os.path.dirname(scriptpath),
                                  'gen-machine-scripts')
    return genscriptspath

_MBVXlenDone = False
def GetMBVXlen(work, dts_path, hw_file):
    '''Auto-detect the MicroBlaze-V RISC-V -march (tune features) and register
    width (XLEN) from the design by running the microblaze-riscv lop and reading
    cflags.yaml. Returns a tuple (m_arch, xlen): m_arch is the -march string
    (e.g. "rv64imafdc", or '' if not found) and xlen is 32 or 64 (default 32).'''
    global _MBVXlenDone
    if not _MBVXlenDone:
        lopper_utils.RunLopperUsingDomainFile(['lop-microblaze-riscv.dts'],
                                              work, dts_path, hw_file)
        _MBVXlenDone = True
    cflags_file = os.path.join(work, 'cflags.yaml')
    if not os.path.isfile(cflags_file):
        raise Exception('cflags file does not exist: %s, required to detect the '
                        'MicroBlaze-V tune features and register width' % cflags_file)
    cflags_data = yaml_utils.ReadYaml(cflags_file) or {}
    march_match = re.search(r'-march=(\S+)', cflags_data.get('cflags', ''))
    m_arch = march_match.group(1) if march_match else ''
    xlen_match = re.match(r'rv(\d+)', m_arch)
    if not xlen_match:
        logger.warning('Unable to detect MicroBlaze-V -march, defaulting to 32-bit')
        return m_arch, 32
    return m_arch, int(xlen_match.group(1))


def ConvertMCTargetsToKconfig(bbmctargets, multiconfig_min):
    multiconfig_str = 'menu "Multiconfig Targets"'
    multiconfig_str += Kconfig_multitarget_dtsi.format(
                                        'LINUX', 'linux', '')
    for target in bbmctargets:
        enable = 'n'
        if target in multiconfig_min:
            enable = 'y'
        target_K = target.upper().replace('-', '_')
        multiconfig_str += Kconfig_multitarget.format(
                                target_K, target, enable)
        multiconfig_str += Kconfig_multitarget_dtsi.format(
                    target_K, target, f'depends on YOCTO_BBMC_{target_K}')
    multiconfig_str += 'endmenu'
    return multiconfig_str


LinuxDisabledInYaml = False
def MultiConfigYaml(yaml_file, multiconfig_dict):
    multiconf_yaml = []
    os_hint_yaml = []
    for _file in yaml_file.split():
        _file = common_utils.ExpandFilePath(_file)
        for mc_config in multiconfig_dict:
            _mc_config_dict = multiconfig_dict.get(mc_config)
            cpuname = _mc_config_dict.get('cpuname', '')
            cpu = _mc_config_dict.get('cpu', '')
            os_hint = _mc_config_dict.get('os_hint', '')
            domain_name, _ = yaml_utils.GetDomainName(cpuname, cpu, os_hint, _file)
            if domain_name:
                os_hint_yaml.append(os_hint)
                multiconf_yaml.append(mc_config)

    # Check if linux is present once all yamls parsed
    global LinuxDisabledInYaml
    if 'linux' not in os_hint_yaml:
        LinuxDisabledInYaml = True

    return multiconf_yaml


def GenKconfigProj(args, system_conffile, hw_info, MCObject=None):
    genmachine_scripts = GenMachineScriptsPath()
    project_cfgdir = os.path.join(args.output, 'configs')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    Kconfig_files = glob.glob(os.path.join(
                        genmachine_scripts, 'configs', 'Kconfig.*'))

    if not os.path.isfile(Kconfig_syshw):
        raise Exception('%s is not found in tool' % Kconfig_syshw)

    if common_utils.FileChanged(args.output, 'HW_FILE', args.hw_file):
        common_utils.CommitFileHash(args.output, 'HW_FILE', args.hw_file)
        # When multiple SDT files configured with same memory ip with different
        # size offsets mconf/conf will use the old configs instead of new
        # to fix that removing old MEMORY related configs from sysconfig
        # for the first time with every new SDT configured.
        common_utils.RemoveConfigs('CONFIG_SUBSYSTEM_MEMORY_', system_conffile)

    if not MCObject and 'cpu_info_dict' in hw_info:
        MCObject = multiconfigs.ParseMultiConfigFiles(
            args, hw_info['cpu_info_dict'])

    if MCObject:
        bbmctargets, multiconfig_min = MCObject.ParseCpuDict()
        hw_info['multiconfigs'] = MCObject.MultiConfMap
        if hasattr(args, 'domain_file') and args.domain_file:
            _multiconfig_min = MultiConfigYaml(args.domain_file, hw_info['multiconfigs'])
            multiconfig_min =  list(dict.fromkeys(multiconfig_min + _multiconfig_min))
    else:
        bbmctargets = []
        multiconfig_min = []

    # If the config switch that all multiconfigs are to be includes, they become
    # the minimum (defaults to on)
    if hasattr(args, 'multiconfigfull') and args.multiconfigfull:
        multiconfig_min = bbmctargets

    Kconfig_BBMCTargets = ''
    if bbmctargets:
        Kconfig_BBMCTargets = ConvertMCTargetsToKconfig(
            bbmctargets, multiconfig_min)

    # Generate the per-domain Serial Settings menu. This needs the multiconfig
    # target list (known here) and the SDT serial IPs (from sys_hw_data.yaml).
    # The menu is injected into the Subsystem Hardware Settings menu of
    # Kconfig.syshw via the @@serialmenustr@@ placeholder.
    import kconfig_syshw
    Kconfig_SerialMenu = ''
    syshw_file = os.path.join(args.output, 'sys_hw_data.yaml')
    if os.path.exists(syshw_file) and 'proc_type' in hw_info:
        Kconfig_SerialMenu = kconfig_syshw.GenSerialDomainsKconfig(
            syshw_file, hw_info['proc_type'], bbmctargets)
    common_utils.ReplaceStrFromFile(
                Kconfig_syshw, '@@serialmenustr@@', Kconfig_SerialMenu)

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
    if args.soc_family == 'microblaze-v':
        _m_arch, mbv_xlen = GetMBVXlen(args.work, os.getcwd(), args.hw_file)
        Kconfig_str += mbv_xlen_menu.format(mbv_xlen)
    # Emit the SDT flow config if the user requested it (via --hw-flow sdt)
    if getattr(args, 'hw_flow', '') == 'sdt':
        Kconfig_str += Kconfig_sdt
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
        if '=' in string:
            conf, value = string.split('=', 1)  # split only once
        else:
            conf = string.strip()
            value = 'y'
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
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_DT_WORKSPACE',
                                       '"%s"' % args.dts_path, system_conffile)

    # Read the args.gen_pl_overlay and update sysconfig
    if hasattr(args, 'gen_pl_overlay') and args.gen_pl_overlay:
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_FPGA_MANAGER',
                                        'y', system_conffile)
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_PL_DT_OVERLAY_%s' %
                args.gen_pl_overlay.replace('-','_').upper(), 'y', system_conffile)

    # Domain file path from args to config
    if hasattr(args, 'domain_file') and args.domain_file:
        common_utils.UpdateConfigValue('CONFIG_YOCTO_MC_DOMAIN_FILEPATH',
                                       f'"{args.domain_file}"',
                                       system_conffile)

    # Read the YAML kconfig variables and update the project configs
    Yamlconfigs = yaml_utils.TemplateYamlData.get('kconfig', {})
    for conf, value in (Yamlconfigs or {}).items():
        if not conf or value is None:
            continue
        if value not in ('y', 'n', 'Y', 'N') and \
                not (isinstance(value, str) and value.startswith('0x')):
            value = '"%s"' % value
        common_utils.UpdateConfigValue(conf, value, system_conffile)

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

def GetFilesToTrack(args, system_conffile):
    '''Single source of truth for every input whose *content* affects the
    generated output. Returns a mapping of .statistics macro -> list of paths,
    used both for change detection (AnyFileChanged) and for recording hashes
    (CommitHashes):
      - HW_FILE:     the system device-tree (hardware description).
      - SYSTEM_CONF: the generated project config file.
      - INPUT_FILES: template YAML, domain files (from
                     CONFIG_YOCTO_MC_DOMAIN_FILEPATH) and custom DTSI files.
    PDI/bitstream, ELF and psu_init inputs are intentionally excluded because
    only their paths (not their content) are embedded into the generated
    machine configuration, so their content cannot change the output.'''
    input_files = []
    if getattr(args, 'template', None):
        input_files.append(args.template)
    # Domain files may come from menuconfig as well as the CLI, so read them
    # from the project config (the source of truth) rather than args.
    domain_file_cfg = common_utils.GetConfigValue(
        'CONFIG_YOCTO_MC_DOMAIN_FILEPATH', system_conffile)
    for _file in domain_file_cfg.split():
        input_files.append(common_utils.ExpandFilePath(_file))
    # Custom DTSI files are baked into the generated DTS, so their content
    # matters. Their paths live in the project config as CONFIG_*_DTSI values.
    if os.path.exists(system_conffile):
        with open(system_conffile) as conf_f:
            for line in conf_f:
                match = re.match(
                    r'^(CONFIG_YOCTO_BBMC_\w+_DTSI)="?(.*?)"?$', line.strip())
                if match:
                    for dtsi in match.group(2).split():
                        input_files.append(common_utils.ExpandFilePath(dtsi))
    return {
        'HW_FILE': [args.hw_file],
        'SYSTEM_CONF': [system_conffile],
        'INPUT_FILES': input_files,
    }


def GenerateConfiguration(args, hw_info, system_conffile, syshw_file, MCObject=None):
    import yocto_machine
    import update_buildconf

    logger.info('Generating configuration files')

    MultiConfDict = {}
    GenMultiConf = True
    files_to_track = GetFilesToTrack(args, system_conffile)
    files_changed = common_utils.AnyFileChanged(args.output, files_to_track)
    # Dont re-trigger the multiconfigs if no changes in any tracked input file
    if not files_changed and \
            os.path.exists(syshw_file) and \
            (hasattr(args, 'dts_path') and os.path.exists(args.dts_path)):
        GenMultiConf = False
        logger.info('No changes detected in tracked input files, '
                    'skipping configuration regeneration '
                    '(use --force to regenerate all configurations)')

    if GenMultiConf and 'cpu_info_dict' in hw_info:
        if hasattr(args, 'dts_path') and args.dts_path:
            common_utils.CreateDir(args.dts_path)

        multiconfig_dir = os.path.join(args.config_dir, 'multiconfig')
        machine_include_dir = os.path.join(args.config_dir, 'machine', 'include')
        for dirpath in [multiconfig_dir, machine_include_dir]:
            common_utils.CreateDir(dirpath)

        args.bbconf_dir = os.path.join(machine_include_dir, args.machine)
        common_utils.CreateDir(args.bbconf_dir)

        if not MCObject and 'cpu_info_dict' in hw_info:
            MCObject = multiconfigs.GenerateMultiConfigFiles(
                args, hw_info['multiconfigs'], system_conffile=system_conffile)

        if MCObject:
            MultiConfDict = MCObject.GenerateMultiConfigs()

    machine_conf_file = yocto_machine.GenerateYoctoMachine(
        args, system_conffile, syshw_file, MultiConfDict)

    update_buildconf.GenLocalConf(args.localconf,
                                  machine_conf_file,
                                  system_conffile)

    # Record hashes only when something changed; on an unchanged run the stored
    # hashes already match, so re-committing would just re-hash every input and
    # rewrite .statistics for no reason.
    if files_changed:
        common_utils.CommitHashes(args.output, files_to_track)
