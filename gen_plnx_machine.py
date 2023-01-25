#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

from gen_yocto_machine import *

plnx_conf_path = ''
global inherit_ext
inherit_ext = ''


def add_remote_sources(component, Kcomponent):
    is_remote = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE'
                                 % Kcomponent, default_cfgfile)
    conf_prop = {
        'linux-xlnx': ['KERNELURI', 'SRCREV', 'KBRANCH', 'LIC_FILES_CHKSUM'],
        'u-boot-xlnx': ['UBOOTURI', 'SRCREV', 'UBRANCH', 'LIC_FILES_CHKSUM'],
        'arm-trusted-firmware': ['REPO', 'SRCREV', 'BRANCH', 'LIC_FILES_CHKSUM'],
        'plm-firmware': ['REPO', 'SRCREV', 'BRANCH', 'LIC_FILES_CHKSUM'],
        'psm-firmware': ['REPO', 'SRCREV', 'BRANCH', 'LIC_FILES_CHKSUM'],
    }
    remort_source = ''
    if is_remote:
        remort_source += '\n#Remote %s source\n' % component
        remote_uri = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE_DOWNLOAD_PATH'
                                      % Kcomponent, default_cfgfile)
        remote_rev = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE_REFERENCE'
                                      % Kcomponent, default_cfgfile)
        remote_branch = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE_BRANCH'
                                         % Kcomponent, default_cfgfile)
        remote_checksum = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_LIC_FILES_CHKSUM_REMOTE'
                                           % Kcomponent, default_cfgfile)
        if remote_uri:
            remort_source += '%s:pn-%s = "%s"\n' \
                % (conf_prop[component][0],
                   component, remote_uri)
        if remote_rev:
            remort_source += '%s:pn-%s = "%s"\n' \
                % (conf_prop[component][1],
                   component, remote_rev)
        if remote_branch:
            remort_source += '%s:pn-%s = "%s"\n' \
                % (conf_prop[component][2],
                   component, remote_branch)
        if remote_checksum:
            remort_source += '%s:pn-%s = "%s"\n' \
                % (conf_prop[component][3],
                   component, remote_checksum)
    return remort_source


def add_external_sources(component, Kcomponent):
    is_external = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_EXT__LOCAL__SRC'
                                   % Kcomponent, default_cfgfile)
    ext_source = ''
    if is_external:
        global inherit_ext
        if not inherit_ext:
            ext_source += 'INHERIT += "externalsrc"\n'
            inherit_ext = True
        ext_source += '\n# External %s source\n' % component
        ext_path = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_EXT_LOCAL_SRC_PATH'
                                    % Kcomponent, default_cfgfile)
        ext_checksum = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_%s_LIC_FILES_CHKSUM_LOCAL__SRC'
                                        % Kcomponent, default_cfgfile)
        if ext_source:
            ext_source += 'EXTERNALSRC:pn-%s = "%s"\n' \
                % (component, ext_path)
        if ext_checksum:
            ext_source += 'LIC_FILES_CHKSUM:pn-%s = "%s"\n' \
                % (component, ext_checksum)
    return ext_source


