#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2025, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import os
import re
import common_utils
import project_config
import glob
from post_process_config import CheckIP, GetIPProperty
import logging


logger = logging.getLogger('Gen-Machineconf')


def GetProcessorProperties(system_conffile, prop):
    processor = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PROCESSOR_', system_conffile, 'choice', '_SELECT=y')
    linux_kernel_properties = ''
    if 'linux_kernel_properties' in plnx_syshw_data['processor'][processor].keys():
        linux_kernel_properties = plnx_syshw_data['processor'][processor]['linux_kernel_properties']
    if linux_kernel_properties and prop in linux_kernel_properties.keys():
        return linux_kernel_properties[prop].split(' ')[0]
    return ''


Tunefeatures = {
    'XILINX_MICROBLAZE0_USE_PCMP_INSTR': {'1': 'pattern-compare'},
    'XILINX_MICROBLAZE0_USE_BARREL': {'1': 'barrel-shift'},
    'XILINX_MICROBLAZE0_USE_DIV': {'1': 'divide-hard'},
    'XILINX_MICROBLAZE0_USE_HW_MUL': {'1': 'multiply-low', '2': 'multiply-high'},
    'XILINX_MICROBLAZE0_USE_FPU': {'1': 'fpu-hard', '2': 'fpu-hard-extended', 'default': 'fpu-soft'},
    'XILINX_MICROBLAZE0_ENDIANNESS': {'!1': 'bigendian'},
    'XILINX_MICROBLAZE0_DATASIZE': {'64': '64-bit'},
    'XILINX_MICROBLAZE0_USE_REORDER_INSTR': {'!0': 'reorder'},
    'XILINX_MICROBLAZE0_AREA_OPTIMIZED': {'2': 'frequency-optimized'}
}


def GetTuneFeatures(soc_family, system_conffile):
    processor = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PROCESSOR_', system_conffile, 'choice', '_SELECT=y')
    tune_features = [soc_family]
    hwversion = GetProcessorProperties(
        system_conffile, 'XILINX_MICROBLAZE0_HW_VER')
    if hwversion:
        hwversion = 'v%s' % hwversion
        tune_features += [hwversion]
    for feature in Tunefeatures.keys():
        param_value = GetProcessorProperties(system_conffile, feature)
        add_key = False
        for key in Tunefeatures[feature].keys():
            if key == param_value or (key.startswith('!') and key[1:] != param_value):
                tune_features += [Tunefeatures[feature][key]]
                add_key = True
        # Add default one from dict if key doesnot match
        if not add_key and 'default' in Tunefeatures[feature].keys():
            tune_features += [Tunefeatures[feature]['default']]

    return ' '.join(tune_features)


