#!/usr/bin/env python3

# Copyright (C) 2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import logging
import os
import common_utils
import sys
import shutil
import re
import glob
import pathlib
import project_config
import post_process_config
import rootfs_config
import multiconfigs
import kconfig_syshw

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
    dtsi_conf = f'CONFIG_YOCTO_BBMC_{mcname.upper()}_DTSI'
    dtsi_files = common_utils.GetConfigValue(dtsi_conf, system_conffile)

    for dtsi_file in dtsi_files.split():
        dtsi_file = os.path.expandvars(dtsi_file)
        # Expand the bitbake variables
        dtsi_file = common_utils.Bitbake.expand(dtsi_file)
        dtsi_file = os.path.realpath(dtsi_file)
        if not os.path.isfile(dtsi_file):
            raise Exception(f'Failed to get dtsi: {dtsi_file}')

        DomainCustomDtsi = f'{mcname}_{os.path.basename(dtsi_file)}'
        with open(dtsi_file, 'r') as f:
            for line in f:
                if '/plugin/;' in line:
                    raise Exception(f'{dtsi_file} is an overlay file and cannot be appended to the final dts file.')
                    break
        common_utils.CopyFile(dtsi_file, os.path.join(outdir, DomainCustomDtsi))
        common_utils.AddStrToFile(dts_file, f'#include "{dtsi_file}"\n', mode='a+')
    if dtsi_files:
        logger.debug(f'Generating {dts_file} including {dtsi_files}')
        RunLopperUsingDomainFile([], outdir, outdir, dts_file, dts_file)

def RunLopperGenDomainYaml(hw_file, iss_file, dts_path, domain_yaml, outdir):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f --enhanced %s -- isospec -v -v --audit %s %s' % (
                             lopper, outdir, hw_file, iss_file, domain_yaml)
    stdout = common_utils.RunCmd(cmd, outdir, shell=True)
    return stdout

def RunLopperGenDomainDTS(outdir, dts_path, hw_file, dts_file, domain_name,
                          domain_yamls, system_conffile):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    domain_yamls_str = ' -i '.join(domain_yamls)
    domain_args = "--auto -x '*.yaml'"
    # Append all the yaml files to SDT
    yaml_dts_file = dts_file.replace('.dts', '-yaml.dts')
    logger.debug(f'Generating DTS {yaml_dts_file} with specified yaml files {domain_yamls}')
    cmd = f'LOPPER_DTC_FLAGS="-b 0 -@" {lopper} -O {outdir} -f --enhanced \
            {domain_args} -i {domain_yamls_str} {hw_file} {yaml_dts_file}'
    common_utils.RunCmd(cmd, dts_path, shell=True)

    # Run domain_access if config domain_access is enabled
    domain_access_enabled = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DT_DOMAIN_ACCESS',
                                                         system_conffile)
    if domain_access_enabled:
        logger.debug(f'Generating DTS {dts_file} with {yaml_dts_file} using domain_access')
        cmd = f'LOPPER_DTC_FLAGS="-b 0 -@" {lopper} -O {outdir} -f --enhanced -t {domain_name} \
                -a domain_access {yaml_dts_file} {dts_file}'
        common_utils.RunCmd(cmd, dts_path, shell=True)
        yaml_dts_file = dts_file

    return yaml_dts_file

def RunLopperUsingDomainFile(domain_files, outdir, dts_path, hw_file,
                             dts_file='', lopper_args='', subcommand_args=''):
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
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s %s %s -- %s' % (
        lopper, outdir, lopper_args, hw_file, subcommand_args)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout

def RunLopperPlOverlaycommand(outdir, dts_path, sdt_gen_pl_dtsi,
                              hw_file, ps_dts_file, subcommand_args, lopper_args=''):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s --enhanced -O %s %s %s %s -- %s %s' % (
        lopper, outdir, lopper_args, hw_file, ps_dts_file, subcommand_args, sdt_gen_pl_dtsi)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout

def CopyPlOverlayfile(outdir, dts_path, pl_overlay_args):
    pl_dt_path = os.path.join(dts_path, 'pl-overlay-%s' % pl_overlay_args)
    common_utils.CreateDir(pl_dt_path)
    common_utils.CopyFile(os.path.join(outdir, 'pl.dtsi'), pl_dt_path)
    logger.info('Lopper generated pl overlay file is found in: %s and a copy of pl.dtsi is stored in: %s'
                % (os.path.join(outdir, 'pl.dtsi'), pl_dt_path))

def GetLopperBaremetalDrvList(cpuname, outdir, dts_path, hw_file, lopper_args=''):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f %s \
                "%s" -- baremetaldrvlist_xlnx %s "%s"' % (
        lopper, outdir, lopper_args,
        hw_file, cpuname, embeddedsw)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout

def IsOpenampEnabled(cpuname, cpu, os_hint, domain_files):
    """
    Check if OpenAMP is enabled for a given CPU and domain configuration.
    This function iterates through domain files to determine if OpenAMP
    is enabled by checking for the 'openamp,domain-to-domain-v1' compatible
    string in the domain-to-domain configuration.

    Returns:
        str: The domain name if OpenAMP is enabled with compatible version,
             empty string otherwise.
    """
    domain_name = ''
    for _file in domain_files.split():
        domain_name, schema = common_utils.GetDomainName(cpuname, cpu, os_hint, _file)
        if domain_name:
            domain_info = schema.get(domain_name, {})
            domain_to_domain = domain_info.get('domain-to-domain', {})
            compatible = domain_to_domain.get('compatible')
            if compatible in ('openamp,domain-to-domain-v1'):
                return domain_name
    return ''

