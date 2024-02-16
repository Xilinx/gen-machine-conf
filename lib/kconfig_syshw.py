#!/usr/bin/env python3

# Copyright (C) 2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import sys
import re
import logging
import common_utils

logger = logging.getLogger('Gen-Machineconf')


def GenConf_processor(procdata):
    ''' Generate Processor Info as Kconfig'''
    if not procdata:
        raise Exception('ERROR: No CPU can be found in the system. Please review your hardware system. '
              'Valid processors are: microblaze, ps7_cortexa9, psu_cortexa53, psv_cortexa72, psx_cortexa78.')
    KconfStr = 'SUBSYSTEM_PROCESSOR'
    confstr = ''
    procconfstr = '\nchoice\n'
    procconfstr += '\tprompt "System Processor"\n'
    procconfstr += '\thelp\n'
    procconfstr += '\tSelect a processor as the system processor.\n'

    archdict = {}
    archKdict = {'microblaze': 'ARCHMB', 'arm': 'ARCHARM', 'aarch64': 'ARCH64'}
    for index, proc in enumerate(procdata.keys()):
        confstr += '\nconfig %s%s_IP_NAME\n' % (KconfStr, index)
        confstr += '\tstring\n'
        confstr += '\tdefault %s\n' % proc
        Kprocselect = '%s_%s_SELECT' % (KconfStr, proc)
        procconfstr += '\nconfig %s\n' % Kprocselect
        procconfstr += '\tbool "%s"\n' % proc
        arch = procdata[proc].get('arch')
        if arch:
            archdict.setdefault(arch, []).append(Kprocselect)

    procconfstr += '\nendchoice\n'

    for arch in archdict.keys():
        confstr += '\nconfig SUBSYSTEM_ENABLE_%s\n' % archKdict.get(arch)
        confstr += '\tbool\n'
        confstr += '\tdefault y\n'
        confstr += '\tselect SUBSYSTEM_ARCH_%s\n' % arch.upper()
        confstr += '\tdepends on %s\n' % ' || '.join(archdict.get(arch))

    confstr += procconfstr
    return confstr