Machinefeatures_soc = {
    'zynqmp': {
        'dr': 'rfsoc', 'ev': 'mali400 vcu', 'eg': 'mali400'
    },
    'versal': {
        'ai-core': 'vdu', 'ai-edge': 'vdu'
    },
    'versal-2ve-2vm': {
        'common': 'vcu2 malig78ae'
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

    return machine_features

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
            logger.warning('Specified %s elf doesnot found : %s, '
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
            logger.warning('Specified %s elf doesnot found : %s, '
                    'Make sure you specified proper .elf file' % (comp, tmp_path))
    else:
        CompMcDepends = MultiConfDict.get(mcdepends)
        CompDeployDir = MultiConfDict.get(deploydir)

    return CompDepends, CompMcDepends, CompDeployDir, CompImageName, RemoveComp


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
            machine_override_string += 'ATF_MEM_BASE ?= "%s"\n' % atf_mem_base
            machine_override_string += 'ATF_MEM_SIZE ?= "%s"\n' % atf_mem_size

        atf_extra_settings = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_EXTRA_COMPILER_FLAGS',
                                                         system_conffile)
        memory = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_', system_conffile,
                                            'choice', '_SELECT=y')
        atf_bl33_offset = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_%s_U__BOOT_TEXTBASE_OFFSET' % memory,
                                                     system_conffile)
        if atf_extra_settings:
            machine_override_string += 'EXTRA_OEMAKE:append:pn-arm-trusted-firmware'\
                                       ' = " %s"\n' % atf_extra_settings
        if atf_bl33_offset:
            machine_override_string += 'TFA_BL33_LOAD ?= "%s"\n' % atf_bl33_offset

        optee_serial_ip_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_OP-TEE_IP_NAME',
                                                        system_conffile)
        optee_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_OP-TEE_SERIAL_MANUAL_SELECT',
                                                        system_conffile)
        if optee_serial_ip_name and not optee_serial_manual:
            machine_override_string += '\n# Yocto OP-TEE variables\n'
            machine_override_string += 'OPTEE_CONSOLE ?= "%s"\n' % optee_serial_ip_name

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
    # Additional kernel make command-line arguments
    if args.soc_family == 'microblaze':
        kernel_loadaddr = ddr_baseaddr
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

    machine_override_string += 'UBOOT_ENTRYPOINT  ?= "%s"\n' % loadaddr
    machine_override_string += 'UBOOT_LOADADDRESS ?= "%s"\n' % loadaddr

    if arch != 'aarch64':
        machine_override_string += 'KERNEL_EXTRA_ARGS += "UIMAGE_LOADADDR=${UBOOT_ENTRYPOINT}"\n'


    machine_features = GetMachineFeatures(args, system_conffile, MultiConfDict)
    if machine_features:
        machine_override_string += '\n# Yocto MACHINE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_FEATURES += "%s"\n' % (
            machine_features.strip())

    if args.soc_variant == 'ev' and args.soc_family == 'zynqmp':
        machine_override_string += '\n# Yocto IMAGE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_HWCODECS = "libvcu-omxil"\n'
        machine_override_string += 'IMAGE_FEATURES += "hwcodecs"\n'

    return machine_override_string


def YoctoMCFimwareConfigs(args, arch, dtg_machine, system_conffile, req_conf_file, MultiConfDict):
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
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze-riscv.inc'))

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
        machine_override_string += '\n# PMU Firware\n'
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
        machine_override_string += '\n# PSM Firware\n'
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
        machine_override_string += '\n# ASU Firware\n'
        machine_override_string += 'ASU_DEPENDS = "%s"\n' % AsuDepends
        machine_override_string += 'ASU_MCDEPENDS = "%s"\n' % AsuMcDepends
        machine_override_string += 'ASU_DEPLOY_DIR = "%s"\n' % AsuDeployDir.rstrip('/')
        if AsuImageName:
            machine_override_string += 'machine_override_string += "%s"\n' % AsuImageName
        if RemoveAsu:
            machine_override_string += '\n# Remove the ASU from Boot.bin\n'
            machine_override_string += 'BIF_PARTITION_ATTR:remove = "asufw"\n'

    return machine_override_string


