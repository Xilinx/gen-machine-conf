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
import logging
import xilinx_mirrors
import re
import project_config
from post_process_config import GetIPProperty


logger = logging.getLogger('Gen-Machineconf')

global inherit_ext
inherit_ext = ''


def AddRemoteSources(component, Kcomponent):
    is_remote = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE'
                                            % Kcomponent, system_conffile)
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
        remote_uri = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE_DOWNLOAD_PATH'
                                                 % Kcomponent, system_conffile)
        remote_rev = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE_REFERENCE'
                                                 % Kcomponent, system_conffile)
        remote_branch = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_REMOTE_BRANCH'
                                                    % Kcomponent, system_conffile)
        remote_checksum = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_LIC_FILES_CHKSUM_REMOTE'
                                                      % Kcomponent, system_conffile)
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


def AddExternalSources(component, Kcomponent):
    is_external = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_EXT__LOCAL__SRC'
                                              % Kcomponent, system_conffile)
    ext_source = ''
    if is_external:
        global inherit_ext
        if not inherit_ext:
            ext_source += 'INHERIT += "externalsrc"\n'
            inherit_ext = True
        ext_source += '\n# External %s source\n' % component
        ext_path = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_NAME_EXT_LOCAL_SRC_PATH'
                                               % Kcomponent, system_conffile)
        ext_checksum = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_%s_LIC_FILES_CHKSUM_LOCAL__SRC'
                                                   % Kcomponent, system_conffile)
        if ext_source:
            ext_source += 'EXTERNALSRC:pn-%s = "%s"\n' \
                % (component, ext_path)
        if ext_checksum:
            ext_source += 'LIC_FILES_CHKSUM:pn-%s = "%s"\n' \
                % (component, ext_checksum)
    return ext_source


def GenerateKernelCfg(args):
    logger.info('Generating kernel configuration files')
    genmachine_scripts = project_config.GenMachineScriptsPath()
    sysconf_koptions = os.path.join(
        genmachine_scripts, 'data/sysconf_koptions.yaml')
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
                cfg_value = common_utils.GetConfigValue(
                    'CONFIG_%s' % is_valid, system_conffile)

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

    ipinfo_file = os.path.join(genmachine_scripts, 'data/ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    with open(ipinfo_file, 'r') as ipinfo_file_f:
        ipinfo_data = yaml.safe_load(ipinfo_file_f)
    ipinfo_file_f.close()
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
    plnx_syshw_file_f.close()
    processor = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PROCESSOR_', system_conffile,
                                            'choice', '_SELECT=y')
    slaves_dict = common_utils.convert_dictto_lowercase(
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
        devname = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_%s_' % devtype.upper(),
                                              system_conffile, 'choice', '_SELECT=y')
        devipname = GetIPProperty(devname, system_conffile)
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
    memory = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_', system_conffile,
                                         'choice', '_SELECT=y')
    memory_baseaddr = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_MEMORY_%s_BASEADDR'
                                                  % memory, system_conffile)
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


