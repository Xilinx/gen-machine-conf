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


def find_file(search_file: str, search_path: str):
    """
    This api find the file in sub-directories and returns absolute path of
    file, if file exists

    Args:
        | search_file: The regex pattern to be searched in file names
        | search_path: The directory that needs to be searched
    Returns:
        string: Path of the first file that matches the pattern
    """
    file_list = list(pathlib.Path(search_path).glob(f"**/{search_file}"))
    if len(file_list) > 1:
        raise Exception('More than one {search_file} found')
    elif len(file_list) == 0:
        return None
    elif os.path.isfile(file_list[0]):
        return file_list[0]

def get_domain_name(proc_name: str, yaml_file: str):
    schema = common_utils.ReadYaml(yaml_file)["domains"]
    for subsystem in schema:
        if schema[subsystem].get("domains", {}):
            for dom in schema[subsystem]["domains"]:
                domain_name = schema[subsystem]["domains"][dom]["cpus"][0]["cluster_cpu"]
                if domain_name == proc_name:
                    return dom
    return None

def RunLopperGenDomainYaml(hw_file, iss_file, dts_path, domain_yaml, outdir):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f --enhanced %s -- isospec -v -v --audit %s %s' % (
                             lopper, outdir, hw_file, iss_file, domain_yaml)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout

def RunLopperGenDomainDTS(outdir, dts_path, hw_file, dts_file, domain_name, domain_yaml):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    domain_args = "--auto -x '*.yaml'"
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f --enhanced -t %s -a domain_access %s -i %s %s %s' % (
                             lopper, outdir, domain_name, domain_args, domain_yaml, hw_file, dts_file)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout

def RunLopperUsingDomainFile(domain_files, outdir, dts_path, hw_file,
                             dts_file='', lopper_args=''):
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

def RunLopperPlOverlaycommand(outdir, dts_path, hw_file, ps_dts_file, subcommand_args, lopper_args=''):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s --enhanced -O %s %s %s %s -- %s' % (
        lopper, outdir, lopper_args, hw_file, ps_dts_file, subcommand_args)
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


class sdtGenerateMultiConfigFiles(multiconfigs.GenerateMultiConfigFiles):
    def GenLibxilFeatures(self, lopdts, extra_conf=''):
        mc_filename = "%s-%s" % (self.args.machine, self.mcname)
        dts_file = os.path.join(self.args.dts_path, '%s.dts' % mc_filename)
        conf_file = os.path.join(self.args.config_dir,
                                 'multiconfig', '%s.conf' % mc_filename)
        libxil = os.path.join(self.args.bbconf_dir,
                              '%s-libxil.conf' % mc_filename)
        features = os.path.join(self.args.bbconf_dir,
                                '%s-features.conf' % mc_filename)
        lopper_args = ''
        # Build device tree
        domain_files = [lopdts]
        if self.args.domain_file:
            lopper_args = '-x "*.yaml"'
            domain_files.append(self.args.domain_file)

        if self.domain_yaml:
            domain_name = get_domain_name(self.cpuname, self.domain_yaml)
            if domain_name:
                domain_dts_file = os.path.join(self.args.dts_path, '%s.dts'
                                               % domain_name.lower())
                RunLopperGenDomainDTS(self.args.output, self.args.dts_path, self.args.hw_file,
		                              domain_dts_file, domain_name, self.domain_yaml)
            else:
                domain_dts_file = self.args.hw_file
        else:
            domain_dts_file = self.args.hw_file
        RunLopperUsingDomainFile(domain_files, self.args.output, self.args.dts_path,
                                 domain_dts_file, dts_file, lopper_args)

        # Build baremetal multiconfig
        if self.args.domain_file:
            lopper_args = '--enhanced -x "*.yaml"'
        GetLopperBaremetalDrvList(self.cpuname, self.args.output, self.args.dts_path,
                                  domain_dts_file, lopper_args)

        common_utils.RenameFile(os.path.join(
            self.args.output, 'libxil.conf'), libxil)
        common_utils.RenameFile(os.path.join(
            self.args.output, 'distro.conf'), features)
        common_utils.ReplaceStrFromFile(
            features, 'DISTRO_FEATURES', 'MACHINE_FEATURES')
        conf_file_str  = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
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
        # Remove pl dt nodes from linux dts by running xlnx_overlay_dt script
        # in lopper. This script provides full, dfx(static) pl overlays.
        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                      ps_dts_file, 'xlnx_overlay_dt cortexa9-%s %s'
                                      % (self.args.soc_family, self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a9 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = self.args.hw_file
            logger.debug('No pl-overlay is enabled for cortex-a9 Linux dts file: %s'
                         % ps_dts_file)

        # We need linux dts for with and without pl-overlay else without
        # cortexa9-linux.dts it fails to build.
        lopper_args = '-f --enhanced'
        if self.args.domain_file:
            lopper_args += '-x "*.yaml"'
        domain_files = [self.args.domain_file]
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, domain_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            '-f')
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)

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
        # Remove pl dt nodes from linux dts by running xlnx_overlay_dt script
        # in lopper. This script provides full, dfx(static) pl overlays.
        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                      ps_dts_file, 'xlnx_overlay_dt cortexa53-%s %s'
                                      % (self.args.soc_family, self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a53 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = self.args.hw_file
            logger.debug('No pl-overlay is enabled for cortex-a53 Linux dts file: %s'
                         % ps_dts_file)

        # We need linux dts for with and without pl-overlay else without
        # cortexa53-zynqmp-linux.dts it fails to build.
        lopper_args = '-f --enhanced'
        if self.args.domain_file:
            lopper_args += '-x "*.yaml"'
        domain_files = [self.args.domain_file, 'lop-a53-imux.dts']
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, domain_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            '-f')
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
        # Remove pl dt nodes from linux dts by running xlnx_overlay_dt script
        # in lopper. This script provides full(segmented configuration),
        # dfx(static) pl overlays.
        ps_dts_file = ''
        if self.domain_yaml:
            domain_name = get_domain_name(self.cpuname, self.domain_yaml)
            if domain_name:
                ps_dts_file = os.path.join(self.args.dts_path, '%s.dts'
                                           % domain_name.lower())
                RunLopperGenDomainDTS(self.args.output, self.args.dts_path, self.args.hw_file,
		                       ps_dts_file, domain_name, self.domain_yaml)
            else:
                ps_dts_file = self.args.hw_file
        elif self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                      ps_dts_file, 'xlnx_overlay_dt cortexa72-%s %s'
                                      % (self.args.soc_family, self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a72 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = self.args.hw_file
            logger.debug('No pl-overlay is enabled for cortex-a72 Linux dts file: %s'
                         % ps_dts_file)

        # We need linux dts for with and without pl-overlay else without
        # cortexa72-versal-linux.dts it fails to build.
        lopper_args = '-f --enhanced'
        if self.args.domain_file:
            lopper_args += '-x "*.yaml"'
        domain_files = [self.args.domain_file, 'lop-a72-imux.dts']
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, domain_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            '-f')
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
        # Remove pl dt nodes from linux dts by running xlnx_overlay_dt script
        # in lopper. This script provides full(segmented configuration),
        # dfx(static) pl overlays.
        ps_dts_file = ''
        if self.gen_pl_overlay:
            # Do not overwrite original SDT file during overlay processing, Instead
            # write out to a intermediate file in output directory and use this
            # file for lopper pl overlay operation.
            ps_dts_file = os.path.join(self.args.dts_path, '%s-no-pl.dts'
                                       % pathlib.Path(self.args.hw_file).stem)
            RunLopperPlOverlaycommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                      ps_dts_file, 'xlnx_overlay_dt cortexa78-%s %s'
                                      % (self.args.soc_family, self.gen_pl_overlay),
                                      '-f')
            logger.info('pl-overlay [ %s ] is enabled for cortex-a78 file: %s and stored in intermediate ps dts file: %s'
                        % (self.gen_pl_overlay, self.args.hw_file, ps_dts_file))
            # Once RunLopperPlOverlaycommand API is executed pl.dtsi will be
            # generated in lopper output directory. Hence copy pl.dtsi from
            # output directory to dts_path/pl-overlay-{full|dfx} directory.
            # Later user can use this pl.dtsi as input file to firmware recipes.
            CopyPlOverlayfile(self.args.output, self.args.dts_path, self.gen_pl_overlay)
        else:
            ps_dts_file = self.args.hw_file
            logger.debug('No pl-overlay is enabled for cortex-a78 Linux dts file: %s'
                         % ps_dts_file)

        # We need linux dts for with and without pl-overlay else without
        # cortexa78-versal-linux.dts it fails to build.
        lopper_args = '-f --enhanced'
        if self.args.domain_file:
            lopper_args += '-x "*.yaml"'
        domain_files = [self.args.domain_file, 'lop-a78-imux.dts']
        RunLopperGenLinuxDts(self.args.output, self.args.dts_path, domain_files, ps_dts_file,
                            dts_file, 'gen_domain_dts %s linux_dt' % self.cpuname,
                            '-f')
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "${CONFIG_DTFILE_DIR}/%s"\n' % os.path.basename(dts_file)
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

    def PmuMicroblaze(self):
        ''' pmu-microblaze is ALWAYS Baremetal, no domain'''
        logger.info('Generating microblaze baremetal configuration for ZynqMP PMU')
        self.MBTuneFeatures()
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_PLM=1"\n'
        self.GenLibxilFeatures('', extra_conf_str)

    def PmcMicroblaze(self):
        logger.info('Generating microblaze baremetal configuration for Versal PMC (PLM)')
        self.MBTuneFeatures()
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_PLM=1"\n'
        self.GenLibxilFeatures('', extra_conf_str)

    def PsmMicroblaze(self):
        logger.info('Generating microblaze baremetal configuration for Versal PSM')
        self.MBTuneFeatures()
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_psm=1"\n'
        self.GenLibxilFeatures('', extra_conf_str)

    def ArmCortexA9Setup(self):
        if self.os_hint.startswith('linux'):
            if not self.GenLinuxDts:
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
            if not self.GenLinuxDts:
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
            if not self.GenLinuxDts:
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
            if not self.GenLinuxDts:
                self.CortexA78Linux()
        elif self.os_hint.startswith('baremetal'):
            self.CortexA78Baremetal()
        elif self.os_hint.startswith('freertos'):
            self.CortexA78FreeRtos()
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
                else:
                    logger.warning('Unknown CPU %s' % self.cpu)

    def GenerateMultiConfigs(self):
        multiconfigs.GenerateMultiConfigFiles.GenerateMultiConfigs(self)

        self.ParseCpuDict()

        return self.MultiConfDict

    def __init__(self, args, multi_conf_map, system_conffile=''):
        multiconfigs.GenerateMultiConfigFiles.__init__(self, args, multi_conf_map, system_conffile=system_conffile)

        self.MBTunesDone = self.GenLinuxDts = False
        self.gen_pl_overlay = None
        self.domain_yaml = None
        iss_file = find_file("*.iss",  os.path.dirname(self.args.hw_file.rstrip(os.path.sep)))
        if iss_file:
            self.domain_yaml = os.path.join(self.args.config_dir, "domains.yaml")
            RunLopperGenDomainYaml(self.args.hw_file, iss_file, self.args.dts_path,
                                   self.domain_yaml, self.args.config_dir)

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
                            help='Generate pl overlay for full, dfx configuration using xlnx_overlay_dt lopper script')
    parser_sdt.add_argument('-d', '--domain-file', metavar='<domain_file>',
                            help='Path to domain file (.yaml/.dts)', type=os.path.realpath)
    parser_sdt.add_argument('-i', '--psu-init-path', metavar='<psu_init_path>',
                            help='Path to psu_init or ps7_init files, defaults to system device tree output directory',
                            type=os.path.realpath)
    parser_sdt.add_argument('-p', '--pl', metavar='<pl_path>',
                            help='Path to pdi or bitstream file', type=os.path.realpath)
    parser_sdt.add_argument('-l', '--localconf', metavar='<config_file>',
                            help='Write local.conf changes to this file', type=os.path.realpath)
    parser_sdt.add_argument('--multiconfigfull', action='store_true',
                            help='Generate/Enable Full set of multiconfig .conf and .dts files. Default is minimal)')
    parser_sdt.add_argument('--dts-path', metavar='<dts_path>',
                            help='Absolute path or subdirectory of conf/dts to place DTS files in (usually auto detected from DTS)')

    parser_sdt.set_defaults(func=ParseSDT)