def YoctoXsctConfigs(args, arch, dtg_machine, system_conffile, req_conf_file, MultiConfDict):
    machine_override_string = ''

    soc_family = args.soc_family
    soc_variant = args.soc_variant

    # Set Tune Features for MicroBlaze
    if soc_family == 'microblaze':
        tune_settings = GetTuneFeatures(soc_family, system_conffile)
        # MicroBlaze Tune features Settings
        machine_override_string += '\n# MicroBlaze Tune features Settings\n'
        machine_override_string += 'TUNE_FEATURES:tune-microblaze ?= "%s"\n' \
                                   % tune_settings
        machine_override_string += 'DEFAULTTUNE ?= "microblaze"\n'

    machine_override_string += '\n# Yocto device-tree variables\n'
    serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_MANUAL_SELECT',
                                                system_conffile)
    serial_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_IP_NAME',
                                                system_conffile)
    if not serial_manual:
        machine_override_string += 'YAML_CONSOLE_DEVICE_CONFIG:pn-device-tree ?= "%s"\n' \
            % serial_ipname

    memory_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_MANUAL_SELECT',
                                                system_conffile)
    memory_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_IP_NAME',
                                                system_conffile)
    if not memory_manual:
        machine_override_string += 'YAML_MAIN_MEMORY_CONFIG:pn-device-tree ?= "%s"\n' \
            % memory_ipname

    dt_padding_size = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DTB_PADDING_SIZE',
                                                  system_conffile)
    machine_override_string += 'DT_PADDING_SIZE:pn-device-tree ?= "%s"\n' \
        % dt_padding_size

    dt_compiler_flags = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DEVICETREE_COMPILER_FLAGS',
                                                    system_conffile)
    machine_override_string += 'DTC_FLAGS:pn-device-tree ?= "%s"\n' \
        % dt_compiler_flags

    processor_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PROCESSOR0_IP_NAME',
                                                   system_conffile)
    if soc_family == 'microblaze':
        machine_override_string += 'XSCTH_PROC:pn-device-tree ?= "%s"\n' \
            % processor_ipname

    # Set dt board file as per the machine file
    # if config set to template/auto/AUTO
    if dtg_machine:
        if dtg_machine.lower() != 'auto':
            machine_override_string += 'YAML_DT_BOARD_FLAGS ?= "{BOARD %s}"\n'\
                % dtg_machine

    machine_override_string += '\n# Yocto u-boot-xlnx variables\n'
    uboot_config = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_CONFIG_TARGET',
                                               system_conffile)
    if uboot_config and uboot_config.lower() != 'auto':
        machine_override_string += 'UBOOT_MACHINE ?= "%s"\n' % uboot_config

    if soc_family == 'versal':
        machine_override_string += '\n# Yocto PLM variables\n'
        plm_serial_ip_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_PLM_IP_NAME',
                                                         system_conffile)
        plm_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PLM_SERIAL_MANUAL_SELECT',
                                                        system_conffile)
        if not plm_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-plm-firmware ?= "%s"\n' \
                                       % plm_serial_ip_name
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-plm-firmware ?= "%s"\n' \
                                       % plm_serial_ip_name

    if soc_family == 'zynqmp':
        machine_override_string += '\n# Yocto PMUFW variables\n'
        pmufw_extraflags = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PMUFW_COMPILER_EXTRA_FLAGS',
                                                       system_conffile)
        machine_override_string += 'YAML_COMPILER_FLAGS:append:pn-pmu-firmware = " %s"\n' \
                                   % pmufw_extraflags
        pmufw_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PMUFW_SERIAL_MANUAL_SELECT',
                                                          system_conffile)
        pmufw_serial_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_PMUFW_IP_NAME',
                                                          system_conffile)
        if not pmufw_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-pmu-firmware ?= "%s"\n' \
                                       % pmufw_serial_ipname
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-pmu-firmware ?= "%s"\n' \
                                       % pmufw_serial_ipname

    if soc_family in ['zynqmp', 'zynq']:
        machine_override_string += '\n# Yocto FSBL variables\n'
        fsbl_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FSBL_SERIAL_MANUAL_SELECT',
                                                         system_conffile)
        fsbl_serial_ipname = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_SERIAL_FSBL_IP_NAME', system_conffile)
        if not fsbl_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-fsbl-firmware ?= "%s"\n' \
                                       % fsbl_serial_ipname
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-fsbl-firmware ?= "%s"\n' \
                                       % fsbl_serial_ipname

    if soc_family == 'microblaze':
        machine_override_string += '\n# Yocto FS-Boot variables\n'
        fsboot_serial_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_FSBOOT_IP_NAME',
                                                           system_conffile)
        fsboot_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FSBOOT_SERIAL_MANUAL_SELECT',
                                                           system_conffile)
        if not fsboot_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-fs-boot ?= "%s"\n' \
                                       % fsboot_serial_ipname
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-fs-boot ?= "%s"\n' \
                                       % fsboot_serial_ipname
        fsboot_memory_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_MANUAL_SELECT',
                                                           system_conffile)
        fsboot_memory_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_IP_NAME',
                                                           system_conffile)
        fsboot_flash_ipname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FLASH_IP_NAME',
                                                          system_conffile)
        if not fsboot_memory_manual:
            machine_override_string += 'YAML_MAIN_MEMORY_CONFIG:pn-fs-boot ?= "%s"\n' \
                                       % fsboot_memory_ipname
            machine_override_string += 'YAML_FLASH_MEMORY_CONFIG:pn-fs-boot ?= "%s"\n' \
                                       % fsboot_flash_ipname
        processor_ip_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PROCESSOR0_IP_NAME',
                                                        system_conffile)
        machine_override_string += 'XSCTH_PROC:pn-fs-boot ?= "%s"\n' % processor_ip_name

    serialname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_', system_conffile,
                                             'choice', '_SELECT=y')
    if serialname != 'MANUAL':
        serialipname = GetIPProperty(serialname, system_conffile)
        baudrate = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_%s_BAUDRATE_'
                                               % serialname, system_conffile, 'choice', '=y')
        if serialipname == 'axi_uartlite' or serialipname == 'mdm':
            serial_console = '%s;ttyUL0' % baudrate
        elif serialipname == 'axi_uart16550':
            serial_console = '%s;ttyS0' % baudrate
        elif serialipname == 'psv_sbsauart' or serialipname == 'psx_sbsauart':
            serial_console = '%s;ttyAMA0' % baudrate
        else:
            serial_console = '%s;ttyPS0' % baudrate

        machine_override_string += '\n# Serial Console Settings\n'
        # parse the selected serial IP if no_alias selected to get the serial no.
        # serial no. will be suffix to the serial ip name Ex:psu_uart_1 -> serial no. is 1.
        no_alias = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS', system_conffile)
        serial_no = ''
        if no_alias == 'y':
            if "_" in serialname:
                try:
                    serial_no = serialname.lower().split(serialipname + '_')[1]
                except IndexError:
                    serial_no = re.findall('[0-9]+', serialname)[0]
                serial_console = serial_console[:-1]
                serial_console = serial_console + serial_no
            else:
                tmp = re.findall('[0-9]+', serialname)
                serial_no = tmp[0]
                serial_console = serial_console[:-1]
                serial_console = serial_console + serial_no
        machine_override_string += 'SERIAL_CONSOLES ?= "%s"\n' % serial_console
        machine_override_string += 'YAML_SERIAL_CONSOLE_BAUDRATE ?= "%s"\n' \
                                   % baudrate

    machine_override_string += YoctoCommonConfigs(args, arch, system_conffile, MultiConfDict)

    # Variables that changes based on hw design or board specific requirement must be
    # defined before calling the required inclusion file else pre-expansion value
    # defined in respective generic machine conf will be set.
    machine_override_string += '\n# Required generic machine inclusion\n'
    machine_override_string += 'require conf/machine/%s.conf\n' % \
        req_conf_file

    machine_override_string += '\n# This is an \'XSCT\' based BSP\n'
    xsct_version = common_utils.Bitbake.getVar('XILINX_XSCT_VERSION')
    if xsct_version:
        machine_override_string += 'XILINX_XSCT_VERSION = "%s"\n' % xsct_version
    machine_override_string += 'XILINX_WITH_ESW = "xsct"\n'

    # Variable used for Vivado XSA path, name using local file or subversion
    # path
    machine_override_string += '\n# Add system XSA\n'
    machine_override_string += 'HDF_URI = "%s"\n' % args.src_uri
    try:
        machine_override_string += 'HDF_URI[sha256sum] = "%s"\n' % args.sha256sum
    except AttributeError:
        raise Exception('XSA workflow requires a sha256sum to have been computed.')
    if args.s_dir:
        machine_override_string += 'HDF_URI[S] = "%s"\n' % os.path.join("${WORKDIR}", args.s_dir).rstrip('/')

    return machine_override_string


