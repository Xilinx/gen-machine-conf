#!/usr/bin/env python3

# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import os
import re
import yaml
import copy
import logging
import common_utils

logger = logging.getLogger('Gen-Machineconf')

# Global variable for template YAML data
TemplateYamlData = {}
# Global list to store machine names from all YAML files
MachineNamesList = []


def ParseYamlFlagsToDict(yaml_flags):
    """Extract argument flags and their values from a list of YAML arguments."""
    flag_map = {}
    for arg_str in yaml_flags:
        parts = arg_str.split() if isinstance(arg_str, str) else arg_str
        i = 0
        while i < len(parts):
            if parts[i].startswith('-'):
                flag = parts[i]
                i += 1
                # Collect values until we hit another flag or end
                values = []
                while i < len(parts) and not parts[i].startswith('-'):
                    values.append(parts[i])
                    i += 1
                flag_map[flag] = ' '.join(values) if values else True
            else:
                i += 1
    return flag_map


def MergeYamlArgs(base_yaml_args, inherit_yaml_args, mode='override'):
    '''
    Merge YAML arguments with specified mode: 'override', 'append', or 'prepend'.

    Supports nested dictionaries with deep merging. Lists are converted to dicts via ParseYamlFlagsToDict.
    Also collects --machine-name values into global MachineNamesList.
    '''
    global MachineNamesList

    # Parse to dict if not already (for command-line style arguments from lists)
    baseyaml_flags = base_yaml_args if isinstance(base_yaml_args, dict) else ParseYamlFlagsToDict(base_yaml_args)
    inherit_flags = inherit_yaml_args if isinstance(inherit_yaml_args, dict) else ParseYamlFlagsToDict(inherit_yaml_args)

    # Create a deep copy to avoid modifying the original
    merged_flags = copy.deepcopy(inherit_flags)

    for flag, new_value in baseyaml_flags.items():
        existing_value = merged_flags.get(flag)

        # If both values are dictionaries, recursively merge them
        if isinstance(new_value, dict) and isinstance(existing_value, dict):
            merged_flags[flag] = MergeYamlArgs(new_value, existing_value, mode)
        # If no existing value or override mode, use new value
        elif existing_value is None or mode == 'override':
            merged_flags[flag] = copy.deepcopy(new_value)
        # If existing value is True (flag only), replace with new value
        elif existing_value is True:
            merged_flags[flag] = copy.deepcopy(new_value)
        # If new value is not True and both are strings/values, concatenate
        elif new_value is not True and not isinstance(new_value, dict):
            merged_flags[flag] = f'{new_value} {existing_value}' if mode == 'prepend' else f'{existing_value} {new_value}'
        else:
            # Default: use new value
            merged_flags[flag] = copy.deepcopy(new_value)

    # Collect --machine-name values from inherit flags
    for flags_dict in [inherit_flags]:
        machine_name = flags_dict.get('--machine-name')
        if machine_name and machine_name not in MachineNamesList:
            MachineNamesList.append(machine_name)
            logger.debug('Collected machine name: %s', machine_name)

    return merged_flags


def MergeYamlData(TemplateYamlData, InheritYamlData):
    '''
    Merges two dictionaries with intelligent merge strategies based on key suffixes.
    '''
    yaml_data = InheritYamlData.copy()

    # Keys that support prepend/append operations
    mergeable_keys = ['args', 'kconfig', 'machine']

    # Get all unique keys from both dictionaries
    all_keys = set(InheritYamlData.keys()) | set(TemplateYamlData.keys())

    for key in all_keys:
        if key in mergeable_keys:
            merged_data = MergeYamlArgs(TemplateYamlData.get(key, {}),
                                        InheritYamlData.get(key, {}))
            # Handle prepend and append operations
            for mode in ['prepend', 'append']:
                operation_key = f'{key}_{mode}'
                operation_data = TemplateYamlData.get(operation_key)
                if operation_data:
                    logger.debug('%s found for %s: %s', mode.capitalize(), key, operation_data)
                    merged_data = MergeYamlArgs(operation_data, merged_data, mode=mode)
            yaml_data[key] = merged_data

    return yaml_data


def ReadYaml(yamlfile):
    '''Read the given YAML file and return the contents as a dictionary.'''
    with open(yamlfile, 'r') as yaml_fd:
        try:
            return yaml.safe_load(yaml_fd)
        except yaml.YAMLError as exc:
            raise Exception(exc)


def CleanupEscapes(obj):
    '''Recursively removes backslash escape sequences followed by any
    whitespace, tab, or newline characters from strings within the given object.
    '''
    if isinstance(obj, str):
        # Remove backslash followed by any whitespace or tabs or newline
        return re.sub(r'\\\s*', ' ', obj)
    elif isinstance(obj, list):
        return [CleanupEscapes(x) for x in obj]
    elif isinstance(obj, tuple):
        return tuple(CleanupEscapes(x) for x in obj)
    elif isinstance(obj, dict):
        return {k: CleanupEscapes(v) for k, v in obj.items()}
    else:
        return obj