class sdtGenerateMultiConfigFiles(multiconfigs.GenerateMultiConfigFiles):
    def GenOpenampDts(self, ps_dts_file, subcommand_args=''):
        """
        Generate OpenAMP device tree source file for the specified CPU.
        This method checks if OpenAMP is enabled for the current CPU and generates
        an OpenAMP-specific device tree source (DTS) file if applicable.

        Returns:
            str: The path to the generated OpenAMP DTS file or the original DTS file
                 if OpenAMP is not enabled.
        """
        openamp_domain = IsOpenampEnabled(self.cpuname, self.cpu,
                                        self.os_hint, self.args.domain_file)
        if not openamp_domain:
            return ps_dts_file
        logger.debug(f'Generating OpenAMP DTS for core {self.cpuname} {self.core}')
        # Generate Domain specific dts file
        openamp_dts_file = os.path.join(self.args.output, f'{self.cpuname}-openamp.dts')
        RunLopperUsingDomainFile([], self.args.output, self.args.dts_path,
                                ps_dts_file, openamp_dts_file, '',
                                f'openamp {self.cpuname} {subcommand_args}')
        return openamp_dts_file

    def GenDTSWithYaml(self):
        """
        Generates a Device Tree Source (DTS) file based on the provided YAML hardware and domain files.

        This method determines the domain name from the specified domain files, sanitizes it for use as a filename,
        and then generates a DTS file using the Lopper tool. If no valid domain name is found, it logs a debug message.

        Returns:
            str: The path to the generated or selected DTS file.
        """
        dts_file = self.args.hw_file
        domain_name = ''
        for _file in self.args.domain_file.split():
            # The second value from GetDomainName is intentionally ignored
            domain_name, _ = common_utils.GetDomainName(self.cpuname, self.cpu, self.os_hint, _file)
            if domain_name:
                break

        if domain_name:
            # Sanitize domain_name to avoid invalid filename characters
            sanitized_domain_name = re.sub(r'[^A-Za-z0-9_\-]', '_', domain_name.lower())
            sanitized_dts_file = os.path.join(self.args.output, '%s.dts' % sanitized_domain_name)
            dts_file = RunLopperGenDomainDTS(self.args.output, self.args.dts_path, self.args.hw_file,
                                  sanitized_dts_file, '/domains/%s' % domain_name,
                                  self.args.domain_file.split(), self.system_conffile)
        else:
            logger.debug(f'No domain for cpu {self.cpuname} in any domain files')

        return dts_file

    def GenDomainDTS(self, dts_file, lopdts):
        # Build device tree
        lopper_args = ''
        domain_files = [lopdts]
        subcommand_args = f'gen_domain_dts {self.cpuname}'
        #TODO: xilpm fails with domain dts for zynqmp platform, revert this once its fixed in lopper
        if self.args.soc_family == 'zynqmp' and self.os_hint == 'fsbl':
            subcommand_args = ''

        # Generate the DTs file using user specified domain yaml file
        DTSFile = self.GenDTSWithYaml()

        # Generate OpenAMP DTS if applicable
        openamp_args = ''
        if self.os_hint.startswith('zephyr'):
            openamp_args = 'zephyr_dt'
        DTSFile = self.GenOpenampDts(DTSFile, openamp_args)

        RunLopperUsingDomainFile(domain_files, self.args.output, self.args.dts_path,
                                DTSFile, dts_file, lopper_args, subcommand_args)

        # Return domain specific full dts file if domain file specified
        return DTSFile

    def GenLibxilFeatures(self, lopdts, extra_conf=''):
        mc_filename = "%s-%s" % (self.args.machine, self.mcname)
        dts_file = os.path.join(self.args.dts_path, '%s.dts' % mc_filename)
        conf_file = os.path.join(self.args.config_dir,
                                 'multiconfig', '%s.conf' % mc_filename)
        libxil = os.path.join(self.args.bbconf_dir,
                              '%s-libxil.conf' % mc_filename)
        features = os.path.join(self.args.bbconf_dir,
                                '%s-features.conf' % mc_filename)
        domain_dts_file = self.GenDomainDTS(dts_file, lopdts)
        lopper_args = ''
        # Build baremetal multiconfig
        GetLopperBaremetalDrvList(self.cpuname, self.args.output, self.args.dts_path,
                                  domain_dts_file, lopper_args)

        common_utils.RenameFile(os.path.join(
            self.args.output, 'libxil.conf'), libxil)
        common_utils.RenameFile(os.path.join(
            self.args.output, 'distro.conf'), features)
        common_utils.ReplaceStrFromFile(
            features, 'DISTRO_FEATURES', 'MACHINE_FEATURES')
        conf_file_str  = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
        IncludeCustomDtsi(self.args.output, self.mcname, dts_file, self.system_conffile)
        conf_file_str += 'ESW_MACHINE = "%s"\n' % self.cpuname
        conf_file_str += extra_conf
        common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def CortexA9Baremetal(self):
        extra_conf_str = ''
        if self.os_hint == 'fsbl':
            logger.info('Generating cortex-a9 baremetal configuration for FSBL')
            for psu_init_f in ['ps7_init.c', 'ps7_init.h']:
                if not os.path.exists(os.path.join(
                        self.args.psu_init_path, psu_init_f)):
                    logger.error('Unable to find %s in %s' % (
                        psu_init_f, self.args.psu_init_path))
        else:
            logger.info(
                'Generating cortex-a9 baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('', extra_conf_str)

    def CortexA53Baremetal(self):
        extra_conf_str = ''
        if self.os_hint == 'fsbl':
            logger.info('Generating cortex-a53 baremetal configuration for FSBL')
            for psu_init_f in ['psu_init.c', 'psu_init.h']:
                if not os.path.exists(os.path.join(
                        self.args.psu_init_path, psu_init_f)):
                    logger.error('Unable to find %s in %s' % (
                        psu_init_f, self.args.psu_init_path))
        else:
            logger.info(
                'Generating cortex-a53 baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('lop-a53-imux.dts', extra_conf_str)

    def CortexA72Baremetal(self):
        logger.info(
            'Generating cortex-a72 baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-standalone-nolto'
        self.GenLibxilFeatures('lop-a72-imux.dts')

    def CortexA78Baremetal(self):
        logger.info(
            'Generating cortex-a78 baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-standalone-nolto'
        self.GenLibxilFeatures('lop-a78-imux.dts')

    def CortexR5Baremetal(self):
        extra_conf_str = ''
        if self.os_hint == 'fsbl':
            logger.info('Generating cortex-r5 baremetal configuration for FSBL')
            for psu_init_f in ['psu_init.c', 'psu_init.h']:
                if not os.path.exists(os.path.join(
                        self.args.psu_init_path, psu_init_f)):
                    logger.error('Unable to find %s in %s' % (
                        psu_init_f, self.args.psu_init_path))
        else:
            logger.info(
                'Generating cortex-r5 baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('lop-r5-imux.dts', extra_conf_str)

    def CortexR52Baremetal(self):
        logger.info(
                'Generating cortex-r52 baremetal configuration for core %s [ %s ]' % (self.core, self.domain))
        self.GenLibxilFeatures('lop-r52-imux.dts')

    def CortexA53FreeRtos(self):
        logger.info(
            'Generating cortex-a53 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('lop-a53-imux.dts')

    def CortexA9FreeRtos(self):
        logger.info(
            'Generating cortex-a9 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('')

    def CortexA72FreeRtos(self):
        logger.info(
            'Generating cortex-a72 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('lop-a72-imux.dts')

    def CortexA78FreeRtos(self):
        logger.info(
            'Generating cortex-a78 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        self.GenLibxilFeatures('lop-a78-imux.dts')

    def CortexR5FreeRtos(self):
        logger.info(
            'Generating cortex-r5 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))
        self.GenLibxilFeatures('lop-r5-imux.dts')

    def CortexR52FreeRtos(self):
        logger.info(
            'Generating cortex-r52 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))
        self.GenLibxilFeatures('lop-r52-imux.dts')

    def CortexR52Zephyr(self):
        logger.info(
            'Generating cortex-r52 Zephyr configuration for core %s [ %s ]' % (self.core, self.domain))
        # Generate Domain specific dts file
        mc_filename = "%s-%s" % (self.args.machine, self.mcname)
        ZephyrImuxDTS = os.path.join(self.args.output, '%s-imux.dts' % mc_filename)
        domain_dts_file = self.GenDomainDTS(ZephyrImuxDTS, 'lop-r52-imux.dts')

        # Generate zephyr dt
        ZephyrBoardDTS = os.path.join(self.args.dts_path, '%s.dts' % mc_filename)
        RunLopperUsingDomainFile([], self.args.output, self.args.dts_path,
                                 ZephyrImuxDTS, ZephyrBoardDTS, '', 'gen_domain_dts %s zephyr_dt' % self.cpuname)
        # Update multiconfig with dt file
        conf_file_str  = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(ZephyrBoardDTS)
        conf_file = os.path.join(self.args.config_dir,
                                 'multiconfig', '%s.conf' % mc_filename)
        common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def CortexA78Zephyr(self):
        logger.info(
            'Generating cortex-a78 Zephyr configuration for core %s [ %s ]' % (self.core, self.domain))
        # Generate Domain specific dts file
        mc_filename = "%s-%s" % (self.args.machine, self.mcname)
        ZephyrImuxDTS = os.path.join(self.args.output, '%s-imux.dts' % mc_filename)
        domain_dts_file = self.GenDomainDTS(ZephyrImuxDTS, 'lop-a78-imux.dts')

        # Generate zephyr dt
        ZephyrBoardDTS = os.path.join(self.args.dts_path, '%s.dts' % mc_filename)
        RunLopperUsingDomainFile([], self.args.output, self.args.dts_path,
                                 ZephyrImuxDTS, ZephyrBoardDTS, '', 'gen_domain_dts %s zephyr_dt' % self.cpuname)
        # Update multiconfig with dt file
        conf_file_str  = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(ZephyrBoardDTS)
        conf_file = os.path.join(self.args.config_dir,
                                 'multiconfig', '%s.conf' % mc_filename)
        common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def CortexA9Linux(self):
        mc_name = self.mcname
        if mc_name == '':
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'cortexa9-linux.dts')
            conf_file = None
        else:
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    '%s.dts' % mc_name)
            conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_name)
        self.GenLinuxDts = True
        self.MultiConfDict['LinuxDT'] = dts_file
        logger.info('Generating cortex-a9 Linux configuration [ %s ]' % self.domain)

        # Generate the DTs file using user specified domain yaml file
        DTSFile = self.GenDTSWithYaml()

        # Remove pl dt nodes from linux dts by running xlnx_overlay_pl_dt script
        # in lopper. This script provides full, dfx(static) pl overlays.
        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            # Get Actual pl.dtsi path
            hw_dir = pathlib.Path(self.args.hw_file).parent
            sdt_gen_pl_dtsi = os.path.join(hw_dir, 'pl.dtsi')
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, sdt_gen_pl_dtsi, DTSFile,
                                      ps_dts_file, 'xlnx_overlay_pl_dt cortexa9-zynq %s'
                                      % (self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a9 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = DTSFile
            logger.debug('No pl-overlay is enabled for cortex-a9 Linux dts file: %s'
                         % ps_dts_file)

        # We need linux dts for with and without pl-overlay else without
        # cortexa9-linux.dts it fails to build.
        lop_files = []
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, lop_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            '-f')
        IncludeCustomDtsi(self.args.output, self.mcname, dts_file, self.system_conffile)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
            common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def CortexA53Linux(self):
        mc_name = self.mcname
        if mc_name == '':
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'cortexa53-linux.dts')
            conf_file = None
        else:
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    '%s.dts' % mc_name)
            conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_name)
        self.GenLinuxDts = True
        self.MultiConfDict['LinuxDT'] = dts_file
        logger.info('Generating cortex-a53 Linux configuration [ %s ]' % self.domain)
        # Remove pl dt nodes from linux dts by running xlnx_overlay_pl_dt script
        # in lopper. This script provides full, dfx(static) pl overlays.

        # Generate the DTs file using user specified domain yaml file
        DTSFile = self.GenDTSWithYaml()

        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            # Get Actual pl.dtsi path
            hw_dir = pathlib.Path(self.args.hw_file).parent
            sdt_gen_pl_dtsi = os.path.join(hw_dir, 'pl.dtsi')
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, sdt_gen_pl_dtsi, DTSFile,
                                      ps_dts_file, 'xlnx_overlay_pl_dt cortexa53-zynqmp %s'
                                      % (self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a53 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = DTSFile
            logger.debug('No pl-overlay is enabled for cortex-a53 Linux dts file: %s'
                         % ps_dts_file)

        # Generate OpenAMP DTS if applicable
        ps_dts_file = self.GenOpenampDts(ps_dts_file, 'linux_dt')

        # We need linux dts for with and without pl-overlay else without
        # cortexa53-zynqmp-linux.dts it fails to build.
        lopper_args = '-f --enhanced '
        lop_files = ['lop-a53-imux.dts']
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, lop_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            lopper_args)
        IncludeCustomDtsi(self.args.output, self.mcname, dts_file, self.system_conffile)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
            common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def CortexA72Linux(self):
        mc_name = self.mcname
        if mc_name == '':
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'cortexa72-linux.dts')
            conf_file = None
        else:
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    '%s.dts' % mc_name)
            conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_name)
        self.GenLinuxDts = True
        self.MultiConfDict['LinuxDT'] = dts_file
        logger.info('Generating cortex-a72 Linux configuration [ %s ]' % self.domain)
        # Remove pl dt nodes from linux dts by running xlnx_overlay_pl_dt script
        # in lopper. This script provides full(segmented configuration),
        # dfx(static) pl overlays.

        # Generate the DTs file using user specified domain yaml file
        DTSFile = self.GenDTSWithYaml()

        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            # Get Actual pl.dtsi path
            hw_dir = pathlib.Path(self.args.hw_file).parent
            sdt_gen_pl_dtsi = os.path.join(hw_dir, 'pl.dtsi')
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, sdt_gen_pl_dtsi, DTSFile,
                                      ps_dts_file, 'xlnx_overlay_pl_dt cortexa72-versal %s'
                                      % (self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a72 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = DTSFile
            logger.debug('No pl-overlay is enabled for cortex-a72 Linux dts file: %s'
                         % ps_dts_file)

        # Generate OpenAMP DTS if applicable
        ps_dts_file = self.GenOpenampDts(ps_dts_file, 'linux_dt')

        # We need linux dts for with and without pl-overlay else without
        # cortexa72-versal-linux.dts it fails to build.
        lopper_args = '-f --enhanced '
        lop_files = ['lop-a72-imux.dts']
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, lop_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            lopper_args)
        IncludeCustomDtsi(self.args.output, self.mcname, dts_file, self.system_conffile)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
            common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def CortexA78Linux(self):
        mc_name = self.mcname
        if mc_name == '':
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'cortexa78-linux.dts')
            conf_file = None
        else:
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    '%s.dts' % mc_name)
            conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_name)
        self.GenLinuxDts = True
        self.MultiConfDict['LinuxDT'] = dts_file
        logger.info('Generating cortex-a78 Linux configuration [ %s ]' % self.domain)
        # Remove pl dt nodes from linux dts by running xlnx_overlay_pl_dt script
        # in lopper. This script provides full(segmented configuration),
        # dfx(static) pl overlays.

        # Generate the DTs file using user specified domain yaml file
        DTSFile = self.GenDTSWithYaml()

        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            # Get Actual pl.dtsi path
            hw_dir = pathlib.Path(self.args.hw_file).parent
            sdt_gen_pl_dtsi = os.path.join(hw_dir, 'pl.dtsi')
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, sdt_gen_pl_dtsi, DTSFile,
                                      ps_dts_file, 'xlnx_overlay_pl_dt cortexa78_0 %s'
                                      % (self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a78 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = DTSFile
            logger.debug('No pl-overlay is enabled for cortex-a78 Linux dts file: %s'
                         % ps_dts_file)

        # Generate OpenAMP DTS if applicable
        ps_dts_file = self.GenOpenampDts(ps_dts_file, 'linux_dt')

        # We need linux dts for with and without pl-overlay else without
        # cortexa78-versal-linux.dts it fails to build.
        lopper_args = ' -f --enhanced '
        lop_files = ['lop-a78-imux.dts']
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, lop_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            lopper_args)
        IncludeCustomDtsi(self.args.output, self.mcname, dts_file, self.system_conffile)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
            common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def MBRiscVLinux(self):
        dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'microblaze-riscv-linux.dts')
        self.GenLinuxDts = True
        self.MultiConfDict['LinuxDT'] = dts_file
        logger.info('Generating microblaze riscv Linux configuration [ %s ]' % self.domain)

        # Generate the DTs file using user specified domain yaml file
        DTSFile = self.GenDTSWithYaml()

        # Generate Linux dts for Microblaze-V
        lopper_args = ' -f --enhanced '
        lop_files = []
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, lop_files, DTSFile,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            lopper_args)

    def MBRiscVZephyr(self):
        mc_filename = "%s-%s" % (self.args.machine, self.mcname)
        conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_filename)
        DomainDTS = os.path.join(self.args.dts_path, '%s-domain.dts' % mc_filename)
        BoardDTS = os.path.join(self.args.dts_path, '%s-board.dts' % mc_filename)
        Mbv32Dts = os.path.join(self.args.dts_path, '%s.dts' % mc_filename)

        logger.info('Generating microblaze riscv %s configuration [ %s ]' % (self.os_hint, self.domain))
        # Generate Domain specific dts file
        domain_dts_file = self.GenDomainDTS(DomainDTS, 'lop-microblaze-riscv.dts')
        # Generate zephyr dt
        RunLopperUsingDomainFile(['lop-microblaze-riscv.dts'], self.args.output, self.args.dts_path,
                                 DomainDTS, BoardDTS, '', 'gen_domain_dts %s zephyr_dt' % self.cpuname)
        # Generate zephyr mbv32 dt
        RunLopperUsingDomainFile(['lop-mbv-zephyr-intc.dts'], self.args.output, self.args.dts_path,
                                 BoardDTS, Mbv32Dts)
        SocKconfigFile_S = os.path.join(self.args.output, 'Kconfig')
        SocKconfigFile_D = os.path.join(self.args.dts_path, '%s-Kconfig' % mc_filename)
        SocKconfigDefconfigFile_S = os.path.join(self.args.output, 'Kconfig.defconfig')
        SocKconfigDefconfigFile_D = os.path.join(self.args.dts_path, '%s-Kconfig.defconfig' % mc_filename)
        common_utils.CopyFile(SocKconfigFile_S, SocKconfigFile_D)
        common_utils.CopyFile(SocKconfigDefconfigFile_S, SocKconfigDefconfigFile_D)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(Mbv32Dts)
            conf_file_str += 'ZEPHYR_SDT_SOC_KCONFIG  = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(SocKconfigFile_D)
            conf_file_str += 'ZEPHYR_SDT_SOC_KCONFIG_DEFCONFIG  = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(SocKconfigDefconfigFile_D)
            common_utils.AddStrToFile(conf_file, conf_file_str, mode='a+')

    def MBTuneFeatures(self):
        if self.MBTunesDone:
            return
        logger.info('Generating microblaze processor tunes')
        stdout = RunLopperUsingDomainFile(['lop-microblaze-yocto.dts'],
                                          self.args.output, os.getcwd(), self.args.hw_file)
        microblaze_inc = os.path.join(self.args.bbconf_dir, 'microblaze.inc')
        common_utils.AddStrToFile(microblaze_inc, stdout[0])
        common_utils.AddStrToFile(microblaze_inc,
                                  '\nrequire conf/machine/include/xilinx-microblaze.inc\n',
                                  mode='a+')
        self.MBTunesDone = True

    def GetRiscVTuneFeatures(self):
        logger.info('Generating microblaze riscv processor tunes')
        RunLopperUsingDomainFile(['lop-microblaze-riscv.dts'],
                                 self.args.output, os.getcwd(), self.args.hw_file)
        cflags_file = os.path.join(self.args.output, 'cflags.yaml')
        if not os.path.isfile(cflags_file):
            raise Exception('cflags file does not exist: %s, required to generate the mb-v tune features' % cflags_file)
        cflags_data = common_utils.ReadYaml(cflags_file) or {}
        m_arch = ''
        microblaze_riscv_inc = ''
        if 'cflags' in cflags_data:
            cflags_str = cflags_data['cflags']
            # Extract -march value
            march_match = re.search(r'-march=(\S+)', cflags_str)
            if march_match:
                m_arch = march_match.group(1)
        return m_arch

    def MBRiscVTuneFeatures(self):
        if self.MBVTunesDone:
            return
        m_arch = self.GetRiscVTuneFeatures()
        if m_arch:
            MBV_variables = '# compatible = "xlnx,microblaze_riscv";\n'
            MBV_variables += f'TUNE_FEATURES:tune-microblaze-riscv = "${{@mbv.tune.riscv_isa_to_tune("{m_arch}")}}"\n'
            microblaze_riscv_inc = os.path.join(self.args.bbconf_dir, 'microblaze-riscv.inc')
            common_utils.AddStrToFile(microblaze_riscv_inc, MBV_variables)
        self.MBVTunesDone = True

    def MBRiscVAsuTuneFeatures(self):
        m_arch = self.GetRiscVTuneFeatures()
        if m_arch:
            MBV_variables = '# compatible = "xlnx,microblaze_riscv";\n'
            MBV_variables += f'TUNE_FEATURES:tune-microblaze-riscv = "{m_arch}"\n'
            MBV_variables += 'AVAILTUNES += "microblaze-riscv"\n'
            MBV_variables += f'TUNEVALID[{m_arch}] = "Enable-march={m_arch}"\n'
            MBV_variables += 'TUNE_ARCH:tune-microblaze-riscv = "riscv32"\n'
            MBV_variables += 'TUNE_PKGARCH:tune-microblaze-riscv = "riscv32nf"\n'
            MBV_variables += 'PACKAGE_EXTRA_ARCHS:tune-microblaze-riscv = "${TUNE_PKGARCH}"\n'
            MBV_variables += '\nrequire conf/machine/include/riscv/tune-riscv.inc\n'
            microblaze_riscv_inc = os.path.join(self.args.bbconf_dir, 'microblaze-riscv.inc')
            common_utils.AddStrToFile(microblaze_riscv_inc, MBV_variables)

    def PmuMicroblaze(self):
        ''' pmu-microblaze is ALWAYS Baremetal, no domain'''
        logger.info('Generating microblaze baremetal configuration for ZynqMP PMU')
        self.MBTuneFeatures()
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_PLM=1"\n'
        self.GenLibxilFeatures('', extra_conf_str)

    def PmcMicroblaze(self):
        logger.info('Generating microblaze baremetal configuration for %s PMC (PLM)' % self.args.soc_family)
        self.MBTuneFeatures()
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_PLM=1"\n'
        self.GenLibxilFeatures('', extra_conf_str)

    def PsmMicroblaze(self):
        logger.info('Generating microblaze baremetal configuration for Versal PSM')
        self.MBTuneFeatures()
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_psm=1"\n'
        self.GenLibxilFeatures('', extra_conf_str)

    def AsuMicroblaze(self):
        logger.info('Generating microblaze baremetal configuration for %s ASU' % self.args.soc_family)
        self.MBRiscVAsuTuneFeatures()
        # TARGET_CFLAGS need to be update
        extra_conf_str = ''
        self.GenLibxilFeatures('', extra_conf_str)

    def MBRiscVSetup(self):
        self.MBRiscVTuneFeatures()
        if self.os_hint.startswith('linux'):
            if not self.GenLinuxDts:
                self.MBRiscVLinux()
        elif self.os_hint.startswith('zephyr'):
            self.MBRiscVZephyr()

    def ArmCortexA9Setup(self):
        if self.os_hint.startswith('linux'):
            if not self.GenLinuxDts and not project_config.LinuxDisabledInYaml:
                self.CortexA9Linux()
        elif self.os_hint == 'fsbl':
            self.CortexA9Baremetal()
        elif self.os_hint.startswith('baremetal'):
            self.CortexA9Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexA9FreeRtos()
        else:
            logger.warning('cortex-a9 for unknown OS (%s), \
                    parsing Baremetal. %s' % (self.os_hint, self.domain))
            self.CortexA9Baremetal()

    def ArmCortexA53Setup(self):
        if self.os_hint.startswith('linux'):
            if not self.GenLinuxDts and not project_config.LinuxDisabledInYaml:
                self.CortexA53Linux()
        elif self.os_hint == 'fsbl':
            self.CortexA53Baremetal()
        elif self.os_hint.startswith('baremetal'):
            self.CortexA53Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexA53FreeRtos()
        else:
            logger.warning('cortex-a53 for unknown OS (%s), \
                    parsing Baremetal. %s' % (self.os_hint, self.domain))
            self.CortexA53Baremetal()

    def ArmCortexA72Setup(self):
        if self.os_hint.startswith('linux'):
            if not self.GenLinuxDts and not project_config.LinuxDisabledInYaml:
                self.CortexA72Linux()
        elif self.os_hint.startswith('baremetal'):
            self.CortexA72Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexA72FreeRtos()
        else:
            logger.warning('cortex-a72 for unknown OS (%s), \
                        parsing Baremetal. %s' % (self.os_hint, self.domain))
            self.CortexA72Baremetal()

    def ArmCortexA78Setup(self):
        if self.os_hint.startswith('linux'):
            if not self.GenLinuxDts and not project_config.LinuxDisabledInYaml:
                self.CortexA78Linux()
        elif self.os_hint.startswith('baremetal'):
            self.CortexA78Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexA78FreeRtos()
        elif self.os_hint.startswith('zephyr'):
            self.CortexA78Zephyr()
        else:
            logger.warning('cortex-a78 for unknown OS (%s), \
                        parsing Baremetal. %s' % (self.os_hint, self.domain))
            self.CortexA78Baremetal()

    def ArmCortexR5Setup(self):
        if self.os_hint == 'fsbl':
            self.CortexR5Baremetal()
        elif self.os_hint.startswith('baremetal'):
            self.CortexR5Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexR5FreeRtos()
        else:
            self.CortexR5Baremetal()

    def ArmCortexR52Setup(self):
        if self.os_hint.startswith('baremetal'):
            self.CortexR52Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexR52FreeRtos()
        elif self.os_hint.startswith('zephyr'):
            self.CortexR52Zephyr()
        else:
            self.CortexR52Baremetal()

    def MicroblazeSetup(self):
        self.MBTuneFeatures()
        if self.os_hint == 'None' or self.os_hint.startswith('baremetal'):
            logger.warning(
                'Microblaze baremetal configuration is %s not yet implemented' % self.domain)
        elif self.os_hint == 'Linux':
            logger.warning(
                'Microblaze Linux configuration is %s not yet implemented' % self.domain)
        else:
            logger.warning('Microblaze for unknown OS (%s), not yet implemented. %s' % (
                self.os_hint, self.domain))

    def ParseCpuDict(self):
        if not self.MultiConfUser or not self.MultiConfMap:
            logger.debug("No multilibs enabled.")
            return

        for mc_name in self.MultiConfUser:
            if mc_name not in self.MultiConfMap:
                logger.error("Unable to find selected multiconfig (%s)" % mc_name)
            else:
                self.mcname = mc_name
                self.cpuname = self.MultiConfMap[mc_name]['cpuname']
                self.cpu = self.MultiConfMap[mc_name]['cpu']
                self.core = self.MultiConfMap[mc_name]['core']
                self.domain = self.MultiConfMap[mc_name]['domain']
                self.os_hint = self.MultiConfMap[mc_name]['os_hint']
                if self.cpu == 'arm,cortex-a9':
                    self.ArmCortexA9Setup()
                elif self.cpu == 'arm,cortex-a53':
                    self.ArmCortexA53Setup()
                elif self.cpu == 'arm,cortex-a72':
                    self.ArmCortexA72Setup()
                elif self.cpu == 'arm,cortex-a78':
                    self.ArmCortexA78Setup()
                elif self.cpu == 'arm,cortex-r5':
                    self.ArmCortexR5Setup()
                elif self.cpu == 'arm,cortex-r52':
                    self.ArmCortexR52Setup()
                elif self.cpu == 'xlnx,microblaze':
                    self.MicroblazeSetup()
                elif self.cpu == 'pmu-microblaze':
                    self.PmuMicroblaze()
                elif self.cpu == 'pmc-microblaze':
                    self.PmcMicroblaze()
                elif self.cpu == 'psm-microblaze':
                    self.PsmMicroblaze()
                elif self.cpu.startswith('xlnx,microblaze-riscv'):
                    self.MBRiscVSetup()
                elif self.cpu == 'xlnx,asu-microblaze_riscv':
                    self.AsuMicroblaze()
                else:
                    logger.warning('Unknown CPU %s' % self.cpu)

    def GenerateMultiConfigs(self):
        multiconfigs.GenerateMultiConfigFiles.GenerateMultiConfigs(self)

        self.ParseCpuDict()

        return self.MultiConfDict

    def __init__(self, args, multi_conf_map, system_conffile=''):
        multiconfigs.GenerateMultiConfigFiles.__init__(self, args, multi_conf_map, system_conffile=system_conffile)

        self.MBTunesDone = self.MBVTunesDone = self.GenLinuxDts = False
        self.gen_pl_overlay = None

        if system_conffile:
            # Get the PL_DT_OVERLAY type from config
            self.gen_pl_overlay = common_utils.GetConfigValue(
                                        'CONFIG_SUBSYSTEM_PL_DT_OVERLAY_', system_conffile,
                                        'choice', '=y').lower().replace('_', '-')

def GetProcNameFromCpuInfo(cpuinfo_dict):
    for cpukey in cpuinfo_dict.keys():
        if re.findall('.*cortexa78.*|.*cortexa72.*|.*cortexa53.*|.*cortexa9.*|microblaze', cpukey):
            return cpukey


def CpuInfoToDict(cpu_info):
    cpu_info_dict = {}
    for _cpu in cpu_info.splitlines():
        if not _cpu.startswith('#') or _cpu.startswith('['):
            cpu, core, domain, cpu_name, os_hint = _cpu.split(' ', 4)
            # cpu_name is unique so using it as key
            cpu_info_dict[cpu_name] = {'cpu': cpu, 'core': core,
                                       'domain': domain, 'os_hint': os_hint}
    return cpu_info_dict


def GenSdtSystemHwFile(genmachine_scripts, Kconfig_syshw, proc_type, hw_file, output):
    logger.info('Generating Kconfig for the project')
    sdtipinfo_schema = os.path.join(
        genmachine_scripts, 'data', 'sdt_ipinfo.yaml')
    ipinfo_schema = os.path.join(
        genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(output, 'petalinux_config.yaml')

    RunLopperSubcommand(output, output, hw_file,
                                     'petalinuxconfig_xlnx %s %s' % (proc_type,
                                                                     sdtipinfo_schema))
    logger.debug('Generating System HW file')
    kconfig_syshw.GenKconfigSysHW(plnx_syshw_file, ipinfo_schema, Kconfig_syshw)
    if not os.path.exists(Kconfig_syshw):
        raise Exception('Failed to Generate Kconfig_syshw File')


def ParseSDT(args):
    if args.hw_flow == 'xsct':
        raise Exception('Invalide HW source Specified for System-Device-Tree.')

    '''Check if vitis environment set and show the warning'''
    if 'XILINX_VITIS' in os.environ.keys():
        logger.warning('Vitis environment(XILINX_VITIS) found, '
                        'this may lead to failures. Recommended to start with new bash shell')

    def gatherHWInfo():
        hw_info = {}

        logger.info('Getting Platform info from HW file')

        if args.machine:
            logger.debug('Using the machine specified by user:%s' % args.machine)
            hw_info['machine'] = args.machine

        if args.soc_family:
            logger.debug('Using the soc_family specified by user:%s' % args.soc_family)
            hw_info['soc_family'] = args.soc_family

        if args.soc_variant:
            logger.debug('Using the soc_variant specified by user:%s' % args.soc_variant)
            hw_info['soc_variant'] = args.soc_variant

        # Get machinefile name, device-id and model
        machine_info = RunLopperUsingDomainFile(['lop-machine-name.dts'],
                                                             args.output, args.output,
                                                             args.hw_file, '')[0]
        local_machine_conf, hw_info['device_id'], hw_info['model'] = machine_info.strip().split(' ', 2)

        if 'machine' not in hw_info:
            hw_info['machine'] = local_machine_conf

        # Generate CPU list
        cpu_info = RunLopperUsingDomainFile(['lop-xilinx-id-cpus.dts'],
                                                         args.output, args.output,
                                                         args.hw_file, '')[0]
        hw_info['cpu_info_dict'] = CpuInfoToDict(cpu_info)

        # Get proc name
        if 'proc_type' not in hw_info:
            hw_info['proc_type'] = GetProcNameFromCpuInfo(hw_info['cpu_info_dict'])
        if 'soc_family' not in hw_info:
            hw_info['soc_family'] = project_config.DetectSocFamily(hw_info['proc_type'])
        if 'soc_variant' not in hw_info:
            hw_info['soc_variant'] = project_config.DetectSocVariant(hw_info['device_id'])

        # Generate Kconfig.syshw only when hw_file changes
        if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False) or \
                not os.path.exists(Kconfig_syshw):
            GenSdtSystemHwFile(genmachine_scripts, Kconfig_syshw,
                               hw_info['proc_type'], args.hw_file, args.output)

        template_cfgfile = os.path.join(
            genmachine_scripts, 'configs', 'config_%s' % hw_info['soc_family'])

        if not os.path.isfile(template_cfgfile):
            raise Exception('Unsupported soc_family: %s' % hw_info['soc_family'])

        return hw_info


    #### Setup:

    genmachine_scripts = project_config.GenMachineScriptsPath()

    project_cfgdir = os.path.join(args.output, 'configs')
    common_utils.CreateDir(project_cfgdir)

    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'petalinux_config.yaml')
    system_conffile = os.path.join(args.output, 'config')

    config_dtsdir = os.path.join(args.config_dir, 'dts')


    if not args.psu_init_path:
        args.psu_init_path = os.path.dirname(args.hw_file)
    else:
        logger.warning("Specifying the psu_init_path will result in a non-portable configuration.  For a portable configuration, adjust the ps init files within the SDT directory.")

    # Update PDI or bitstream path
    if not args.pl:
        args.pl = os.path.dirname(args.hw_file)


    #### Gather:
    hw_info = gatherHWInfo()

    if hw_info['machine']:
        args.machine = hw_info['machine']
    args.soc_family = hw_info['soc_family']
    args.soc_variant = hw_info['soc_variant']

    #### Generate Kconfig:
    project_config.GenKconfigProj(args, system_conffile, hw_info)

    # In case config file exists before prepocess use that
    cfg_machine = common_utils.GetConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                                    system_conffile)
    if cfg_machine:
        args.machine = cfg_machine

    project_config.PrintSystemConfiguration(args, hw_info['model'],
                            hw_info['device_id'], hw_info['cpu_info_dict'])

    # Update the sysconfig with command line arguments
    # to reflect in menuconfig/config
    project_config.PreProcessSysConf(args, system_conffile, hw_info)
    common_utils.RunMenuconfig(Kconfig, system_conffile,
                               True if args.menuconfig == 'project' else False,
                               args.output, 'project')

    #### Process the configuration:
    post_process_config.PostProcessSysConf(
        args, system_conffile, ipinfo_file, plnx_syshw_file)

    # In case machine name updated in config
    cfg_machine = common_utils.GetConfigValue('CONFIG_YOCTO_MACHINE_NAME',
                                                     system_conffile)
    if cfg_machine:
        args.machine = cfg_machine

    # In case domain file provided in config
    domain_file_cfg = common_utils.GetConfigValue('CONFIG_YOCTO_MC_DOMAIN_FILEPATH',
                                                    system_conffile)
    args.domain_file = ''
    for _file in domain_file_cfg.split():
        _file = os.path.expandvars(_file)
        # Expand the bitbake variables
        _file = common_utils.Bitbake.expand(_file)
        args.domain_file += os.path.realpath(_file) + ' '

    # In case dts_path updated in config
    cfg_dtspath = common_utils.GetConfigValue('CONFIG_SUBSYSTEM_DT_XSCT_WORKSPACE',
                                                     system_conffile)
    if cfg_dtspath:
        args.dts_path = os.path.expandvars(cfg_dtspath)
    else:
        args.dts_path = args.machine

    if not os.path.isabs(args.dts_path):
        args.dts_path = os.path.join(config_dtsdir, args.dts_path)
    else:
        args.dts_path = os.path.realpath(args.dts_path)

    if args.petalinux:
        rootfs_config.GenRootfsConfig(args, system_conffile)

    #### Generate the configuration:
    MCObject = sdtGenerateMultiConfigFiles(args, hw_info['multiconfigs'], system_conffile=system_conffile)

    project_config.GenerateConfiguration(args, hw_info,
                                         system_conffile,
                                         plnx_syshw_file,
                                         MCObject=MCObject)

def register_commands(subparsers):
    parser_sdt = subparsers.add_parser('parse-sdt',
                                       help='Parse System devicet-tree file and generate Yocto/PetaLinux configurations.',
                                       usage='%(prog)s [--hw-description'
                                       ' <PATH_TO_SDTDIR>] [other options]'
                                       )
    parser_sdt.add_argument('-g', '--gen-pl-overlay', choices=['full', 'dfx'],
                            default=common_utils.AddYamlDefaultValues(['-g', '--gen-pl-overlay']),
                            help='Generate pl overlay for full, dfx configuration using xlnx_overlay_pl_dt lopper script')
    parser_sdt.add_argument('-d', '--domain-file', metavar='<domain_file>',
                            default=common_utils.AddYamlDefaultValues(['-d', '--domain-file']),
                            action=common_utils.AppendArgWithSpace,
                            help='Path to domain file (.yaml) to use for generating the device tree.')
    parser_sdt.add_argument('-i', '--psu-init-path', metavar='<psu_init_path>',
                            default=common_utils.AddYamlDefaultValues(['-i', '--psu-init-path']),
                            help='Path to psu_init or ps7_init files, defaults to system device tree output directory',
                            type=os.path.realpath)
    parser_sdt.add_argument('-p', '--pl', metavar='<pl_path>',
                            default=common_utils.AddYamlDefaultValues(['-p', '--pl']),
                            help='Path to pdi or bitstream file', type=os.path.realpath)
    parser_sdt.add_argument('-l', '--localconf', metavar='<config_file>',
                            default=common_utils.AddYamlDefaultValues(['-l', '--localconf']),
                            help='Write local.conf changes to this file', type=os.path.realpath)
    parser_sdt.add_argument('--multiconfigfull', action='store_true',
                            default=common_utils.AddYamlDefaultValues('--multiconfigfull', False),
                            help='Generate/Enable Full set of multiconfig .conf and .dts files. Default is minimal.'
                                ' Search for CONFIG_YOCTO_BBMC prefix in --menuconfig to get the available multiconfig targets.')
    parser_sdt.add_argument('--dts-path', metavar='<dts_path>',
                            default=common_utils.AddYamlDefaultValues('--dts-path'),
                            help='Absolute path or subdirectory of conf/dts to place DTS files in (usually auto detected from DTS)')

    parser_sdt.set_defaults(func=ParseSDT)
