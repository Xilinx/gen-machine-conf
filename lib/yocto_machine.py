#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import configparser
import os
import re
import common_utils
import yaml_utils
import project_config
import lopper_utils
import glob
import logging


logger = logging.getLogger('Gen-Machineconf')


Machinefeatures_soc = {
    'zynqmp': {
        'dr': 'rfsoc', 'ev': 'mali400 vcu', 'eg': 'mali400'
    },
    'versal': {
        'ai-core': 'vdu', 'ai-edge': 'vdu'
    },
    'versal-2ve-2vm': {
        'common': 'vcu2 malig78ae'
    },
    'versal-2vp': {
    }
}

def GetMachineFeatures(args, system_conffile, MultiConfDict):
    machine_features = ''

    if args.soc_family in Machinefeatures_soc.keys():
        machine_features = Machinefeatures_soc[args.soc_family].get('common', '')
        machine_features += ' %s' % Machinefeatures_soc[args.soc_family].get(args.soc_variant, '')
    if 'AsuTune' in MultiConfDict:
        machine_features += 'asu'

    is_optee = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_OPTEE', system_conffile)
    if is_optee == 'y':
        machine_features += ' optee'

    is_fpga_manager = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_FPGA_MANAGER', system_conffile)
    if is_fpga_manager == 'y':
        machine_features += ' fpga-overlay'

    is_efi = common_utils.GetConfigValue(
        'CONFIG_YOCTO_MACHINE_FEATURE_EFI', system_conffile)
    if is_efi == 'y':
        machine_features += ' efi'

    return ' '.join(machine_features.split())


def GetQemuMemCfg(outdir, dts_path, hw_file):
    lopper_utils.RunLopperSubcommand(outdir, dts_path, hw_file, 'gen_qemu_mem_cfg')
    qemu_mem_cfg = os.path.join(outdir, 'memory.qemuboot.conf')
    if os.path.isfile(qemu_mem_cfg):
        config = configparser.ConfigParser(interpolation=None)
        config.read(qemu_mem_cfg)
        data = config.get('config_bsp', 'qb_mem', fallback='').strip()
        logger.debug(f'QEMU Memory Config: {data}')
        if data:
            return f'QB_MEM = "{data}"\n'
    return ''


def GetBootCompSource(args, comp, mcdepends, deploydir, MultiConfDict, system_conffile):
    CompFrom = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_FROM_' % comp,
                                           system_conffile, 'choice', '=y').lower()
    CompDepends = CompMcDepends = CompImageName = RemoveComp = ''

    if CompFrom == 'base_pdi':
        CompDeployDir = 'undefined'
        CompImageName = 'undefined'
        RemoveComp = True
    elif CompFrom == 'sdt_path':
        CompDepends = '${SYSTEM_DTFILE_DEPENDS}:do_populate_sysroot'
        CompDeployDir = '${SYSTEM_DTFILE_DIR}'
        CompImageName = common_utils.GetConfigValue(
                            'CONFIG_SUBSYSTEM_COMPONENT_%s_ELF_NAME' % comp, system_conffile)
        if CompImageName.endswith('.elf'):
            CompImageName = CompImageName.rsplit('.elf', 1)[0]
        tmp_path = os.path.join(os.path.dirname(args.hw_file), CompImageName) + '.elf'
        if not CompImageName:
            logger.warning('CONFIG_SUBSYSTEM_COMPONENT_%s_ELF_NAME is not specified,'
                            'Defaulting to plm.elf' % comp)
        elif not os.path.isfile(tmp_path):
            logger.warning('Specified %s elf not found : %s, '
                    'Make sure you specified proper .elf file' % (comp, tmp_path))
    elif CompFrom == 'local_path':
        CompLocalPath = common_utils.GetConfigValue(
                    'CONFIG_SUBSYSTEM_COMPONENT_%s_ELF_PATH' % comp, system_conffile)
        CompDeployDir = os.path.dirname(CompLocalPath)
        CompImageName = os.path.basename(CompLocalPath)
        if CompImageName.endswith('.elf'):
            CompImageName = CompImageName.rsplit('.elf', 1)[0]
        tmp_path = os.path.join(CompDeployDir, CompImageName) + '.elf'
        if not CompLocalPath:
            logger.warning('CONFIG_SUBSYSTEM_COMPONENT_%s_ELF_PATH is not specified. '
                        'Please specify the proper .elf file to avoid build failures' % comp)
        elif not os.path.isfile(tmp_path):
            logger.warning('Specified %s elf not found : %s, '
                    'Make sure you specified proper .elf file' % (comp, tmp_path))
    else:
        CompMcDepends = MultiConfDict.get(mcdepends)
        CompDeployDir = MultiConfDict.get(deploydir)

    return CompDepends, CompMcDepends, CompDeployDir, CompImageName, RemoveComp


