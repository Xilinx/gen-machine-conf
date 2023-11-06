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
import project_config
import logging


logger = logging.getLogger('Gen-Machineconf')


def CheckIP(prop, system_conffile):
    global plnx_syshw_data
    processor = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PROCESSOR_', system_conffile, 'choice', '_SELECT=y')
    if prop == 'MANUAL':
        return ''
    for key in plnx_syshw_data['processor'][processor]['slaves'].keys():
        if 'ip_name' in plnx_syshw_data['processor'][processor]['slaves'][key].keys():
            if prop == plnx_syshw_data['processor'][processor]['slaves'][key]['ip_name']:
                return True
    return ''


def GetIPProperty(device_name, system_conffile, prop='ip_name'):
    processor = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PROCESSOR_', system_conffile, 'choice', '_SELECT=y')
    if device_name == 'MANUAL':
        return ''
    ipname = ''
    global slaves_dict
    global plnx_syshw_data
    slaves_dict = common_utils.convert_dictto_lowercase(
        plnx_syshw_data['processor'][processor]['slaves'])
    if device_name.lower() in slaves_dict.keys():
        if prop == 'ip_name':
            ipname = slaves_dict[device_name.lower()]['ip_name']
            return ipname
        else:
            prop_value = ''
            if prop in slaves_dict[device_name.lower()].keys():
                prop_value = slaves_dict[device_name.lower()][prop]
                return prop_value
            else:
                return ''
    return ''


def UpdateMemConfigs(args, system_conffile):
    ''' updating dtb load addr and u-boot text base based on user bank selection if they select
    otherthan manual or starting from zero bank as the default values does not work for those cases.
    '''
    memory = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_', system_conffile,
                                         'choice', '_SELECT=y')
    if memory != 'MANUAL':
        memory_baseaddr = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_MEMORY_%s_BASEADDR' % memory, system_conffile)
        memory_size = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_MEMORY_%s_SIZE' % memory, system_conffile)
        max_mem_size = int(memory_baseaddr, base=16) + \
            int(memory_size, base=16)
    if memory == 'MANUAL' or int(memory_baseaddr, base=16) == 0:
        # removing u-boot config.cfg file if already exists from previous bank selection
        # as this is not required for manual or base mem zero case as default values works.
        if os.path.exists(os.path.join(args.output, 'u-boot-xlnx', 'config.cfg')):
            os.remove(os.path.join(args.output, 'u-boot-xlnx', 'config.cfg'))
        # updating for manual memory case and base mem zero
        # if selected different value from previous bank selection
        # for zynq BL33 address not applicable
        if args.soc_family != 'zynq':
            bl33_offset = common_utils.GetConfigValue(
                'CONFIG_SUBSYSTEM_MEMORY_%s_U__BOOT_TEXTBASE_OFFSET' % memory, system_conffile)
    else:
        # updating the dtb load address for u-boot
        if args.soc_family == 'versal':
            dtb_offset = '0x1000'
        elif args.soc_family in ['zynqmp', 'zynq']:
            dtb_offset = '0x100000'
        dtb_load_addr = hex(int(memory_baseaddr, base=16) +
                            int(dtb_offset, base=16))
        uboot_dir = os.path.join(args.output, 'u-boot-xlnx')
        if not os.path.exists(uboot_dir):
            os.makedirs(uboot_dir)
        uboot_config = os.path.join(uboot_dir, 'config.cfg')
        if int(dtb_load_addr, base=16) < max_mem_size:
            common_utils.UpdateConfigValue(
                'CONFIG_XILINX_OF_BOARD_DTB_ADDR', dtb_load_addr, uboot_config)
        else:
            logger.error('dtb load addr %s exceeding max mem size %s' % (
                dtb_load_addr, max_mem_size))
        # updating the u-boot load address for u-boot
        uboot_load_addr = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_MEMORY_%s_U__BOOT_TEXTBASE_OFFSET' % memory, system_conffile)
        common_utils.UpdateConfigValue('CONFIG_TEXT_BASE',
                                       uboot_load_addr, uboot_config)
        # updating bl33 address based on the u-boot text base
        if args.soc_family in ['versal', 'zynqmp']:
            bl33_offset = common_utils.GetConfigValue(
                'CONFIG_TEXT_BASE', uboot_config)
            bl33_addr = bl33_offset
            if int(bl33_addr, base=16) > max_mem_size:
                logger.error('bl33 addr %s exceeding max mem size %s' % (
                    bl33_addr, max_mem_size))

