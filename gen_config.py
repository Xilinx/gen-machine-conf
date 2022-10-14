# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

import sys
import os
import pathlib
import subprocess
import re
import shutil

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

scripts_dir = os.path.join(os.path.dirname(__file__),'plnx-scripts')

def update_config_value(macro, value, filename):
    with open(filename, 'r') as file_data:
        lines = file_data.readlines()
    file_data.close()

    with open(filename, 'w') as file_data:
        for line in lines:
            if re.search('# %s is not set' % macro,line) or re.search('%s=' % macro,line):
                continue
            file_data.write(line)
        if value == 'disable':
            file_data.write('# %s is not set\n' % macro)
        else:
            file_data.write('%s=%s\n' % (macro,value))
    file_data.close()

def get_config_value(macro, filename, Type='bool', end_macro='=y'):
    with open(filename, 'r') as file_data:
        lines = file_data.readlines()
    file_data.close()
    value = ''
    if Type == 'bool':
        for line in lines:
            line = line.strip()
            if line.startswith(macro + '='):
                value = line.replace(macro + '=','').replace('"','')
                break
    elif Type == 'choice':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value = line.replace(macro,'').replace(end_macro,'')
                break
    elif Type == 'asterisk':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and re.search(end_macro,line):
                value = line.split('=')[1].replace('"','')
                break
    return value

def convert_dictto_lowercase(data_dict):
    if isinstance(data_dict, dict):
        return {k.lower():convert_dictto_lowercase(v) for k, v in data_dict.items()}
    elif isinstance(data_dict, (list, set, tuple)):
        t = type(data_dict)
        return t(convert_dictto_lowercase(o) for o in data_dict)
    elif isinstance(data_dict, str):
        return data_dict.lower()
    else:
        return data_dict

def get_ipproperty(device_name, default_cfgfile, prop='ip_name'):
    processor = get_config_value('CONFIG_SUBSYSTEM_PROCESSOR_',default_cfgfile, 'choice','_SELECT=y')
    if device_name == 'MANUAL':
        return ''
    ipname = ''
    global slaves_dict
    slaves_dict = convert_dictto_lowercase(plnx_syshw_data['processor'][processor]['slaves'])
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

def get_mb_hwversion(default_cfgfile):
    processor = get_config_value('CONFIG_SUBSYSTEM_PROCESSOR_',default_cfgfile, 'choice','_SELECT=y')
    global slaves_dict
    if 'linux_kernel_properties' in plnx_syshw_data['processor'][processor].keys():
        linux_kernel_properties = plnx_syshw_data['processor'][processor]['linux_kernel_properties']
        if 'XILINX_MICROBLAZE0_HW_VER' in linux_kernel_properties.keys():
            return linux_kernel_properties['XILINX_MICROBLAZE0_HW_VER'].split(' ')[0]
        else:
            return ''
    return ''

def check_ip(prop, default_cfgfile):
    processor = get_config_value('CONFIG_SUBSYSTEM_PROCESSOR_',default_cfgfile, 'choice','_SELECT=y')
    if prop == 'MANUAL':
        return ''
    for key in plnx_syshw_data['processor'][processor]['slaves'].keys():
        if 'ip_name' in plnx_syshw_data['processor'][processor]['slaves'][key].keys():
            if prop == plnx_syshw_data['processor'][processor]['slaves'][key]['ip_name']:
                return True
    return ''

