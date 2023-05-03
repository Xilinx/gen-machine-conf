# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import sys
import os
import pathlib
import subprocess
import re
import shutil
import logger_setup

logger, console_h = logger_setup.setup_logger()


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

Kconfig_arch = '''
config system-{0}
        bool
        default y

'''
Kconfig_sdt = '''
config SUBSYSTEM_SDT_FLOW
        bool
        default y
        help

'''

Kconfig_multitarget = '''
config YOCTO_BBMC_{0}
        bool "{1}"
        default y
'''

base_dir = os.path.dirname(__file__)
scripts_dir = os.path.join(base_dir, 'gen-machine-scripts')


def get_filehashvalue(filename):
    import mmap
    import hashlib
    method = hashlib.sha256()
    with open(filename, "rb") as f:
        try:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                for chunk in iter(lambda: mm.read(8192), b''):
                    method.update(chunk)
        except ValueError:
            # You can't mmap() an empty file so silence this exception
            pass
    return method.hexdigest()


def validate_hashfile(args, macro, infile, update=True):
    statistics_file = os.path.join(args.output, '.statistics')
    old_hashvalue = get_config_value(macro, statistics_file)
    new_hashvalue = get_filehashvalue(infile)
    if old_hashvalue != new_hashvalue:
        if update:
            update_config_value(macro, new_hashvalue, statistics_file)
        return False
    return True


def update_config_value(macro, value, filename):
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()

    with open(filename, 'w') as file_data:
        for line in lines:
            if re.search('# %s is not set' % macro, line) or re.search('%s=' % macro, line):
                continue
            file_data.write(line)
        if value == 'disable':
            file_data.write('# %s is not set\n' % macro)
        else:
            file_data.write('%s=%s\n' % (macro, value))
    file_data.close()


def get_config_value(macro, filename, Type='bool', end_macro='=y'):
    lines = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_data:
            lines = file_data.readlines()
        file_data.close()
    value = ''
    if Type == 'bool':
        for line in lines:
            line = line.strip()
            if line.startswith(macro + '='):
                value = line.replace(macro + '=', '').replace('"', '')
                break
    elif Type == 'choice':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value = line.replace(macro, '').replace(end_macro, '')
                break
    elif Type == 'choicelist':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and line.endswith(end_macro):
                value += ' ' + line.replace(macro, '').replace(end_macro, '')
    elif Type == 'asterisk':
        for line in lines:
            line = line.strip()
            if line.startswith(macro) and re.search(end_macro, line):
                value = line.split('=')[1].replace('"', '')
                break
    return value


def convert_dictto_lowercase(data_dict):
    if isinstance(data_dict, dict):
        return {k.lower(): convert_dictto_lowercase(v) for k, v in data_dict.items()}
    elif isinstance(data_dict, (list, set, tuple)):
        t = type(data_dict)
        return t(convert_dictto_lowercase(o) for o in data_dict)
    elif isinstance(data_dict, str):
        return data_dict.lower()
    else:
        return data_dict