def GetSysConsoleBootargs(system_conffile, soc_family, soc_variant):
    global ipinfo_data
    serialname = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_SERIAL_', system_conffile, 'choice', '_SELECT=y')
    serialipname = GetIPProperty(serialname, system_conffile)
    serial_devfile = ''
    serial_earlycon = ''
    if serialipname in ipinfo_data.keys():
        if isinstance(ipinfo_data[serialipname]['device_type'], dict) and \
                'serial' in ipinfo_data[serialipname]['device_type'].keys():
            if 'linux_console_file_name' in ipinfo_data[serialipname]['device_type']['serial'].keys():
                serial_devfile = ipinfo_data[serialipname]['device_type']['serial']['linux_console_file_name']
            if 'linux_earlycon_str' in ipinfo_data[serialipname]['device_type']['serial'].keys():
                serial_earlycon = ipinfo_data[serialipname]['device_type']['serial']['linux_earlycon_str']
    else:
        return ''
    if not serial_devfile:
        logger.error('Unknown serial ipname %s for %s.' %
                     (serialipname, serialname))
        sys.exit(255)
    no_alias = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS', system_conffile)
    serial_no = ''
    if no_alias == 'y':
        if "_" in serialname:
            serial_no = serialname.lower().split(serialipname + '_')[1]
        else:
            tmp = re.findall('[0-9]+', serialname)
            serial_no = tmp[0]
    if serial_no:
        serial_devfile = '%s%s' % (serial_devfile[:-1], serial_no)
    baudrate = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_SERIAL_%s_BAUDRATE_' % serialname, system_conffile, 'choice', '=y')
    if not baudrate:
        logger.error('Failed to get baudrate of %s' % serialname)
        sys.exit(255)
    early_printk = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_BOOTARGS_EARLYPRINTK', system_conffile)
    if early_printk == 'y':
        earlyprintk = " earlycon"
        if soc_family == 'versal' and soc_variant != 'net':
            serial_offset = '0xFF000000'
            if re.search('psv_sbsauart_1', serialname.lower()) or \
                    re.search('psx_sbsauart_1', serialname.lower()):
                serial_offset = '0xFF010000'
            earlyprintk = ' earlycon=pl011,mmio32,%s,%sn8' % (
                serial_offset, baudrate)
    else:
        earlyprintk = ''
    if serial_earlycon:
        earlycon_addr = GetIPProperty(
            serialname, system_conffile, 'baseaddr')
        if isinstance(earlycon_addr, str):
            earlycon_addr = int(earlycon_addr, base=16)
        earlycon_addr = hex(earlycon_addr).upper()
        if soc_family != 'versal':
            return '%s console=%s,%s clk_ignore_unused' % (earlyprintk, serial_devfile, baudrate)
        else:
            if soc_variant == 'net':
                return '%s console=%s,%s clk_ignore_unused' % (earlyprintk, serial_devfile, baudrate)
            else:
                return 'console=%s %s clk_ignore_unused' % (serial_devfile, earlyprintk)
    else:
        return 'console=%s,%s%s' % (serial_devfile, baudrate, earlyprintk)