def get_sysconsole_bootargs(default_cfgfile, soc_family):
    global ipinfo_data
    serialname = get_config_value('CONFIG_SUBSYSTEM_SERIAL_',default_cfgfile,'choice','_SELECT=y')
    serialipname = get_ipproperty(serialname, default_cfgfile)
    serial_devfile = ''
    serial_earlycon = ''
    if serialipname in ipinfo_data.keys():
        if 'linux_console_file_name' in ipinfo_data[serialipname]['device_type']['serial'].keys():
            serial_devfile = ipinfo_data[serialipname]['device_type']['serial']['linux_console_file_name']
        if 'linux_earlycon_str' in ipinfo_data[serialipname]['device_type']['serial'].keys():
            serial_earlycon = ipinfo_data[serialipname]['device_type']['serial']['linux_earlycon_str']
    else:
        return ''
    if not serial_devfile:
        print('ERROR: Unknown serial ipname %s for %s.' % (serialipname,serialname))
        sys.exit(255)
    no_alias = get_config_value('CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS',default_cfgfile)
    serial_no = ''
    if no_alias == 'y':
        serial_no = serialname.lower().split(serialipname + '_')[1]
    if serial_no:
        serial_devfile = '%s%s' % ( serial_devfile[:-1], serial_no)
    baudrate = get_config_value('CONFIG_SUBSYSTEM_SERIAL_%s_BAUDRATE_' % serialname, default_cfgfile,'choice','=y')
    if not baudrate:
        print('ERROR: Failed to get baudrate of %s' % serialname)
        sys.exit(255)
    early_printk = get_config_value('CONFIG_SUBSYSTEM_BOOTARGS_EARLYPRINTK', default_cfgfile)
    if early_printk == 'y':
        earlyprintk = " earlycon"
        if soc_family == 'versal':
            serial_offset = '0xFF000000'
            if re.search('psv_sbsauart_1', serialname.lower()) or \
                    re.search('psx_sbsauart_1', serialname.lower()):
                serial_offset = '0xFF010000'
            earlyprintk=' earlycon=pl011,mmio32,%s,%sn8' % (serial_offset, baudrate)
    else:
        earlyprintk = ''
    if serial_earlycon:
        earlycon_addr = hex(get_ipproperty(serialname, default_cfgfile, 'baseaddr')).upper()
        if soc_family != 'versal':
            return '%s console=%s,%s clk_ignore_unused' % (earlyprintk, serial_devfile, baudrate)
        else:
            return 'console=%s %s clk_ignore_unused' % (serial_devfile, earlyprintk)
    else:
        return 'console=%s,%s%s' % (serial_devfile, baudrate, earlyprintk)

def get_soc_variant(soc_family, output):
    global plnx_syshw_data
    device_id = ''
    if 'device_id' in plnx_syshw_data.keys():
        device_id = plnx_syshw_data['device_id']
    soc_variant = ''
    if soc_family == 'zynqmp':
        if device_id.endswith('ev') or device_id.endswith('k26'):
            soc_variant = 'ev'
        elif device_id.endswith('eg'):
            soc_variant = 'eg'
        elif device_id.endswith('dr'):
            soc_variant = 'dr'
        else:
            soc_variant = 'eg'
    elif soc_family == 'versal':
        if device_id.startswith('xcvm'):
            soc_variant = 'prime'
        elif device_id.startswith('xcvc'):
            soc_variant = 'ai-core'
        elif device_id.startswith('xcvn'):
            soc_variant = 'net'
    return soc_variant

def pre_sys_conf(args, default_cfgfile):
    if args.machine:
        update_config_value('CONFIG_YOCTO_MACHINE_NAME', \
                '"%s"' % args.machine, default_cfgfile)

def post_sys_conf(args,default_cfgfile):
    output = args.output

    bootargs_auto = get_config_value('CONFIG_SUBSYSTEM_BOOTARGS_AUTO',default_cfgfile)
    rootfs_type = get_config_value('CONFIG_SUBSYSTEM_ROOTFS_',default_cfgfile,'choice')
    bootargs = ''
    if rootfs_type == 'INITRD':
        bootargs = 'root=/dev/ram0 rw'
    elif rootfs_type == 'NFS':
        ethdevname = get_config_value('CONFIG_SUBSYSTEM_ETHERNET_',default_cfgfile,'choice','_SELECT=y')
        nfsdir = get_config_value('CONFIG_SUBSYSTEM_NFSROOT_DIR',default_cfgfile)
        nfsserverip = get_config_value('CONFIG_SUBSYSTEM_NFSSERVER_IP',default_cfgfile) #petalinux-find-ipaddr TODO auto assign IP if AUTO
        use_dhcp = get_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_USE_DHCP' % ethdevname, default_cfgfile)
        static_ip = get_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_IP_ADDRESS' % ethdevname, default_cfgfile)
        bootargs = 'root=/dev/nfs nfsroot=%s:%s,tcp' % (nfsserverip, nfsdir)
        if use_dhcp:
            bootargs += ' ip=dhcp'
        elif static_ip:
            bootargs += ' ip=%s:%s' % (static_ip, nfsserverip)
        elif ethdevname == 'MANUAL':
            bootargs += ' ip=dhcp' # We assume to use dhcp for "manual" ethernet device
        bootargs += ' rw'
        # Make sure the NFSROOT_DIR is in /etc/exports
        #TODO Check /etc/exports file for nfs directory if not give warning
    elif rootfs_type == 'JFFS2':
        jffs2_partname = get_config_value('CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_JFFS2_PART_NAME', default_cfgfile)
        if not jffs2_partname:
            jffs2_partname = 'jffs2'
            if bootargs_auto:
                print('INFO: Jffs2 rootfs partition name is set to the default one "jffs2" since you haven\'t specify one')
        found_part = get_config_value('CONFIG_SUBSYSTEM_FLASH_', default_cfgfile, 'choice', '_NAME="%s"' % jffs2_partname)
        if not found_part:
            print('Warning: Jffs2 is selected as root FS but the jffs2 partition: "%s" is not defined in the system config menu.' % jffs2_partname)
            print('Warning: Please make sure you have "%s" defined in your flash partitions table.' % jffs2_partname)
        bootargs = 'root=mtd:%s rw rootfstype=jffs2' % jffs2_partname
    elif rootfs_type == 'UBIFS':
        ubi_partname = get_config_value('CONFIG_SUBSYSTEM_UBI_PART_NAME',default_cfgfile)
        if not ubi_partname:
            ubi_partname = 'ubifs'
            if bootargs_auto:
                print('INFO: UBIFS rootfs partition name is set to the default one "ubifs" since you haven\'t specify one')
        found_part = get_config_value('CONFIG_SUBSYSTEM_FLASH_', default_cfgfile, 'choice', '_NAME="%s"' % ubi_partname)
        ubi_partno = ''
        if not found_part:
             print('Warning: UBIFS is selected as root FS but the ubi partition: "%s" is not defined in the system config menu.' % ubi_partname)
             print('Warning: Please make sure you have "%s" defined as 2nd part in your flash partitions table' % ubi_partname)
        else:
            ubi_partno = found_part.split('_PART')[1]
        if not ubi_partno:
            ubi_partno = '2'
        bootargs = 'noinitrd root=ubi0:%s rw rootfstype=ubifs ubi.mtd=%s' % (ubi_partname, ubi_partno)
    elif rootfs_type == 'EXT4':
        sdrootdev = get_config_value('CONFIG_SUBSYSTEM_SDROOT_DEV', default_cfgfile)
        bootargs = 'root=%s rw rootwait' % sdrootdev

    ethdevname = get_config_value('CONFIG_SUBSYSTEM_ETHERNET_',default_cfgfile,'choice','_SELECT=y')
    macaddrauto = get_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_AUTO' % ethdevname, default_cfgfile)
    if macaddrauto == 'y':
        macaddr = ''
        macaddrpattern = get_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_PATTERN' % ethdevname,default_cfgfile)
        if not macaddrpattern:
            macaddrpattern = '00:0a:35:00:??:??'
        new_mac = ''
        import random
        for x in range(17):
            if macaddrpattern[x] == '?':
                new_mac += str(random.randint(0, 9))
            else:
                new_mac += macaddrpattern[x]
        update_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC' % ethdevname, '"%s"' % new_mac, default_cfgfile)
        update_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_AUTO' % ethdevname, 'disable', default_cfgfile)

    if bootargs_auto == 'y':
        consolebootargs = get_sysconsole_bootargs(default_cfgfile,args.soc_family)
        ramdisk_image = get_config_value('CONFIG_SUBSYSTEM_INITRAMFS_IMAGE_NAME', default_cfgfile)
        if ramdisk_image and re.search('initramfs',ramdisk_image):
            bootargs += ' init_fatal_sh=1'
        bootargs = '%s %s' % (consolebootargs, bootargs)
        vcu_bootargs = ''
        vcu_maxsize = ''
        if check_ip('vcu', default_cfgfile):
            vcu_maxsize = ipinfo_data['vcu']['linux_kernel_properties']['CMA_SIZE_MBYTES']
            if vcu_maxsize:
                vcu_bootargs = 'cma=%sM' % vcu_maxsize
        bootargs = '%s %s' % (bootargs, vcu_bootargs)
        extra_bootargs = get_config_value('CONFIG_SUBSYSTEM_EXTRA_BOOTARGS', default_cfgfile)
        if extra_bootargs:
            bootargs = '%s %s' % (bootargs, extra_bootargs)
        update_config_value('CONFIG_SUBSYSTEM_BOOTARGS_GENERATED', '"%s"' % bootargs, default_cfgfile)

def get_hw_description(args):
    hw_description = os.path.abspath(args.hw_description)
    output = os.path.abspath(args.output)
    soc_family = args.soc_family
    menuconfig = args.menuconfig

    if not os.path.exists(output):
        os.makedirs(output)
    if not os.path.isfile(hw_description):
        print('ERROR: XSA file doensn\'t exists: %s' % hw_description)
        sys.exit(255)
    hw_ext = pathlib.Path(hw_description).suffix
    if hw_ext != '.xsa':
        print('ERROR: Only .xsa file are supported given %s' % hw_ext)
        sys.exit(255)

    template_cfgfile = os.path.join(scripts_dir,'configs/config_%s' % soc_family)
    if not os.path.isfile(template_cfgfile):
        print('ERROR: Insupported soc_family: %s' % soc_family)
        sys.exit(255)

    # XSCT command to read the hw file and generate syshw file
    cmd = 'xsct -sdx -nodisp %s/hw-description.tcl plnx_gen_hwsysconf %s %s' % \
                (scripts_dir, hw_description, 'Kconfig.syshw')
    print('Running CMD: %s' % cmd)
    subprocess.check_call(cmd.split(),cwd=output)

    Kconfig_part = os.path.join(scripts_dir,'configs/Kconfig.part')
    ipinfo_file = os.path.join(scripts_dir,'data/ipinfo.yaml')
    plnx_syshw_file = os.path.join(output,'plnx_syshw_data')
    Kconfig_syshw = os.path.join(output,'Kconfig.syshw')

    for file_path in [Kconfig_part, ipinfo_file, plnx_syshw_file, Kconfig_syshw]:
        if not os.path.isfile(file_path):
            print('ERROR: %s is not found in tool' % file_path)
            sys.exit(255)

    import yaml
    global plnx_syshw_data
    global ipinfo_data
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()

    with open(ipinfo_file, 'r') as ipinfo_file_f:
        ipinfo_data = yaml.safe_load(ipinfo_file_f)
    ipinfo_file_f.close()

    Kconfig = os.path.join(output,'Kconfig')
    default_cfgfile = os.path.join(output,'config')
    if not os.path.isfile(default_cfgfile):
        shutil.copy2(template_cfgfile,default_cfgfile)
    if not os.path.isfile(Kconfig_part):
        shutil.copy2(Kconfig_part,output)

    soc_variant = get_soc_variant(soc_family, output)
    Kconfig_soc_family = soc_family.upper()
    Kconfig_str = start_menu.format(Kconfig_soc_family,output)
    if soc_variant:
        Kconfig_soc_variant = soc_variant.upper()
        Kconfig_str += socvariant_menu.format(Kconfig_soc_family,Kconfig_soc_variant)
    with open(Kconfig_part,'r',encoding='utf-8') as kconfig_part_f:
        kconfig_part_data = kconfig_part_f.read()
    kconfig_part_f.close()
    Kconfig_str += kconfig_part_data.replace('source ./Kconfig.syshw','source %s' % Kconfig_syshw)
    with open(Kconfig,'w') as kconfig_f:
        kconfig_f.write(Kconfig_str)
    kconfig_f.close()
    # Update the sysconfig with command line arguments
    # to reflect in menuconfig/config
    pre_sys_conf(args, default_cfgfile)
    if not menuconfig:
        cmd = 'yes "" | env KCONFIG_CONFIG=%s conf %s' % (default_cfgfile,Kconfig)
        print('Running CMD: %s' % cmd)
        os.system(cmd)
    else:
        cmd = 'env KCONFIG_CONFIG=%s mconf %s' % (default_cfgfile,Kconfig)
        print('Running CMD: %s' % cmd)
        subprocess.check_call(cmd.split(),cwd=output)
    post_sys_conf(args,default_cfgfile)
