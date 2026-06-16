#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT


import yaml
import common_utils


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


def CheckDeviceCount(device_type, system_conffile):
    processor = common_utils.GetConfigValue(
        'CONFIG_SUBSYSTEM_PROCESSOR_', system_conffile, 'choice', '_SELECT=y')
    global plnx_syshw_data
    slaves = plnx_syshw_data["processor"][processor]["slaves"]
    device_ips = []
    for key, value in slaves.items():
       if isinstance(value, dict) and value.get('device_type', '') == device_type:
           device_ips.append(key)
    return device_ips


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


def PostProcessSysConf(args, system_conffile, plnx_syshw_file):
    global plnx_syshw_data
    with open(plnx_syshw_file, 'r') as plnx_syshw_file_f:
        plnx_syshw_data = yaml.safe_load(plnx_syshw_file_f)
