#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import os
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


def YoctoCommonConfigs(args, arch, system_conffile):
    machine_features = ''
    machine_override_string = ''
    is_fpga_manager = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_FPGA_MANAGER', system_conffile)
    if is_fpga_manager == 'y':
        machine_features = ' fpga-overlay'

    if CheckIP('vdu', system_conffile):
        machine_features += ' vdu'

    if machine_features:
        machine_override_string += '\n# Yocto MACHINE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_FEATURES += "%s"\n' % (
            machine_features.strip())

    return machine_override_string


def YoctoXsctConfigs(args, arch, dtg_machine, system_conffile, req_conf_file):
    soc_family = args.soc_family
    soc_variant = args.soc_variant
    machine_override_string = '\n# Yocto device-tree variables\n'
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

    if arch == 'aarch64':
        baseaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_',
                                               system_conffile, 'asterisk', '_BASEADDR=')
        machine_override_string += '\n# Yocto arm-trusted-firmware(TF-A) variables\n'
        atf_serial_ip_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_SERIAL_TF-A_IP_NAME',
                                                         system_conffile)
        atf_serial_manual = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_TF-A_SERIAL_MANUAL_SELECT',
                                                        system_conffile)
        if not atf_serial_manual:
            machine_override_string += 'ATF_CONSOLE ?= "%s"\n' % atf_serial_ip_name
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

    machine_override_string += '\n# Yocto KERNEL Variables\n'
    # Additional kernel make command-line arguments
    if soc_family == 'microblaze':
        kernel_loadaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_',
                                                      system_conffile, 'asterisk', '_BASEADDR=')
    else:
        kernel_baseaddr = '0x0'
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
                serial_no = serialname.lower().split(serialipname + '_')[1]
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
    # Variables that changes based on hw design or board specific requirement must be
    # defined before calling the required inclusion file else pre-expansion value
    # defined in respective generic machine conf will be set.
    machine_override_string += '\n# Required generic machine inclusion\n'
    machine_override_string += 'require conf/machine/%s.conf\n' % \
        req_conf_file

    # Variable used for Vivado XSA path, name using local file or subversion
    # path
    machine_override_string += '\n# Add system XSA\n'
    machine_override_string += 'HDF_EXT = "xsa"\n'
    machine_override_string += 'HDF_BASE = "file://"\n'
    machine_override_string += 'HDF_PATH = "%s"\n' % args.hw_file

    # Set Tune Features for MicroBlaze
    if soc_family == 'microblaze':
        tune_settings = GetTuneFeatures(soc_family, system_conffile)
        # MicroBlaze Tune features Settings
        machine_override_string += '\n# MicroBlaze Tune features Settings\n'
        machine_override_string += 'TUNE_FEATURES:tune-microblaze = "%s"\n' \
                                   % tune_settings

    if soc_variant == 'ev' and soc_family == 'zynqmp':
        machine_override_string += '\n# Yocto IMAGE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_HWCODECS = "libomxil-xlnx"\n'
        machine_override_string += 'IMAGE_FEATURES += "hwcodecs"\n'

    machine_override_string += YoctoCommonConfigs(args, arch, system_conffile)

    return machine_override_string


