#!/usr/bin/env python3

# Copyright (C) 2023-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import sys
import os
import re
import logging
import common_utils
import yaml_utils
import project_config

logger = logging.getLogger('Gen-Machineconf')


def GenConf_processor(procdata):
    ''' Generate Processor Info as Kconfig'''
    if not procdata:
        raise Exception('ERROR: No CPU can be found in the system. Please review your hardware system. '
              'Valid processors are: microblaze-v, ps7_cortexa9, psu_cortexa53, psv_cortexa72, psx_cortexa78.')
    KconfStr = 'SUBSYSTEM_PROCESSOR'
    confstr = ''
    procconfstr = '\nchoice\n'
    procconfstr += '\tprompt "System Processor"\n'
    procconfstr += '\thelp\n'
    procconfstr += '\tSelect a processor as the system processor.\n'

    for index, proc in enumerate(procdata.keys()):
        confstr += '\nconfig %s%s_IP_NAME\n' % (KconfStr, index)
        confstr += '\tstring\n'
        confstr += '\tdefault %s\n' % proc
        instance_path = procdata[proc].get('instance_path')
        if instance_path:
            confstr += '\nconfig %s%s_INSTANCE_PATH\n' % (KconfStr, index)
            confstr += '\tstring\n'
            confstr += '\tdefault %s\n' % instance_path
        Kprocselect = '%s_%s_SELECT' % (KconfStr, proc)
        procconfstr += '\nconfig %s\n' % Kprocselect
        procconfstr += '\tbool "%s"\n' % proc

    procconfstr += '\nendchoice\n'

    confstr += procconfstr
    return confstr