def get_ipproperty(device_name, default_cfgfile, prop='ip_name'):
    processor = get_config_value(
        'CONFIG_SUBSYSTEM_PROCESSOR_', default_cfgfile, 'choice', '_SELECT=y')
    if device_name == 'MANUAL':
        return ''
    ipname = ''
    global slaves_dict
    slaves_dict = convert_dictto_lowercase(
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


def get_processor_property(default_cfgfile, prop):
    processor = get_config_value(
        'CONFIG_SUBSYSTEM_PROCESSOR_', default_cfgfile, 'choice', '_SELECT=y')
    global slaves_dict
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


def get_tunefeatures(soc_family, default_cfgfile):
    processor = get_config_value(
        'CONFIG_SUBSYSTEM_PROCESSOR_', default_cfgfile, 'choice', '_SELECT=y')
    tune_features = [soc_family]
    hwversion = get_processor_property(
        default_cfgfile, 'XILINX_MICROBLAZE0_HW_VER')
    if hwversion:
        hwversion = 'v%s' % hwversion
        tune_features += [hwversion]
    for feature in Tunefeatures.keys():
        param_value = get_processor_property(default_cfgfile, feature)
        add_key = False
        for key in Tunefeatures[feature].keys():
            if key == param_value or (key.startswith('!') and key[1:] != param_value):
                tune_features += [Tunefeatures[feature][key]]
                add_key = True
        # Add default one from dict if key doesnot match
        if not add_key and 'default' in Tunefeatures[feature].keys():
            tune_features += [Tunefeatures[feature]['default']]

    return ' '.join(tune_features)


def check_ip(prop, default_cfgfile):
    processor = get_config_value(
        'CONFIG_SUBSYSTEM_PROCESSOR_', default_cfgfile, 'choice', '_SELECT=y')
    if prop == 'MANUAL':
        return ''
    for key in plnx_syshw_data['processor'][processor]['slaves'].keys():
        if 'ip_name' in plnx_syshw_data['processor'][processor]['slaves'][key].keys():
            if prop == plnx_syshw_data['processor'][processor]['slaves'][key]['ip_name']:
                return True
    return ''


def get_sysconsole_bootargs(default_cfgfile, soc_family, soc_variant):
    global ipinfo_data
    serialname = get_config_value(
        'CONFIG_SUBSYSTEM_SERIAL_', default_cfgfile, 'choice', '_SELECT=y')
    serialipname = get_ipproperty(serialname, default_cfgfile)
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
    no_alias = get_config_value(
        'CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS', default_cfgfile)
    serial_no = ''
    if no_alias == 'y':
        if "_" in serialname:
            serial_no = serialname.lower().split(serialipname + '_')[1]
        else:
            tmp = re.findall('[0-9]+', serialname)
            serial_no = tmp[0]
    if serial_no:
        serial_devfile = '%s%s' % (serial_devfile[:-1], serial_no)
    baudrate = get_config_value(
        'CONFIG_SUBSYSTEM_SERIAL_%s_BAUDRATE_' % serialname, default_cfgfile, 'choice', '=y')
    if not baudrate:
        logger.error('Failed to get baudrate of %s' % serialname)
        sys.exit(255)
    early_printk = get_config_value(
        'CONFIG_SUBSYSTEM_BOOTARGS_EARLYPRINTK', default_cfgfile)
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
        earlycon_addr = get_ipproperty(
            serialname, default_cfgfile, 'baseaddr')
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


def get_soc_variant(soc_family, output):
    global plnx_syshw_data
    device_id = ''
    if 'device_id' in plnx_syshw_data.keys():
        device_id = plnx_syshw_data['device_id']
    soc_variant = ''
    if soc_family == 'zynqmp':
        if device_id.endswith('ev') or device_id.endswith('k26'):
            soc_variant = 'ev'
        elif device_id.endswith('eg') or device_id.endswith('k24'):
            soc_variant = 'eg'
        elif device_id.endswith('dr'):
            soc_variant = 'dr'
        elif device_id.endswith('cg'):
            soc_variant = 'cg'
    elif soc_family == 'versal':
        if device_id.startswith('xcvm'):
            soc_variant = 'prime'
        elif device_id.startswith('xcvc'):
            soc_variant = 'ai-core'
        elif device_id.startswith('xcve'):
            soc_variant = 'ai-edge'
        elif device_id.startswith('xcvn'):
            soc_variant = 'net'
        elif device_id.startswith('xcvp'):
            soc_variant = 'premium'
        elif device_id.startswith('xcvh'):
            soc_variant = 'hbm'
    return soc_variant


def pre_sys_conf(args, default_cfgfile):
    if args.machine:
        update_config_value('CONFIG_YOCTO_MACHINE_NAME',
                            '"%s"' % args.machine, default_cfgfile)


def post_sys_conf(args, default_cfgfile, hw_flow, soc_variant):
    output = args.output

    bootargs_auto = get_config_value(
        'CONFIG_SUBSYSTEM_BOOTARGS_AUTO', default_cfgfile)
    rootfs_type = get_config_value(
        'CONFIG_SUBSYSTEM_ROOTFS_', default_cfgfile, 'choice')
    bootargs = ''
    if rootfs_type == 'INITRD':
        bootargs = 'root=/dev/ram0 rw'
    elif rootfs_type == 'NFS':
        ethdevname = get_config_value(
            'CONFIG_SUBSYSTEM_ETHERNET_', default_cfgfile, 'choice', '_SELECT=y')
        nfsdir = get_config_value(
            'CONFIG_SUBSYSTEM_NFSROOT_DIR', default_cfgfile)
        nfsserverip = get_config_value(
            'CONFIG_SUBSYSTEM_NFSSERVER_IP', default_cfgfile)
        cmd = '%s/petalinux-find-ipaddr %s' % (scripts_dir, nfsserverip)
        nfsserverip = run_cmd(cmd, output, args.logfile)[0].strip()
        use_dhcp = get_config_value(
            'CONFIG_SUBSYSTEM_ETHERNET_%s_USE_DHCP' % ethdevname, default_cfgfile)
        static_ip = get_config_value(
            'CONFIG_SUBSYSTEM_ETHERNET_%s_IP_ADDRESS' % ethdevname, default_cfgfile)
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
        jffs2_partname = get_config_value(
            'CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_JFFS2_PART_NAME', default_cfgfile)
        if not jffs2_partname:
            jffs2_partname = 'jffs2'
            if bootargs_auto:
                logger.info(
                    'Jffs2 rootfs partition name is set to the default one "jffs2" since you haven\'t specify one')
        found_part = get_config_value(
            'CONFIG_SUBSYSTEM_FLASH_', default_cfgfile, 'choice', '_NAME="%s"' % jffs2_partname)
        if not found_part:
            logger.warning(
                'Jffs2 is selected as root FS but the jffs2 partition: "%s" is not defined in the system config menu.' % jffs2_partname)
            logger.warning(
                'Please make sure you have "%s" defined in your flash partitions table.' % jffs2_partname)
        bootargs = 'root=mtd:%s rw rootfstype=jffs2' % jffs2_partname
    elif rootfs_type == 'UBIFS':
        ubi_partname = get_config_value(
            'CONFIG_SUBSYSTEM_UBI_PART_NAME', default_cfgfile)
        if not ubi_partname:
            ubi_partname = 'ubifs'
            if bootargs_auto:
                logger.info(
                    'UBIFS rootfs partition name is set to the default one "ubifs" since you haven\'t specify one')
        found_part = get_config_value(
            'CONFIG_SUBSYSTEM_FLASH_', default_cfgfile, 'choice', '_NAME="%s"' % ubi_partname)
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
        sdrootdev = get_config_value(
            'CONFIG_SUBSYSTEM_SDROOT_DEV', default_cfgfile)
        bootargs = 'root=%s ro rootwait' % sdrootdev

    ethdevname = get_config_value(
        'CONFIG_SUBSYSTEM_ETHERNET_', default_cfgfile, 'choice', '_SELECT=y')
    macaddrauto = get_config_value(
        'CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_AUTO' % ethdevname, default_cfgfile)
    if macaddrauto == 'y':
        macaddr = ''
        macaddrpattern = get_config_value(
            'CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_PATTERN' % ethdevname, default_cfgfile)
        if not macaddrpattern:
            macaddrpattern = '00:0a:35:00:??:??'
        new_mac = ''
        import random
        for x in range(17):
            if macaddrpattern[x] == '?':
                new_mac += str(random.randint(0, 9))
            else:
                new_mac += macaddrpattern[x]
        update_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC' %
                            ethdevname, '"%s"' % new_mac, default_cfgfile)
        update_config_value('CONFIG_SUBSYSTEM_ETHERNET_%s_MAC_AUTO' %
                            ethdevname, 'disable', default_cfgfile)

    if bootargs_auto == 'y':
        consolebootargs = get_sysconsole_bootargs(
            default_cfgfile, args.soc_family, soc_variant)
        ramdisk_image = get_config_value(
            'CONFIG_SUBSYSTEM_INITRAMFS_IMAGE_NAME', default_cfgfile)
        if ramdisk_image and re.search('initramfs', ramdisk_image):
            bootargs += ' init_fatal_sh=1'
        bootargs = '%s %s' % (consolebootargs, bootargs)
        vcu_bootargs = ''
        vcu_maxsize = ''
        if check_ip('vcu', default_cfgfile):
            vcu_maxsize = ipinfo_data['vcu']['linux_kernel_properties']['CMA_SIZE_MBYTES']
            if vcu_maxsize:
                vcu_bootargs = 'cma=%sM' % vcu_maxsize
        bootargs = '%s %s' % (bootargs, vcu_bootargs)

        vdu_bootargs = ''
        vdu_maxsize = ''
        if check_ip('vdu', default_cfgfile):
            vdu_maxsize = ipinfo_data['vdu']['linux_kernel_properties']['CMA_SIZE_MBYTES']
            if vdu_maxsize:
                vdu_bootargs = 'cma=%sM' % vdu_maxsize
        bootargs = '%s %s' % (bootargs, vdu_bootargs)
        extra_bootargs = get_config_value(
            'CONFIG_SUBSYSTEM_EXTRA_BOOTARGS', default_cfgfile)
        if extra_bootargs:
            bootargs = '%s %s' % (bootargs, extra_bootargs)
        update_config_value('CONFIG_SUBSYSTEM_BOOTARGS_GENERATED',
                            '"%s"' % re.sub(' +', ' ', bootargs.strip()), default_cfgfile)
    # generate flash parts info for given xsa
    if hw_flow == 'xsct':
        ipinfo_file = os.path.join(scripts_dir, 'data/ipinfo.yaml')
        flashinfo_file = os.path.join(output, 'flash_parts.txt')
        # No need to run if system conf file(config) is doesnot change
        if validate_hashfile(args, 'SYSTEM_CONF', default_cfgfile, update=False) and \
                os.path.exists(flashinfo_file):
            return 0

        with open(flashinfo_file, 'w') as fp:
            pass
        cmd = 'xsct -sdx -nodisp %s/petalinux_hsm.tcl get_flash_width_parts %s %s %s %s' % \
            (scripts_dir, default_cfgfile, ipinfo_file, args.hw_file,
             flashinfo_file)
        run_cmd(cmd, output, args.logfile)