def generate_kernel_cfg(args):
    logger.info('Generating kernel configuration files')
    sysconf_koptions = os.path.join(scripts_dir, 'data/sysconf_koptions.yaml')
    import yaml
    with open(sysconf_koptions, 'r') as sysconf_koptions_f:
        sysconf_koptions_data = yaml.safe_load(sysconf_koptions_f)
    sysconf_koptions_f.close()
    invalide_props = []
    # Filter sysconf_koptions.yaml, remove the ip list which are not enabled in design
    for device in sysconf_koptions_data['selected_device'].keys():
        is_invalid = ''
        if 'is_valid_and' in sysconf_koptions_data['selected_device'][device].keys():
            for is_valid in sysconf_koptions_data['selected_device'][device]['is_valid_and'].keys():
                value = sysconf_koptions_data['selected_device'][device]['is_valid_and'][is_valid]
                cfg_value = get_config_value(
                    'CONFIG_%s' % is_valid, default_cfgfile)

                if value != 'n':
                    if cfg_value != value:
                        if not device in invalide_props:
                            invalide_props.append(device)
                else:
                    if cfg_value == 'n':
                        if not device in invalide_props:
                            invalide_props.append(device)
    # remove the ip's in invalide_props from sysconf_koptions_data
    for prop in invalide_props:
        sysconf_koptions_data['selected_device'].pop(prop)
    kernel_opts = ''
    # Add linux_kernel_properties from sysconf_koptions.yaml
    for device in sysconf_koptions_data['selected_device'].keys():
        if 'linux_kernel_properties' in sysconf_koptions_data['selected_device'][device].keys():
            for prop in sysconf_koptions_data['selected_device'][device]['linux_kernel_properties'].keys():
                value = sysconf_koptions_data['selected_device'][device]['linux_kernel_properties'][prop]
                value = value.replace('bool', '').strip()
                if value == 'y':
                    kernel_opts += 'CONFIG_%s=y\n' % prop
                elif value == 'n':
                    kernel_opts += '# CONFIG_%s is not set\n' % prop

    ipinfo_file = os.path.join(scripts_dir, 'data/ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    with open(ipinfo_file, 'r') as ipinfo_file_f:
        ipinfo_data = yaml.safe_load(ipinfo_file_f)
    ipinfo_file_f.close()
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()
    processor = get_config_value('CONFIG_SUBSYSTEM_PROCESSOR_', default_cfgfile,
                                 'choice', '_SELECT=y')
    slaves_dict = convert_dictto_lowercase(
        plnx_syshw_data['processor'][processor]['slaves'])
    slaves = []
    # Get the slave ip_name from plnx_syshw_data which are enabled in design
    for slave in slaves_dict.keys():
        ipname = slaves_dict[slave]['ip_name']
        if ipname not in slaves:
            slaves.append(ipname)
    # Add linux_kernel_properties from ipinfo.yaml
    for slave in slaves:
        if slave in ipinfo_data.keys():
            if 'linux_kernel_properties' in ipinfo_data[slave].keys():
                for prop in ipinfo_data[slave]['linux_kernel_properties'].keys():
                    value = ipinfo_data[slave]['linux_kernel_properties'][prop]
                    value = value.replace('bool', '').strip()
                    if value == 'y':
                        kernel_opts += 'CONFIG_%s=y\n' % prop
                    elif value == 'n':
                        kernel_opts += '# CONFIG_%s is not set\n' % prop
    devtypes = []
    generic_devtype_kdrvs = ''
    ipdevtype_kdrvs = ''
    # Add device_type/linux_kernel_properties from ipinfo.yaml
    for ip in ipinfo_data.keys():
        if 'device_type' in ipinfo_data[ip].keys():
            for ip_type in ipinfo_data[ip]['device_type'].keys():
                if ipinfo_data[ip]['device_type'][ip_type]:
                    if 'linux_kernel_properties' in ipinfo_data[ip]['device_type'][ip_type].keys():
                        if ip_type not in devtypes:
                            devtypes.append(ip_type)

    for devtype in devtypes:
        devname = get_config_value('CONFIG_SUBSYSTEM_%s_' % devtype.upper(),
                                   default_cfgfile, 'choice', '_SELECT=y')
        devipname = get_ipproperty(devname, default_cfgfile)
        if not devipname:
            continue
        # Add devtype linux_kernel_properties from sysconfig_kernel.yaml
        if devtype in sysconf_koptions_data['selected_device'].keys():
            if 'linux_kernel_properties' in sysconf_koptions_data['selected_device'][devtype].keys():
                for prop in sysconf_koptions_data['selected_device'][devtype]['linux_kernel_properties'].keys():
                    value = sysconf_koptions_data['selected_device'][devtype]['linux_kernel_properties'][prop]
                    value = value.replace('bool', '').strip()
                    if value == 'y':
                        generic_devtype_kdrvs += 'CONFIG_%s=y\n' % prop
                    elif value == 'n':
                        generic_devtype_kdrvs += '# CONFIG_%s is not set\n' % prop
        # Add devtype linux_kernel_properties from ipinfo.yaml
        if devipname in ipinfo_data.keys():
            if devtype in ipinfo_data[devipname]['device_type'].keys():
                if 'linux_kernel_properties' in ipinfo_data[devipname]['device_type'][devtype].keys():
                    for prop in ipinfo_data[devipname]['device_type'][devtype]['linux_kernel_properties'].keys():
                        value = ipinfo_data[devipname]['device_type'][devtype]['linux_kernel_properties'][prop]
                        value = value.replace('bool', '').strip()
                        if value == 'y':
                            ipdevtype_kdrvs += 'CONFIG_%s=y\n' % prop
                        elif value == 'n':
                            ipdevtype_kdrvs += '# CONFIG_%s is not set\n' % prop
    if args.soc_family == 'microblaze':
        ipdevtype_kdrvs += 'CONFIG_EARLY_PRINTK=y\n'

    # Add processor related linux_kernel_properties from plnx_syshw_data
    if 'linux_kernel_properties' in plnx_syshw_data['processor'][processor].keys():
        for prop in plnx_syshw_data['processor'][processor]['linux_kernel_properties'].keys():
            valstr = plnx_syshw_data['processor'][processor]['linux_kernel_properties'][prop]
            val = valstr.split()[0]
            valtype = valstr.split()[1]
            if valtype == 'string':
                kernel_opts += 'CONFIG_%s="%s"\n' % (prop, val)
            else:
                kernel_opts += 'CONFIG_%s=%s\n' % (prop, val)
    memory = get_config_value('CONFIG_SUBSYSTEM_MEMORY_', default_cfgfile,
                              'choice', '_SELECT=y')
    memory_baseaddr = get_config_value('CONFIG_SUBSYSTEM_MEMORY_%s_BASEADDR'
                                       % memory, default_cfgfile)
    kernel_opts += 'CONFIG_KERNEL_BASE_ADDR=%s\n' % memory_baseaddr
    kernel_opts += 'CONFIG_BLK_DEV_INITRD=y\n'
    kernel_opts += '# CONFIG_CMDLINE_FORCE is not set\n'

    if generic_devtype_kdrvs:
        kernel_opts += generic_devtype_kdrvs
    if ipdevtype_kdrvs:
        kernel_opts += ipdevtype_kdrvs

    # Create and add kernel configs into plnx_kernel.cfg
    auto_linux_file = os.path.join(args.output, 'linux-xlnx/plnx_kernel.cfg')
    if not os.path.isdir(os.path.dirname(auto_linux_file)):
        os.makedirs(os.path.dirname(auto_linux_file))
    with open(auto_linux_file, 'w') as auto_linux_file_f:
        auto_linux_file_f.write(kernel_opts)
    auto_linux_file_f.close()


def generate_plnx_config(args, machine_conf_file, hw_flow):
    global default_cfgfile
    default_cfgfile = os.path.join(args.output, 'config')
    default_rfsfile = os.path.join(args.output, 'rootfs_config')
    if not os.path.isfile(default_cfgfile):
        logger.error('Failed to generate .conf file, Unable to find config'
                     ' file at: %s' % args.output)
        sys.exit(255)
    arch = get_config_value('CONFIG_SUBSYSTEM_ARCH_',
                            default_cfgfile, 'choice', '=y').lower()

    # Create a PetaLinux tool configuration file.
    global plnx_conf_path
    plnx_conf_file = 'plnxtool.conf'
    plnx_conf_path = os.path.join(args.output, plnx_conf_file)
    # Generate the plnxtool.conf if config/rootfs_config changed
    if validate_hashfile(args, 'SYSTEM_CONF', default_cfgfile, update=False) and \
            validate_hashfile(args, 'RFS_CONF', default_rfsfile, update=False) and \
            os.path.exists(plnx_conf_path):
        return plnx_conf_file
    logger.info('Generating plnxtool conf file')

    # Create a PetaLinux tool configuration file(plnxtool.conf) which set's
    # above generated ${MACHINE}-${DEVICE_ID} as Yocto MACHINE.
    soc_family = args.soc_family

    import yaml
    if hw_flow == 'xsct':
        plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    else:
        plnx_syshw_file = os.path.join(args.output, 'petalinux_config.yaml')
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()

    # Variable for constructing plnxtool.conf file.
    override_string = ''

    tmp_dir = get_config_value('CONFIG_TMP_DIR_LOCATION', default_cfgfile)
    override_string += '# PetaLinux Tool Auto generated file\n'
    override_string += '\n# Generic variables\n'
    override_string += generate_mirrors(args, arch)
    if hw_flow == 'xsct':
        override_string += '\nMACHINE = "%s"\n' % machine_conf_file

    if tmp_dir:
        override_string += 'TMPDIR = "%s"\n' % tmp_dir
        if hw_flow == 'sdt':
            override_string += 'BASE_TMPDIR = "%s-multiconfig"\n' % tmp_dir

    # AUTO add local uninative tarball if exists, to support no network case.
    # CONFIG_SITE variable exported in case of extensible SDK only
    import glob
    if 'CONFIG_SITE' in os.environ.keys():
        config_site = os.environ['CONFIG_SITE']
        sdk_path = os.path.dirname(config_site)
        if os.path.exists(sdk_path):
            uninative_path = os.path.join(sdk_path, 'downloads', 'uninative')
            # Check for exact x86_64-nativesdk file
            uninative_file = glob.glob(
                uninative_path + '/*/x86_64-nativesdk-libc*')
            if uninative_file:
                uninative_dir = os.path.dirname(uninative_file[0])
                # Add trainling slash if not present
                if not uninative_dir.endswith(os.path.sep):
                    uninative_dir += os.path.sep
                override_string += 'UNINATIVE_URL = "file://%s"\n' % uninative_dir
            if hw_flow == 'sdt':
                # Adding yocto-uninative.inc content due to getting multiple warnings
                poky_uninative_file = os.path.join(sdk_path, 'layers', 'poky', 'meta',
                                                   'conf', 'distro', 'include', 'yocto-uninative.inc')
                if os.path.exists(poky_uninative_file):
                    with open(poky_uninative_file, 'r') as file_data:
                        lines = file_data.readlines()
                        for line in lines:
                            line = line.strip()
                            if line.startswith('#') or line.startswith('UNINATIVE_URL'):
                                continue
                            else:
                                override_string += '%s\n' % line
                    file_data.close()
    bb_no_network = get_config_value('CONFIG_YOCTO_BB_NO_NETWORK',
                                     default_cfgfile)
    if bb_no_network:
        override_string += 'BB_NO_NETWORK = "1"\n'
    bb_num_threads = get_config_value('CONFIG_YOCTO_BB_NUMBER_THREADS',
                                      default_cfgfile)
    if bb_num_threads:
        override_string += 'BB_NUMBER_THREADS = "%s"\n' % bb_num_threads
    parallel_make = get_config_value('CONFIG_YOCTO_PARALLEL_MAKE',
                                     default_cfgfile)
    if parallel_make:
        override_string += 'PARALLEL_MAKE = "-j %s"\n' % parallel_make

    if soc_family == "zynqmp":
        override_string += 'LICENSE_FLAGS_ACCEPTED:append = " xilinx_pmu-rom-native"\n'

    override_string += 'PACKAGE_CLASSES = "package_rpm"\n'
    override_string += 'DL_DIR = "${TOPDIR}/downloads"\n'

    host_name = get_config_value('CONFIG_SUBSYSTEM_HOSTNAME', default_cfgfile)
    product_name = get_config_value(
        'CONFIG_SUBSYSTEM_PRODUCT', default_cfgfile)
    firmware_version = get_config_value('CONFIG_SUBSYSTEM_FW_VERSION',
                                        default_cfgfile)

    override_string += 'SSTATE_DIR = "${TOPDIR}/sstate-cache"\n'
    override_string += 'hostname:pn-base-files = "%s"\n' % host_name
    override_string += 'PETALINUX_PRODUCT:pn-base-files-plnx = "%s"\n' \
                       % product_name
    override_string += 'DISTRO_VERSION:pn-base-files-plnx = "%s"\n' \
                       % firmware_version

    if args.xsct_tool and hw_flow == 'xsct':
        override_string += '\n# SDK path variables\n'
        override_string += 'XILINX_SDK_TOOLCHAIN = "%s"\n' % args.xsct_tool
        override_string += 'USE_XSCT_TARBALL = "0"\n'

    override_string += '\n# PetaLinux tool linux-xlnx variables\n'
    override_string += add_remote_sources('linux-xlnx', 'LINUX__KERNEL')
    override_string += add_external_sources('linux-xlnx', 'LINUX__KERNEL')
    override_string += 'RRECOMMENDS:${KERNEL_PACKAGE_NAME}-base = ""\n'
    kernel_config = get_config_value('CONFIG_SUBSYSTEM_LINUX_CONFIG_TARGET',
                                     default_cfgfile)
    if kernel_config and kernel_config.lower() != 'auto':
        override_string += 'KBUILD_DEFCONFIG:%s = "%s"\n' % (
            soc_family, kernel_config)
    kernel_autoconfig = get_config_value('CONFIG_SUBSYSTEM_AUTOCONFIG_KERNEL',
                                         default_cfgfile)

    # Generate linux-xlnx fragment config for microblaze based on xsa.
    if soc_family == 'microblaze':
        if kernel_autoconfig:
            override_string += 'KERNEL_AUTO_CONFIG:pn-linux-xlnx = "1"\n'
            generate_kernel_cfg(args)

    override_string += '\n# PetaLinux tool device-tree variables\n'
    autoconfig_dt = get_config_value('CONFIG_SUBSYSTEM_AUTOCONFIG_DEVICE__TREE',
                                     default_cfgfile)
    if not autoconfig_dt:
        override_string += 'CONFIG_DISABLE:pn-device-tree = "1"\n'
    dt_xsct_ws = get_config_value('CONFIG_SUBSYSTEM_DT_XSCT_WORKSPACE',
                                  default_cfgfile)
    if dt_xsct_ws:
        override_string += 'XSCTH_WS:pn-device-tree = "%s"\n' % dt_xsct_ws

    dt_overlay = get_config_value('CONFIG_SUBSYSTEM_DTB_OVERLAY',
                                  default_cfgfile)
    if dt_overlay:
        override_string += 'YAML_ENABLE_DT_OVERLAY:pn-device-tree = "1"\n'
    dt_no_alias = get_config_value('CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS',
                                   default_cfgfile)
    if dt_no_alias:
        override_string += 'YAML_ENABLE_NO_ALIAS = "1"\n'
    dt_verbose = get_config_value('CONFIG_SUBSYSTEM_ENABLE_DT_VERBOSE',
                                  default_cfgfile)
    if dt_verbose:
        override_string += 'YAML_ENABLE_DT_VERBOSE = "1"\n'
    extra_dt_files = get_config_value('CONFIG_SUBSYSTEM_EXTRA_DT_FILES',
                                      default_cfgfile)
    if autoconfig_dt:
        override_string += 'EXTRA_DT_FILES = "%s"\n' % extra_dt_files
    dt_remove_pl = get_config_value('CONFIG_SUBSYSTEM_REMOVE_PL_DTB',
                                    default_cfgfile)
    if dt_remove_pl:
        override_string += 'YAML_REMOVE_PL_DT:pn-device-tree = "1"\n'
    dt_include_dir = get_config_value('CONFIG_SUBSYSTEM_DEVICE_TREE_INCLUDE_DIR',
                                      default_cfgfile)
    dt_manual_include = get_config_value('CONFIG_SUBSYSTEM_DEVICE_TREE_MANUAL_INCLUDE',
                                         default_cfgfile)
    if dt_manual_include:
        override_string += 'KERNEL_INCLUDE:append:pn-device-tree = " %s"\n' \
                           % dt_include_dir
    dt_openamp_dtsi = get_config_value('CONFIG_SUBSYSTEM_ENABLE_OPENAMP_DTSI',
                                       default_cfgfile)
    if dt_openamp_dtsi:
        override_string += 'ENABLE_OPENAMP_DTSI = "1"\n'

    override_string += '\n# PetaLinux tool U-boot variables\n'
    override_string += add_remote_sources('u-boot-xlnx', 'U__BOOT')
    override_string += add_external_sources('u-boot-xlnx', 'U__BOOT')
    uboot_autoconfig = get_config_value('CONFIG_SUBSYSTEM_AUTOCONFIG_U__BOOT',
                                        default_cfgfile)
    if soc_family == 'microblaze':
        if uboot_autoconfig:
            override_string += 'U_BOOT_AUTO_CONFIG:pn-u-boot-xlnx = "1"\n'
            auto_uboot_dir = os.path.join(args.output, 'u-boot-xlnx')
            if not os.path.isdir(auto_uboot_dir):
                os.makedirs(auto_uboot_dir)
            logger.info('Generating u-boot configuration files')
            cmd = 'xsct -sdx -nodisp %s/petalinux_hsm_bridge.tcl -c %s -a u-boot_bsp -hdf %s -o %s -data %s' % \
                (scripts_dir, default_cfgfile, os.path.abspath(args.hw_file),
                    auto_uboot_dir, os.path.join(scripts_dir, 'data'))
            run_cmd(cmd, args.output, args.logfile)

    if arch == 'aarch64':
        override_string += '\n# PetaLinux tool Arm-trusted-firmware variables\n'
        override_string += add_remote_sources(
            'arm-trusted-firmware', 'TRUSTED__FIRMWARE__ARM')
        override_string += add_external_sources(
            'arm-trusted-firmware', 'TRUSTED__FIRMWARE__ARM')
        atf_debug = get_config_value(
            'CONFIG_SUBSYSTEM_TF-A_DEBUG', default_cfgfile)
        if atf_debug:
            override_string += 'DEBUG_ATF = "1"\n'

    if soc_family == 'versal':
        override_string += '\n# PetaLinux tool PLM variables\n'
        override_string += add_remote_sources('plm-firmware', 'PLM')
        override_string += add_external_sources('plm-firmware', 'PLM')
        override_string += add_remote_sources('psm-firmware', 'PSM__FIRMWARE')
        override_string += add_external_sources(
            'psm-firmware', 'PSM__FIRMWARE')

    if soc_family in ['zynqmp', 'zynq']:
        fsbl_bspcompiler_flags = get_config_value('CONFIG_SUBSYSTEM_FSBL_BSPCOMPILER_FLAGS',
                                                  default_cfgfile)
        fsbl_bspcompiler_flagset = get_config_value('CONFIG_SUBSYSTEM_FSBL_BSPCOMPILER_FLAGSSET',
                                                    default_cfgfile)
        override_string += '\n# PetaLinux tool FSBL variables\n'
        if fsbl_bspcompiler_flagset:
            override_string += 'YAML_BSP_COMPILER_FLAGS:append:pn-fsbl-firmware = " %s"' \
                               % fsbl_bspcompiler_flags
        fsbl_compiler_extra_flags = get_config_value('CONFIG_SUBSYSTEM_FSBL_COMPILER_EXTRA_FLAGS',
                                                     default_cfgfile)
        override_string += 'YAML_COMPILER_FLAGS:append:pn-fsbl-firmware = " %s"\n' \
                           % fsbl_compiler_extra_flags

    if soc_family in ['zynqmp']:
        override_string += '\n# PetaLinux tool PMUFW variables\n'
        pmufw_bspcompiler_flags = get_config_value('CONFIG_SUBSYSTEM_PMUFW_BSPCOMPILER_FLAGS',
                                                   default_cfgfile)
        pmufw_bspcompiler_flagset = get_config_value('CONFIG_SUBSYSTEM_PMUFW_BSPCOMPILER_FLAGSSET',
                                                     default_cfgfile)
        if pmufw_bspcompiler_flagset:
            override_string += 'YAML_BSP_COMPILER_FLAGS:append:pn-pmu-firmware = " %s"' \
                % pmufw_bspcompiler_flags
        override_string += '\n'

    is_uboot_dtb = get_config_value('CONFIG_SUBSYSTEM_UBOOT_EXT_DTB',
                                    default_cfgfile)
    ubootdtb_dts_path = get_config_value('CONFIG_UBOOT_EXT_DTB_FROM_DTS',
                                         default_cfgfile)
    ubootdtb_packagename = get_config_value('CONFIG_UBOOT_DTB_PACKAGE_NAME',
                                            default_cfgfile)
    if is_uboot_dtb == 'y':
        override_string += 'PACKAGE_UBOOT_DTB_NAME = "%s"\n' % ubootdtb_packagename
        override_string += 'PACKAGES_LIST:append = " uboot-device-tree"'
        if ubootdtb_dts_path:
            override_string += 'UBOOT_DTS = "%s"\n' % ubootdtb_dts_path

    kernel_images = 'fitImage vmlinux'
    kernel_image = ''
    kernel_alt_image = ''
    if arch == 'arm':
        kernel_image = 'zImage'
        kernel_alt_image = 'uImage'
    elif arch == 'microblaze':
        kernel_image = 'linux.bin.ub'
        kernel_images += ' simpleImage.mb'
    elif arch == 'aarch64':
        kernel_images += ' Image.gz'
    if kernel_image:
        override_string += 'KERNEL_IMAGETYPE = "%s"\n' % kernel_image
    if kernel_alt_image:
        override_string += 'KERNEL_ALT_IMAGETYPE = "uImage"\n'

    override_string += '\n# PetaLinux tool FIT Variables\n'
    override_string += 'KERNEL_CLASSES:append = " kernel-fitimage"\n'
    override_string += 'KERNEL_IMAGETYPES:append = " %s"\n' % kernel_images
    override_string += '\n#Add u-boot-xlnx-scr Variables\n'
    if hw_flow == 'sdt':
        override_string += 'SYMLINK_FILES:%s = "%s:%s"\n' \
            % (soc_family, 'system-default.dtb', 'system.dtb')
        override_string += 'DEVICE_TREE_NAME = "system.dtb"\n'
    override_string += 'BOOTMODE = "generic"\n'
    override_string += 'BOOTFILE_EXT = ""\n'
    # Use MACHINE as override due to u-boot-xlnx-scr has $soc_family-$soc_variant overrides
    override_string += 'RAMDISK_IMAGE:${MACHINE} = "rootfs.cpio.gz.u-boot"\n'
    override_string += 'RAMDISK_IMAGE1:${MACHINE} = "ramdisk.cpio.gz.u-boot"\n'
    override_string += 'KERNEL_IMAGE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_KERNEL_IMAGE',
                           default_cfgfile)
    override_string += 'DEVICETREE_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_DEVICETREE_OFFSET',
                           default_cfgfile)
    override_string += 'KERNEL_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_KERNEL_OFFSET',
                           default_cfgfile)
    override_string += 'RAMDISK_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_RAMDISK_IMAGE_OFFSET',
                           default_cfgfile)
    override_string += 'QSPI_KERNEL_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_QSPI_KERNEL_OFFSET',
                           default_cfgfile)
    override_string += 'QSPI_KERNEL_SIZE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_QSPI_KERNEL_SIZE',
                           default_cfgfile)
    override_string += 'QSPI_RAMDISK_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_QSPI_RAMDISK_OFFSET',
                           default_cfgfile)
    override_string += 'QSPI_RAMDISK_SIZE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_QSPI_RAMDISK_SIZE',
                           default_cfgfile)
    override_string += 'QSPI_FIT_IMAGE_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_QSPI_FIT_IMAGE_OFFSET',
                           default_cfgfile)
    override_string += 'QSPI_FIT_IMAGE_SIZE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_QSPI_FIT_IMAGE_SIZE',
                           default_cfgfile)
    override_string += 'NAND_KERNEL_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_NAND_KERNEL_OFFSET',
                           default_cfgfile)
    override_string += 'NAND_KERNEL_SIZE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_NAND_KERNEL_SIZE',
                           default_cfgfile)
    override_string += 'NAND_RAMDISK_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_NAND_RAMDISK_OFFSET',
                           default_cfgfile)
    override_string += 'NAND_RAMDISK_SIZE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_NAND_RAMDISK_SIZE',
                           default_cfgfile)
    override_string += 'NAND_FIT_IMAGE_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_NAND_FIT_IMAGE_OFFSET',
                           default_cfgfile)
    override_string += 'NAND_FIT_IMAGE_SIZE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_NAND_FIT_IMAGE_SIZE',
                           default_cfgfile)
    override_string += 'FIT_IMAGE:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_FIT_IMAGE',
                           default_cfgfile)
    override_string += 'FIT_IMAGE_OFFSET:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_FIT_IMAGE_OFFSET',
                           default_cfgfile)
    override_string += 'PRE_BOOTENV:${MACHINE} = "%s"\n' \
        % get_config_value('CONFIG_SUBSYSTEM_UBOOT_PRE_BOOTENV',
                           default_cfgfile)

    rootfs_jffs2 = get_config_value('CONFIG_SUBSYSTEM_ROOTFS_JFFS2',
                                    default_cfgfile)
    if rootfs_jffs2:
        jffs2_size = get_config_value('CONFIG_SUBSYSTEM_JFFS2_ERASE_SIZE_',
                                      default_cfgfile, 'choice')
        jffs2_size = hex(int(jffs2_size) * 1024)
        override_string += '\n#jffs2 variables\n'
        override_string += 'JFFS2_ERASEBLOCK = "%s"\n' % jffs2_size

    rootfs_ubifs = get_config_value('CONFIG_SUBSYSTEM_ROOTFS_UBIFS',
                                    default_cfgfile)
    if rootfs_ubifs:
        override_string += '\n#ubi/ubifs variables\n'
        ubi_mubifs_args = get_config_value('CONFIG_SUBSYSTEM_UBI_MKUBIFS_ARGS',
                                           default_cfgfile)
        ubi_ubinize_args = get_config_value('CONFIG_SUBSYSTEM_UBI_UBINIZE_ARGS',
                                            default_cfgfile)
        ubi_part_name = get_config_value('CONFIG_SUBSYSTEM_UBI_PART_NAME',
                                         default_cfgfile)
        override_string += 'MKUBIFS_ARGS = "%s"\n' % ubi_mubifs_args
        override_string += 'UBINIZE_ARGS = "%s"\n' % ubi_ubinize_args
        override_string += 'UBI_VOLNAME = "%s"\n' % ubi_part_name

    provides_name = get_config_value('CONFIG_SUBSYSTEM_INITRAMFS_IMAGE_NAME',
                                     default_cfgfile)
    rootfs_initrd = get_config_value('CONFIG_SUBSYSTEM_ROOTFS_INITRD',
                                     default_cfgfile)
    if rootfs_initrd:
        override_string += '\nINITRAMFS_IMAGE = "%s"\n' % provides_name

    rootfs_initramfs = get_config_value('CONFIG_SUBSYSTEM_ROOTFS_INITRAMFS',
                                        default_cfgfile)
    if rootfs_initramfs:
        override_string += '\nINITRAMFS_IMAGE_BUNDLE = "1"\n'
        override_string += 'INITRAMFS_IMAGE = "%s"\n' % provides_name
        override_string += 'INITRAMFS_MAXSIZE = "524288"\n'

    rootfs_types = get_config_value('CONFIG_SUBSYSTEM_RFS_FORMATS',
                                    default_cfgfile)
    if rootfs_types:
        override_string += 'IMAGE_FSTYPES:%s = "%s"\n' % (
            soc_family, rootfs_types)

    if re.search('initramfs', provides_name):
        override_string += 'INITRAMFS_FSTYPES = "cpio.gz cpio.gz.u-boot tar.gz"\n'
        override_string += 'IMAGE_FSTYPES:pn-${INITRAMFS_IMAGE}:%s = "${INITRAMFS_FSTYPES}"\n' \
                           % (soc_family)

    override_string += '\n#Add EXTRA_IMAGEDEPENDS\n'
    imagedepends = {
        'microblaze': ['virtual/bootloader', 'virtual/fsboot',
                       'virtual/elfrealloc', 'u-boot-xlnx-scr'],
        'zynq': ['virtual/bootloader', 'virtual/fsbl', 'u-boot-xlnx-scr'],
        'zynqmp': ['virtual/bootloader', 'virtual/fsbl', 'virtual/pmu-firmware',
                   'arm-trusted-firmware', 'qemu-devicetrees', 'pmu-rom-native',
                   'u-boot-xlnx-scr'],
        'versal': ['virtual/bootloader', 'virtual/psm-firmware', 'virtual/plm',
                   'arm-trusted-firmware', 'u-boot-xlnx-scr',
                   'qemu-devicetrees', 'extract-cdo'],
    }
    imagedepends_remove = ['virtual/boot-bin']
    is_imgsel = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_IMG_SEL',
                                 default_cfgfile)
    is_uboot_dtb = get_config_value('CONFIG_SUBSYSTEM_UBOOT_EXT_DTB',
                                    default_cfgfile)
    if is_imgsel:
        imagedepends[soc_family].append('virtual/imgsel')
    if is_uboot_dtb:
        imagedepends[soc_family].append('virtual/uboot-dtb')

    is_fsboot = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_BOOTLOADER_NAME_FS__BOOT',
                                 default_cfgfile)
    if not is_fsboot and 'virtual/fsboot' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/fsboot')
        imagedepends_remove.append('virtual/fsboot')
    if not is_fsboot and 'virtual/elfrealloc' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/elfrealloc')
        imagedepends_remove.append('virtual/elfrealloc')
    is_fsbl = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_BOOTLOADER_AUTO_FSBL',
                               default_cfgfile)
    if not is_fsbl and 'virtual/fsbl' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/fsbl')
        imagedepends_remove.append('virtual/fsbl')
    is_pmufw = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_PMU_FIRMWARE',
                                default_cfgfile)
    if not is_pmufw and 'virtual/pmu-firmware' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/pmu-firmware')
        imagedepends_remove.append('virtual/pmu-firmware')
    is_plm = get_config_value(
        'CONFIG_SUBSYSTEM_COMPONENT_PLM', default_cfgfile)
    if not is_plm and 'virtual/plm' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/plm')
        imagedepends_remove.append('virtual/plm')
    is_psmfw = get_config_value('CONFIG_SUBSYSTEM_COMPONENT_PSM_FIRMWARE',
                                default_cfgfile)
    if not is_psmfw and 'virtual/psm-firmware' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/psm-firmware')
        imagedepends_remove.append('virtual/psm-firmware')
    override_string += 'EXTRA_IMAGEDEPENDS:append = " %s"\n' \
                       % ' '.join(imagedepends[soc_family])
    if imagedepends_remove:
        override_string += 'EXTRA_IMAGEDEPENDS:remove = "%s"\n' \
            % ' '.join(imagedepends_remove)
    override_string += 'SPL_BINARY = ""\n'
    if is_imgsel:
        override_string += 'PACKAGES_LIST:append = " imgsel"'

    pdi_name = get_config_value(
        'CONFIG_SUBSYSTEM_PDI_FILENAME', default_cfgfile)
    if pdi_name:
        override_string += 'BASE_PDI_NAME = "%s"\n' % pdi_name

    override_string += '\n#SDK variables\n'
    override_string += 'SDK_EXT_TYPE = "minimal"\n'
    override_string += 'SDK_INCLUDE_BUILDTOOLS = "0"\n'

    override_string += '\n# deploy class variables\n'
    override_string += 'INHERIT += "plnx-deploy"\n'
    plnx_deploydir = get_config_value(
        'CONFIG_PLNX_IMAGES_LOCATION', default_cfgfile)
    if plnx_deploydir:
        override_string += 'PLNX_DEPLOY_DIR = "%s"\n' % plnx_deploydir
    dtb_deployname = get_config_value(
        'CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_DTB_IMAGE_NAME', default_cfgfile)
    override_string += 'PACKAGE_DTB_NAME = "%s"\n' % dtb_deployname
    fit_deployname = get_config_value(
        'CONFIG_SUBSYSTEM_UIMAGE_NAME', default_cfgfile)
    override_string += 'PACKAGE_FITIMG_NAME = "%s"\n' % fit_deployname

    # Get design name from xsa
    design_name = ''
    if 'hw_design_name' in plnx_syshw_data.keys():
        design_name = plnx_syshw_data['hw_design_name']
    is_overlay = get_config_value(
        'CONFIG_SUBSYSTEM_DTB_OVERLAY', default_cfgfile)
    bitfile_name = 'system.bit'
    if is_overlay == 'y' and design_name:
        bitfile_name = design_name + '.bit'

    bitfile = glob.glob(os.path.dirname(args.hw_file) + '/*.bit')
    extra_files = '%s:config' % os.path.join(args.output, 'config')
    if bitfile:
        extra_files += ' %s:%s' % (bitfile[0], bitfile_name)

    override_string += 'EXTRA_FILESLIST:append = " %s"\n' % extra_files

    override_string += '\n#Below variables helps to add bbappend changes when this file included\n'
    override_string += 'WITHIN_PLNX_FLOW = "1"\n'
    override_string += 'SYSCONFIG_DIR = "%s"\n' % args.output

    with open(plnx_conf_path, 'w') as override_conf_f:
        override_conf_f.write(override_string)
    override_conf_f.close()

    # Rootfs configs
    rfsconfig_py = os.path.join(scripts_dir,
                                'rootfsconfigs/rootfs_config.py')
    default_rfsfile = os.path.join(args.output, 'rootfs_config')
    cmd = 'python3 %s --update_cfg %s %s %s' \
        % (rfsconfig_py, default_rfsfile,
           plnx_conf_path, soc_family)
    run_cmd(cmd, args.output, args.logfile)

    # Update config and rootfs_config file hash if changed
    validate_hashfile(args, 'SYSTEM_CONF', default_cfgfile)
    validate_hashfile(args, 'RFS_CONF', default_rfsfile)
    return plnx_conf_file