def GenConf_memory(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate Memory Info as Kconfig'''
    confstr = ''
    memoryconfstr = ''
    confstr += '\nmenu "Memory Settings"\n'
    confstr += 'choice\n'
    confstr += '\tprompt "Primary Memory"\n'
    confstr += '\thelp\n'
    confstr += '\tThe configuration in this menu impacts the\n'
    confstr += '\tmemory settings in the device tree autoconfig files.\n'
    confstr += '\tIf you select "manual",\n'
    confstr += '\tPetaLinux will auto generate memory node based on user inputs,\n'
    confstr += '\tyou will need to specify base address and memory size.\n'
    confstr += '\tTo skip generating lower or upper memory node specify 0x0 offset to the memory size.\n'
    KconfPrefix = 'SUBSYSTEM_MEMORY'
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
        banksize = hex(int(highaddr, base=16) - int(baseaddr, base=16))
        if not int(banksize, base=16) >= 0x2000000:
            continue
        memKconf = '%s_%s' % (KconfPrefix, slave.upper())
        confstr += '\nconfig %s_SELECT\n' % memKconf
        confstr += '\tbool "%s"\n' % slave

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
        memoryconfstr += '\tdefault %s if SUBSYSTEM_ARCH_AARCH64\n' % (
            hex(int(baseaddr, base=16) + 0x8000000))
        memoryconfstr += '\tdefault %s if SUBSYSTEM_ARCH_ARM\n' % (
            hex(int(baseaddr, base=16) + 0x4000000))
        memoryconfstr += '\tdefault %s if SUBSYSTEM_ARCH_MICROBLAZE\n' % (
            hex(int(baseaddr, base=16) + 0x100000))
        memoryconfstr += '\trange %s %s\n' % (hex(int(baseaddr, base=16) + 0x100000),
                                              hex(int(baseaddr, base=16) + int(highaddr, base=16) - 0x2000000 + 0x100000))
        memoryconfstr += '\tdepends on %s_SELECT\n' % memKconf
        memoryconfstr += '\tdepends on !SUBSYSTEM_COMPONENT_U__BOOT_NAME_NONE\n'
        memoryconfstr += '\thelp\n'
        memoryconfstr += '\tu-boot text base address by specifying from the memory base address.\n'
        memoryconfstr += '\tu-boot load address = bank base address + offset. And same value will\n'
        memoryconfstr += '\tpass to TF-A also. Minimum suggested is 1MB.\n'

        memoryconfstr += '\nconfig %s_IP_NAME\n' % KconfPrefix
        memoryconfstr += '\tstring\n'
        memoryconfstr += '\tdefault %s\n' % slave
        memoryconfstr += '\tdepends on %s_SELECT\n' % memKconf

    confstr += '\nconfig %s_MANUAL_SELECT\n' % KconfPrefix
    confstr += '\tbool "manual"\n'
    confstr += '\nendchoice\n'

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


def GenConf_serial(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate Serial Info as Kconfig'''
    confstr = '\nmenu "Serial Settings"\n'
    serialconfstr = ''
    serial_Kconf = 'SUBSYSTEM_SERIAL'
    serialdict = {'microblaze': ['FSBOOT', 'DTG'],
                  'ps7_cortexa9': ['FSBL', 'DTG'],
                  'psu_cortexa53': ['PMUFW', 'FSBL', 'TF-A', 'DTG'],
                  'psv_cortexa72': ['PLM', 'TF-A', 'DTG'],
                  'psx_cortexa78': ['PLM', 'TF-A', 'DTG']
                  }
    def_baudrates = ['600', '9600', '28800',
                     '115200', '230400', '460800', '921600']
    for comp in serialdict.get(proc_ipname):
        confstr += '\nchoice\n'
        confstr += '\tprompt "%s Serial stdin/stdout"\n' % (
                'U-boot/Linux' if comp == 'DTG' else comp)
        confstr += '\thelp\n'
        confstr += '\tSelect a serial as the %s\'s stdin,stdout.\n' % (
            'U-boot and Linux' if comp == 'DTG' else comp)
        confstr += '\tIf you select \'manual\', you will need to add this variable\n'
        if comp == 'TF-A':
            confstr += '\tATF_CONSOLE:forcevariable = "<serial_ipname>" in petalinuxbps.conf\n'
        else:
            confstr += '\tYAML_SERIAL_CONSOLE_STDIN:forcevariable:pn-<recipename> = "<serial_ipname>"\n'
            confstr += '\tYAML_SERIAL_CONSOLE_STDOUT:forcevariable:pn-<recipename> = \"<serial_ipname>\"\n'
            confstr += '\tin petalinuxbsp.conf file to specify the stdin/stdout."\n'

        serialconfstr += '\nconfig %s_%s_IP_NAME\n' % (
            serial_Kconf, comp.upper())
        serialconfstr += '\tstring\n'
        for slave in IpsToAdd + ['manual']:
            confstr += '\nconfig SUBSYSTEM_%sSERIAL_%s_SELECT\n' % (
                '%s_' % comp if comp != 'DTG' else '', slave.upper())
            confstr += '\tbool "%s"\n' % slave
            if slave == 'manual':
                continue
            serialconsole = slave
            if comp == 'TF-A':
                ip_name = slavesdict[slave].get('ip_name')
                if ip_name == 'psu_uart':
                    if re.search(r'.*uart0.*', slave.replace('_', '')):
                        serialconsole = 'cadence'
                    elif re.search(r'.*uart1.*', slave.replace('_', '')):
                        serialconsole = 'cadence1'
                elif ip_name in ['psv_sbsauart', 'psx_sbsauart']:
                    if re.search(r'.*uart0.*', slave.replace('_', '')):
                        serialconsole = 'pl011'
                    elif re.search(r'.*uart1.*', slave.replace('_', '')):
                        serialconsole = 'pl011_1'
                else:
                    serialconsole = 'dcc'
            serialconfstr += '\tdefault %s if SUBSYSTEM_%sSERIAL_%s_SELECT\n' % (
                serialconsole, '%s_' % comp if comp != 'DTG' else '', slave.upper())

        confstr += '\nendchoice\n'

    # Baudrate settings
    for slave in IpsToAdd:
        confstr += '\nchoice\n'
        confstr += '\tprompt "System stdin/stdout baudrate for %s"\n' % slave
        confstr += '\tdefault %s_%s_BAUDRATE_115200\n' % (
            serial_Kconf, slave.upper())
        for baudrate in def_baudrates:
            confstr += '\nconfig %s_%s_BAUDRATE_%s\n' % (
                serial_Kconf, slave.upper(), baudrate)
            confstr += '\tbool "%s"\n' % baudrate

        confstr += '\nendchoice\n'

    confstr += serialconfstr
    confstr += '\nendmenu\n'

    return confstr


def GenConf_ethernet(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate Ethernet Info as Kconfig'''
    eth_Kconf = 'SUBSYSTEM_ETHERNET'
    confstr = '\nmenu "Ethernet Settings"\n'
    confstr += '\nchoice\n'
    confstr += '\tprompt "Primary Ethernet"\n'
    confstr += '\thelp\n'
    confstr += '\tSelect a Ethernet used as primary Ethernet.\n'
    confstr += '\tThe primary ethernet will be used for u-boot networking if u-boot is\n'
    confstr += '\tselected and will be used as eth0 in Linux.\n'
    confstr += '\tIf your preferred primary ethernet is not on the list, please select"\n'
    confstr += '\t\'manual\'.\n'
    serialconfstr = ''
    for slave in IpsToAdd + ['manual']:
        confstr += '\nconfig %s_%s_SELECT\n' % (eth_Kconf, slave.upper())
        confstr += '\tbool "%s"\n' % slave
        if slave == 'manual':
            continue
        serialconfstr += '\nconfig %s_%s_MAC_AUTO\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\tbool "Randomise MAC address"\n'
        serialconfstr += '\tdefault y if SUBSYSTEM_ARCH_MICROBLAZE\n'
        serialconfstr += '\tdefault n\n'
        serialconfstr += '\tdepends on %s_%s_SELECT\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\trandomise MAC address for the primary ethernet.\n'

        serialconfstr += '\nconfig %s_%s_MAC_PATTERN\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\tstring "Template for randomised MAC address"\n'
        serialconfstr += '\tdefault "00:0a:35:00:??:??"\n'
        serialconfstr += '\tdepends on %s_%s_SELECT && %s_%s_MAC_AUTO\n' % (
            eth_Kconf, slave.upper(), eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\tPattern for generating random MAC addresses - question mark\n'
        serialconfstr += '\tcharacters will be replaced by random hex digits\n'

        serialconfstr += '\nconfig %s_%s_MAC\n' % (eth_Kconf, slave.upper())
        serialconfstr += '\tstring "Ethernet MAC address"\n'
        serialconfstr += '\tdefault "ff:ff:ff:ff:ff:ff"\n'
        serialconfstr += '\tdepends on %s_%s_SELECT && !%s_%s_MAC_AUTO\n' % (
            eth_Kconf, slave.upper(), eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\tDefault mac set to ff:ff:ff:ff:ff:ff invalid mac address to read from EEPROM\n'
        serialconfstr += '\tif you want change with desired value you can change, example: 00:0a:35:00:22:01\n'

        serialconfstr += '\nconfig %s_%s_USE_DHCP\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\tbool "Obtain IP address automatically"\n'
        serialconfstr += '\tdefault y\n'
        serialconfstr += '\tdepends on %s_%s_SELECT\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\tSet this option if you would like your SUBSYSTEM to use DHCP for\n'
        serialconfstr += '\tobtaining an IP address.\n'

        serialconfstr += '\nconfig %s_%s_IP_ADDRESS\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\tstring "Static IP address"\n'
        serialconfstr += '\tdefault "192.168.0.10"\n'
        serialconfstr += '\tdepends on %s_%s_SELECT && !%s_%s_USE_DHCP\n' % (
            eth_Kconf, slave.upper(), eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\tThe IP address of your main network interface when static network\n'
        serialconfstr += '\taddress assignment is used.\n'

        serialconfstr += '\nconfig %s_%s_IP_NETMASK\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\tstring "Static IP netmask"\n'
        serialconfstr += '\tdefault "255.255.255.0"\n'
        serialconfstr += '\tdepends on %s_%s_SELECT && !%s_%s_USE_DHCP\n' % (
            eth_Kconf, slave.upper(), eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\tDefault netmask when static network address assignment is used.\n'
        serialconfstr += '\tIn case of systemd please specify netmask value like CIDR notation Eg: 24 instead of 255.255.255.0\n'
        serialconfstr += '\tIn case of sysvinit please specify netmask value like dot-decimal notation Eg: 255.255.255.0 instead of 24\n'

        serialconfstr += '\nconfig %s_%s_IP_GATEWAY\n' % (
            eth_Kconf, slave.upper())
        serialconfstr += '\tstring "Static IP gateway"\n'
        serialconfstr += '\tdefault "192.168.0.1"\n'
        serialconfstr += '\tdepends on %s_%s_SELECT && !%s_%s_USE_DHCP\n' % (
            eth_Kconf, slave.upper(), eth_Kconf, slave.upper())
        serialconfstr += '\thelp\n'
        serialconfstr += '\tDefault gateway when static network address assignment is used.\n'

    confstr += '\nendchoice\n'
    confstr += serialconfstr
    confstr += '\nendmenu\n'
    return confstr


def GenConf_flash(IpsToAdd, slavesdict, proc_ipname, arch):
    ''' Generate Flash Info as Kconfig'''
    flash_Kconf = 'SUBSYSTEM_FLASH'
    flashpart_dict = {'aarch64': {'boot': '0x100000', 'kernel': '0x1600000', 'bootenv': '0x40000'},
                      'arm': {'boot': '0x500000', 'kernel': '0xA80000', 'bootenv': '0x20000'},
                      'microblaze': {'fpga': '0xB00000', 'boot': '0x40000', 'bootenv': '0x20000', 'kernel': '0xC00000'}
                      }
    confstr = '\nmenu "Flash Settings"\n'
    confstr += '\nchoice\n'
    confstr += '\tprompt "Primary Flash"\n'
    confstr += '\thelp\n'
    confstr += '\tSelect a Flash instance used as Primary Flash.\n'
    confstr += '\tPetaLinux auto config will apply the flash partition table settings\n'
    confstr += '\tto the primary flash.\n'
    confstr += '\tIf you preferred flash is not on the list or you don\'t want PetaLinux\n'
    confstr += '\tto manage your flash partition, please select manual.\n'
    flashconfstr = ''
    for slave in IpsToAdd + ['manual']:
        confstr += '\nconfig %s_%s_SELECT\n' % (flash_Kconf, slave.upper())
        confstr += '\tbool "%s"\n' % slave
        if slave == 'manual':
            continue
        ip_name = slavesdict.get(slave)['ip_name']
        global ipinfodata
        try:
            flash_prefix = '%s-' % (
                ipinfodata[ip_name]['device_type']['flash'].get('flash_prefix'))
        except KeyError:
            flash_prefix = ''
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


# Supported Device Types to create Kconfig file
devicetypes = {
    'memory': {'exclude': ['psu_ocm']},
    'serial': {}, 'ethernet': {}, 'flash': {}, 'sd': {}
}


def GenKconfigSysHW(hwyamlinfile, ipinfofile, outfile):
    ''' Read Input Yaml(plnx sys HW data) and convert into
    Kconfig for described device types'''
    global hwyamldata, ipinfodata
    hwyamldata = common_utils.ReadYaml(hwyamlinfile)
    ipinfodata = common_utils.ReadYaml(ipinfofile)
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
        KconfStr += '\nendif\n'
    KconfStr += '\nendmenu\n'
    common_utils.AddStrToFile(outfile, KconfStr)
