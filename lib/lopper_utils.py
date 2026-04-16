#!/usr/bin/env python3

# Copyright (C) 2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import logging
import os
import common_utils

logger = logging.getLogger('Gen-Machineconf')


def IncludeCustomDtsi(outdir, mcname, dts_file, system_conffile):
    """
    Includes custom DTSI files into a final DTS file based on configuration.

    This function retrieves DTSI file paths from the system configuration using domain-specific
    configuration key. For each DTSI file:
      - Expands environment and bitbake variables in the file path.
      - Verifies the file exists.
      - Copies the file to the output directory with a domain-specific name.
      - Checks if the file is an overlay (contains '/plugin/;') and raises an exception if so.
      - Appends an #include directive for the DTSI file to the final DTS file.

    If any DTSI files are included, it triggers the Lopper tool to process the final DTS file.
    """
    if not mcname:
        mcname = 'linux'
    dtsi_conf = f'CONFIG_YOCTO_BBMC_{mcname.upper().replace("-", "_")}_DTSI'
    dtsi_files = common_utils.GetConfigValue(dtsi_conf, system_conffile)

    for dtsi_file in dtsi_files.split():
        dtsi_file = common_utils.ExpandFilePath(dtsi_file)
        if not os.path.isfile(dtsi_file):
            raise Exception(f'Failed to get dtsi: {dtsi_file}')

        DomainCustomDtsi = f'{mcname}_{os.path.basename(dtsi_file)}'
        domain_dtsi_path = os.path.join(outdir, DomainCustomDtsi)
        with open(dtsi_file, 'r') as f:
            for line in f:
                if '/plugin/;' in line:
                    raise Exception(f'{dtsi_file} is an overlay file and cannot be appended to the final dts file.')
        common_utils.CopyFile(dtsi_file, domain_dtsi_path)
        common_utils.AddStrToFile(dts_file, f'#include "{domain_dtsi_path}"\n', mode='a+')
    if dtsi_files:
        logger.debug(f'Generating {dts_file} including {dtsi_files}')
        RunLopperUsingDomainFile([], outdir, outdir, dts_file, dts_file)


def RunLopperGenDomainDTS(outdir, dts_path, hw_file, dts_file, domain_name,
                          domain_yamls, system_conffile):
    """
    Generate domain-specific DTS files with YAML integration.

    This function processes hardware description files through multiple lopper transformations
    to create domain-specific device tree source files. The process includes:
    - Appending all specified YAML files to the System Device Tree (SDT)
    - Updating the chosen node reference from /domains to /root namespace
    - Optionally running domain_access lopper script if CONFIG_SUBSYSTEM_DT_DOMAIN_ACCESS is enabled

    The function creates intermediate DTS files at each stage (*-yaml.dts, *-chosen.dts) and
    returns the path to the final processed YAML-integrated DTS file.
    """
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    domain_yamls_str = ' -i '.join(domain_yamls)
    domain_args = "-x '*.yaml'"
    # Append all the yaml files to SDT
    yaml_dts_file = dts_file.replace('.dts', '-yaml.dts')
    logger.debug(f'Generating DTS {yaml_dts_file} with specified yaml files {domain_yamls}')
    cmd = f'LOPPER_DTC_FLAGS="-b 0 -@" {lopper} -O {outdir} -f --enhanced \
            {domain_args} -i {domain_yamls_str} {hw_file} {yaml_dts_file}'
    common_utils.RunCmd(cmd, dts_path, shell=True)

    # Update chosen node from /domains to /root
    yaml_chosen_dts_file = dts_file.replace('.dts', '-chosen.dts')
    logger.debug(f'Generating DTS {yaml_chosen_dts_file} to update chosen node')
    cmd = f'LOPPER_DTC_FLAGS="-b 0 -@" {lopper} -O {outdir} -f --enhanced \
            -i lop-domain-chosen.dts -t {domain_name} {yaml_dts_file} {yaml_chosen_dts_file}'
    common_utils.RunCmd(cmd, dts_path, shell=True)
    yaml_dts_file = yaml_chosen_dts_file

    # Run domain_access if config domain_access is enabled
    domain_access_enabled = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DT_DOMAIN_ACCESS',
                                                         system_conffile)
    if domain_access_enabled:
        logger.debug(f'Generating DTS {dts_file} with {yaml_dts_file} using domain_access')
        cmd = f'LOPPER_DTC_FLAGS="-b 0 -@" {lopper} -O {outdir} -f --enhanced \
                {yaml_dts_file} {dts_file} -- domain_access -t {domain_name}'
        common_utils.RunCmd(cmd, dts_path, shell=True)
        yaml_dts_file = dts_file

    return yaml_dts_file


def RunLopperUsingDomainFile(domain_files, outdir, dts_path, hw_file,
                             dts_file='', lopper_args='', subcommand_args=''):
    """
    Generic lopper execution with domain files.

    Executes the lopper tool with specified domain files and optional subcommands. This is a
    flexible wrapper that handles both absolute and relative domain file paths, automatically
    resolving relative paths within the lopper lops directory. Supports enhanced mode with
    device tree compiler flags and can execute additional lopper subcommands as needed.
    """
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    domain_args = ''
    for domain in list(filter(None, domain_files)):
        if not os.path.isabs(domain):
            domain_args += ' -i %s' % os.path.join(lops_dir, domain)
        else:
            domain_args += ' -i %s' % domain
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f --enhanced %s %s %s %s' % (
        lopper, outdir, lopper_args,
        domain_args, hw_file, dts_file)

    if subcommand_args != '':
        cmd += ' -- %s' % (subcommand_args)

    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout


def RunLopperGenLinuxDts(outdir, dts_path, domain_files, hw_file, dts_file, subcommand_args, lopper_args=''):
    """
    Generate Linux device tree source files using lopper.

    Executes lopper in enhanced mode to generate Linux-compatible device tree source files
    from hardware description files. Processes domain files and applies Linux-specific
    transformations through lopper subcommands to create kernel-compatible device tree bindings.
    """
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    domain_args = ''
    for domain in list(filter(None, domain_files)):
        if not os.path.isabs(domain):
            domain_args += ' -i %s' % os.path.join(lops_dir, domain)
        else:
            domain_args += ' -i %s' % domain
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s --enhanced -O %s %s %s %s %s -- %s' % (
        lopper, outdir, lopper_args, domain_args, hw_file, dts_file, subcommand_args)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout


def RunLopperSubcommand(outdir, dts_path, hw_file, subcommand_args, lopper_args=''):
    """
    Execute lopper with custom subcommands.

    Provides a lightweight interface to run lopper with custom subcommands without domain files.
    This is useful for executing specialized lopper scripts or transformations that don't require
    domain-specific processing, such as hardware analysis, metadata extraction, or custom assists.
    """
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s %s %s -- %s' % (
        lopper, outdir, lopper_args, hw_file, subcommand_args)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout


def RunLopperPlOverlaycommand(outdir, dts_path, sdt_gen_pl_dtsi,
                              hw_file, ps_dts_file, subcommand_args,
                              lopper_args='', system_conffile=''):
    """
    Generate Programmable Logic (PL) overlay device tree using xlnx_overlay_pl_dt lopper script.

    Creates device tree overlay files for Xilinx FPGA programmable logic regions. The function
    combines the Processing System (PS) device tree with PL DTSI files generated from System
    Device Tree (SDT) to produce overlay files that can be dynamically loaded for partial
    reconfiguration or Device Tree overlay use cases.

    If CONFIG_SUBSYSTEM_PL_INPUT_DTSI is set in system_conffile, the specified dtsi file
    is passed as a lopper input (-i) to be merged into the generated PL overlay.
    """
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    pl_input_dtsi_arg = ''
    if system_conffile:
        pl_input_dtsi_files = common_utils.GetConfigValue(
            'CONFIG_SUBSYSTEM_PL_INPUT_DTSI', system_conffile)
        for pl_input_dtsi in pl_input_dtsi_files.split():
            pl_input_dtsi = common_utils.ExpandFilePath(pl_input_dtsi)
            if not os.path.isfile(pl_input_dtsi):
                raise Exception(f'Failed to get PL input dtsi: {pl_input_dtsi}')
            pl_input_dtsi_arg += ' -i %s' % pl_input_dtsi
            logger.debug(f'Using PL input dtsi: {pl_input_dtsi}')
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s --enhanced -O %s %s%s %s %s -- %s %s' % (
        lopper, outdir, lopper_args, pl_input_dtsi_arg, hw_file, ps_dts_file, subcommand_args, sdt_gen_pl_dtsi)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout


def CopyPlOverlayfile(outdir, dts_path, pl_overlay_args):
    """
    Copy PL overlay file to designated directory.

    Creates a dedicated directory for PL overlay files based on the overlay type (e.g., 'full' or 'dfx')
    and copies the generated pl.dtso file from the lopper output directory. This organizes overlay
    files for different partial reconfiguration scenarios and logs the file locations for user reference.
    """
    pl_dtso_file = os.path.join(outdir, 'pl.dtso')
    if not os.path.isfile(pl_dtso_file):
        logger.warning('pl.dtso not found in: %s. '
                       'This may indicate that the design has no PL components or '
                       'the lopper pl overlay command (xlnx_overlay_pl_dt) did not produce '
                       'an overlay output. Skipping pl overlay copy to '
                       'pl-overlay-%s directory.' % (outdir, pl_overlay_args))
        return

    pl_dt_path = os.path.join(dts_path, 'pl-overlay-%s' % pl_overlay_args)
    common_utils.CreateDir(pl_dt_path)

    common_utils.CopyFile(pl_dtso_file, pl_dt_path)
    logger.info('Lopper generated pl overlay file is found in: %s and a copy of pl.dtso is stored in: %s'
                % (pl_dtso_file, pl_dt_path))


def GetLopperBaremetalDrvList(cpuname, outdir, dts_path, hw_file, lopper_args=''):
    """
    Generate baremetal driver list using baremetaldrvlist_xlnx lopper script.

    Invokes the lopper baremetaldrvlist_xlnx assist to analyze the hardware description and
    generate a list of required baremetal drivers for the specified CPU. This is used to
    determine which embedded software drivers are needed for standalone (non-OS) applications
    running on the target processor.
    """
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f %s \
                "%s" -- baremetaldrvlist_xlnx %s "%s"' % (
        lopper, outdir, lopper_args,
        hw_file, cpuname, embeddedsw)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout
