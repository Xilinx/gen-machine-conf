#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import common_utils
import logging

logger = logging.getLogger('Gen-Machineconf')


def GenLocalConf(conf_file, machine_conf_file, system_conffile):
    sdt_conf_str  = '# Use the newly generated MACHINE\n'
    sdt_conf_str += 'MACHINE = "%s"\n' % machine_conf_file

    multiconfig_min = common_utils.GetConfigValue('CONFIG_YOCTO_BBMC_', system_conffile,
                                                  'choicelist', '=y').lower().replace('_', '-')
    if multiconfig_min:
        sdt_conf_str += '\n# Avoid errors in some baremetal configs as these layers may be present\n'
        sdt_conf_str += '# but are not used.  Note the following lines are optional and can be\n'
        sdt_conf_str += '# safely disabled.\n'
        sdt_conf_str += 'SKIP_META_VIRT_SANITY_CHECK = "1"\n'
        sdt_conf_str += 'SKIP_META_SECURITY_SANITY_CHECK = "1"\n'
        sdt_conf_str += 'SKIP_META_TPM_SANITY_CHECK = "1"\n'

    if not conf_file:
        logger.note('To enable this, add the following to your local.conf:\n')
        logger.plain(sdt_conf_str)
    else:
        logger.note('Configuration for local.conf written to %s' %
                    conf_file)
        logger.debug(sdt_conf_str)
        common_utils.CreateFile(conf_file)
        common_utils.AddStrToFile(conf_file, sdt_conf_str, 'a+')