def YoctoSdtConfigs(args, arch, dtg_machine, system_conffile, req_conf_file, MultiConfDict):
    machine_override_string = ''

    config_dtfile = MultiConfDict.get('LinuxDT')
    config_dtfile = os.path.relpath(config_dtfile, start=args.config_dir)

    machine_override_string += '\n# Set the default (linux) domain device tree\n'
    machine_override_string += 'CONFIG_DTFILE_DIR := "${@bb.utils.which(d.getVar(\'BBPATH\'), \'conf/%s\')}"\n' % os.path.dirname(config_dtfile)
    machine_override_string += 'CONFIG_DTFILE ?= "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(config_dtfile)
    machine_override_string += 'CONFIG_DTFILE[vardepsexclude] += "CONFIG_DTFILE_DIR"\n'

    machine_override_string += YoctoCommonConfigs(args, arch, system_conffile, MultiConfDict)

    # Variables that changes based on hw design or board specific requirement must be
    # defined before calling the required inclusion file else pre-expansion value
    # defined in respective generic machine conf will be set.
    machine_override_string += '\n# Required generic machine inclusion\n'
    machine_override_string += 'require conf/machine/%s.conf\n' % \
        req_conf_file

    machine_override_string += '\n# This is an \'SDT\' based BSP\n'
    machine_override_string += 'XILINX_WITH_ESW = "sdt"\n'

    # Handle the URL passed to us
    machine_override_string += '\n# Original SDT artifacts URL\n'
    machine_override_string += 'SDT_URI = "%s"\n' % args.src_uri
    # A local directory could be used instead
    if hasattr(args, 'sha256sum'):
        machine_override_string += 'SDT_URI[sha256sum] = "%s"\n' % args.sha256sum
    if args.s_dir:
        machine_override_string += 'SDT_URI[S] = "%s"\n' % os.path.join("${WORKDIR}", args.s_dir).rstrip('/')

    if args.psu_init_path != os.path.dirname(args.hw_file):
        machine_override_string += '\n# Custom PSU_INIT_PATH artifacts URL\n'
        machine_override_string += 'PSU_INIT_PATH = "%s"\n' % args.psu_init_path.rstrip('/')

    # The system_dt_dir is constructed by the sdt-artifacts recipe, it copies
    # the contents of 'S' (SDT_URI[S] above) into the target 
    # ${datadir}/sdt/${MACHINE}/%s directory.
    #
    # Generally this means that the path will be EMPTY or a 'short' value for a directory
    system_dt_file = ("${RECIPE_SYSROOT}${datadir}/sdt/${MACHINE}/%s" % '').rstrip('/')

    machine_override_string += '\n# Set the system device trees\n'
    machine_override_string += 'SYSTEM_DTFILE_DEPENDS = "sdt-artifacts"\n'
    machine_override_string += 'SYSTEM_DTFILE_DIR = "%s"\n' % system_dt_file
    machine_override_string += 'SYSTEM_DTFILE = "${SYSTEM_DTFILE_DIR}/%s"\n' % \
                               os.path.basename(args.hw_file)

    machine_override_string += '\n# Load the dynamic machine features\n'
    machine_override_string += 'include conf/machine/include/%s/${BB_CURRENT_MC}-features.conf\n' % args.machine
    machine_override_string += 'LIBXIL_CONFIG = "conf/machine/include/%s/${BB_CURRENT_MC}-libxil.conf"\n' % args.machine

    if args.soc_family in ('versal', 'versal-2ve-2vm'):
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

            machine_override_string += '\n# Versal PDI\n'
            machine_override_string += 'PDI_PATH_DEPENDS = "sdt-artifacts"\n'
            machine_override_string += 'PDI_PATH_DIR = "%s"\n' % pdi_path_dir
            machine_override_string += 'PDI_PATH = "${PDI_PATH_DIR}/%s"\n' % \
                                       os.path.basename(args.pl)

    if args.soc_family in ['zynqmp', 'zynq'] and not args.gen_pl_overlay:
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
                # cases do not inlcude BITSTREAM_PATH.
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

    machine_override_string += '\n# Update bootbin to use proper device tree\n'
    machine_override_string += 'BIF_PARTITION_IMAGE[device-tree] = "${RECIPE_SYSROOT}/boot/devicetree/${@os.path.basename(d.getVar(\'CONFIG_DTFILE\').replace(\'.dts\', \'.dtb\'))}"\n'
    machine_override_string += '\n# Remap boot files to ensure the right device tree is listed first\n'
    machine_override_string += 'IMAGE_BOOT_FILES =+ "devicetree/${@os.path.basename(d.getVar(\'CONFIG_DTFILE\').replace(\'.dts\', \'.dtb\'))}"\n'

    return machine_override_string