def UpdateYamlConfigs(dict_key, machine_override_string):
    '''
    Iterates each var and checks if it exists in machine_override_string using regex.
    If found, replaces the line with var op "val".
    If not found, appends var op "val" as a new line.
    Returns the updated string with newline at the end.
    '''
    yaml_configs = YamlMachineConfs.get(dict_key, {})
    if not isinstance(yaml_configs, dict) or not yaml_configs:
        return machine_override_string

    lines = machine_override_string.strip().split('\n')
    first_new_added = False
    for var, values in yaml_configs.items():
        comment = values.get('comment', '')
        op = values.get('op', '=')
        pattern = re.compile(rf'^{re.escape(var)}\s+.*{re.escape(op)}')
        val = values.get('val')
        # Skip adding value if not found in yaml
        if val is not None:
            _newline = f'{var} {op} "{val}"'
        else:
            _newline = f'{var} {op}'
        found = False
        new_lines = []

        for line in lines:
            if pattern.search(line):
                if comment:
                    new_lines.append(f'# {comment}')
                new_lines.append(_newline)
                found = True
            else:
                new_lines.append(line)

        if not found:
            if not first_new_added:
                # Blank line before the first inserted one
                new_lines.append('')
                first_new_added = True
            if comment:
                new_lines.append(f'# {comment}')
            new_lines.append(_newline)

        lines = new_lines  # carry over updated content to next iteration

    return '\n'.join(lines) + '\n'


def YoctoCommonConfigs(args, arch, system_conffile, MultiConfDict):
    machine_override_string = ''
    if arch == 'aarch64':
        baseaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_',
                                               system_conffile, 'asterisk', '_BASEADDR=')
        machine_override_string += '\n# Yocto arm-trusted-firmware(TF-A) variables\n'
        atf_serial_ip_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_TF-A_IP_NAME',
                                                         system_conffile)
        atf_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_SERIAL_MANUAL_SELECT',
                                                        system_conffile)
        if not atf_serial_manual:
            machine_override_string += 'TFA_CONSOLE ?= "%s"\n' % atf_serial_ip_name
        atf_mem_settings = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_MEMORY_SETTINGS',
                                                       system_conffile)
        atf_mem_base = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_MEM_BASE',
                                                   system_conffile)
        atf_mem_size = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_MEM_SIZE',
                                                   system_conffile)
        if atf_mem_settings:
            machine_override_string += 'TFA_MEM_BASE ?= "%s"\n' % atf_mem_base
            machine_override_string += 'TFA_MEM_SIZE ?= "%s"\n' % atf_mem_size

        atf_extra_settings = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_EXTRA_COMPILER_FLAGS',
                                                         system_conffile)
        memory = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_', system_conffile,
                                            'choice', '_SELECT=y')
        atf_bl33_offset = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_%s_U__BOOT_TEXTBASE_OFFSET' % memory,
                                                     system_conffile)
        if atf_extra_settings:
            machine_override_string += 'EXTRA_OEMAKE:append:pn-trusted-firmware-a'\
                                       ' = " %s"\n' % atf_extra_settings
        if atf_bl33_offset:
            machine_override_string += 'TFA_BL33_LOAD ?= "%s"\n' % atf_bl33_offset

        atf_debug = common_utils.GetConfigValue(
                'CONFIG_SUBSYSTEM_TF-A_DEBUG', system_conffile)
        if atf_debug:
            machine_override_string += 'DEBUG_ATF = "1"\n'

        optee_serial_ip_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_OP-TEE_IP_NAME',
                                                        system_conffile)
        optee_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_OP-TEE_SERIAL_MANUAL_SELECT',
                                                        system_conffile)
        if optee_serial_ip_name and not optee_serial_manual:
            machine_override_string += '\n# Yocto OP-TEE variables\n'
            machine_override_string += 'OPTEE_CONSOLE ?= "%s"\n' % optee_serial_ip_name

        optee_mem_settings = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_OPTEE_MEMORY_SETTINGS',
                                                      system_conffile)

        optee_tzdram_start = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_OPTEE_TZDRAM_START',
                                                     system_conffile)

        optee_tzdram_size = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_OPTEE_TZDRAM_SIZE',
                                                      system_conffile)

        if optee_mem_settings:
           machine_override_string += 'OPTEE_TZDRAM_START ?= "%s"\n' % optee_tzdram_start
           machine_override_string += 'OPTEE_TZDRAM_SIZE ?= "%s"\n' % optee_tzdram_size


    machine_override_string += '\n# Yocto u-boot-xlnx variables\n'
    uboot_config = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_CONFIG_TARGET',
                                               system_conffile)
    if uboot_config and uboot_config.lower() != 'auto':
        machine_override_string += f'UBOOT_MACHINE ?= "{uboot_config}"\n'

    uboot_spl_type = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_SPL_BINARY_TYPE',
                                                 system_conffile)
    if uboot_spl_type:
        machine_override_string += f'SPL_BINARY ?= "{uboot_spl_type}"\n'

    ddr_baseaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_', system_conffile,
                                               'asterisk', '_BASEADDR=')
    if not ddr_baseaddr:
        ddr_baseaddr = '0x0'
    machine_override_string += '\n# Set DDR Base address for u-boot-xlnx-scr '\
                               'variables\n'
    machine_override_string += 'DDR_BASEADDR ?= "%s"\n' % ddr_baseaddr
    skip_append_baseaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_APPEND_BASEADDR',
                                                       system_conffile)
    if skip_append_baseaddr:
        machine_override_string += 'SKIP_APPEND_BASEADDR ?= "0"\n'
    else:
        machine_override_string += 'SKIP_APPEND_BASEADDR ?= "1"\n'

    machine_override_string += '\n# Yocto KERNEL Variables\n'

    #Apply user-selected kernel defconfig from gen-machineconf menuconfig.
    kernel_config = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_LINUX_CONFIG_TARGET',
                                                system_conffile)
    if kernel_config and kernel_config.lower() != 'auto':
        machine_override_string += 'KBUILD_DEFCONFIG = "%s"\n' % kernel_config

    # Additional kernel make command-line arguments
    if args.soc_family == 'microblaze-v':
        uboot_entry_offset = '0x1200000'
        kernel_loadaddr = hex(int(ddr_baseaddr, 16) + int(uboot_entry_offset, 16))
    else:
        kernel_baseaddr = ddr_baseaddr
        kernel_offset = '0x200000'
        kernel_loadaddr = hex(int(kernel_baseaddr, 16) +
                            int(kernel_offset, 16))
        kernel_loadaddr = '0x%s' % kernel_loadaddr[2:].upper()
    if kernel_loadaddr and int(kernel_loadaddr, 16) >> 32:
        MSB = '0x%s' % hex(int(kernel_loadaddr, 16) >> 32)[2:].upper()
        LSB = '0x%s' % hex(int(kernel_loadaddr, 16) & 0x0ffffffff)[2:].upper()
        loadaddr = '%s %s' % (MSB, LSB)
    else:
        loadaddr = kernel_loadaddr

    machine_override_string += 'UBOOT_ENTRYPOINT ?= "%s"\n' % loadaddr
    machine_override_string += 'UBOOT_LOADADDRESS ?= "%s"\n' % loadaddr

    if arch != 'aarch64' and args.soc_family != 'microblaze-v':
        machine_override_string += 'KERNEL_EXTRA_ARGS += "UIMAGE_LOADADDR=${UBOOT_ENTRYPOINT}"\n'


    machine_features = GetMachineFeatures(args, system_conffile, MultiConfDict)
    if machine_features:
        machine_override_string += '\n# Yocto MACHINE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_FEATURES += "%s"\n' % (machine_features)

    if args.soc_variant == 'ev' and args.soc_family == 'zynqmp':
        machine_override_string += '\n# Yocto IMAGE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_HWCODECS = "libvcu-omxil"\n'
        machine_override_string += 'IMAGE_FEATURES += "hwcodecs"\n'

    return machine_override_string


