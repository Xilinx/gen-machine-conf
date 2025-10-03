#!/usr/bin/env python3

# Copyright (C) 2023, Advanced Micro Devices, Inc.  All rights reserved.
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
import pathlib

logger = logging.getLogger('Gen-Machineconf')

class ParseMultiConfigFiles():
    def ArmCortexSetup(self):
        cpu = self.cpu[4:].replace('-', '')
        domain_suffix = '-%s' % self.domain if self.domain and self.domain != 'None' else ''
        if self.os_hint != 'None':
            if self.os_hint.startswith('linux'):
                # Linux is the default OS
                mc_name = ''
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : self.os_hint };
            else:
                mc_name = '%s-%s%s-%s' % (cpu, self.core, domain_suffix, self.os_hint)
                self.MultiConfFiles.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : self.os_hint };
        else:
            # Default Cortex-A is Linux
            if self.cpu.startswith('arm,cortex-a') and self.core == '0':
                mc_name = ''
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : 'linux' };

            # Do we need an FSBL?
            if self.args.soc_family in [ 'zynq', 'zynqmp' ] and self.cpu in [ 'arm,cortex-a9', 'arm,cortex-a53', 'arm,cortex-r5' ] and self.core == '0':
                mc_name = '%s-fsbl' % cpu
                self.MultiConfFiles.append(mc_name)
                # Only the cortex-a is the default FSBL
                if self.cpu in [ 'arm,cortex-a9', 'arm,cortex-a53' ]:
                    self.MultiConfMin.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : 'fsbl' };

            # Iterate over the non-Linux OSes
            NonLinuxOS = [ 'baremetal', 'freertos' ]
            if self.cpu in ['arm,cortex-r52', 'arm,cortex-a78']:
                NonLinuxOS.append('zephyr')
            for os_hint in NonLinuxOS:
                mc_name = '%s-%s%s-%s' % (cpu, self.core, domain_suffix, os_hint)
                self.MultiConfFiles.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : os_hint };

    def MicroblazeSetup(self):
        logger.warn('Microblaze configuration detected, this is not supported.')
        # Do nothing, this is presumed to be Linux
        pass

    def MicroblazeVSetup(self):
        cpu = self.cpu.replace('xlnx,','')
        if self.args.soc_family == 'microblaze':
            mc_name = ''
            os_hint = 'linux'
            self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : os_hint};
        # For Mb-v add zephyr as default MC
        os_hint = 'zephyr'
        mc_name = '%s-%s-%s' % (cpu, self.core, os_hint)
        self.MultiConfFiles.append(mc_name)
        self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : os_hint};

    def ParseCpuDict(self):
        for cpuname in self.cpu_info_dict.keys():
            self.cpuname = cpuname
            self.cpu, self.core, self.domain, self.os_hint = (
                self.cpu_info_dict[self.cpuname].get(v) for v in (
                    'cpu', 'core', 'domain', 'os_hint'))
            if self.cpu.startswith('arm,cortex'):
                self.ArmCortexSetup()
            elif self.cpu == 'xlnx,microblaze':
                self.MicroblazeSetup()
            elif self.cpu.startswith('xlnx,microblaze-riscv'):
                self.MicroblazeVSetup()
            elif self.cpu == 'pmu-microblaze':
                mc_name = 'microblaze-pmu'
                self.MultiConfFiles.append(mc_name)
                self.MultiConfMin.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : self.os_hint };
            elif self.cpu == 'pmc-microblaze':
                mc_name = 'microblaze-pmc'
                self.MultiConfFiles.append(mc_name)
                self.MultiConfMin.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : self.os_hint };
            elif self.cpu == 'psm-microblaze':
                mc_name = 'microblaze-psm'
                self.MultiConfFiles.append(mc_name)
                self.MultiConfMin.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : self.os_hint };
            elif self.cpu == 'xlnx,asu-microblaze_riscv':
                mc_name = 'microblaze-riscv-asu'
                self.MultiConfFiles.append(mc_name)
                self.MultiConfMin.append(mc_name)
                self.MultiConfMap[mc_name] = { 'cpuname' : self.cpuname, 'cpu' : self.cpu, 'core' : self.core, 'domain' : self.domain, 'os_hint' : self.os_hint };
            else:
                logger.warning('Unknown CPU %s' % self.cpu)
        # Return list of conf files if files_only True
        return self.MultiConfFiles, self.MultiConfMin

    def __init__(self, args, cpu_info_dict):
        self.MultiConfFiles = []
        self.MultiConfMin = []
        self.MultiConfMap = {}
        self.cpu_info_dict = cpu_info_dict
        self.args = args