YoctoGenericMachines = ('microblaze-generic', 'zynq-generic',
                        'zynqmp-generic','versal-generic', 'versal-net-generic', 'versal-2ve-2vm-generic')

def GenerateYoctoMachine(args, system_conffile, plnx_syshw_file, MultiConfDict=''):
    genmachine_scripts = project_config.GenMachineScriptsPath()
    if not os.path.isfile(system_conffile):
        raise Exception('Failed to generate .conf file, Unable to find config'
                     ' file at: %s' % args.output)
    arch = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ARCH_',
                                       system_conffile, 'choice', '=y').lower()

    soc_family = args.soc_family
    import yaml
    global plnx_syshw_data
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()

    # Get the device_id from plnx_syshw_data
    device_id = '999'
    if 'device_id' in plnx_syshw_data.keys():
        device_id = plnx_syshw_data['device_id']

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
    dtg_machine = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MACHINE_NAME',
                                              system_conffile)
    # Use the sysconfig machine name as yocto machine
    machine_conf_file = yocto_machine_name

    # Check if machine name from sysconfig is generic machine
    # or machine_name and include_machine_name is same then
    # Append device_id/999 to yocto_machine_name
    if machine_conf_file in YoctoGenericMachines or machine_conf_file == req_conf_file:
        machine_conf_file += '-' + device_id

    machine_conf_dir = os.path.join(args.config_dir, 'machine')
    common_utils.CreateDir(machine_conf_dir)
    machine_conf_file = machine_conf_file.lower()
    machine_conf_path = os.path.join(machine_conf_dir, machine_conf_file + '.conf')
    machine_override = machine_conf_file

    # Generate the yocto machine if config file changed.
    if common_utils.ValidateHashFile(args.output, 'SYSTEM_CONF',
                                     system_conffile, update=False) and \
            os.path.exists(machine_conf_path):
        return machine_conf_file

    logger.info('Generating machine conf file')
    # Variable for constructing ${MACHINE}.conf files.
    machine_override_string = ''

    # Start of ${MACHINE}-${DEVICE_ID}.conf
    machine_override_string += '#@TYPE: Machine\n'
    machine_override_string += '#@NAME: %s\n' % machine_conf_file
    machine_override_string += '#@DESCRIPTION: Machine configuration for the '\
        '%s boards.\n' % machine_conf_file

    if MultiConfDict and 'BBMULTICONFIG' in MultiConfDict and MultiConfDict['BBMULTICONFIG']:
        machine_override_string += '\nBBMULTICONFIG += "%s"\n' % MultiConfDict['BBMULTICONFIG']

    # Add config machine overrides into machine conf file
    overrides = common_utils.GetConfigValue(
        'CONFIG_YOCTO_ADD_OVERRIDES', system_conffile)

    if overrides:
        machine_override_string += 'MACHINEOVERRIDES .= ":%s"\n' % overrides

    machine_override_string += '\n#### Preamble\n'
    machine_override_string += 'MACHINEOVERRIDES =. "'"${@['', '%s:']['%s' !=" \
                               "'${MACHINE}']}"'"\n'\
                               % (machine_conf_file, machine_conf_file)
    machine_override_string += '#### Regular settings follow\n'

    machine_override_string += YoctoMCFimwareConfigs(args, arch, dtg_machine,
                                                     system_conffile, req_conf_file, MultiConfDict)

    if args.hw_flow == 'xsct':
        machine_override_string += YoctoXsctConfigs(args, arch, dtg_machine,
                                                    system_conffile, req_conf_file, MultiConfDict)
    elif args.hw_flow == 'sdt':
        machine_override_string += YoctoSdtConfigs(args, arch, dtg_machine,
                                                   system_conffile, req_conf_file, MultiConfDict)

    machine_override_string += '\n#### No additional settings should be after '\
        'the Postamble\n'
    machine_override_string += '#### Postamble\n'
    machine_override_string += 'PACKAGE_EXTRA_ARCHS:append = "'"${@['', " \
                               "' %s']['%s' != '${MACHINE}']}"'"\n'\
                               % (machine_conf_file.replace('-', '_'),
                                  machine_conf_file)

    with open(machine_conf_path, 'w') as machine_override_conf_f:
        machine_override_conf_f.write(machine_override_string)
    machine_override_conf_f.close()
    return machine_conf_file