def GenConf_memory(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate Memory Info as Kconfig'''
    confstr = ''
    memoryconfstr = ''
    memoryconfdefaultstr = ''
    confstr += '\nmenu "Memory Settings"\n'
    confstr += 'choice\n'
    confstr += '\tprompt "Primary Memory"\n'
    confstr += '\t@@DEFAULT_MEMBANK@@\n'
    confstr += '\thelp\n'
    confstr += '\tThe configuration in this menu impacts the\n'
    confstr += '\tmemory settings in the device tree autoconfig files.\n'
    confstr += '\tIf you select "manual",\n'
    confstr += '\tAuto generate the memory node based on user inputs,\n'
    confstr += '\tyou will need to specify base address and memory size.\n'
    confstr += '\tTo skip generating lower or upper memory node specify 0x0 offset to the memory size.\n'
    KconfPrefix = 'SUBSYSTEM_MEMORY'
    DefaultBank = ''
    DefaultBaseAddr = ''
    for slave in IpsToAdd:
        baseaddr = slavesdict[slave].get('baseaddr')
        if isinstance(baseaddr, int):
            baseaddr = hex(baseaddr)
        highaddr = slavesdict[slave].get('highaddr')
        if isinstance(highaddr, int):
            highaddr = hex(highaddr)
        if not baseaddr or not highaddr:
            logger.warning('No memory base address and high address is provided for %s' % slave)
            continue
        banksize = hex((int(highaddr, base=16) - int(baseaddr, base=16)) + 0x01)
        if not int(banksize, base=16) >= 0x2000000:
            continue
        memKconf = '%s_%s' % (KconfPrefix, slave.upper())
        confstr += '\nconfig %s_SELECT\n' % memKconf
        confstr += '\tbool "%s"\n' % slave
        # Check each IP baseaddr and use the lower one as default
        if not DefaultBaseAddr or \
                int(DefaultBaseAddr, base=16) > int(baseaddr, base=16):
            DefaultBaseAddr = baseaddr
            DefaultBank = 'default %s_SELECT\n' % memKconf

        memoryconfstr += '\nconfig %s_BASEADDR\n' % memKconf
        memoryconfstr += '\thex "System memory base address"\n'
        memoryconfstr += '\tdefault %s\n' % baseaddr
        memoryconfstr += '\trange %s %s\n' % (baseaddr,
                                hex(int(highaddr, base=16) - 0x2000000))
        memoryconfstr += '\tdepends on %s_SELECT\n' % memKconf
        memoryconfstr += '\thelp\n'
        memoryconfstr += '\tStart address of the system memory.\n'
        memoryconfstr += '\tIt has to be within the selected primary memory physical address range.\n'
        memoryconfstr += '\tMake sure the DT memory entry should start with provided address.\n'

        memoryconfstr += '\nconfig %s_SIZE\n' % memKconf
        memoryconfstr += '\thex "System memory size"\n'
        memoryconfstr += '\tdefault %s\n' % banksize
        memoryconfstr += '\trange 0x2000000 %s\n' % banksize
        memoryconfstr += '\tdepends on %s_SELECT\n' % memKconf
        memoryconfstr += '\thelp\n'
        memoryconfstr += '\tSize of the system memory. Minimum is 32MB, maximum is the size of\n'
        memoryconfstr += '\tthe selected primary memory physical address range.\n'

        memoryconfstr += '\nconfig %s_U__BOOT_TEXTBASE_OFFSET\n' % memKconf
        memoryconfstr += '\thex "u-boot text base address"\n'
        memoryconfstr += '\tdefault %s if SYSTEM_VERSAL-2VE-2VM\n' % (
            hex(int(baseaddr, base=16) + 0x40000000))
        memoryconfstr += '\tdefault %s if SUBSYSTEM_ARCH_AARCH64\n' % (
            hex(int(baseaddr, base=16) + 0x8000000))
        memoryconfstr += '\tdefault %s if SUBSYSTEM_ARCH_ARM\n' % (
            hex(int(baseaddr, base=16) + 0x4000000))
        memoryconfstr += '\tdefault %s if SUBSYSTEM_ARCH_MICROBLAZE-V\n' % (
            hex(int(baseaddr, base=16) + 0x100000))
        memoryconfstr += '\trange %s %s\n' % (hex(int(baseaddr, base=16) + 0x100000),
                                              hex(int(baseaddr, base=16) + int(highaddr, base=16) - 0x2000000 + 0x100000))
        memoryconfstr += '\tdepends on %s_SELECT\n' % memKconf
        memoryconfstr += '\tdepends on !SUBSYSTEM_COMPONENT_U__BOOT_NAME_NONE\n'
        memoryconfstr += '\thelp\n'
        memoryconfstr += '\tu-boot text base address by specifying from the memory base address.\n'
        memoryconfstr += '\tu-boot load address = bank base address + offset. And same value will\n'
        memoryconfstr += '\tpass to TF-A also. Minimum suggested is 1MB.\n'

        memoryconfdefaultstr += f'\tdefault {slave} if {memKconf}_SELECT\n'

    memoryconfstr += '\nconfig %s_IP_NAME\n' % KconfPrefix
    memoryconfstr += '\tstring\n'
    memoryconfstr += memoryconfdefaultstr

    confstr += '\nconfig %s_MANUAL_SELECT\n' % KconfPrefix
    confstr += '\tbool "manual"\n'
    confstr += '\nendchoice\n'
    confstr = confstr.replace('@@DEFAULT_MEMBANK@@', DefaultBank)

    memoryconfstr += '\nconfig %s_MANUAL_LOWER_BASEADDR\n' % KconfPrefix
    memoryconfstr += '\thex "Lower memory base address"\n'
    memoryconfstr += '\tdefault 0x0\n'
    memoryconfstr += '\tdepends on %s_MANUAL_SELECT\n' % KconfPrefix
    memoryconfstr += '\thelp\n'
    memoryconfstr += '\tbase address of the lower memory\n'
    memoryconfstr += '\tMake sure the DT memory entry should start with provided address.\n'

    memoryconfstr += '\nconfig %s_MANUAL_LOWER_MEMORYSIZE\n' % KconfPrefix
    memoryconfstr += '\thex "Lower memory size"\n'
    memoryconfstr += '\tdefault 0x80000000\n'
    memoryconfstr += '\tdepends on %s_MANUAL_SELECT\n' % KconfPrefix
    memoryconfstr += '\thelp\n'
    memoryconfstr += '\tSize of the lower memory. Minimum is 32MB, maximum is the size of\n'
    memoryconfstr += '\tthe selected primary memory physical address range.\n'
    memoryconfstr += '\tIf you specify 0x0 offset then it will skip generating lower memory node.\n'

    memoryconfstr += '\nconfig %s_MANUAL_UPPER_BASEADDR\n' % KconfPrefix
    memoryconfstr += '\thex "Upper memory base address"\n'
    memoryconfstr += '\tdefault 0x800000000\n'
    memoryconfstr += '\tdepends on %s_MANUAL_SELECT\n' % KconfPrefix
    memoryconfstr += '\tdepends on SUBSYSTEM_ARCH_AARCH64\n'
    memoryconfstr += '\thelp\n'
    memoryconfstr += '\tbase address of the upper memory\n'
    memoryconfstr += '\tMake sure the DT memory entry should start with provided address.\n'

    memoryconfstr += '\nconfig %s_MANUAL_UPPER_MEMORYSIZE\n' % KconfPrefix
    memoryconfstr += '\thex "Upper memory size"\n'
    memoryconfstr += '\tdefault 0x80000000\n'
    memoryconfstr += '\tdepends on %s_MANUAL_SELECT\n' % KconfPrefix
    memoryconfstr += '\tdepends on SUBSYSTEM_ARCH_AARCH64\n'
    memoryconfstr += '\thelp\n'
    memoryconfstr += '\tSize of the lower memory. Minimum is 32MB, maximum is the size of\n'
    memoryconfstr += '\tthe selected primary memory physical address range.\n'
    memoryconfstr += '\tIf you specify 0x0 offset then it will skip generating lower memory node.\n'
    memoryconfstr += '\nendmenu\n'

    confstr += memoryconfstr
    return confstr


def _SerialPortNum(slave):
    ''' Return the port index ('0' or '1') encoded in the serial name. '''
    nslave = slave.replace('_', '')
    if re.search(r'(uart|serial)0', nslave):
        return '0'
    if re.search(r'(uart|serial)1', nslave):
        return '1'
    return ''


def _GetSerialConsoleToken(domain_kind, slave, ip_name):
    ''' Derive the console token for a serial slave.
    For TF-A/OP-TEE the firmware expects an ip alias (cadence/pl011/dcc or
    serial number); for the device-tree (Linux/baremetal) domains the token
    is the serial slave name itself. The TF-A console aliases are read from
    sdt_ipinfo.yaml ('firmware_console_alias' per serial IP). A serial IP may
    report a SoC-specific ip_name (e.g. a versal-net psx_sbsauart node maps to
    the psv_sbsauart entry); such variants are declared explicitly via the
    'ip_name_aliases' list in the canonical sdt_ipinfo.yaml entry. '''
    if domain_kind not in ('tfa', 'optee'):
        return slave
    entry = ipinfodata.get(ip_name) if ip_name else None
    if not entry and ip_name:
        for val in ipinfodata.values():
            if not isinstance(val, dict) or val.get('device_type') != 'serial':
                continue
            if ip_name in (val.get('ip_name_aliases') or []):
                entry = val
                break
    aliases = entry.get('firmware_console_alias') or {} if isinstance(entry, dict) else {}
    if not aliases:
        return 'dcc'
    port = _SerialPortNum(slave)
    if not port:
        return slave
    return port if domain_kind == 'optee' else aliases.get(port, slave)


def _GenSerialChoice(label, depends, domain_kind, serial_ips, slaves_dict,
                     select_sym_fmt, ipname_sym):
    ''' Generate a single per-domain serial choice plus the hidden
    <ipname_sym> string used by the machine conf generators.
    select_sym_fmt is a '%s' template taking the upper-cased slave name so
    that the legacy config symbol naming can be preserved per domain.
    The default option depends on the domain kind:
      - device-tree domains (Linux/baremetal) default to 'From SDT', meaning
        the console defined in the SDT chosen node is used as-is;
      - TF-A/OP-TEE have no chosen-node console, so they default to the first
        detected serial console. A 'manual' option is still offered to fall
        back to the firmware recipe's own default console.
    'From SDT' and 'manual' emit no <ipname_sym> default (no override). '''
    # (symbol token, display label) for each option in menu order, and the
    # token that should be the choice default.
    if domain_kind in ('tfa', 'optee'):
        # Real serial IPs first, then a 'manual' fallback. Default to the
        # first detected console.
        serial_options = [(slave.upper(), slave) for slave in serial_ips]
        serial_options.append(('MANUAL', 'manual'))
        default_option = serial_ips[0].upper() if serial_ips else 'MANUAL'
        extra_help = ('\tSelect \'manual\' to use the %s recipe\'s default '
                      'console.\n' % label)
    else:
        # 'From SDT' first (default), then the real serial IPs.
        serial_options = [('FROM_SDT', 'From SDT')]
        serial_options += [(slave.upper(), slave) for slave in serial_ips]
        default_option = 'FROM_SDT'
        extra_help = ('\tSelect \'From SDT\' to use the console defined in '
                      'the SDT chosen node.\n')

    # Options that represent "no IP override" (use SDT / recipe default).
    no_override_options = ('FROM_SDT', 'MANUAL')

    confstr = '\nchoice\n'
    confstr += '\tprompt "%s Serial stdin/stdout"\n' % label
    if depends:
        confstr += '\tdepends on %s\n' % depends
    confstr += '\tdefault %s\n' % (select_sym_fmt % default_option)
    confstr += '\thelp\n'
    confstr += '\tSelect a serial device as the %s stdin/stdout.\n' % label
    confstr += extra_help

    ipname_str = '\nconfig %s\n\tstring\n' % ipname_sym
    for option_key, option_label in serial_options:
        select_sym = select_sym_fmt % option_key
        confstr += '\nconfig %s\n\tbool "%s"\n' % (select_sym, option_label)
        if option_key in no_override_options:
            continue
        console_token = _GetSerialConsoleToken(
            domain_kind, option_label,
            slaves_dict.get(option_label, {}).get('ip_name'))
        ipname_str += '\tdefault %s if %s\n' % (console_token, select_sym)
    confstr += '\nendchoice\n'
    confstr += ipname_str
    return confstr


def _GenBaudrateChoice(slave, def_baudrates):
    ''' Generate the baudrate choice for a single (Linux) serial IP. '''
    confstr = '\nchoice\n'
    confstr += '\tprompt "System stdin/stdout baudrate for %s"\n' % slave
    confstr += '\tdefault SUBSYSTEM_SERIAL_%s_BAUDRATE_115200\n' % slave.upper()
    confstr += '\thelp\n'
    confstr += '\tBaudrate settings for serial Ip %s\n' % slave
    confstr += '\tThe Baudrate setting applies only for U-boot/Linux serial Ip\n'
    for brate in def_baudrates:
        confstr += '\nconfig SUBSYSTEM_SERIAL_%s_BAUDRATE_%s\n' % (
            slave.upper(), brate)
        confstr += '\tbool "%s"\n' % brate
    confstr += '\nendchoice\n'
    return confstr


def GenSerialDomainsKconfig(syshw_file, proc_type, bbmctargets):
    ''' Generate the per-domain Serial Settings menu.
    One serial choice dropdown is created for each domain (Linux, TF-A,
    OP-TEE and every enabled multiconfig target). The default for each
    domain is derived from the SDT serial IPs; the visibility of each
    multiconfig domain is gated on its YOCTO_BBMC_<MC> enable symbol.
    The Linux/TF-A/OP-TEE domains reuse the legacy config symbol names so
    that existing consumer scripts keep working unchanged. '''
    global ipinfodata
    if 'ipinfodata' not in globals():
        ipinfo_file = os.path.join(
            project_config.GenMachineScriptsPath(), 'data', 'sdt_ipinfo.yaml')
        ipinfodata = yaml_utils.ReadYaml(ipinfo_file)
    hwyamldata = common_utils.GetSyshwData(syshw_file)
    procdata = hwyamldata.get('processor', {})
    if proc_type not in procdata:
        return ''
    arch = procdata[proc_type].get('arch')
    proc_ipname = procdata[proc_type].get('ip_name')
    slaves_dict = procdata[proc_type].get('slaves', {})
    serial_ips = [re.sub('_bankless$', '', slave) for slave in slaves_dict
                  if slaves_dict[slave].get('device_type') == 'serial']
    if not serial_ips:
        return ''

    def_baudrates = ['600', '9600', '28800',
                     '115200', '230400', '460800', '921600']

    # Domains as (label, depends, domain_kind, config_infix). config_infix is
    # the config symbol infix: '' keeps the legacy Linux 'SUBSYSTEM_SERIAL_'
    # names; others use 'SUBSYSTEM_<config_infix>_SERIAL_' so they don't
    # collide with the Linux read.
    domains = [('Linux/U-Boot', '', 'dtg', '')]
    if arch == 'aarch64':
        domains.append(('TF-A', 'SUBSYSTEM_ARCH_AARCH64', 'tfa', 'TF-A'))
    if proc_ipname == 'cortexa78':
        domains.append(('OP-TEE', 'SUBSYSTEM_ARCH_AARCH64', 'optee', 'OP-TEE'))
    for target in bbmctargets:
        config_infix = target.upper().replace('-', '_')
        domains.append((target, 'YOCTO_BBMC_%s' % config_infix, 'dtg',
                        config_infix))

    confstr = '\nmenu "Serial Settings"\n'
    # Emit all per-domain serial console dropdowns first so they stay
    # grouped together in the menu.
    for label, depends, domain_kind, config_infix in domains:
        if config_infix:
            select_sym_fmt = 'SUBSYSTEM_%s_SERIAL_%%s_SELECT' % config_infix
            ipname_sym = 'SUBSYSTEM_SERIAL_%s_IP_NAME' % config_infix
        else:
            select_sym_fmt = 'SUBSYSTEM_SERIAL_%s_SELECT'
            ipname_sym = 'SUBSYSTEM_SERIAL_IP_NAME'
        confstr += _GenSerialChoice(label, depends, domain_kind, serial_ips,
                                    slaves_dict, select_sym_fmt, ipname_sym)
    # Baudrate applies only to the Linux/U-Boot serial console; place it
    # after all the serial dropdowns.
    for slave in serial_ips:
        confstr += _GenBaudrateChoice(slave, def_baudrates)
    confstr += '\nendmenu\n'

    return confstr


def GenConf_flash(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate Flash Info as Kconfig'''
    flash_Kconf = 'SUBSYSTEM_FLASH'
    flashpart_dict = {'aarch64': {'boot': '0x100000', 'kernel': '0x1600000', 'bootenv': '0x40000'},
                      'arm': {'boot': '0x500000', 'kernel': '0xA80000', 'bootenv': '0x20000'},
                      'microblaze-v': {'fpga': '0xB00000', 'boot': '0x40000', 'bootenv': '0x20000', 'kernel': '0xC00000'}
                      }
    confstr = '\nmenu "Flash Settings"\n'
    confstr += '\nchoice\n'
    confstr += '\tprompt "Primary Flash"\n'
    confstr += '\thelp\n'
    confstr += '\tSelect a Flash instance used as Primary Flash.\n'
    confstr += '\tAuto config will apply the flash partition table settings\n'
    confstr += '\tto the primary flash.\n'
    confstr += '\tIf you preferred flash is not on the list or you don\'t want\n'
    confstr += '\tto manage your flash partition, please select manual.\n'
    flashconfstr = ''
    flaship = ''
    for slave in IpsToAdd + ['manual']:
        confstr += '\nconfig %s_%s_SELECT\n' % (flash_Kconf, slave.upper())
        confstr += '\tbool "%s"\n' % slave
        if slave == 'manual':
            continue
        ip_name = slavesdict.get(slave)['ip_name']
        global ipinfodata
        flash_prefix = ''
        if ip_name in ipinfodata and ipinfodata[ip_name].get('device_type') == 'flash':
            flash_prefix = ipinfodata[ip_name].get('flash_prefix', '')
        if flash_prefix:
            flash_prefix = flash_prefix + '-'
        flashconfstr += '\nconfig %s__ADVANCED_AUTOCONFIG\n' % flash_Kconf
        flashconfstr += '\tbool "Advanced Flash Auto Configuration"\n'
        flashconfstr += '\tdefault n\n'
        flashconfstr += '\tdepends on !%s_MANUAL_SELECT\n' % flash_Kconf
        flashconfstr += '\thelp\n'

        for count in range(0, 20):
            try:
                defpart_name = '%s%s' % (flash_prefix,
                                         list(flashpart_dict.get(arch).keys())[count])
                defpart_size = list(flashpart_dict.get(arch).values())[count]
            except IndexError:
                defpart_name = ''
                defpart_size = '0x0'
            flashconfstr += '\ncomment "partition %s"\n' % count
            flashconfstr += '\tdepends on %s\n' % (
                '%s_%s_SELECT' % (flash_Kconf, slave.upper()) if count == 0 else
                '%s_%s_PART%s_NAME != ""' % (flash_Kconf, slave.upper(), count - 1))

            flashconfstr += '\nconfig %s_%s_PART%s_NAME\n' % (
                flash_Kconf, slave.upper(), count)
            flashconfstr += '\tstring "name"\n'
            flashconfstr += '\tdefault "%s"\n' % defpart_name
            flashconfstr += '\tdepends on %s\n' % (
                '%s_%s_SELECT' % (flash_Kconf, slave.upper()) if count == 0 else
                '%s_%s_PART%s_NAME != ""' % (flash_Kconf, slave.upper(), count - 1))

            flashconfstr += '\nconfig %s_%s_PART%s_SIZE\n' % (
                flash_Kconf, slave.upper(), count)
            flashconfstr += '\thex "size"\n'
            flashconfstr += '\tdefault %s\n' % defpart_size
            flashconfstr += '\tdepends on %s_%s_PART%s_NAME != ""\n' % (
                flash_Kconf, slave.upper(), count)

            flashconfstr += '\nconfig %s_%s_PART%s_FLAGS\n' % (
                flash_Kconf, slave.upper(), count)
            flashconfstr += '\tstring "flash partition flags"\n'
            flashconfstr += '\tdefault ""\n'
            flashconfstr += '\tdepends on %s_%s_PART%s_NAME != "" && %s__ADVANCED_AUTOCONFIG\n' % (
                flash_Kconf, slave.upper(), count, flash_Kconf)
            flashconfstr += '\thelp\n'
            flashconfstr += '\tPass the flash partition flags to DTS. Use comma separatioon for\n'
            flashconfstr += '\tmultiple flags, e.g. abc,def,...,xyz\n'
            flashconfstr += '\tCurrently, the supported string is RO ("read-only" string) flag\n'
            flashconfstr += '\twhich marks the partition read-only\n'

        flashconfstr += '\nconfig %s_IP_NAME\n' % flash_Kconf
        flashconfstr += '\tstring\n'
        if re.search(r'.*_bank0', slave):
            flaship = re.sub('_bank0$', '', slave)
            flashconfstr += '\tdefault %s\n' % flaship
        else:
            flashconfstr += '\tdefault %s\n' % slave
        flashconfstr += '\tdepends on %s_%s_SELECT\n' % (
            flash_Kconf, slave.upper())

    confstr += '\nendchoice\n'
    confstr += flashconfstr
    confstr += '\nendmenu\n'

    return confstr


def GenConf_sd(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate SD Info as Kconfig'''
    sd_Kconf = 'SUBSYSTEM_PRIMARY_SD'
    confstr = '\nmenu "SD/SDIO Settings"\n'
    confstr += '\nchoice\n'
    confstr += '\tprompt "Primary SD/SDIO"\n'
    confstr += '\thelp\n'
    confstr += '\tSelect a SD instanced used as primary SD/SDIO.\n'
    confstr += '\tIt allows you to select which SD controller is in the systems primary SD card interface.\n'
    for slave in IpsToAdd + ['manual']:
        confstr += '\nconfig %s_%s_SELECT\n' % (sd_Kconf, slave.upper())
        confstr += '\tbool "%s"\n' % slave
        if slave == 'manual':
            continue

    confstr += '\nendchoice\n'
    confstr += '\nendmenu\n'

    return confstr


BootModes_dict = {
    'zynq': {
        'bootmodes': {
            'JTAG': '0', 'QSPI': 1, 'NOR': 2, 'NAND': 4, 'SD': 5
        },
        'def_bootmode': '5'
    },
    'zynqmp': {
        'bootmodes': {
            'JTAG': '0', 'QSPI (24b)': 1, 'QSPI (32b)': 2,
            'SD0 (2.0)': 3, 'NAND': 4, 'SD1 (2.0)': 5,
            'eMMC (1.8V)': 6, 'SD1 LS (3.0)': 14
        },
        'def_bootmode': '3'
    },
    'versal': {
        'bootmodes': {
            'JTAG': '0','QSPI24': 1, 'QSPI32': 2, 'SD0 (v3.0)': 3,
            'SD1 (v2.0)': 5, 'eMMC1 (v4.51)': 6,
            'OSPI': 8, 'SD1 (v3.0)': 14
        },
        'def_bootmode': '8'
    },
    'versal-2ve-2vm': {
        'bootmodes': {
            'JTAG': '0','QSPI24': 1, 'QSPI32': 2, 'SD0 (v3.0)': 3,
            'SD0 (v2.0)': 5, 'eMMC (v5.1)': 6, 'OSPI': 8,
            'UFS': 11, 'SD1 (v3.0)': 14
        },
        'def_bootmode': '8'
    },
    'versal-2vp': {
        'bootmodes': {
            'JTAG': '0','QSPI24': 1, 'QSPI32': 2, 'SD0 (v3.0)': 3,
            'SD1 (v2.0)': 5, 'eMMC1 (v4.51)': 6,
            'OSPI': 8, 'SD1 (v3.0)': 14
        },
        'def_bootmode': '8'
    }
}


def GenConf_bootmodes(proc):
    soc_family = project_config.DetectSocFamily(
                            proc, hwyamldata.get('device_id', ''))
    bootmode_info = BootModes_dict.get(soc_family, {})
    bootmodes = bootmode_info.get('bootmodes', {})
    default_bootmode = bootmode_info.get('def_bootmode', '')
    if not bootmodes:
        return ''
    # Boot mode is a boot/u-boot concept; hide it for 32-bit MicroBlaze-V (Zephyr).
    confstr = '\nif SUBSYSTEM_SDT_FLOW && !SUBSYSTEM_MICROBLAZE_V_XLEN_32\n'
    confstr += '\nmenu "Boot Mode Settings"\n'
    confstr += '\nchoice\n'
    confstr += '\tprompt "Primary Boot Mode"\n'
    if default_bootmode:
        confstr += f'\tdefault SUBSYSTEM_BOOTMODE_{default_bootmode}\n'
    confstr += '\thelp\n'
    help_text = (
        f'\tSelect the primary boot mode for the processor {proc}.\n'
        '\tThis selection is used to package Boot.BIN and set runqemu\n'
        '\tboot arguments.\n'
        '\tFor details, see:\n'
        '\t Zynq: UG585, "Flash-Devices-Master-Mode-Boot" section\n'
        '\t ZynqMP: UG1085, "Boot Modes" section\n'
        '\t Versal Gen1: AM011, "Boot Modes and Interfaces" section\n'
        '\t Versal Gen2: AM026, "Boot Mode and Interfaces" section\n'
    )
    confstr += help_text
    # The boot mode configs
    for bootmode, value in bootmodes.items():
        confstr += f'\nconfig SUBSYSTEM_BOOTMODE_{value}\n'
        confstr += f'\tbool "{value} - {bootmode}"\n'
    confstr += '\nendchoice\n'
    confstr += '\nendmenu\n'
    confstr += '\nendif\n'
    return confstr


# Supported Device Types to create Kconfig file
devicetypes = {
    'memory': {'exclude': ['psu_ocm']},
    'flash': {}, 'sd': {}
}


def GenKconfigSysHW(hwyamlinfile, ipinfofile, outfile):
    ''' Read Input Yaml(sys HW data) and convert into
    Kconfig for described device types'''
    global hwyamldata, ipinfodata
    hwyamldata = common_utils.GetSyshwData(hwyamlinfile)
    ipinfodata = yaml_utils.ReadYaml(ipinfofile)
    procdata = hwyamldata.get('processor')
    KconfStr = 'menu "Subsystem Hardware Settings"\n'
    KconfStr += GenConf_processor(procdata)
    for proc in procdata.keys():
        arch = hwyamldata['processor'][proc].get('arch')
        proc_ipname = hwyamldata['processor'][proc].get('ip_name')
        KconfStr += '\nif SUBSYSTEM_PROCESSOR_%s_SELECT\n' % proc
        slavesdict = procdata[proc].get('slaves')
        for devtype in devicetypes.keys():
            devtype_exclude = devicetypes[devtype].get('exclude', [])
            IpsToAdd = []
            for slave in slavesdict.keys():
                slave_devtype = slavesdict[slave].get('device_type')
                slave_ip = slavesdict[slave].get('ip_name')
                if slave_devtype and slave_devtype == devtype and \
                        slave_ip not in devtype_exclude:
                    slave = re.sub('_bankless$', '', slave)
                    IpsToAdd.append(slave)

            KconfStr += eval('GenConf_%s(IpsToAdd, slavesdict, \
                                    proc_ipname, arch)' % (devtype))
        KconfStr += GenConf_bootmodes(proc)
        KconfStr += '\nendif\n'
    # Placeholder for the per-domain Serial Settings menu. It is filled in by
    # project_config.GenKconfigProj where the multiconfig target list is known.
    KconfStr += '\n@@serialmenustr@@\n'
    KconfStr += '\nendmenu\n'
    common_utils.AddStrToFile(outfile, KconfStr)