def PostProcessSysConf(args, system_conffile, ipinfo_file, plnx_syshw_file):
    genmachine_scripts = project_config.GenMachineScriptsPath()
    import yaml
    global plnx_syshw_data
    global ipinfo_data
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()

    with open(ipinfo_file, 'r') as ipinfo_file_f:
        ipinfo_data = yaml.safe_load(ipinfo_file_f)
    ipinfo_file_f.close()

    bootargs_auto = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_BOOTARGS_AUTO', system_conffile)
    rootfs_type = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_ROOTFS_', system_conffile, 'choice')
    bootargs = ''
    if rootfs_type == 'INITRD':
        bootargs = 'root=/dev/ram0 rw'
    elif rootfs_type == 'NFS':
        ethdevname = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_ETHERNET_', system_conffile, 'choice', '_SELECT=y')
        nfsdir = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_NFSROOT_DIR', system_conffile)
        nfsserverip = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_NFSSERVER_IP', system_conffile)
        cmd = '%s/petalinux-find-ipaddr %s' % (genmachine_scripts, nfsserverip)
        nfsserverip = common_utils.RunCmd(cmd, args.output, shell=True)[0].strip()
        use_dhcp = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_ETHERNET_%s_USE_DHCP' % ethdevname, system_conffile)
        static_ip = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_ETHERNET_%s_IP_ADDRESS' % ethdevname, system_conffile)
        bootargs = 'root=/dev/nfs nfsroot=%s:%s,tcp' % (nfsserverip, nfsdir)
        if use_dhcp:
            bootargs += ' ip=dhcp'
        elif static_ip:
            bootargs += ' ip=%s:%s' % (static_ip, nfsserverip)
        elif ethdevname == 'MANUAL':
            bootargs += ' ip=dhcp'  # We assume to use dhcp for "manual" ethernet device
        bootargs += ' rw'
        # Make sure the NFSROOT_DIR is in /etc/exports
        # TODO Check /etc/exports file for nfs directory if not give warning
    elif rootfs_type == 'JFFS2':
        jffs2_partname = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_JFFS2_PART_NAME', system_conffile)
        if not jffs2_partname:
            jffs2_partname = 'jffs2'
            if bootargs_auto:
                logger.info(
                    'Jffs2 rootfs partition name is set to the default one "jffs2" since you haven\'t specify one')
        found_part = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_FLASH_', system_conffile, 'choice', '_NAME="%s"' % jffs2_partname)
        if not found_part:
            logger.warning(
                'Jffs2 is selected as root FS but the jffs2 partition: "%s" is not defined in the system config menu.' % jffs2_partname)
            logger.warning(
                'Please make sure you have "%s" defined in your flash partitions table.' % jffs2_partname)
        bootargs = 'root=mtd:%s rw rootfstype=jffs2' % jffs2_partname
    elif rootfs_type == 'UBIFS':
        ubi_partname = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_UBI_PART_NAME', system_conffile)
        if not ubi_partname:
            ubi_partname = 'ubifs'
            if bootargs_auto:
                logger.info(
                    'UBIFS rootfs partition name is set to the default one "ubifs" since you haven\'t specify one')
        found_part = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_FLASH_', system_conffile, 'choice', '_NAME="%s"' % ubi_partname)
        ubi_partno = ''
        if not found_part:
            logger.warning(
                'UBIFS is selected as root FS but the ubi partition: "%s" is not defined in the system config menu.' % ubi_partname)
            logger.warning(
                'Please make sure you have "%s" defined as 2nd part in your flash partitions table' % ubi_partname)
        else:
            ubi_partno = found_part.split('_PART')[1]
        if not ubi_partno:
            ubi_partno = '2'
        bootargs = 'noinitrd root=ubi0:%s rw rootfstype=ubifs ubi.mtd=%s' % (
            ubi_partname, ubi_partno)
    elif rootfs_type == 'EXT4':
        sdrootdev = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_SDROOT_DEV', system_conffile)
        bootargs = 'root=%s ro rootwait' % sdrootdev

    ethdevname = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_ETHERNET_', system_conffile, 'choice', '_SELECT=y')
    macaddrauto = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_AUTO' % ethdevname, system_conffile)
    if macaddrauto == 'y':
        macaddr = ''
        macaddrpattern = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_PATTERN' % ethdevname, system_conffile)
        if not macaddrpattern:
            macaddrpattern = '00:0a:35:00:??:??'
        new_mac = ''
        import random
        for x in range(17):
            if macaddrpattern[x] == '?':
                new_mac += str(random.randint(0, 9))
            else:
                new_mac += macaddrpattern[x]
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC' %
                                       ethdevname, '"%s"' % new_mac, system_conffile)
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_AUTO' %
                                       ethdevname, 'disable', system_conffile)
    if args.soc_family != 'microblaze':
        UpdateMemConfigs(args, system_conffile)
    if bootargs_auto == 'y':
        consolebootargs = GetSysConsoleBootargs(
            system_conffile, args.soc_family, args.soc_variant)
        ramdisk_image = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_INITRAMFS_IMAGE_NAME', system_conffile)
        if ramdisk_image and re.search('initramfs', ramdisk_image):
            bootargs += ' init_fatal_sh=1'
        bootargs = '%s %s' % (consolebootargs, bootargs)
        vcu_bootargs = ''
        vcu_maxsize = ''
        if CheckIP('vcu', system_conffile):
            vcu_maxsize = ipinfo_data['vcu']['linux_kernel_properties']['CMA_SIZE_MBYTES']
            if vcu_maxsize:
                vcu_bootargs = 'cma=%sM' % vcu_maxsize
        bootargs = '%s %s' % (bootargs, vcu_bootargs)

        vdu_bootargs = ''
        vdu_maxsize = ''
        if CheckIP('vdu', system_conffile):
            vdu_maxsize = ipinfo_data['vdu']['linux_kernel_properties']['CMA_SIZE_MBYTES']
            if vdu_maxsize:
                vdu_bootargs = 'cma=%sM' % vdu_maxsize
        bootargs = '%s %s' % (bootargs, vdu_bootargs)
        extra_bootargs = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_EXTRA_BOOTARGS', system_conffile)
        if extra_bootargs:
            bootargs = '%s %s' % (bootargs, extra_bootargs)
        common_utils.UpdateConfigValue('CONFIG_SUBSYSTEM_BOOTARGS_GENERATED',
                                       '"%s"' % re.sub(' +', ' ', bootargs.strip()), system_conffile)