class GenerateMultiConfigFiles():
    def ZephyrConfigurations(self, mc_target):
        ZephyrDict = {
            'microblaze' : { 'board' : 'mbv32' },
            'versal-net' : { 'board' : 'versalnet_rpu'},
            'versal-2ve-2vm' : { 'board' : 'versal2_rpu'}
            }
        distro = 'amd-zephyr'
        ZephyrVars = '# Zephyr RTOS settings.\n'
        board = ''
        if ZephyrDict.get(mc_target):
            board = ZephyrDict[mc_target].get('board', '')
        if board:
            ZephyrVars += 'ZEPHYR_BOARD = "%s"\n' % board
        return distro, ZephyrVars

    def GenerateMultiConfigs(self):
        tuneDict = { 'arm,cortex-a9'  : 'cortexa9',
                     'arm,cortex-a53' : 'cortexa53',
                     'arm,cortex-a72' : 'cortexa72',
                     'arm,cortex-a78' : 'cortexa72',
                     'arm,cortex-r5'  : 'cortexr5',
                     'arm,cortex-r52' : 'cortexr52',
                     'pmu-microblaze' : 'microblaze-pmu',
                     'pmc-microblaze' : 'microblaze-pmc',
                     'psm-microblaze' : 'microblaze-psm',
                     'xlnx,microblaze-riscv-1.0' : 'riscv32',
                     'xlnx,asu-microblaze_riscv' : 'microblaze-riscv-asu' }

        if not self.MultiConfUser or not self.MultiConfMap:
            logger.debug("No multilibs enabled.")
            return self.MultiConfDict

        bbmulticonfig = []
        for mc_name in self.MultiConfUser:
            if mc_name not in self.MultiConfMap:
                logger.error("Unable to find selected multiconfig (%s)" % mc_name)
            else:
                if mc_name == "":
                    # Generate files here, if needed
                    pass
                else:
                    mc_filename = self.args.machine + '-' + mc_name

                    cpu = self.MultiConfMap[mc_name]['cpu']
                    defaulttune = cpu
                    if cpu in tuneDict:
                       defaulttune = tuneDict[cpu]

                    distro = self.MultiConfMap[mc_name]['os_hint']
                    McExtraVars = ''
                    if cpu == 'pmu-microblaze':
                        self.MultiConfDict['PmuTune'] = defaulttune
                        self.MultiConfDict['PmuMcDepends'] = 'mc::%s:pmu-firmware:do_deploy' % mc_filename
                        self.MultiConfDict['PmuFWDeployDir'] = '${TMPDIR}-%s/deploy/images/${MACHINE}' % mc_filename
                        distro = 'xilinx-standalone'
                    elif cpu == 'pmc-microblaze':
                        self.MultiConfDict['PlmTune'] = defaulttune
                        self.MultiConfDict['PlmMcDepends'] = 'mc::%s:plm-firmware:do_deploy' % mc_filename
                        self.MultiConfDict['PlmDeployDir'] = '${TMPDIR}-%s/deploy/images/${MACHINE}' % mc_filename
                        distro = 'xilinx-standalone'
                    elif cpu == 'psm-microblaze':
                        self.MultiConfDict['PsmTune'] = defaulttune
                        self.MultiConfDict['PsmMcDepends'] = 'mc::%s:psm-firmware:do_deploy' % mc_filename
                        self.MultiConfDict['PsmFWDeployDir'] = '${TMPDIR}-%s/deploy/images/${MACHINE}' % mc_filename
                        distro = 'xilinx-standalone-nolto'
                    elif cpu == 'xlnx,asu-microblaze_riscv':
                        self.MultiConfDict['AsuTune'] = defaulttune
                        self.MultiConfDict['AsuMcDepends'] = 'mc::%s:asu-firmware:do_deploy' % mc_filename
                        self.MultiConfDict['AsuFWDeployDir'] = '${TMPDIR}-%s/deploy/images/${MACHINE}' % mc_filename
                        distro = 'xilinx-standalone-nolto'

                    if distro == 'fsbl':
                        if cpu in [ 'arm,cortex-a9', 'arm,cortex-a53' ]:
                            self.MultiConfDict['FsblMcDepends'] = 'mc::%s:fsbl-firmware:do_deploy' % mc_filename
                            self.MultiConfDict['FsblDeployDir'] = '${TMPDIR}-%s/deploy/images/${MACHINE}' % mc_filename
                        elif cpu in [ 'arm,cortex-r5' ]:
                            self.MultiConfDict['R5FsblMcDepends'] = 'mc::%s:fsbl-firmware:do_deploy' % mc_filename
                            self.MultiConfDict['R5FsblDeployDir'] = '${TMPDIR}-%s/deploy/images/${MACHINE}' % mc_filename
                        else:
                            logger.error('Unknown FSBL CPU type %s' % cpu)
                        distro = 'xilinx-standalone'
                    elif distro.startswith('baremetal'):
                        lto = '-nolto' if 'domain' not in self.MultiConfMap[mc_name] or self.MultiConfMap[mc_name]['domain'] == 'None' else ''
                        distro = 'xilinx-standalone%s' % lto
                    elif distro.startswith('freertos'):
                        distro = 'xilinx-freertos'
                    elif distro.startswith('zephyr'):
                        mc_target = self.args.soc_family
                        if self.args.soc_family == 'versal' and self.args.soc_variant == 'net':
                            mc_target += '-net'
                        if cpu.startswith('xlnx,microblaze-riscv'):
                            McExtraVars += '#Risc-V Tune features\n'
                            McExtraVars += 'require conf/machine/include/riscv/tune-riscv.inc\n'
                            mc_target = 'microblaze'
                        distro, ExtraVars = self.ZephyrConfigurations(mc_target)
                        McExtraVars += ExtraVars

                    bbmulticonfig.append(mc_filename)
                    conf_file = os.path.join(self.args.config_dir, 'multiconfig', mc_filename + '.conf')
                    with open(conf_file, 'w') as file_f:
                        if McExtraVars:
                            file_f.write(McExtraVars)
                        file_f.write('TMPDIR .= "-${BB_CURRENT_MC}"\n')
                        file_f.write('\n')
                        file_f.write('DISTRO = "%s"\n' % distro)
                        file_f.write('DEFAULTTUNE = "%s"\n' % defaulttune)

        self.MultiConfDict['BBMULTICONFIG'] = ' '.join(bbmulticonfig)

        return self.MultiConfDict

    def __init__(self, args, multi_conf_map, system_conffile=''):
        self.MBTunesDone = self.GenLinuxDts = False
        self.MultiConfFiles = []
        self.MultiConfMin = []
        self.MultiConfMap = multi_conf_map
        self.MultiConfUser = []
        self.MultiConfDict = {}
        self.args = args
        self.system_conffile = system_conffile

        # Get the BBMC targets from system config file and generate
        # multiconfig targets only for enabled
        self.MultiConfUser = common_utils.GetConfigValue(
                                        'CONFIG_YOCTO_BBMC_', system_conffile,
                                        'choicelist', '=y').lower().replace('_', '-')
        self.MultiConfUser = list(self.MultiConfUser.split(' '))