# Run menuconfig/silentconfig
def run_menuconfig(Kconfig, cfgfile, ui, out_dir, component):
    if not ui:
        logger.info('Silentconfig %s' % (component))
        cmd = 'yes "" | env KCONFIG_CONFIG=%s conf %s' % (cfgfile, Kconfig)
        logger.debug('Running CMD: %s' % cmd)
        status, stdout = subprocess.getstatusoutput(cmd)
        logger.debug(stdout)
        if status != 0:
            logger.error('Failed to silentconfig %s' % component)
            raise Exception(stdout)
    else:
        logger.info('Menuconfig %s' % (component))
        cmd = 'env KCONFIG_CONFIG=%s mconf -s %s' % (cfgfile, Kconfig)
        logger.debug('Running CMD: %s' % cmd)
        try:
            subprocess.check_call(cmd.split(), cwd=out_dir)
        except subprocess.CalledProcessError as e:
            if e.returncode != 0:
                logger.error('Failed to Menuconfig %s' % component)
                raise Exception


# Run shell commands
def run_cmd(command, out_dir, logfile, shell=False):
    logger.debug('Running CMD: %s' % command)
    command = command.split() if not shell else command
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=shell,
                               cwd=out_dir)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise Exception(stderr.decode("utf-8"))
    else:
        if not stdout is None:
            stdout = stdout.decode("utf-8")
        if not stderr is None:
            stderr = stderr.decode("utf-8")
    logger.debug(stdout)
    return stdout, stderr