def ReadTemplateYaml(yamlfile):
    '''
    Reads the specified YAML file and stores the contents into the global TemplateYamlData.
    '''
    if not yamlfile:
        return
    if not os.path.isfile(yamlfile):
        raise Exception('Specified yaml file does not exist: %s' % yamlfile)
    global TemplateYamlData
    TemplateYamlData = ReadYaml(yamlfile) or {}
    TemplateYamlData = CleanupEscapes(TemplateYamlData)
    # Read and merge the inherit key if present
    inherit_files = TemplateYamlData.get('inherit', '')
    # Split by spaces to handle multiple files
    for inherit_file in inherit_files.split():
        inherit_file = os.path.expandvars(inherit_file)
        # Expand the bitbake variables
        inherit_file = common_utils.Bitbake.expand(inherit_file)
        inherit_file = os.path.realpath(inherit_file)
        InheritYamlData = ReadYaml(inherit_file) or {}
        InheritYamlData = CleanupEscapes(InheritYamlData)
        # Merge with InheritYamlData having priority
        TemplateYamlData = MergeYamlData(TemplateYamlData, InheritYamlData)


def AddYamlDefaultValues(arg=None, default=None):
    '''
    Retrieve YAML argument values by key or list of keys.
    '''
    if arg is None:
        return default

    global TemplateYamlData
    TemplateYamlDataArgs = TemplateYamlData.get('args', {})
    if isinstance(TemplateYamlDataArgs, list):
        TemplateYamlDataArgs = ParseYamlFlagsToDict(TemplateYamlDataArgs)
    # Handle arg as a list - return first match
    if isinstance(arg, list):
        for key in arg:
            if key in TemplateYamlDataArgs.keys():
                return TemplateYamlDataArgs[key]
        return default

    # Handle arg as a string
    return TemplateYamlDataArgs.get(arg, default)


def GenCPUNames(cluster: str, cpu: str, cpumask_hex: str):
    """
    Generates a list of CPU names based on the cluster name, CPU string, and CPU mask.
    Args:
        cluster (str): The name of the CPU cluster, expected to match the pattern 'cpus_<type>[_<number>]'.
        cpu (str): A string representing CPU identifiers, typically comma-separated and may include ranges.
        cpumask_hex (str or int): A hexadecimal string or integer representing the CPU mask.
    Returns:
        list[str]: A list of CPU names in the format '<cpu_prefix><cpu_type>_<core_index>' for each core enabled in the mask.
        If the cluster name does not match the expected pattern, returns an empty string.
    """
    match = re.match(r'cpus_(\w+?)(?:_\d+)?$', cluster)
    if not match:
        return ''
    cpu_split = cpu.split(',')
    if len(cpu_split) > 1:
        cpu_prefix = cpu_split[1].split('-')[0]
    else:
        cpu_prefix = cpu_split[0].split('-')[0]
    cpu_type = match.group(1)
    if isinstance(cpumask_hex, int):
        cpumask = cpumask_hex
    else:
        cpumask = int(str(cpumask_hex), 16)
    bit_positions = [i for i in range(cpumask.bit_length()) if cpumask & (1 << i)]
    # Generate cpunames like cortex<type>_<core_index>
    cpunames = [f"{cpu_prefix}{cpu_type}_{i}" for i in bit_positions]

    return cpunames


def GetDomainName(proc_name: str, cpu: str, os_hint: str, yaml_file: str):
    """
    Retrieves the domain name for a given processor name, CPU, and OS hint from a YAML configuration file.
    Args:
        proc_name (str): The name of the processor to search for.
        cpu (str): The CPU identifier used for generating CPU names.
        os_hint (str): The operating system type to match.
        yaml_file (str): Path to the YAML file containing domain configurations.
    Returns:
        str or None: The domain name if found, otherwise None.
    """
    try:
        yaml_content = ReadYaml(yaml_file)
        if not yaml_content or 'domains' not in yaml_content:
            return None, None
        schema = yaml_content['domains']
        for subsystem in schema:
            os_type = schema[subsystem].get('os,type', '')
            for cpu_dict in schema[subsystem].get('cpus', []):
                cluster = cpu_dict.get('cluster', '')
                cpumask = cpu_dict.get('cpumask', '')
                cpunames = GenCPUNames(cluster, cpu, cpumask)
                if proc_name.endswith(tuple(cpunames)):
                    if not os_type:
                        logger.warning(f'OS type not defined for domain {subsystem} (proc_name: {proc_name}), skipping entry.')
                        return None, None
                    elif os_type.lower() == os_hint:
                        logger.debug(f'Found domain name {subsystem} for proc_name {proc_name} with os type {os_type}')
                        return subsystem, schema
    except Exception as e:
        raise Exception(f"Error in GetDomainName: {e}")
    return None, None