def YoctoSdtConfigs(args, arch, dtg_machine, system_conffile, req_conf_file, MultiConfDict):
    machine_override_string = ''
    if args.soc_family == 'zynqmp':
        machine_override_string += 'TUNEFILE[microblaze-pmu] = "%s"\n' % (
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze.inc'))
    elif args.soc_family == 'versal':
        machine_override_string += 'TUNEFILE[microblaze-pmc] = "%s"\n' % (
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze.inc'))
        machine_override_string += 'TUNEFILE[microblaze-psm] = "%s"\n' % (
            os.path.join('conf', 'machine', 'include', args.machine, 'microblaze.inc'))

    machine_override_string += '\n# Set the default (linux) domain device tree\n'
    machine_override_string += 'CONFIG_DTFILE_DIR = "%s"\n' % os.path.dirname(
        MultiConfDict.get('LinuxDT'))
    machine_override_string += 'CONFIG_DTFILE ?= "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(
        MultiConfDict.get('LinuxDT'))
    machine_override_string += 'CONFIG_DTFILE[vardepsexclude] += "CONFIG_DTFILE_DIR"\n'

    machine_override_string += '\n# Required generic machine inclusion\n'
    machine_override_string += 'require conf/machine/%s.conf\n' % \
        req_conf_file
    machine_override_string += '\n# System Device Tree does not use HDF_MACHINE\n'
    machine_override_string += 'HDF_MACHINE = ""\n'

    machine_override_string += '\n# Set the system device trees\n'
    machine_override_string += 'SYSTEM_DTFILE_DIR = "%s"\n' % os.path.dirname(
        args.hw_file)
    machine_override_string += 'SYSTEM_DTFILE = "${SYSTEM_DTFILE_DIR}/%s"\n' % os.path.basename(
        args.hw_file)
    machine_override_string += 'SYSTEM_DTFILE[vardepsexclude] += "SYSTEM_DTFILE_DIR"\n'

    machine_override_string += '\n# Load the dynamic machine features\n'
    machine_override_string += 'include conf/machine/include/%s/${BB_CURRENT_MC}-features.conf\n' % args.machine
    machine_override_string += 'LIBXIL_CONFIG = "conf/machine/include/%s/${BB_CURRENT_MC}-libxil.conf"\n' % args.machine

    if MultiConfDict.get('FsblMcDepends'):
        machine_override_string += '\n# First Stage Boot Loader\n'
        machine_override_string += 'FSBL_DEPENDS = ""\n'
        machine_override_string += 'FSBL_MCDEPENDS = "%s"\n' % MultiConfDict.get(
            'FsblMcDepends')
        machine_override_string += 'FSBL_DEPLOY_DIR = "%s"\n' % MultiConfDict.get(
            'FsblDeployDir')

    if MultiConfDict.get('R5FsblMcDepends'):
        machine_override_string += '\n# Cortex-R5 First Stage Boot Loader\n'
        machine_override_string += 'R5FSBL_DEPENDS = ""\n'
        machine_override_string += 'R5FSBL_MCDEPENDS = "%s"\n' % MultiConfDict.get(
            'R5FsblMcDepends')
        machine_override_string += 'R5FSBL_DEPLOY_DIR = "%s"\n' % MultiConfDict.get(
            'R5FsblDeployDir')

    if MultiConfDict.get('PmuMcDepends'):
        machine_override_string += '\n# PMU Firware\n'
        machine_override_string += 'PMU_DEPENDS = ""\n'
        machine_override_string += 'PMU_MCDEPENDS = "%s"\n' % MultiConfDict.get(
            'PmuMcDepends')
        machine_override_string += 'PMU_FIRMWARE_DEPLOY_DIR = "%s"\n' % MultiConfDict.get(
            'PmuFWDeployDir')

    if MultiConfDict.get('PlmMcDepends'):
        machine_override_string += '\n# Platform Loader and Manager\n'
        machine_override_string += 'PLM_DEPENDS = ""\n'
        machine_override_string += 'PLM_MCDEPENDS = "%s"\n' % MultiConfDict.get(
            'PlmMcDepends')
        machine_override_string += 'PLM_DEPLOY_DIR = "%s"\n' % MultiConfDict.get(
            'PlmDeployDir')

    if MultiConfDict.get('PsmMcDepends'):
        machine_override_string += '\n# PSM Firware\n'
        machine_override_string += 'PSM_DEPENDS = ""\n'
        machine_override_string += 'PSM_MCDEPENDS = "%s"\n' % MultiConfDict.get(
            'PsmMcDepends')
        machine_override_string += 'PSM_FIRMWARE_DEPLOY_DIR = "%s"\n' % MultiConfDict.get(
            'PsmFWDeployDir')

    if args.soc_family == 'versal':
        if os.path.isdir(args.fpga):
            pdis = glob.glob(os.path.join(args.fpga, '*.pdi'))
            if not pdis:
                raise Exception('Unable to find a pdi file in %s, \
                        use the -i/--fpga option to point to the directory containing a .pdi file' % args.fpga)
            elif len(pdis) > 1:
                # To handle the segmented flow where we will have *_boot.pdi and
                # *_pld.pdi and picking up *_boot.pdi for base boot.
                seg_pdis = glob.glob(os.path.join(args.fpga, '*_boot.pdi'))
                if seg_pdis:
                    logger.warning(
                        'Multiple PDI files found, using *_boot.pdi for segmented configuration %s', seg_pdis[0])
                    pdis = seg_pdis
                else:
                    logger.warning(
                        'Multiple PDI files found, using the first available pdi %s', pdis[0])
            args.fpga = pdis[0]
        if args.fpga:
            machine_override_string += '\n# Versal PDI\n'
            machine_override_string += 'PDI_PATH_DIR = "%s"\n' % os.path.dirname(
                args.fpga)
            machine_override_string += 'PDI_PATH = "${PDI_PATH_DIR}/%s"\n' % os.path.basename(
                args.fpga)
            machine_override_string += 'PDI_PATH[vardepsexclude] += "PDI_PATH_DIR"\n'

    machine_override_string += '\n# Exclude MC_TMPDIR_PREFIX from hash calculations\n'
    machine_override_string += 'MC_TMPDIR_PREFIX ??= "${TMPDIR}"\n'
    machine_override_string += 'BB_HASHEXCLUDE_COMMON:append = " MC_TMPDIR_PREFIX"\n'
    machine_override_string += '\n# Update bootbin to use proper device tree\n'
    machine_override_string += 'BIF_PARTITION_IMAGE[device-tree] = "${RECIPE_SYSROOT}/boot/devicetree/${@os.path.basename(d.getVar(\'CONFIG_DTFILE\').replace(\'.dts\', \'.dtb\'))}"\n'
    machine_override_string += '\n# Remap boot files to ensure the right device tree is listed first\n'
    machine_override_string += 'IMAGE_BOOT_FILES =+ "devicetree/${@os.path.basename(d.getVar(\'CONFIG_DTFILE\').replace(\'.dts\', \'.dtb\'))}"\n'

    machine_override_string += YoctoCommonConfigs(args, arch, system_conffile)

    return machine_override_string


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
    device_id = ''
    if 'device_id' in plnx_syshw_data.keys():
        device_id = plnx_syshw_data['device_id']

    soc_variant = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_VARIANT_%s'
                                              % soc_family.upper(),
                                              system_conffile, 'choice').lower()

    # Include user given machine if INCLUDE_MACHINE_NAME set
    req_conf_file = common_utils.GetConfigValue('CONFIG_YOCTO_INCLUDE_MACHINE_NAME',
                                                system_conffile)

    # Include soc_variant specific generic machine if soc_variant found
    # if not, include soc_family machine file.
    if not req_conf_file:
        if soc_variant:
            req_conf_file = '%s-%s-generic' % (soc_family, soc_variant)
        else:
            req_conf_file = '%s-generic' % (soc_family)

    # Machine conf json file
    import json
    machinejson_file = os.path.join(
        genmachine_scripts, 'data', 'machineconf.json')
    if not os.path.isfile(machinejson_file):
        raise Exception('Machine json file doesnot exist at: %s' %
                     machinejson_file)
    # Get the machine file name from sys config
    yocto_machine_name = common_utils.GetConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                                     system_conffile)
    dtg_machine = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MACHINE_NAME',
                                              system_conffile)
    # Use the sysconfig machine name as yocto machine
    machine_conf_file = yocto_machine_name
    json_yocto_vars = ''
    # Parse json to string
    with open(machinejson_file, 'r') as data_file:
        machinejson_data = json.load(data_file)
    data_file.close()

    # Get optional machine name from sysconfig and check with json
    if yocto_machine_name and yocto_machine_name in machinejson_data.keys():
        if 'extra-yocto-vars' in machinejson_data[machine_conf_file].keys():
            json_yocto_vars = '\n'.join(var for var in
                                        machinejson_data[machine_conf_file]['extra-yocto-vars'])
    else:
        # Check if machine name from sysconfig is generic machine
        # or machine_name and include_machine_name is same then
        # Append device_id/999 to yocto_machine_name
        if machine_conf_file in machinejson_data['generic-machines'] \
                or machine_conf_file == req_conf_file:
            if device_id:
                machine_conf_file += '-' + device_id
            else:
                machine_conf_file += '-999'
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

    if MultiConfDict:
        multiconfig_min = common_utils.GetConfigValue('CONFIG_YOCTO_BBMC_', system_conffile,
                                                      'choicelist', '=y').lower().replace('_', '-')
        machine_override_string += '\nBBMULTICONFIG += "%s"\n' % multiconfig_min

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

    # Update machine conf file with yocto variabls from json file
    if json_yocto_vars:
        machine_override_string += '\n# Machine specific yocto variables\n'
        machine_override_string += '%s\n' % json_yocto_vars

    if args.hw_flow == 'xsct':
        machine_override_string += YoctoXsctConfigs(args, arch, dtg_machine,
                                                    system_conffile, req_conf_file)
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