# Rootfs configs starts
def add_rootfs_configs(args, default_cfgfile):
    arch = get_config_value('CONFIG_SUBSYSTEM_ARCH_',
                            default_cfgfile, 'choice', '=y').lower()
    # template files for rootfs
    template_rfsfile = os.path.join(scripts_dir,
                                    'rootfsconfigs/rootfsconfig_%s' % args.soc_family)
    template_Kconfig = os.path.join(scripts_dir,
                                    'rootfsconfigs/Kconfig-%s.part' % arch)
    rfsconfig_py = os.path.join(scripts_dir,
                                'rootfsconfigs/rootfs_config.py')
    if args.add_rootfsconfig:
        user_cfg = os.path.realpath(args.add_rootfsconfig)
    else:
        user_cfg = os.path.join(scripts_dir,
                                'rootfsconfigs/user-rootfsconfig')

    # Create rootfsconfigs dir if not found
    rootfs_cfgdir = os.path.join(args.output, 'rootfsconfigs')
    if not os.path.exists(rootfs_cfgdir):
        os.makedirs(rootfs_cfgdir)

    default_rfsfile = os.path.join(args.output, 'rootfs_config')
    rfsKconfig_part = os.path.join(rootfs_cfgdir, 'Kconfig.part')
    rfsKconfig_user = os.path.join(rootfs_cfgdir, 'Kconfig.user')
    rootfs_Kconfig = os.path.join(rootfs_cfgdir, 'Kconfig')

    for file_path in [template_rfsfile, template_Kconfig, rfsconfig_py]:
        if not os.path.isfile(file_path):
            logger.error('%s is not found in tool' % file_path)
            sys.exit(255)

    if not os.path.isfile(default_rfsfile):
        shutil.copy2(template_rfsfile, default_rfsfile)
    if not os.path.isfile(rfsKconfig_part):
        shutil.copy2(template_Kconfig, rfsKconfig_part)
    shutil.copy2(user_cfg, rootfs_cfgdir)
    # No need to run if user_rootfsconfig doesnot changes
    if not validate_hashfile(args, 'USER_RFS_CFG', user_cfg) or \
            not os.path.exists(rfsKconfig_user):
        logger.info('Generating kconfig for rootfs')
        cmd = 'python3 %s --generate_kconfig %s %s' \
            % (rfsconfig_py, user_cfg, rootfs_cfgdir)
        run_cmd(cmd, args.output, args.logfile)
    rfsKconfig_str = Kconfig_arch.format(args.soc_family)
    with open(rfsKconfig_part, 'r', encoding='utf-8') as rfskconfig_part_f:
        rfskconfig_part_data = rfskconfig_part_f.read()
    rfskconfig_part_f.close()
    rfsKconfig_str += rfskconfig_part_data.replace(
        'source ./Kconfig.user', 'source %s' % rfsKconfig_user)
    with open(rootfs_Kconfig, 'w') as rfskconfig_f:
        rfskconfig_f.write(rfsKconfig_str)
    rfskconfig_f.close()
    run_menuconfig(rootfs_Kconfig, default_rfsfile,
                   True if args.menuconfig == 'rootfs' else False,
                   args.output, 'rootfs')


def get_hw_description(args, hw_flow):
    builddir = os.environ.get('BUILDDIR', '')
    output = os.path.abspath(args.output)
    soc_family = args.soc_family
    menuconfig = args.menuconfig
    project_cfgdir = os.path.join(output, 'configs')

    if not os.path.exists(project_cfgdir):
        os.makedirs(project_cfgdir)

    template_cfgfile = os.path.join(
        scripts_dir, 'configs/config_%s' % soc_family)
    if not os.path.isfile(template_cfgfile):
        logger.error('Unsupported soc_family: %s' % soc_family)
        sys.exit(255)

    # XSCT command to read the hw file and generate syshw file
    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    if hw_flow == 'xsct':
        cmd = 'xsct -sdx -nodisp %s/hw-description.tcl plnx_gen_hwsysconf %s %s' % \
            (scripts_dir, args.hw_file, Kconfig_syshw)
        ipinfo_file = os.path.join(scripts_dir, 'data/ipinfo.yaml')
        plnx_syshw_file = os.path.join(output, 'plnx_syshw_data')
    elif hw_flow == 'sdt':
        cmd = 'chmod 777 %s/sdt-description.tcl;' % (scripts_dir)
        cmd += 'tclsh %s/sdt-description.tcl plnx_gen_hwsysconf "" %s' % \
            (scripts_dir, Kconfig_syshw)
        ipinfo_file = os.path.join(scripts_dir, 'data/sdt_ipinfo.yaml')
        plnx_syshw_file = os.path.join(output, 'petalinux_config.yaml')
    ipinfo_file = os.path.join(scripts_dir, 'data/ipinfo.yaml')

    # Generate Kconfig.syshw only when hw_file changes
    if not validate_hashfile(args, 'HW_FILE', args.hw_file) or \
            not os.path.exists(Kconfig_syshw):
        logger.info('Generating Kconfig for project')
        run_cmd(cmd, output, args.logfile, shell=True)
    Kconfig_part = os.path.join(scripts_dir, 'configs/Kconfig.part')

    for file_path in [Kconfig_part, ipinfo_file, plnx_syshw_file, Kconfig_syshw]:
        if not os.path.isfile(file_path):
            logger.error('%s is not found in tool' % file_path)
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

    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    default_cfgfile = os.path.join(output, 'config')
    if not os.path.isfile(default_cfgfile):
        shutil.copy2(template_cfgfile, default_cfgfile)
    if not os.path.isfile(Kconfig_part):
        shutil.copy2(Kconfig_part, output)

    soc_variant = get_soc_variant(soc_family, output)
    Kconfig_soc_family = soc_family.upper()
    Kconfig_str = start_menu.format(Kconfig_soc_family, output)
    if hw_flow == 'sdt':
        if builddir:
            bbmulticonfig = get_config_value(
                'BBMULTICONFIG',
                os.path.join(builddir, 'conf', 'sdt-auto.conf'), 'asterisk', '=')
            Kconfig_str += "menu \"Multiconfig Targets\""
            for config in bbmulticonfig.split():
                Kconfig_str += Kconfig_multitarget.format(
                    config.upper().replace("-", "_"), config)
            Kconfig_str += "endmenu"
        Kconfig_str += Kconfig_sdt
    if soc_variant:
        Kconfig_soc_variant = soc_variant.upper()
        Kconfig_str += socvariant_menu.format(
            Kconfig_soc_family, Kconfig_soc_variant)
    with open(Kconfig_part, 'r', encoding='utf-8') as kconfig_part_f:
        kconfig_part_data = kconfig_part_f.read()
    kconfig_part_f.close()
    Kconfig_str += kconfig_part_data.replace(
        'source ./Kconfig.syshw', 'source %s' % Kconfig_syshw)
    with open(Kconfig, 'w') as kconfig_f:
        kconfig_f.write(Kconfig_str)
    kconfig_f.close()
    # Update the sysconfig with command line arguments
    # to reflect in menuconfig/config
    pre_sys_conf(args, default_cfgfile)
    run_menuconfig(Kconfig, default_cfgfile,
                   True if menuconfig == 'project' else False,
                   output, 'project')
    post_sys_conf(args, default_cfgfile, hw_flow, soc_variant)
    # update rootfs configs to plnxtool.conf
    add_rootfs_configs(args, default_cfgfile)
