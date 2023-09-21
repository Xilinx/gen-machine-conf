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
import glob


logger = logging.getLogger('Gen-Machineconf')


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


def RunLopperSubcommand(outdir, dts_path, hw_file, subcommand_args, lopper_args=''):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s %s %s -- %s' % (
        lopper, outdir, lopper_args, hw_file, subcommand_args)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout


def GetLopperBaremetalDrvList(cpuname, outdir, dts_path, hw_file, lopper_args=''):
    lopper, lopper_dir, lops_dir, embeddedsw = common_utils.GetLopperUtilsPath()
    cmd = 'LOPPER_DTC_FLAGS="-b 0 -@" %s -O %s -f %s \
                "%s" -- baremetaldrvlist_xlnx %s "%s"' % (
        lopper, outdir, lopper_args,
        hw_file, cpuname, embeddedsw)
    stdout = common_utils.RunCmd(cmd, dts_path, shell=True)
    return stdout


class CreateMultiConfigFiles():
    def GenLibxilFeatures(self, lopdts,
                          mc_name, distro_name, tune, extra_conf=''):
        dts_file = os.path.join(self.args.dts_path, '%s.dts' % mc_name)
        conf_file = os.path.join(self.args.config_dir,
                                 'multiconfig', '%s.conf' % mc_name)
        libxil = os.path.join(self.args.bbconf_dir,
                              '%s-libxil.conf' % mc_name)
        features = os.path.join(self.args.bbconf_dir,
                                '%s-features.conf' % mc_name)
        lopper_args = ''
        # Build device tree
        domain_files = [lopdts]
        if self.args.domain_file:
            lopper_args = '-x "*.yaml"'
            domain_files.append(self.args.domain_file)
        RunLopperUsingDomainFile(domain_files, self.args.output, self.args.dts_path,
                                 self.args.hw_file, dts_file, lopper_args)

        # Build baremetal multiconfig
        if self.args.domain_file:
            lopper_args = '--enhanced -x "*.yaml"'
        GetLopperBaremetalDrvList(self.cpuname, self.args.output, self.args.dts_path,
                                  self.args.hw_file, lopper_args)

        common_utils.RenameFile(os.path.join(
            self.args.output, 'libxil.conf'), libxil)
        common_utils.RenameFile(os.path.join(
            self.args.output, 'distro.conf'), features)
        common_utils.ReplaceStrFromFile(
            features, 'DISTRO_FEATURES', 'MACHINE_FEATURES')
        conf_file_str = 'CONFIG_DTFILE = "%s"\n' % dts_file
        conf_file_str += 'ESW_MACHINE = "%s"\n' % self.cpuname
        conf_file_str += 'DEFAULTTUNE = "%s"\n' % tune
        conf_file_str += 'TMPDIR = "${BASE_TMPDIR}/tmp-%s"\n' % mc_name
        conf_file_str += 'DISTRO = "%s"\n' % distro_name
        conf_file_str += extra_conf
        common_utils.AddStrToFile(conf_file, conf_file_str)

    def CortexA53Baremetal(self, domain=''):
        if not domain:
            domain = self.domain
        suffix = '-%s' % domain if domain and domain != 'None' else ''
        lto = '-nolto' if not domain or domain == 'None' else ''
        mc_name = 'cortexa53-%s-%s%s-baremetal' % (
            self.core, self.args.soc_family, suffix)
        self.a53FsblDone = True
        self.MultiConfFiles.append(mc_name)
        if domain == 'fsbl':
            self.MultiConfMin.append(mc_name)
        if self.ReturnConfFiles:
            return
        extra_conf_str = ''
        if domain == 'fsbl':
            logger.info('cortex-a53 FSBL Baremetal configuration')
            for psu_init_f in ['psu_init.c', 'psu_init.h']:
                if not os.path.exists(os.path.join(
                        self.args.psu_init_path, psu_init_f)):
                    logger.warning('Unable to find %s in %s' % (
                        psu_init_f, self.args.psu_init_path))
            self.MultiConfDict['FsblMcDepends'] = 'mc::%s:fsbl-firmware:do_deploy' % mc_name
            self.MultiConfDict['FsblDeployDir'] = '${BASE_TMPDIR}/tmp-%s/deploy/images/${MACHINE}' % mc_name
            extra_conf_str = 'PSU_INIT_PATH = "%s"\n' % self.args.psu_init_path
        else:
            logger.info(
                'cortex-a53 Baremetal configuration for core %s [ %s ]' % (self.core, domain))

        distro_name = 'xilinx-standalone%s' % lto
        self.GenLibxilFeatures(
            'lop-a53-imux.dts', mc_name, distro_name, 'cortexa53', extra_conf_str)

    def CortexA72Baremetal(self):
        suffix = '-%s' % self.domain if self.domain and self.domain != 'None' else ''
        mc_name = 'cortexa72-%s-%s%s-baremetal' % (
            self.core, self.args.soc_family, suffix)
        self.MultiConfFiles.append(mc_name)
        if self.ReturnConfFiles:
            return
        logger.info(
            'cortex-a72 Baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-standalone-nolto'
        self.GenLibxilFeatures(
            'lop-a72-imux.dts', mc_name, distro_name, 'cortexa72')

    def CortexR5Baremetal(self, domain=''):
        if not domain:
            domain = self.domain
        suffix = '-%s' % domain if domain and domain != 'None' else ''
        lto = '-nolto' if not domain or domain == 'None' else ''
        mc_name = 'cortexr5-%s-%s%s-baremetal' % (self.core,
                                                  self.args.soc_family, suffix)
        self.r5FsblDone = True
        self.MultiConfFiles.append(mc_name)
        if self.ReturnConfFiles:
            return
        extra_conf_str = ''
        if domain == 'fsbl':
            logger.info('cortex-r5 FSBL Baremetal configuration')
            for psu_init_f in ['psu_init.c', 'psu_init.h']:
                if not os.path.exists(os.path.join(
                        self.args.psu_init_path, psu_init_f)):
                    logger.warning('Unable to find %s in %s' % (
                        psu_init_f, self.args.psu_init_path))
            self.MultiConfDict['R5FsblMcDepends'] = 'mc::%s:fsbl-firmware:do_deploy' % mc_name
            self.MultiConfDict['R5FsblDeployDir'] = '${BASE_TMPDIR}/tmp-%s/deploy/images/${MACHINE}' % mc_name
            extra_conf_str = 'PSU_INIT_PATH = "%s"\n' % self.args.psu_init_path
        else:
            logger.info(
                'cortex-r5 Baremetal configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-standalone%s' % lto
        self.GenLibxilFeatures('lop-r5-imux.dts', mc_name,
                               distro_name, 'cortexr5', extra_conf_str)

    def CortexA53FreeRtos(self):
        suffix = '-%s' % self.domain if self.domain and self.domain != 'None' else ''
        mc_name = 'cortexa53-%s-%s%s-freertos' % (self.core,
                                                  self.args.soc_family, suffix)
        self.MultiConfFiles.append(mc_name)
        if self.ReturnConfFiles:
            return
        logger.info(
            'cortex-a53 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-freertos'
        self.GenLibxilFeatures('lop-a53-imux.dts',
                               mc_name, distro_name, 'cortexa53')

    def CortexA72FreeRtos(self):
        suffix = '-%s' % self.domain if self.domain and self.domain != 'None' else ''
        mc_name = 'cortexa72-%s-%s%s-freertos' % (self.core,
                                                  self.args.soc_family, suffix)
        self.MultiConfFiles.append(mc_name)
        if self.ReturnConfFiles:
            return
        logger.info(
            'cortex-a72 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-freertos'
        self.GenLibxilFeatures('lop-a72-imux.dts',
                               mc_name, distro_name, 'cortexa72')

    def CortexR5FreeRtos(self):
        suffix = '-%s' % self.domain if self.domain and self.domain != 'None' else ''
        mc_name = 'cortexr5-%s-%s%s-freertos' % (self.core,
                                                 self.args.soc_family, suffix)
        self.MultiConfFiles.append(mc_name)
        if self.ReturnConfFiles:
            return
        logger.info(
            'cortex-r5 FreeRTOS configuration for core %s [ %s ]' % (self.core, self.domain))

        distro_name = 'xilinx-freertos'
        self.GenLibxilFeatures('lop-r5-imux.dts',
                               mc_name, distro_name, 'cortexr5')

    def CortexA53Linux(self):
        if self.domain == 'None':
            mc_name = ''
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'cortexa53-%s-linux.dts' % self.args.soc_family)
            conf_file = ''
        else:
            mc_name = 'cortexa53-%s-%s-linux' % (
                self.args.soc_family, self.domain)
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    '%s.dts' % mc_name)
            conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_name)
        self.GenLinuxDts = True
        if mc_name:
            self.MultiConfFiles.append(mc_name)
        self.MultiConfDict['LinuxDT'] = dts_file
        if self.ReturnConfFiles:
            return
        logger.info('cortex-a53 for Linux [ %s ]' % self.domain)
        # Check if it is overlay dts otherwise just create linux dts
        if self.args.overlay:
            if self.args.external_fpga:
                RunLopperSubcommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                    'xlnx_overlay_dt %s full' % self.args.soc_family,
                                    '-f')
            else:
                RunLopperSubcommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                    'xlnx_overlay_dt %s partial' % self.args.soc_family)
            common_utils.RunCmd('dtc -q -O dtb -o %s -b 0 -@ %s' % (
                os.path.join(self.args.dts_path, 'pl.dtbo'),
                os.path.join(self.args.dts_path, 'pl.dtsi')))
        else:
            lopper_args = '-f --enhanced'
            if self.args.domain_file:
                lopper_args += '-x "*.yaml"'
            domain_files = [self.args.domain_file, 'lop-a53-imux.dts']
            domain_files += ['lop-domain-linux-a53.dts',
                             'lop-domain-linux-a53-prune.dts']
            RunLopperUsingDomainFile(domain_files, self.args.output, self.args.dts_path,
                                     self.args.hw_file, dts_file, lopper_args)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "%s\n"' % dts_file
            conf_file_str += 'TMPDIR = "${BASE_TMPDIR}/tmp-%s\n"' % mc_name
            common_utils.AddStrToFile(conf_file, conf_file_str)

    def CortexA72Linux(self):
        if self.domain == 'None':
            mc_name = ''
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    'cortexa72-%s-linux.dts' % self.args.soc_family)
            conf_file = ''
        else:
            mc_name = 'cortexa72-%s-%s-linux' % (
                self.args.soc_family, self.domain)
            dts_file = os.path.join(self.args.dts_path if self.args.dts_path else '',
                                    '%s.dts' % mc_name)
            conf_file = os.path.join(self.args.config_dir,
                                     'multiconfig', '%s.conf' % mc_name)
        self.GenLinuxDts = True
        if mc_name:
            self.MultiConfFiles.append(mc_name)
        self.MultiConfDict['LinuxDT'] = dts_file
        if self.ReturnConfFiles:
            return
        logger.info('cortex-a72 for Linux [ %s ]' % self.domain)
        # Check if it is overlay dts otherwise just create linux dts
        if self.args.overlay:
            if self.args.external_fpga:
                # As there is no partial support on Versal, As per fpga manager implementation there is
                # a flag "external_fpga" which says apply overlay without loading the bit file.
                RunLopperSubcommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                    'xlnx_overlay_dt %s full external_fpga' % self.args.soc_family,
                                    '-f')
            else:
                # If there is no external_fpga flag, then the default is full
                RunLopperSubcommand(self.args.output, self.args.dts_path, self.args.hw_file,
                                    'xlnx_overlay_dt %s full' % self.args.soc_family)
            common_utils.RunCmd('dtc -q -O dtb -o %s -b 0 -@ %s' % (
                os.path.join(self.args.dts_path, 'pl.dtbo'),
                os.path.join(self.args.dts_path, 'pl.dtsi')))
        else:
            lopper_args = '-f --enhanced'
            if self.args.domain_file:
                lopper_args += '-x "*.yaml"'
            domain_files = [self.args.domain_file, 'lop-a72-imux.dts']
            domain_files += ['lop-domain-a72.dts', 'lop-domain-a72-prune.dts']
            RunLopperUsingDomainFile(domain_files, self.args.output, self.args.dts_path,
                                     self.args.hw_file, dts_file, lopper_args)
        if conf_file:
            conf_file_str = 'CONFIG_DTFILE = "%s\n"' % dts_file
            conf_file_str += 'TMPDIR = "${BASE_TMPDIR}/tmp-%s\n"' % mc_name
            common_utils.AddStrToFile(conf_file, conf_file_str)

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
        mc_name = 'microblaze-0-pmu'
        self.MultiConfFiles.append(mc_name)
        self.MultiConfMin.append(mc_name)
        if self.ReturnConfFiles:
            return
        logger.info('Microblaze ZynqMP PMU')
        self.MBTuneFeatures()
        self.MultiConfDict['PmuMcDepends'] = 'mc::%s:pmu-firmware:do_deploy' % mc_name
        self.MultiConfDict['PmuFWDeployDir'] = '${BASE_TMPDIR}/tmp-%s/deploy/images/${MACHINE}' % mc_name
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_PLM=1"\n'
        self.GenLibxilFeatures('', mc_name,
                               'xilinx-standalone', 'microblaze-pmu', extra_conf_str)

    def PmcMicroblaze(self):
        mc_name = 'microblaze-0-pmc'
        self.MultiConfFiles.append(mc_name)
        self.MultiConfMin.append(mc_name)
        if self.ReturnConfFiles:
            return
        logger.info('Microblaze Versal PMC')
        self.MBTuneFeatures()
        self.MultiConfDict['PlmMcDepends'] = 'mc::%s:plm-firmware:do_deploy' % mc_name
        self.MultiConfDict['PlmDeployDir'] = '${BASE_TMPDIR}/tmp-%s/deploy/images/${MACHINE}' % mc_name
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_PLM=1"\n'
        self.GenLibxilFeatures('', mc_name,
                               'xilinx-standalone', 'microblaze-pmc', extra_conf_str)

    def PsmMicroblaze(self):
        mc_name = 'microblaze-0-psm'
        self.MultiConfFiles.append(mc_name)
        self.MultiConfMin.append(mc_name)
        if self.ReturnConfFiles:
            return mc_name
        logger.info('Microblaze Versal PSM')
        self.MBTuneFeatures()
        self.MultiConfDict['PsmMcDepends'] = 'mc::%s:psm-firmware:do_deploy' % mc_name
        self.MultiConfDict['PsmFWDeployDir'] = '${BASE_TMPDIR}/tmp-%s/deploy/images/${MACHINE}' % mc_name
        extra_conf_str = 'TARGET_CFLAGS += "-DVERSAL_psm=1"\n'
        self.GenLibxilFeatures('', mc_name,
                               'xilinx-standalone', 'microblaze-psm', extra_conf_str)

    def ArmCortexA53Setup(self):
        if self.core == '0' and not self.a53FsblDone:
            # We need a base CortexA53Baremetal for the FSBL
            self.CortexA53Baremetal('fsbl')
        if self.os_hint != 'None':
            if self.os_hint.startswith('linux'):
                if not self.GenLinuxDts:
                    self.CortexA53Linux()
            elif self.os_hint.startswith('baremetal'):
                self.CortexA53Baremetal()
            elif self.os_hint.startswith('freertos'):
                self.CortexA53FreeRtos()
            else:
                logger.warning('cortex-a53 for unknown OS (%s), \
                        parsing Baremetal. %s' % (self.os_hint, self.domain))
                self.CortexA53Baremetal()
        else:
            if not self.GenLinuxDts:
                self.CortexA53Linux()
            self.CortexA53Baremetal()
            self.CortexA53FreeRtos()

    def ArmCortexA72Setup(self):
        if self.os_hint != 'None':
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
        else:
            if not self.GenLinuxDts:
                self.CortexA72Linux()
            self.CortexA72Baremetal()
            self.CortexA72FreeRtos()

    def ArmCortexR5Setup(self):
        if self.os_hint != 'None':
            if self.os_hint.startswith('baremetal'):
                self.CortexR5Baremetal()
            elif self.os_hint.startswith('freertos'):
                self.CortexR5FreeRtos()
            else:
                self.CortexR5Baremetal()
        else:
            if self.args.soc_family == 'zynqmp' and not self.r5FsblDone:
                # We need a base CortexR5Baremetal for the FSBL for ZynqMP platform
                self.CortexR5Baremetal('fsbl')
            self.CortexR5Baremetal()
            self.CortexR5FreeRtos()

    def MicroblazeSetup(self):
        self.MBTuneFeatures()
        if self.os_hint == 'None' or os_hint.startswith('baremetal'):
            logger.warning(
                'Microblaze for Baremetal %s not yet implemented' % self.domain)
        elif self.os_hint == 'Linux':
            logger.warning(
                'Microblaze for Linux %s not yet implemented' % self.domain)
        else:
            logger.warning('Microblaze for unknown OS (%s), not yet implemented. %s' % (
                self.os_hint, self.domain))

    def ParseCpuDict(self):
        for cpuname in self.cpu_info_dict.keys():
            self.cpuname = cpuname
            self.cpu, self.core, self.domain, self.os_hint = (
                self.cpu_info_dict[self.cpuname].get(v) for v in (
                    'cpu', 'core', 'domain', 'os_hint'))
            if self.cpu == 'arm,cortex-a53':
                self.ArmCortexA53Setup()
            elif self.cpu == 'arm,cortex-a72':
                self.ArmCortexA72Setup()
            elif self.cpu == 'arm,cortex-r5':
                self.ArmCortexR5Setup()
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
        # Return list of conf files if files_only True
        if self.ReturnConfFiles:
            return self.MultiConfFiles, self.MultiConfMin
        # MultiConfDict will have the configuration info
        # to create machine and local.conf files
        return self.MultiConfDict

    def __init__(self, args, cpu_info_dict, file_names_only=False):
        self.a53FsblDone = self.r5FsblDone = False
        self.MBTunesDone = self.GenLinuxDts = False
        self.MultiConfFiles = []
        self.MultiConfMin = []
        self.MultiConfDict = {}
        self.cpu_info_dict = cpu_info_dict
        self.args = args
        # self.Retur.nConfFiles if true returns the file names which is required
        # to create Kconfig
        self.ReturnConfFiles = file_names_only