def YoctoMCFimwareConfigs(args, arch, system_conffile, req_conf_file, MultiConfDict):
    machine_override_string = ''
    # Capture the tunes
    if 'PmuTune' in MultiConfDict:
        machine_override_string += 'TUNEFILE[%s] = "%s"\n' % (
            MultiConfDict['PmuTune'],
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze.inc'))

    if 'PlmTune' in MultiConfDict:
        machine_override_string += 'TUNEFILE[%s] = "%s"\n' % (
            MultiConfDict['PlmTune'],
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze.inc'))

    if 'PsmTune' in MultiConfDict:
        machine_override_string += 'TUNEFILE[%s] = "%s"\n' % (
            MultiConfDict['PsmTune'],
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze.inc'))

    if 'AsuTune' in MultiConfDict:
        machine_override_string += 'TUNEFILE[%s] = "%s"\n' % (
            MultiConfDict['AsuTune'],
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze-v.inc'))

    # Linux baremeal file pointers and dependencies
    if 'FsblMcDepends' in MultiConfDict:
        FsblDepends, FsblMcDepends, FsblDeployDir, FsblImageName, _ = GetBootCompSource(
                args, 'FSBL', 'FsblMcDepends', 'FsblDeployDir', MultiConfDict, system_conffile)
        machine_override_string += '\n# First Stage Boot Loader\n'
        machine_override_string += 'FSBL_DEPENDS = "%s"\n' % FsblDepends
        machine_override_string += 'FSBL_MCDEPENDS = "%s"\n' % FsblMcDepends
        machine_override_string += 'FSBL_DEPLOY_DIR = "%s"\n' % FsblDeployDir.rstrip('/')
        if FsblImageName:
            machine_override_string += 'FSBL_IMAGE_NAME = "%s"\n' % FsblImageName

    if 'R5FsblMcDepends' in MultiConfDict:
        machine_override_string += '\n# Cortex-R5 First Stage Boot Loader\n'
        machine_override_string += 'R5FSBL_DEPENDS = ""\n'
        machine_override_string += 'R5FSBL_MCDEPENDS = "%s"\n' % MultiConfDict.get(
            'R5FsblMcDepends')
        machine_override_string += 'R5FSBL_DEPLOY_DIR = "%s"\n' % MultiConfDict.get(
            'R5FsblDeployDir').rstrip('/')

    if 'PmuMcDepends' in MultiConfDict:
        PmuDepends, PmuMcDepends, PmuDeployDir, PmuImageName, _ = GetBootCompSource(
                args, 'PMUFW', 'PmuMcDepends', 'PmuFWDeployDir', MultiConfDict, system_conffile)
        machine_override_string += '\n# PMU Firmware\n'
        machine_override_string += 'PMU_DEPENDS = "%s"\n' % PmuDepends
        machine_override_string += 'PMU_MCDEPENDS = "%s"\n' % PmuMcDepends
        machine_override_string += 'PMU_FIRMWARE_DEPLOY_DIR = "%s"\n' % PmuDeployDir.rstrip('/')
        if PmuImageName:
            machine_override_string += 'PMU_FIRMWARE_IMAGE_NAME = "%s"\n' % PmuImageName

    if 'PlmMcDepends' in MultiConfDict:
        PlmDepends, PlmMcDepends, PlmDeployDir, PlmImageName, RemovePlm = GetBootCompSource(
                args, 'PLM', 'PlmMcDepends', 'PlmDeployDir', MultiConfDict, system_conffile)

        machine_override_string += '\n# Platform Loader and Manager\n'
        machine_override_string += 'PLM_DEPENDS = "%s"\n' % PlmDepends
        machine_override_string += 'PLM_MCDEPENDS = "%s"\n' % PlmMcDepends
        machine_override_string += 'PLM_DEPLOY_DIR = "%s"\n' % PlmDeployDir.rstrip('/')
        if PlmImageName:
            machine_override_string += 'PLM_IMAGE_NAME = "%s"\n' % PlmImageName
        if RemovePlm:
            machine_override_string += '\n# Remove the PLM from Boot.bin\n'
            machine_override_string += 'BIF_PARTITION_ATTR:remove = "plmfw"\n'

    if 'PsmMcDepends' in MultiConfDict:
        PsmDepends, PsmMcDepends, PsmDeployDir, PsmImageName, RemovePsm = GetBootCompSource(
                args, 'PSMFW', 'PsmMcDepends', 'PsmFWDeployDir', MultiConfDict, system_conffile)
        machine_override_string += '\n# PSM Firmware\n'
        machine_override_string += 'PSM_DEPENDS = "%s"\n' % PsmDepends
        machine_override_string += 'PSM_MCDEPENDS = "%s"\n' % PsmMcDepends
        machine_override_string += 'PSM_FIRMWARE_DEPLOY_DIR = "%s"\n' % PsmDeployDir.rstrip('/')
        if PsmImageName:
            machine_override_string += 'PSM_FIRMWARE_IMAGE_NAME = "%s"\n' % PsmImageName
        if RemovePsm:
            machine_override_string += '\n# Remove the PSMFW from Boot.bin\n'
            machine_override_string += 'BIF_PARTITION_ATTR:remove = "psmfw"\n'

    if 'AsuMcDepends' in MultiConfDict:
        AsuDepends, AsuMcDepends, AsuDeployDir, AsuImageName, RemoveAsu = GetBootCompSource(
                args, 'ASU', 'AsuMcDepends', 'AsuFWDeployDir', MultiConfDict, system_conffile)
        machine_override_string += '\n# ASU Firmware\n'
        machine_override_string += 'ASU_DEPENDS = "%s"\n' % AsuDepends
        machine_override_string += 'ASU_MCDEPENDS = "%s"\n' % AsuMcDepends
        machine_override_string += 'ASU_DEPLOY_DIR = "%s"\n' % AsuDeployDir.rstrip('/')
        if AsuImageName:
            machine_override_string += 'ASU_FIRMWARE_IMAGE_NAME = "%s"\n' % AsuImageName
        if RemoveAsu:
            machine_override_string += '\n# Remove the ASU from Boot.bin\n'
            machine_override_string += 'BIF_PARTITION_ATTR:remove = "asufw"\n'

    return machine_override_string

def GetSerialConsoleFromSyshw():
    ''' Derive the 'From SDT' console from the syshw /chosen stdout-path
    (e.g. 'serial1:115200n8'): resolve the 'serialN' alias to its 'tty_device'.
    Returns ('<baud>;<tty>', baudrate) or ('', '') if undetermined. '''
    global syshw_data
    chosen = syshw_data.get('chosen', {}) or {}
    stdout_path = str(chosen.get('stdout-path', '') or '')
    if not stdout_path:
        return '', ''
    # stdout-path form: '<alias-or-path>:<baud>n8' (the ':<options>' part is
    # optional). Split off the reference and pull the baudrate from the options.
    ref, _, options = stdout_path.partition(':')
    baud_match = re.search(r'[0-9]+', options)
    baudrate = baud_match.group(0) if baud_match else '115200'
    # Resolve the referenced serial node to its tty device name. The reference
    # is normally a 'serialN' alias; fall back to matching the DT node path.
    tty_device = ''
    for _, slave_data in common_utils.IterSyshwSlaves(syshw_data, 'serial'):
        if ref in (slave_data.get('aliases', []) or []) or \
                ref == slave_data.get('dt_node'):
            tty_device = str(slave_data.get('tty_device', '') or '')
            break
    if not tty_device:
        return '', ''
    return '%s;%s' % (baudrate, tty_device), baudrate


def SerialConsoleSettings(system_conffile, soc_family=''):
    serialname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_', system_conffile,
                                             'choice', '_SELECT=y')
    serial_console = ''
    baudrate = ''
    if serialname == 'FROM_SDT':
        # Console is defined by the SDT, derive it from the syshw chosen node
        serial_console, baudrate = GetSerialConsoleFromSyshw()
        if not serial_console:
            # The syshw chosen node carried no resolvable stdout-path. Fall back
            # to serial0 with the SoC-default tty so the image still gets a
            # login console instead of none. The tty prefix is SoC-determined.
            soc_tty = {'zynq': 'ttyPS0', 'zynqmp': 'ttyPS0',
                       'versal': 'ttyAMA0', 'versal-net': 'ttyAMA0',
                       'versal-2ve-2vm': 'ttyAMA0', 'versal-2vp': 'ttyAMA0',
                       'microblaze-v': 'ttyUL0'}
            tty = soc_tty.get(soc_family, 'ttyPS0')
            baudrate = '115200'
            serial_console = '%s;%s' % (baudrate, tty)
            logger.warning('Serial set to "From SDT" but no console could be '
                           'derived from the syshw chosen node; '
                           'defaulting to serial0 (%s).' % tty)
        return serial_console, baudrate
    if serialname and serialname != 'MANUAL':
        baudrate = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_%s_BAUDRATE_'
                                               % serialname, system_conffile, 'choice', '=y')
        # Resolve the selected UART's tty device from the syshw data. The
        # selection token matches the (bankless) serial slave name.
        serial_slave = serialname.lower()
        for slave_name, slave_data in common_utils.IterSyshwSlaves(syshw_data, 'serial'):
            if re.sub('_bankless$', '', slave_name) == serial_slave:
                tty_device = str(slave_data.get('tty_device', '') or '')
                if tty_device:
                    serial_console = '%s;%s' % (baudrate, tty_device)
                break
    return serial_console, baudrate


def YoctoSdtZephyrConfigs(MultiConfDict, machine):
    """Zephyr primary-domain machine settings (e.g. 32-bit MicroBlaze-V).
    Returns the board block that precedes the shared CONFIG_DTFILE
    settings. The tune features are reused from the generated microblaze-v.inc
    (required in YoctoSdtConfigs, same as the Linux path). Kept separate from
    the Linux path for now; to be consolidated later.
    """
    board = MultiConfDict.get('ZephyrBoard', '')
    machine_override_string  = ''
    if board:
        machine_override_string += '\n# Zephyr RTOS settings\n'
        machine_override_string += 'ZEPHYR_BOARD = "%s"\n' % board
        machine_override_string += 'ARCH = "riscv32"\n'
    machine_override_string += '\n# Warn if this machine is used with a non-Zephyr DISTRO\n'
    # The generic machine include (which inherits xilinx-deprecated in
    # meta-xilinx) is skipped for the Zephyr domain, so inherit it here to
    # activate the XILINX_DEPRECATED warning below.
    machine_override_string += 'INHERIT += "xilinx-deprecated"\n'
    machine_override_string += ('XILINX_DEPRECATED[%s] = "${@\'This configuration is only '
                                'intended for use with DISTRO set to amd-zephyr.  It will '
                                'likely fail with other configurations.\' '
                                'if (d.getVar(\'DISTRO\') != \'amd-zephyr\') else \'\'}"\n'
                                % machine)
    return machine_override_string


def GetSdtDomainConfig(args, MultiConfDict, machine):
    """Return the domain-specific machine settings, selected by the
    authoritative 'PrimaryOs' key (defaults to Linux when unset). Carries the
    device-tree data plus 'emits_*' capability flags gating optional blocks.
    """
    if MultiConfDict.get('PrimaryOs') == 'zephyr':
        board_kconfig = MultiConfDict.get('ZephyrBoardKconfigDefconfig', '')
        post_dtfile = ''
        if board_kconfig:
            post_dtfile = ('ZEPHYR_SDT_BOARD_KCONFIG_DEFCONFIG = '
                           '"${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(board_kconfig))
        return {
            'primary_os': 'zephyr',
            'dtfile': MultiConfDict.get('ZephyrDT', ''),
            'pre_dtfile': YoctoSdtZephyrConfigs(MultiConfDict, machine),
            'post_dtfile': post_dtfile,
            'defaulttune': MultiConfDict.get('ZephyrDefaultTune', ''),
            'emits_dtb_path': False,
            'emits_serial': False,
            'emits_uboot_kernel': False,
            'emits_generic_require': False,
            'emits_bootfw': False,
            'opensbi': False,
        }
    return {
        'primary_os': 'linux',
        'dtfile': MultiConfDict.get('LinuxDT', ''),
        'pre_dtfile': '',
        'post_dtfile': '',
        'defaulttune': '',
        'emits_dtb_path': True,
        'emits_serial': True,
        'emits_uboot_kernel': True,
        'emits_generic_require': True,
        'emits_bootfw': True,
        'opensbi': args.soc_family == 'microblaze-v',
    }


def YoctoSdtConfigs(args, arch, system_conffile, req_conf_file,
                    MultiConfDict, machine_override_string, machine):

    domain_config = GetSdtDomainConfig(args, MultiConfDict, machine)

    if args.soc_family == 'microblaze-v':
        machine_override_string += '\n# MicroBlaze V Tune features Settings\n'
        # Set DEFAULTTUNE before the tune include so it selects the right tune.
        if domain_config.get('defaulttune'):
            machine_override_string += 'DEFAULTTUNE = "%s"\n' % domain_config['defaulttune']
        machine_override_string += f'require {os.path.join("conf", "machine", "include", args.machine, "microblaze-v.inc")}\n'

    machine_override_string += domain_config.get('pre_dtfile', '')

    config_dtfile = domain_config.get('dtfile', '')
    config_dtfile_dir = os.path.relpath(args.dts_path, start=args.config_dir)

    machine_override_string += '\n# Set the default (%s) domain device tree\n' % domain_config.get('primary_os', 'linux')
    machine_override_string += 'CONFIG_DTFILE_DIR := "${@bb.utils.which(d.getVar(\'BBPATH\'), \'conf/%s\')}"\n' % config_dtfile_dir
    if config_dtfile:
        machine_override_string += 'CONFIG_DTFILE ?= "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(config_dtfile)
    machine_override_string += 'CONFIG_DTFILE[vardepsexclude] += "CONFIG_DTFILE_DIR"\n'

    machine_override_string += domain_config.get('post_dtfile', '')

    # The device tree blob, serial getty and the u-boot/kernel variables below
    # are Linux/u-boot specific; each is gated by its domain capability flag.
    if domain_config.get('emits_dtb_path'):
        machine_override_string += '\nDTB_FILE_PATH ?= "${RECIPE_SYSROOT}/boot/devicetree/${@os.path.basename(d.getVar(\'CONFIG_DTFILE\').replace(\'.dts\', \'.dtb\'))}"\n'

    if domain_config.get('emits_serial'):
        serial_console, baudrate = SerialConsoleSettings(system_conffile,
                                                         soc_family=args.soc_family)
        if serial_console:
            machine_override_string += '\n# Serial Console Settings\n'
            machine_override_string += 'SERIAL_CONSOLES ?= "%s"\n' % serial_console

    if domain_config.get('emits_uboot_kernel'):
        machine_override_string += YoctoCommonConfigs(args, arch, system_conffile, MultiConfDict)

    # Add YAML pre yocto configs
    machine_override_string = UpdateYamlConfigs('pre', machine_override_string)

    # Variables that changes based on hw design or board specific requirement must be
    # defined before calling the required inclusion file else pre-expansion value
    # defined in respective generic machine conf will be set.
    # The generic machine include is Linux/u-boot oriented and is gated by the
    # domain capability flag.
    if domain_config.get('emits_generic_require'):
        machine_override_string += '\n# Required generic machine inclusion\n'
        machine_override_string += 'require conf/machine/%s\n' % \
            req_conf_file

    # Add QEMU memory configuration if applicable
    qemu_memory = GetQemuMemCfg(args.work, args.dts_path, args.hw_file)
    if qemu_memory:
        machine_override_string += '\n# QEMU Memory Configuration\n'
        machine_override_string += qemu_memory

    # Add YAML post yocto configs
    machine_override_string = UpdateYamlConfigs('post', machine_override_string)

    if domain_config.get('opensbi'):
        machine_override_string += '\n# Yocto Riscv OPENSBI variables\n'
        ddr_baseaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_', system_conffile,
                                                   'asterisk', '_BASEADDR=')
        if not ddr_baseaddr:
            ddr_baseaddr = '0x0'
        machine_override_string += f'RISCV_SBI_FW_TEXT_START = "{ddr_baseaddr}"\n'

    machine_override_string += '\n# This is an \'SDT\' based BSP\n'
    machine_override_string += 'XILINX_WITH_ESW = "sdt"\n'

    # Handle the URL passed to us
    machine_override_string += '\n# Original SDT artifacts URL\n'
    machine_override_string += 'SDT_URI = "%s"\n' % args.src_uri
    # A local directory could be used instead
    if hasattr(args, 'sha256sum'):
        machine_override_string += 'SDT_URI[sha256sum] = "%s"\n' % args.sha256sum
    if args.s_dir:
        machine_override_string += 'SDT_URI[S] = "%s"\n' % os.path.join("${UNPACKDIR}", args.s_dir).rstrip('/')

    if args.psu_init_path != os.path.dirname(args.hw_file):
        machine_override_string += '\n# Custom PSU_INIT_PATH artifacts URL\n'
        machine_override_string += 'PSU_INIT_PATH = "%s"\n' % args.psu_init_path.rstrip('/')

    # The system_dt_dir is constructed by the sdt-artifacts recipe, it copies
    # the contents of 'S' (SDT_URI[S] above) into the target 
    # ${datadir}/sdt/${MACHINE}/%s directory.
    #
    # Generally this means that the path will be EMPTY or a 'short' value for a directory
    system_dt_file = ("${RECIPE_SYSROOT}${datadir}/sdt/${MACHINE}/%s" % '').rstrip('/')

    if domain_config.get('emits_dtb_path'):
        machine_override_string += '\n# Set the system device trees\n'
        machine_override_string += 'SYSTEM_DTFILE_DEPENDS = "sdt-artifacts"\n'
        machine_override_string += 'SYSTEM_DTFILE_DIR = "%s"\n' % system_dt_file
        machine_override_string += 'SYSTEM_DTFILE = "${SYSTEM_DTFILE_DIR}/%s"\n' % \
                                   os.path.basename(args.hw_file)

    if args.soc_family != 'microblaze-v':
        machine_override_string += '\n# Load the dynamic machine features\n'
        machine_override_string += 'include conf/machine/include/%s/${BB_CURRENT_MC}-features.conf\n' % args.machine
        machine_override_string += 'LIBXIL_CONFIG = "conf/machine/include/%s/${BB_CURRENT_MC}-libxil.conf"\n' % args.machine

    # Determine FPGA image type based on SoC family and device
    if args.soc_family == 'microblaze-v':
        # Mb-V Ultrascale+ uses PDI, 7 Series uses BIT
        fpga_image_type = 'pdi' if args.device_id.startswith('xcsu') else 'bit'
    elif args.soc_family in ['zynq', 'zynqmp']:
        fpga_image_type = 'bit'
    elif args.soc_family in ['versal', 'versal-2ve-2vm', 'versal-2vp']:
        fpga_image_type = 'pdi'
    else:
        fpga_image_type = ''

    if fpga_image_type == 'pdi':
        if os.path.isdir(args.pl):
            pdis = glob.glob(os.path.join(args.pl, '*.pdi'))
            if not pdis:
                raise Exception('Unable to find a pdi file in %s, \
                        use the -p/--pl option to point to the directory containing a .pdi file' % args.pl)
            elif len(pdis) > 1:
                # To handle the segmented flow where we will have *_boot.pdi and
                # *_pld.pdi and picking up *_boot.pdi for base boot.
                seg_pdis = glob.glob(os.path.join(args.pl, '*_boot.pdi'))
                if seg_pdis:
                    logger.warning(
                        'Multiple PDI files found, using *_boot.pdi for segmented configuration %s', seg_pdis[0])
                    pdis = seg_pdis
                else:
                    logger.warning(
                        'Multiple PDI files found, using the first available pdi %s', pdis[0])
            args.pl = pdis[0]
        if args.pl:
            # This is similar to SYSTEM_DTFILE_PATH, the path is constructed
            # by the sdt-artifacts recipe, it copies the contents of 'S'
            # (SDT_URI[S] above) into the target ${datadir}/sdt/${MACHINE}/%s
            # directory.
            #
            # Generally this means that the path will be EMPTY or a 'short' value for a directory
            pdi_path_dir = ("${RECIPE_SYSROOT}${datadir}/sdt/${MACHINE}/%s" % '').rstrip('/')

            machine_override_string += '\n# PDI variables\n'
            machine_override_string += 'PDI_PATH_DEPENDS = "sdt-artifacts"\n'
            machine_override_string += 'PDI_PATH_DIR = "%s"\n' % pdi_path_dir
            machine_override_string += 'PDI_PATH = "${PDI_PATH_DIR}/%s"\n' % \
                                       os.path.basename(args.pl)

    if fpga_image_type == 'bit' and not args.gen_pl_overlay:
        if os.path.isdir(args.pl):
            bit = glob.glob(os.path.join(args.pl, '*.bit'))
            if not bit:
                logger.warning('Unable to find a bit file in %s, \
                        use the -p/--pl option to point to the directory containing a .bit file' % args.pl)
            elif len(bit) > 1:
                raise Exception('Multiple bit files found in %s, \
                        use the -p/--pl option to point to the directory containing a .bit file' % args.pl)
            elif len(bit) == 1:
                # Some Zynq and ZynqMP design can only PS without PL, in such
                # cases do not include BITSTREAM_PATH.
                args.pl = bit[0]
        if args.pl:
            # This is similar to SYSTEM_DTFILE_PATH, the path is constructed
            # by the sdt-artifacts recipe, it copies the contents of 'S'
            # (SDT_URI[S] above) into the target ${datadir}/sdt/${MACHINE}/%s
            # directory.
            #
            # Generally this means that the path will be EMPTY or a 'short' value for a directory
            bitstream_path_dir = ("${RECIPE_SYSROOT}${datadir}/sdt/${MACHINE}/%s" % '').rstrip('/')

            machine_override_string += '\n# %s bitstream path \n' % args.soc_family
            machine_override_string += 'BITSTREAM_PATH_DEPENDS = "sdt-artifacts"\n'
            machine_override_string += 'BITSTREAM_PATH_DIR = "%s"\n' % bitstream_path_dir
            machine_override_string += 'BITSTREAM_PATH = "${BITSTREAM_PATH_DIR}/%s"\n' % \
                                       os.path.basename(args.pl)
    # Bootmode, Boot.bin device tree and boot file remapping are Linux/u-boot
    # boot concepts, gated by the domain capability flag.
    if domain_config.get('emits_bootfw'):
        bootmode_value = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_BOOTMODE_',
                                                        system_conffile, 'choice', '=y')
        # For JTAG bootmode, we want to set the default to empty.
        if bootmode_value == '0':
            bootmode_value = ''
        machine_override_string += '\n# Primary Bootmode value\n'
        machine_override_string += 'DEFAULT_HW_BOOT_MODE = "%s"\n' % bootmode_value

        machine_override_string += '\n# Update bootbin to use proper device tree\n'
        machine_override_string += 'BIF_PARTITION_IMAGE[device-tree] = "${DTB_FILE_PATH}"\n'
        machine_override_string += '\n# Remap boot files to ensure the right device tree is listed first\n'
        machine_override_string += 'IMAGE_BOOT_FILES =+ "devicetree/${@os.path.basename(d.getVar(\'CONFIG_DTFILE\').replace(\'.dts\', \'.dtb\'))}"\n'

    return machine_override_string


YoctoGenericMachines = ('microblaze-v-generic', 'zynq-generic',
                        'zynqmp-generic','versal-generic', 'versal-net-generic', 'versal-2ve-2vm-generic',
                        'versal-2vp-generic')

def GenerateYoctoMachine(args, system_conffile, syshw_file, MultiConfDict=''):
    genmachine_scripts = project_config.GenMachineScriptsPath()
    if not os.path.isfile(system_conffile):
        raise Exception('Failed to generate .conf file, Unable to find config'
                     ' file at: %s' % args.output)
    arch = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ARCH_',
                                       system_conffile, 'choice', '=y').lower()

    global YamlMachineConfs
    YamlMachineConfs = yaml_utils.TemplateYamlData.get('machine', {}) or {}
    soc_family = args.soc_family
    global syshw_data
    syshw_data = common_utils.GetSyshwData(syshw_file)

    # Get the device_id from syshw_data
    args.device_id = '999'
    if 'device_id' in syshw_data.keys():
        args.device_id = syshw_data['device_id']

    # Include user given machine if INCLUDE_MACHINE_NAME set
    req_conf_file = common_utils.GetConfigValue('CONFIG_YOCTO_INCLUDE_MACHINE_NAME',
                                                system_conffile)

    # include soc_family machine file if user not specified.
    if not req_conf_file:
        req_conf_file = '%s-generic' % (soc_family)
        # include versal net if soc_Variant is net
        if soc_family == 'versal' and args.soc_variant == 'net':
            req_conf_file = '%s-net-generic' % (soc_family)

    # Get the machine file name from sys config
    yocto_machine_name = common_utils.GetConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                                     system_conffile)
    # Use the sysconfig machine name as yocto machine
    machine_conf_file = yocto_machine_name

    # Check if machine name from sysconfig is generic machine
    # or machine_name and include_machine_name is same then
    # Append device_id/999 to yocto_machine_name
    if machine_conf_file in YoctoGenericMachines or machine_conf_file == req_conf_file:
        machine_conf_file += '-' + args.device_id

    machine_conf_dir = os.path.join(args.config_dir, 'machine')
    common_utils.CreateDir(machine_conf_dir)
    machine_conf_file = machine_conf_file.lower()
    machine_conf_path = os.path.join(machine_conf_dir, machine_conf_file + '.conf')
    machine_override = machine_conf_file

    # Generate the yocto machine if config file changed.
    if not common_utils.FileChanged(args.output, 'SYSTEM_CONF',
                                    system_conffile) and \
            os.path.exists(machine_conf_path):
        return machine_conf_file

    logger.info('Generating machine conf file')
    # Variable for constructing ${MACHINE}.conf files.
    machine_override_string = ''

    # Start of ${MACHINE}-${DEVICE_ID}.conf
    machine_override_string += '#@TYPE: Machine\n'
    machine_override_string += '#@NAME: %s\n' % machine_conf_file
    machine_description = 'Machine configuration for the %s boards.\n' % machine_conf_file
    machine_override_string += '#@DESCRIPTION: %s\n' % YamlMachineConfs.get(
                                                    'description', machine_description)

    if MultiConfDict and 'BBMULTICONFIG' in MultiConfDict and MultiConfDict['BBMULTICONFIG']:
        machine_override_string += '\nBBMULTICONFIG += "%s"\n' % MultiConfDict['BBMULTICONFIG']

    # Add config machine overrides into machine conf file
    overrides = common_utils.GetConfigValue(
        'CONFIG_YOCTO_ADD_OVERRIDES', system_conffile)

    inherit_overrides = ''
    # Add other machine names from yaml if any to MACHINEOVERRIDES
    if yaml_utils.MachineNamesList:
        if machine_conf_file in yaml_utils.MachineNamesList:
            yaml_utils.MachineNamesList.remove(machine_conf_file)
        if yaml_utils.MachineNamesList:
            inherit_overrides = ' '.join(yaml_utils.MachineNamesList)
            if overrides:
                overrides = overrides + ':'
            overrides = overrides + inherit_overrides

    if overrides:
        overrides = overrides.replace(' ', ':')
        machine_override_string += 'MACHINEOVERRIDES .= ":%s"\n' % overrides

    machine_override_string += '\n#### Preamble\n'
    machine_override_string += 'MACHINEOVERRIDES =. "'"${@['', '%s:']['%s' !=" \
                               "'${MACHINE}']}"'"\n'\
                               % (machine_conf_file, machine_conf_file)
    machine_override_string += '#### Regular settings follow\n'

    machine_override_string += YoctoMCFimwareConfigs(args, arch,
                                                     system_conffile, req_conf_file, MultiConfDict)
    # Required conf file ext can be .inc or .conf
    # add check and modify
    req_ext = os.path.splitext(req_conf_file)[1]
    if not req_ext and req_ext not in ('.inc', '.conf'):
        req_conf_file = req_conf_file + '.conf'

    if args.hw_flow == 'sdt':
        machine_override_string = YoctoSdtConfigs(args, arch,
                                                  system_conffile, req_conf_file,
                                                  MultiConfDict, machine_override_string,
                                                  machine_conf_file)
    # Add PACKAGE_EXTRA_ARCHS for inherit machine overrides
    if inherit_overrides:
        package_archs = inherit_overrides.replace('-', '_')
        machine_override_string += f'PACKAGE_EXTRA_ARCHS:append = " {package_archs}"\n'

    machine_override_string += '\n#### No additional settings should be after '\
        'the Postamble\n'
    machine_override_string += '#### Postamble\n'
    machine_override_string += 'PACKAGE_EXTRA_ARCHS:append = "'"${@['', " \
                               "' %s']['%s' != '${MACHINE}']}"'"\n'\
                               % (machine_conf_file.replace('-', '_'),
                                  machine_conf_file)

    with open(machine_conf_path, 'w') as machine_override_conf_f:
        machine_override_conf_f.write(machine_override_string)

    return machine_conf_file
