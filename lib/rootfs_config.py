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
import logging

logger = logging.getLogger('Gen-Machineconf')

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


def GenRootfsConfig(args, system_conffile):
    arch = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_ARCH_',
                                       system_conffile, 'choice', '=y').lower()
    genmachine_scripts = project_config.GenMachineScriptsPath()
    # template files for rootfs
    template_rfsfile = os.path.join(genmachine_scripts,
                                    'rootfsconfigs/rootfsconfig_%s' % args.soc_family)
    template_Kconfig = os.path.join(genmachine_scripts,
                                    'rootfsconfigs/Kconfig-%s.part' % arch)
    rfsconfig_py = os.path.join(genmachine_scripts,
                                'rootfsconfigs/rootfs_config.py')
    if args.add_rootfsconfig:
        user_cfg = os.path.realpath(args.add_rootfsconfig)
    else:
        user_cfg = os.path.join(genmachine_scripts,
                            'rootfsconfigs/user-rootfsconfig')

    # Create rootfsconfigs dir if not found
    rootfs_cfgdir = os.path.join(args.output, 'rootfsconfigs')
    common_utils.CreateDir(rootfs_cfgdir)

    rootfs_conffile = os.path.join(args.output, 'rootfs_config')
    rfsKconfig_part = os.path.join(rootfs_cfgdir, 'Kconfig.part')
    rfsKconfig_user = os.path.join(rootfs_cfgdir, 'Kconfig.user')
    rootfs_Kconfig = os.path.join(rootfs_cfgdir, 'Kconfig')

    for file_path in [template_rfsfile, template_Kconfig, rfsconfig_py]:
        if not os.path.isfile(file_path):
            raise Exception('%s is not found in tool' % file_path)

    if not os.path.isfile(rootfs_conffile):
        common_utils.CopyFile(template_rfsfile, rootfs_conffile)
    if not os.path.isfile(rfsKconfig_part):
        common_utils.CopyFile(template_Kconfig, rfsKconfig_part)
    common_utils.CopyFile(user_cfg, rootfs_cfgdir)
    # No need to run if user_rootfsconfig doesnot changes
    if not common_utils.ValidateHashFile(args.output, 'USER_RFS_CFG', user_cfg) or \
            not os.path.exists(rfsKconfig_user):
        logger.info('Generating kconfig for rootfs')
        cmd = 'python3 %s --generate_kconfig %s %s' \
            % (rfsconfig_py, user_cfg, rootfs_cfgdir)
        common_utils.RunCmd(cmd, args.output, shell=True)
    rfsKconfig_str = Kconfig_arch.format(args.soc_family)
    with open(rfsKconfig_part, 'r', encoding='utf-8') as rfskconfig_part_f:
        rfskconfig_part_data = rfskconfig_part_f.read()
    rfskconfig_part_f.close()
    rfsKconfig_str += rfskconfig_part_data.replace(
        'source ./Kconfig.user', 'source %s' % rfsKconfig_user)
    with open(rootfs_Kconfig, 'w') as rfskconfig_f:
        rfskconfig_f.write(rfsKconfig_str)
    rfskconfig_f.close()
    common_utils.RunMenuconfig(rootfs_Kconfig, rootfs_conffile,
                               True if args.menuconfig == 'rootfs' else False,
                               args.output, 'rootfs')