def GeneratePlnxConfig(args, machine_conf_file):
    genmachine_scripts = project_config.GenMachineScriptsPath()
    hw_flow = args.hw_flow
    global system_conffile
    system_conffile = os.path.join(args.output, 'config')
    rootfs_conffile = os.path.join(args.output, 'rootfs_config')
    if not os.path.isfile(system_conffile):
        logger.error('Failed to generate .conf file, Unable to find config'
                     ' file at: %s' % args.output)
        sys.exit(255)
    arch = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ARCH_',
                                       system_conffile, 'choice', '=y').lower()

    # Create a PetaLinux tool configuration file.
    plnx_conf_file = 'plnxtool.conf'
    plnx_conf_path = os.path.join(args.config_dir, plnx_conf_file)
    # Generate the plnxtool.conf if config/rootfs_config changed
    if common_utils.ValidateHashFile(args.output, 'SYSTEM_CONF', system_conffile, update=False) and \
            common_utils.ValidateHashFile(args.output, 'RFS_CONF', rootfs_conffile, update=False) and \
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

    tmp_dir = common_utils.GetConfigValue(
        'CONFIG_TMP_DIR_LOCATION', system_conffile)
    override_string += '# PetaLinux Tool Auto generated file\n'
    override_string += '\n# Generic variables\n'
    override_string += xilinx_mirrors.GenerateMirrors(args, arch)
    override_string += '\nSIGGEN_UNLOCKED_RECIPES += "busybox"\n'
    override_string += '\nMACHINE = "%s"\n' % machine_conf_file

    if tmp_dir:
        override_string += 'TMPDIR = "%s"\n' % tmp_dir
        if hw_flow == 'sdt':
            override_string += 'BASE_TMPDIR = "%s-multiconfig"\n' % tmp_dir
    if hw_flow == 'sdt':
        bbmultitargets = common_utils.GetConfigValue('CONFIG_YOCTO_BBMC_', system_conffile,
                                                     'choicelist', '=y').lower().replace('_', '-')
        override_string += '# targets to build the multi artifacts\n'
        override_string += 'BBMULTICONFIG = "%s"\n' % bbmultitargets
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
    bb_no_network = common_utils.GetConfigValue('CONFIG_YOCTO_BB_NO_NETWORK',
                                                system_conffile)
    if bb_no_network:
        override_string += 'BB_NO_NETWORK = "1"\n'
    bb_num_threads = common_utils.GetConfigValue('CONFIG_YOCTO_BB_NUMBER_THREADS',
                                                 system_conffile)
    if bb_num_threads:
        override_string += 'BB_NUMBER_THREADS = "%s"\n' % bb_num_threads
    bb_num_parse_threads = common_utils.GetConfigValue('CONFIG_YOCTO_BB_NUMBER_PARSE_THREADS',
                                                       system_conffile)
    if bb_num_parse_threads:
        override_string += 'BB_NUMBER_PARSE_THREADS = "%s"\n' % bb_num_parse_threads

    parallel_make = common_utils.GetConfigValue('CONFIG_YOCTO_PARALLEL_MAKE',
                                                system_conffile)
    if parallel_make:
        override_string += 'PARALLEL_MAKE = "-j %s"\n' % parallel_make

    override_string += 'PACKAGE_CLASSES = "package_rpm"\n'
    override_string += 'DL_DIR = "${TOPDIR}/downloads"\n'

    host_name = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_HOSTNAME', system_conffile)
    product_name = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PRODUCT', system_conffile)
    firmware_version = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FW_VERSION',
                                                   system_conffile)

    override_string += 'SSTATE_DIR = "${TOPDIR}/sstate-cache"\n'
    override_string += 'hostname:pn-base-files = "%s"\n' % host_name
    override_string += 'PETALINUX_PRODUCT:pn-base-files-plnx = "%s"\n' \
                       % product_name
    override_string += 'DISTRO_VERSION:pn-base-files-plnx = "%s"\n' \
                       % firmware_version

    if hasattr(args, 'xsct_tool') and args.xsct_tool and hw_flow == 'xsct':
        override_string += '\n# SDK path variables\n'
        override_string += 'XILINX_SDK_TOOLCHAIN = "%s"\n' % args.xsct_tool
        override_string += 'USE_XSCT_TARBALL = "0"\n'

    override_string += '\n# PetaLinux tool linux-xlnx variables\n'
    override_string += AddRemoteSources('linux-xlnx', 'LINUX__KERNEL')
    override_string += AddExternalSources('linux-xlnx', 'LINUX__KERNEL')
    override_string += 'RRECOMMENDS:${KERNEL_PACKAGE_NAME}-base = ""\n'
    kernel_config = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_LINUX_CONFIG_TARGET',
                                                system_conffile)
    if kernel_config and kernel_config.lower() != 'auto':
        override_string += 'KBUILD_DEFCONFIG:%s = "%s"\n' % (
            soc_family, kernel_config)
    kernel_autoconfig = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_AUTOCONFIG_KERNEL',
                                                    system_conffile)

    # Generate linux-xlnx fragment config for microblaze based on xsa.
    if soc_family == 'microblaze':
        if kernel_autoconfig:
            override_string += 'KERNEL_AUTO_CONFIG:pn-linux-xlnx = "1"\n'
            GenerateKernelCfg(args)

    override_string += '\n# PetaLinux tool device-tree variables\n'
    autoconfig_dt = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_AUTOCONFIG_DEVICE__TREE',
                                                system_conffile)
    if not autoconfig_dt:
        override_string += 'CONFIG_DISABLE:pn-device-tree = "1"\n'
    dt_xsct_ws = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DT_XSCT_WORKSPACE',
                                             system_conffile)
    if dt_xsct_ws:
        override_string += 'XSCTH_WS:pn-device-tree = "%s"\n' % dt_xsct_ws

    dt_overlay = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DTB_OVERLAY',
                                             system_conffile)
    if dt_overlay:
        override_string += 'YAML_ENABLE_DT_OVERLAY:pn-device-tree = "1"\n'
    dt_no_alias = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_NO_ALIAS',
                                              system_conffile)
    if dt_no_alias:
        override_string += 'YAML_ENABLE_NO_ALIAS = "1"\n'
    # Generate dtg/system-top.dts aliases in final dtb instead of using it from board.dts /DT machine file
    only_dtg_alias = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_DTG_ALIAS',
                                                 system_conffile)
    if only_dtg_alias:
        override_string += 'YAML_ENABLE_DTG_ALIAS = "1"\n'

    dt_no_labels = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_NO_LABELS',
                                               system_conffile)
    if dt_no_labels:
        override_string += 'YAML_ENABLE_NO_LABELS = "1"\n'

    dt_verbose = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_DT_VERBOSE',
                                             system_conffile)
    if dt_verbose:
        override_string += 'YAML_ENABLE_DT_VERBOSE = "1"\n'
    extra_dt_files = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_EXTRA_DT_FILES',
                                                 system_conffile)
    if autoconfig_dt:
        yocto_override = ''
        if hw_flow == 'sdt':
            yocto_override = ':linux'
        override_string += 'EXTRA_DT_FILES%s = "%s"\n' % (
            yocto_override, extra_dt_files)
    dt_remove_pl = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_REMOVE_PL_DTB',
                                               system_conffile)
    if dt_remove_pl:
        override_string += 'YAML_REMOVE_PL_DT:pn-device-tree = "1"\n'
    dt_include_dir = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DEVICE_TREE_INCLUDE_DIR',
                                                 system_conffile)
    dt_manual_include = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DEVICE_TREE_MANUAL_INCLUDE',
                                                    system_conffile)
    if dt_manual_include:
        override_string += 'KERNEL_INCLUDE:append:pn-device-tree = " %s"\n' \
                           % dt_include_dir
    dt_openamp_dtsi = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_OPENAMP_DTSI',
                                                  system_conffile)
    if dt_openamp_dtsi:
        override_string += 'ENABLE_OPENAMP_DTSI = "1"\n'

    dt_xenhw_dtsi = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_XEN_HW_DTSI',
                                                system_conffile)
    if dt_xenhw_dtsi:
        override_string += 'ENABLE_XEN_DTSI = "1"\n'

    dt_xenqemu_dtsi = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ENABLE_XEN_QEMU_DTSI',
                                                  system_conffile)
    if dt_xenqemu_dtsi:
        override_string += 'ENABLE_XEN_QEMU_DTSI = "1"\n'

    override_string += '\n# PetaLinux tool U-boot variables\n'
    override_string += AddRemoteSources('u-boot-xlnx', 'U__BOOT')
    override_string += AddExternalSources('u-boot-xlnx', 'U__BOOT')
    uboot_autoconfig = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_AUTOCONFIG_U__BOOT',
                                                   system_conffile)
    if soc_family == 'microblaze':
        if uboot_autoconfig:
            override_string += 'U_BOOT_AUTO_CONFIG:pn-u-boot-xlnx = "1"\n'
            auto_uboot_dir = os.path.join(args.output, 'u-boot-xlnx')
            if not os.path.isdir(auto_uboot_dir):
                os.makedirs(auto_uboot_dir)
            logger.info('Generating u-boot configuration files')
            cmd = 'xsct -sdx -nodisp %s/petalinux_hsm_bridge.tcl -c %s -a u-boot_bsp -hdf %s -o %s -data %s' % \
                (genmachine_scripts, system_conffile, os.path.abspath(args.hw_file),
                    auto_uboot_dir, os.path.join(genmachine_scripts, 'data'))
            common_utils.RunCmd(cmd, args.output, shell=True)

    if arch == 'aarch64':
        override_string += '\n# PetaLinux tool Arm-trusted-firmware variables\n'
        override_string += AddRemoteSources(
            'arm-trusted-firmware', 'TRUSTED__FIRMWARE__ARM')
        override_string += AddExternalSources(
            'arm-trusted-firmware', 'TRUSTED__FIRMWARE__ARM')
        atf_debug = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_TF-A_DEBUG', system_conffile)
        if atf_debug:
            override_string += 'DEBUG_ATF = "1"\n'

    if soc_family == 'versal':
        override_string += '\n# PetaLinux tool PLM variables\n'
        override_string += AddRemoteSources('plm-firmware', 'PLM')
        override_string += AddExternalSources('plm-firmware', 'PLM')
        override_string += AddRemoteSources('psm-firmware', 'PSM__FIRMWARE')
        override_string += AddExternalSources(
            'psm-firmware', 'PSM__FIRMWARE')

    if soc_family in ['zynqmp', 'zynq']:
        fsbl_bspcompiler_flags = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FSBL_BSPCOMPILER_FLAGS',
                                                             system_conffile)
        fsbl_bspcompiler_flagset = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FSBL_BSPCOMPILER_FLAGSSET',
                                                               system_conffile)
        override_string += '\n# PetaLinux tool FSBL variables\n'
        if fsbl_bspcompiler_flagset:
            override_string += 'YAML_BSP_COMPILER_FLAGS:append:pn-fsbl-firmware = " %s"' \
                               % fsbl_bspcompiler_flags
        fsbl_compiler_extra_flags = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_FSBL_COMPILER_EXTRA_FLAGS',
                                                                system_conffile)
        override_string += 'YAML_COMPILER_FLAGS:append:pn-fsbl-firmware = " %s"\n' \
                           % fsbl_compiler_extra_flags

    if soc_family in ['zynqmp']:
        override_string += '\n# PetaLinux tool PMUFW variables\n'
        pmufw_bspcompiler_flags = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PMUFW_BSPCOMPILER_FLAGS',
                                                              system_conffile)
        pmufw_bspcompiler_flagset = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_PMUFW_BSPCOMPILER_FLAGSSET',
                                                                system_conffile)
        if pmufw_bspcompiler_flagset:
            override_string += 'YAML_BSP_COMPILER_FLAGS:append:pn-pmu-firmware = " %s"' \
                % pmufw_bspcompiler_flags
        override_string += '\n'

    is_uboot_dtb = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_EXT_DTB',
                                               system_conffile)
    ubootdtb_dts_path = common_utils.GetConfigValue('CONFIG_UBOOT_EXT_DTB_FROM_DTS',
                                                    system_conffile)
    ubootdtb_packagename = common_utils.GetConfigValue('CONFIG_UBOOT_DTB_PACKAGE_NAME',
                                                       system_conffile)
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
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_KERNEL_IMAGE',
                                      system_conffile)
    override_string += 'DEVICETREE_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_DEVICETREE_OFFSET',
                                      system_conffile)
    override_string += 'KERNEL_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_KERNEL_OFFSET',
                                      system_conffile)
    override_string += 'RAMDISK_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_RAMDISK_IMAGE_OFFSET',
                                      system_conffile)
    override_string += 'QSPI_KERNEL_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_QSPI_KERNEL_OFFSET',
                                      system_conffile)
    override_string += 'QSPI_KERNEL_SIZE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_QSPI_KERNEL_SIZE',
                                      system_conffile)
    override_string += 'QSPI_RAMDISK_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_QSPI_RAMDISK_OFFSET',
                                      system_conffile)
    override_string += 'QSPI_RAMDISK_SIZE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_QSPI_RAMDISK_SIZE',
                                      system_conffile)
    override_string += 'QSPI_FIT_IMAGE_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_QSPI_FIT_IMAGE_OFFSET',
                                      system_conffile)
    override_string += 'QSPI_FIT_IMAGE_SIZE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_QSPI_FIT_IMAGE_SIZE',
                                      system_conffile)
    override_string += 'NAND_KERNEL_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_NAND_KERNEL_OFFSET',
                                      system_conffile)
    override_string += 'NAND_KERNEL_SIZE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_NAND_KERNEL_SIZE',
                                      system_conffile)
    override_string += 'NAND_RAMDISK_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_NAND_RAMDISK_OFFSET',
                                      system_conffile)
    override_string += 'NAND_RAMDISK_SIZE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_NAND_RAMDISK_SIZE',
                                      system_conffile)
    override_string += 'NAND_FIT_IMAGE_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_NAND_FIT_IMAGE_OFFSET',
                                      system_conffile)
    override_string += 'NAND_FIT_IMAGE_SIZE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_NAND_FIT_IMAGE_SIZE',
                                      system_conffile)
    override_string += 'FIT_IMAGE:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_FIT_IMAGE',
                                      system_conffile)
    override_string += 'FIT_IMAGE_OFFSET:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_FIT_IMAGE_OFFSET',
                                      system_conffile)
    override_string += 'PRE_BOOTENV:${MACHINE} = "%s"\n' \
        % common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_PRE_BOOTENV',
                                      system_conffile)

    rootfs_jffs2 = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ROOTFS_JFFS2',
                                               system_conffile)
    if rootfs_jffs2:
        jffs2_size = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_JFFS2_ERASE_SIZE_',
                                                 system_conffile, 'choice')
        jffs2_size = hex(int(jffs2_size) * 1024)
        override_string += '\n#jffs2 variables\n'
        override_string += 'JFFS2_ERASEBLOCK = "%s"\n' % jffs2_size

    rootfs_ubifs = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ROOTFS_UBIFS',
                                               system_conffile)
    if rootfs_ubifs:
        override_string += '\n#ubi/ubifs variables\n'
        ubi_mubifs_args = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBI_MKUBIFS_ARGS',
                                                      system_conffile)
        ubi_ubinize_args = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBI_UBINIZE_ARGS',
                                                       system_conffile)
        ubi_part_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBI_PART_NAME',
                                                    system_conffile)
        override_string += 'MKUBIFS_ARGS = "%s"\n' % ubi_mubifs_args
        override_string += 'UBINIZE_ARGS = "%s"\n' % ubi_ubinize_args
        override_string += 'UBI_VOLNAME = "%s"\n' % ubi_part_name

    provides_name = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_INITRAMFS_IMAGE_NAME',
                                                system_conffile)
    rootfs_initrd = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ROOTFS_INITRD',
                                                system_conffile)
    xen_enabled = common_utils.GetConfigValue(
        'CONFIG_', rootfs_conffile, 'asterisk', '.+xen.+')
    if xen_enabled:
        override_string += '\nIMAGE_PLNX_XEN_DEPLOY = "1"\n'

    if rootfs_initrd:
        override_string += '\nINITRAMFS_IMAGE = "%s"\n' % provides_name

    rootfs_initramfs = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ROOTFS_INITRAMFS',
                                                   system_conffile)
    if rootfs_initramfs:
        override_string += '\nINITRAMFS_IMAGE_BUNDLE = "1"\n'
        override_string += 'INITRAMFS_IMAGE = "%s"\n' % provides_name
        override_string += 'INITRAMFS_MAXSIZE = "524288"\n'

    rootfs_types = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_RFS_FORMATS',
                                               system_conffile)
    if rootfs_types:
        override_string += 'IMAGE_FSTYPES:%s = "%s"\n' % (
            soc_family, rootfs_types)

    if re.search('initramfs', provides_name):
        if xen_enabled:
            logger.warning('xen enabled, please disable switch_root by changing '
                           'petalinux-initramfs-image to petalinux-image-minimal \n'
                           'using petalinux-config -> Image packaging configuration'
                           '-> INITRAMFS/INITRD Image name. If not, you may see a build failure')
        override_string += 'INITRAMFS_FSTYPES = "cpio.gz cpio.gz.u-boot tar.gz"\n'

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
    is_imgsel = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_IMG_SEL',
                                            system_conffile)
    is_uboot_dtb = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_UBOOT_EXT_DTB',
                                               system_conffile)
    if is_imgsel:
        imagedepends[soc_family].append('virtual/imgsel')
    if is_uboot_dtb:
        imagedepends[soc_family].append('virtual/uboot-dtb')

    is_fsboot = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_BOOTLOADER_NAME_FS__BOOT',
                                            system_conffile)
    if not is_fsboot and 'virtual/fsboot' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/fsboot')
        imagedepends_remove.append('virtual/fsboot')
    if not is_fsboot and 'virtual/elfrealloc' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/elfrealloc')
        imagedepends_remove.append('virtual/elfrealloc')
    is_fsbl = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_BOOTLOADER_AUTO_FSBL',
                                          system_conffile)
    if not is_fsbl and 'virtual/fsbl' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/fsbl')
        imagedepends_remove.append('virtual/fsbl')
    is_pmufw = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_PMU_FIRMWARE',
                                           system_conffile)
    if not is_pmufw and 'virtual/pmu-firmware' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/pmu-firmware')
        imagedepends_remove.append('virtual/pmu-firmware')
    is_plm = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_COMPONENT_PLM', system_conffile)
    if not is_plm and 'virtual/plm' in imagedepends[soc_family]:
        imagedepends[soc_family].remove('virtual/plm')
        imagedepends_remove.append('virtual/plm')
    is_psmfw = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_COMPONENT_PSM_FIRMWARE',
                                           system_conffile)
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

    pdi_name = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PDI_FILENAME', system_conffile)
    if pdi_name:
        override_string += 'BASE_PDI_NAME = "%s"\n' % pdi_name

    override_string += '\n#SDK variables\n'
    override_string += 'SDK_EXT_TYPE = "minimal"\n'
    override_string += 'SDK_INCLUDE_BUILDTOOLS = "0"\n'

    override_string += '\n# deploy class variables\n'
    override_string += 'INHERIT += "plnx-deploy"\n'
    plnx_deploydir = common_utils.GetConfigValue(
        'CONFIG_PLNX_IMAGES_LOCATION', system_conffile)
    if plnx_deploydir:
        override_string += 'PLNX_DEPLOY_DIR = "%s"\n' % plnx_deploydir
    mc_plnx_deploydir = common_utils.GetConfigValue(
        'CONFIG_MC_PLNX_IMAGES_LOCATION', system_conffile)
    if mc_plnx_deploydir:
        override_string += 'MC_PLNX_DEPLOY_DIR = "%s"\n' % mc_plnx_deploydir
    dtb_deployname = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_DTB_IMAGE_NAME', system_conffile)
    override_string += 'PACKAGE_DTB_NAME = "%s"\n' % dtb_deployname
    fit_deployname = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_UIMAGE_NAME', system_conffile)
    override_string += 'PACKAGE_FITIMG_NAME = "%s"\n' % fit_deployname

    # Get design name from xsa
    design_name = ''
    if 'hw_design_name' in plnx_syshw_data.keys():
        design_name = plnx_syshw_data['hw_design_name']
    is_overlay = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_DTB_OVERLAY', system_conffile)
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
    rfsconfig_py = os.path.join(genmachine_scripts,
                                'rootfsconfigs/rootfs_config.py')
    rootfs_conffile = os.path.join(args.output, 'rootfs_config')
    cmd = 'python3 %s --update_cfg %s %s %s' \
        % (rfsconfig_py, rootfs_conffile,
           plnx_conf_path, soc_family)
    common_utils.RunCmd(cmd, args.output, shell=True)

    # Update config and rootfs_config file hash if changed
    # This should call end of the script
    common_utils.ValidateHashFile(args.output, 'SYSTEM_CONF', system_conffile)
    common_utils.ValidateHashFile(args.output, 'RFS_CONF', rootfs_conffile)
    return plnx_conf_file
