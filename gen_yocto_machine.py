#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

from gen_config import *


def generate_yocto_machine(args, hw_flow):
    logger.info('Generating machine conf file')
    global default_cfgfile
    default_cfgfile = os.path.join(args.output, 'config')
    if not os.path.isfile(default_cfgfile):
        logger.error('Failed to generate .conf file, Unable to find config'
                     ' file at: %s' % args.output)
        sys.exit(255)
    arch = get_config_value('CONFIG_SUBSYSTEM_ARCH_',
                            default_cfgfile, 'choice', '=y').lower()

    soc_family = args.soc_family
    import yaml
    if hw_flow == 'xsct':
        plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    else:
        plnx_syshw_file = os.path.join(args.output, 'petalinux_config.yaml')
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()

    # Get the device_id from plnx_syshw_data
    device_id = ''
    if 'device_id' in plnx_syshw_data.keys():
        device_id = plnx_syshw_data['device_id']

    # Get SOC_Family from the xsa device_id for machine generic required
    # inclusion metadata file.
    if device_id.startswith('xcvn'):
        req_conf_file = 'versal-net'
    else:
        req_conf_file = soc_family

    # Machine conf json file
    import json
    machinejson_file = os.path.join(scripts_dir, 'data/machineconf.json')
    if not os.path.isfile(machinejson_file):
        logger.error('Machine json file doesnot exist at: %s' %
                     machinejson_file)
        sys.exit(255)
    # Get the machine file name from sys config
    yocto_machine_name = get_config_value('CONFIG_YOCTO_MACHINE_NAME',
                                          default_cfgfile)
    dtg_machine = get_config_value('CONFIG_SUBSYSTEM_MACHINE_NAME',
                                   default_cfgfile)
    # Use the sysconfig machine name as yocto machine
    machine_conf_file = yocto_machine_name
    machine_conf_path = ''
    dt_board_file = ''
    json_yocto_vars = ''
    board_overrides = ''
    # Parse json to string
    with open(machinejson_file, 'r') as data_file:
        machinejson_data = json.load(data_file)
    data_file.close()

    # Get optional machine name from sysconfig and check with json
    if yocto_machine_name and yocto_machine_name in machinejson_data.keys():
        # These configs includes board dtsi files associated to machine file
        if 'dt-boardfile' in machinejson_data[machine_conf_file].keys():
            dt_board_file = machinejson_data[machine_conf_file]['dt-boardfile']
        if 'machine-overrides' in machinejson_data[machine_conf_file].keys():
            board_overrides = machinejson_data[machine_conf_file]['machine-overrides']
        if 'extra-yocto-vars' in machinejson_data[machine_conf_file].keys():
            json_yocto_vars = '\n'.join(var for var in
                                        machinejson_data[machine_conf_file]['extra-yocto-vars'])
    else:
        # Check if machine name from sysconfig is generic machine
        # Append device_id if its a generic machine
        if yocto_machine_name in machinejson_data['generic-machines']:
            if device_id:
                machine_conf_file += '-' + device_id
            else:
                machine_conf_file += '-999'
    machine_conf_path = os.path.join(args.output, machine_conf_file + '.conf')

    # Variable for constructing ${MACHINE}.conf files.
    machine_override_string = ''

    # Start of ${MACHINE}-${DEVICE_ID}.conf
    machine_override_string += '#@TYPE: Machine\n'
    machine_override_string += '#@NAME: %s\n' % machine_conf_file
    machine_override_string += '#@DESCRIPTION: Machine configuration for the '\
        '%s boards.\n' % machine_conf_file

    if board_overrides:
        machine_override_string += '\n# Compatibility with old BOARD value.\n'
        machine_override_string += 'MACHINEOVERRIDES =. "%s:"\n' % board_overrides

    machine_override_string += '\n#### Preamble\n'
    machine_override_string += 'MACHINEOVERRIDES =. "'"${@['', '%s:']['%s' !=" \
                               "'${MACHINE}']}"'"\n'\
                               % (machine_conf_file, machine_conf_file)
    machine_override_string += '#### Regular settings follow\n'

    machine_override_string += '\n# Required generic machine inclusion\n'
    machine_override_string += 'require conf/machine/%s-generic.conf\n' % \
                               req_conf_file

    # Variable used for Vivado XSA path, name using local file or subversion
    # path
    if hw_flow == 'xsct':
        machine_override_string += '\n# Add system XSA\n'
        machine_override_string += 'HDF_EXT = "xsa"\n'
        machine_override_string += 'HDF_BASE = "file://"\n'
        machine_override_string += 'HDF_PATH = "%s"\n' % \
                                   os.path.abspath(args.hw_description)

    # Set Tune Features for MicroBlaze
    if soc_family == 'microblaze':
        hw_ver = get_mb_hwversion(default_cfgfile)
        if not hw_ver:
            hw_ver = '11.0'
        tune_settings = 'microblaze v%s barrel-shift pattern-compare reorder ' \
                        'divide-hard multiply-high' % hw_ver
        # MicroBlaze Tune features Settings
        machine_override_string += '\n# MicroBlaze Tune features Settings\n'
        machine_override_string += 'TUNE_FEATURES:tune-microblaze = "%s"\n' \
                                   % tune_settings

    soc_variant = get_config_value('CONFIG_SUBSYSTEM_VARIANT_%s'
                                   % soc_family.upper(),
                                   default_cfgfile, 'choice').lower()
    if soc_variant == 'ev' and soc_family == 'zynqmp':
        machine_override_string += 'MACHINE_HWCODECS = "libomxil-xlnx"\n'
        machine_override_string += 'IMAGE_FEATURES += "hwcodecs"\n'
    if soc_variant:
        machine_override_string += 'SOC_VARIANT = "%s"\n' % soc_variant

    # Update machine conf file with yocto variabls from json file
    if json_yocto_vars:
        machine_override_string += '\n# Machine specific yocto variables\n'
        machine_override_string += '%s\n' % json_yocto_vars

    machine_override_string += '\n# Yocto device-tree variables\n'
    serial_manual = get_config_value('CONFIG_SUBSYSTEM_SERIAL_MANUAL_SELECT',
                                     default_cfgfile)
    serial_ipname = get_config_value('CONFIG_SUBSYSTEM_SERIAL_IP_NAME',
                                     default_cfgfile)
    if not serial_manual:
        machine_override_string += 'YAML_CONSOLE_DEVICE_CONFIG:pn-device-tree ?= "%s"\n' \
            % serial_ipname

    memory_manual = get_config_value('CONFIG_SUBSYSTEM_MEMORY_MANUAL_SELECT',
                                     default_cfgfile)
    memory_ipname = get_config_value('CONFIG_SUBSYSTEM_MEMORY_IP_NAME',
                                     default_cfgfile)
    if not memory_manual:
        machine_override_string += 'YAML_MAIN_MEMORY_CONFIG:pn-device-tree = "%s"\n' \
            % memory_ipname

    dt_padding_size = get_config_value('CONFIG_SUBSYSTEM_DTB_PADDING_SIZE',
                                       default_cfgfile)
    machine_override_string += 'DT_PADDING_SIZE:pn-device-tree ?= "%s"\n' \
        % dt_padding_size

    dt_compiler_flags = get_config_value('CONFIG_SUBSYSTEM_DEVICETREE_COMPILER_FLAGS',
                                         default_cfgfile)
    machine_override_string += 'DTC_FLAGS:pn-device-tree ?= "%s"\n' \
        % dt_compiler_flags

    processor_ipname = get_config_value('CONFIG_SUBSYSTEM_PROCESSOR0_IP_NAME',
                                        default_cfgfile)
    if soc_family == 'microblaze':
        machine_override_string += 'XSCTH_PROC:pn-device-tree = "%s"\n' \
            % processor_ipname

    # Set dt board file as per the machine file
    # if config set to template/auto/AUTO
    if dtg_machine:
        if (dtg_machine == 'template' or dtg_machine.lower() == 'auto') \
                and dt_board_file:
            machine_override_string += 'YAML_DT_BOARD_FLAGS = "{BOARD %s}"\n'\
                % dt_board_file
        elif dtg_machine.lower() != 'auto':
            machine_override_string += 'YAML_DT_BOARD_FLAGS = "{BOARD %s}"\n'\
                % dtg_machine

    machine_override_string += '\n# Yocto linux-xlnx variables\n'
    machine_override_string += '\n# Yocto u-boot-xlnx variables\n'
    uboot_config = get_config_value('CONFIG_SUBSYSTEM_UBOOT_CONFIG_TARGET',
                                    default_cfgfile)
    if uboot_config and uboot_config.lower() != 'auto':
        machine_override_string += 'UBOOT_MACHINE ?= "%s"\n' % uboot_config
        machine_override_string += 'HAS_PLATFORM_INIT:append = " %s"\n' \
                                   % uboot_config

    if arch == 'aarch64':
        machine_override_string += '\n# Yocto arm-trusted-firmware(TF-A) variables\n'
        atf_serial_ip_name = get_config_value('CONFIG_SUBSYSTEM_SERIAL_TF-A_IP_NAME',
                                              default_cfgfile)
        atf_serial_manual = get_config_value('CONFIG_SUBSYSTEM_TF-A_SERIAL_MANUAL_SELECT',
                                             default_cfgfile)
        if not atf_serial_manual:
            machine_override_string += 'ATF_CONSOLE ?= "%s"\n' % atf_serial_ip_name
        atf_mem_settings = get_config_value('CONFIG_SUBSYSTEM_TF-A_MEMORY_SETTINGS',
                                            default_cfgfile)
        atf_mem_base = get_config_value('CONFIG_SUBSYSTEM_TF-A_MEM_BASE',
                                        default_cfgfile)
        atf_mem_size = get_config_value('CONFIG_SUBSYSTEM_TF-A_MEM_SIZE',
                                        default_cfgfile)
        if atf_mem_settings:
            machine_override_string += 'ATF_MEM_BASE ?= "%s"\n' % atf_mem_base
            machine_override_string += 'ATF_MEM_SIZE ?= "%s"\n' % atf_mem_size

        atf_extra_settings = get_config_value('CONFIG_SUBSYSTEM_TF-A_EXTRA_COMPILER_FLAGS',
                                              default_cfgfile)
        atf_bl33_load = get_config_value('CONFIG_SUBSYSTEM_PRELOADED_BL33_BASE',
                                         default_cfgfile)
        machine_override_string += 'EXTRA_OEMAKE:append:pn-arm-trusted-firmware'\
                                   ' = " %s PRELOADED_BL33_BASE=%s"\n' \
                                   % (atf_extra_settings, atf_bl33_load)

    if soc_family == 'versal':
        machine_override_string += '\n# Yocto PLM variables\n'
        plm_serial_ip_name = get_config_value('CONFIG_SUBSYSTEM_SERIAL_PLM_IP_NAME',
                                              default_cfgfile)
        plm_serial_manual = get_config_value('CONFIG_SUBSYSTEM_PLM_SERIAL_MANUAL_SELECT',
                                             default_cfgfile)
        if not plm_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-plm-firmware ?= "%s"\n' \
                                       % plm_serial_ip_name
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-plm-firmware ?= "%s"\n' \
                                       % plm_serial_ip_name

    if soc_family == 'zynqmp':
        machine_override_string += '\n# Yocto PMUFW variables\n'
        pmufw_extraflags = get_config_value('CONFIG_SUBSYSTEM_PMUFW_COMPILER_EXTRA_FLAGS',
                                            default_cfgfile)
        machine_override_string += 'YAML_COMPILER_FLAGS:append:pn-pmu-firmware = " %s"\n' \
                                   % pmufw_extraflags
        pmufw_serial_manual = get_config_value('CONFIG_SUBSYSTEM_PMUFW_SERIAL_MANUAL_SELECT',
                                               default_cfgfile)
        pmufw_serial_ipname = get_config_value('CONFIG_SUBSYSTEM_SERIAL_PMUFW_IP_NAME',
                                               default_cfgfile)
        if not pmufw_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-pmu-firmware ?= "%s"\n' \
                                       % pmufw_serial_ipname
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-pmu-firmware ?= "%s"\n' \
                                       % pmufw_serial_ipname

    if soc_family in ['zynqmp', 'zynq']:
        machine_override_string += '\n# Yocto FSBL variables\n'
        fsbl_serial_manual = get_config_value('CONFIG_SUBSYSTEM_FSBL_SERIAL_MANUAL_SELECT',
                                              default_cfgfile)
        fsbl_serial_ipname = get_config_value(
            'CONFIG_SUBSYSTEM_SERIAL_FSBL_IP_NAME', default_cfgfile)
        if not fsbl_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-fsbl-firmware ?= "%s"\n' \
                                       % fsbl_serial_ipname
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-fsbl-firmware ?= "%s"\n' \
                                       % fsbl_serial_ipname

    if soc_family == 'microblaze':
        machine_override_string += '\n# Yocto FS-Boot variables\n'
        fsboot_serial_ipname = get_config_value('CONFIG_SUBSYSTEM_SERIAL_FSBOOT_IP_NAME',
                                                default_cfgfile)
        fsboot_serial_manual = get_config_value('CONFIG_SUBSYSTEM_FSBOOT_SERIAL_MANUAL_SELECT',
                                                default_cfgfile)
        if not fsboot_serial_manual:
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDIN:pn-fs-boot ?= "%s"\n' \
                                       % fsboot_serial_ipname
            machine_override_string += 'YAML_SERIAL_CONSOLE_STDOUT:pn-fs-boot ?= "%s"\n' \
                                       % fsboot_serial_ipname
        fsboot_memory_manual = get_config_value('CONFIG_SUBSYSTEM_MEMORY_MANUAL_SELECT',
                                                default_cfgfile)
        fsboot_memory_ipname = get_config_value('CONFIG_SUBSYSTEM_MEMORY_IP_NAME',
                                                default_cfgfile)
        fsboot_flash_ipname = get_config_value('CONFIG_SUBSYSTEM_FLASH_IP_NAME',
                                               default_cfgfile)
        if not fsboot_memory_manual:
            machine_override_string += 'YAML_MAIN_MEMORY_CONFIG:pn-fs-boot = "%s"\n' \
                                       % fsboot_memory_ipname
            machine_override_string += 'YAML_FLASH_MEMORY_CONFIG:pn-fs-boot = "%s"\n' \
                                       % fsboot_flash_ipname
        processor_ip_name = get_config_value('CONFIG_SUBSYSTEM_PROCESSOR0_IP_NAME',
                                             default_cfgfile)
        machine_override_string += 'XSCTH_PROC:pn-fs-boot = "%s"\n' % processor_ip_name

    machine_features = ''
    is_fpga_manager = get_config_value(
        'CONFIG_SUBSYSTEM_FPGA_MANAGER', default_cfgfile)
    if is_fpga_manager == 'y':
        machine_features = ' fpga-overlay'

    if check_ip('vdu', default_cfgfile):
        machine_features += ' vdu'

    if machine_features:
        machine_override_string += '\n# Yocto MACHINE_FEATURES Variable\n'
        machine_override_string += 'MACHINE_FEATURES += "%s"\n' % (
            machine_features.strip())

    machine_override_string += '\n# Yocto KERNEL Variables\n'
    # Additional kernel make command-line arguments
    if soc_family == 'microblaze':
        kernel_loadaddr = get_config_value('CONFIG_SUBSYSTEM_MEMORY_',
                                           default_cfgfile, 'asterisk', '_BASEADDR=')
    else:
        kernel_baseaddr = get_config_value('CONFIG_SUBSYSTEM_MEMORY_',
                                           default_cfgfile, 'asterisk', '_KERNEL_BASEADDR=')
        if not kernel_baseaddr:
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

    machine_override_string += 'UBOOT_ENTRYPOINT  = "%s"\n' % loadaddr
    machine_override_string += 'UBOOT_LOADADDRESS = "%s"\n' % loadaddr
    machine_override_string += 'KERNEL_EXTRA_ARGS += "LOADADDR=${UBOOT_ENTRYPOINT}"\n'

    if soc_family == 'zynq':
    	machine_override_string += 'KERNEL_EXTRA_ARGS:zynq += "UIMAGE_LOADADDR=${UBOOT_ENTRYPOINT}"\n'

    ddr_baseaddr = get_config_value('CONFIG_SUBSYSTEM_MEMORY_', default_cfgfile,
                                    'asterisk', '_BASEADDR=')
    if not ddr_baseaddr:
        ddr_baseaddr = '0x0'
    machine_override_string += '\n#Set DDR Base address for u-boot-xlnx-scr '\
                               'variables\n'
    machine_override_string += 'DDR_BASEADDR = "%s"\n' % ddr_baseaddr
    skip_append_baseaddr = get_config_value('CONFIG_SUBSYSTEM_UBOOT_APPEND_BASEADDR',
                                            default_cfgfile)
    if skip_append_baseaddr:
        machine_override_string += 'SKIP_APPEND_BASEADDR = "0"\n'
    else:
        machine_override_string += 'SKIP_APPEND_BASEADDR = "1"\n'

    serialname = get_config_value('CONFIG_SUBSYSTEM_SERIAL_', default_cfgfile,
                                  'choice', '_SELECT=y')
    if serialname != 'MANUAL':
        serialipname = get_ipproperty(serialname, default_cfgfile)
        baudrate = get_config_value('CONFIG_SUBSYSTEM_SERIAL_%s_BAUDRATE_'
                                    % serialname, default_cfgfile, 'choice', '=y')
        if serialipname == 'axi_uartlite' or serialipname == 'mdm':
            serial_console = '%s;ttyUL0' % baudrate
        elif serialipname == 'axi_uart16550':
            serial_console = '%s;ttyS0' % baudrate
        elif serialipname == 'psv_sbsauart' or serialipname == 'psx_sbsauart':
            serial_console = '%s;ttyAMA0' % baudrate
        else:
            serial_console = '%s;ttyPS0' % baudrate

        machine_override_string += '\n# %s Serial Console \n' \
                                   % machine_conf_file
        # parse the selected serial IP if no_alias selected to get the serial no.
        # serial no. will be suffix to the serial ip name Ex:psu_uart_1 -> serial no. is 1.
        no_alias = get_config_value(
            'CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS', default_cfgfile)
        serial_no = ''
        if no_alias == 'y':
            serial_no = serialname.lower().split(serialipname + '_')[1]
            serial_console = serial_console[:-1]
            serial_console = serial_console + serial_no
        machine_override_string += 'SERIAL_CONSOLES = "%s"\n' % serial_console
        machine_override_string += 'SERIAL_CONSOLES_CHECK = "${SERIAL_CONSOLES}"\n'
        machine_override_string += 'YAML_SERIAL_CONSOLE_BAUDRATE = "%s"\n' \
                                   % baudrate

    machine_override_string += '\n#### No additional settings should be after '\
        'the Postamble\n'
    machine_override_string += '#### Postamble\n'
    machine_override_string += 'PACKAGE_EXTRA_ARCHS:append = "'"${@['', " \
                               "'%s']['%s' != '${MACHINE}']}"'"\n'\
                               % (machine_conf_file.replace('-', '_'),
                                  machine_conf_file)

    with open(machine_conf_path, 'w') as machine_override_conf_f:
        machine_override_conf_f.write(machine_override_string)
    machine_override_conf_f.close()
    return machine_conf_file
