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
import project_config
import post_process_config
import rootfs_config
import subprocess
import multiconfigs
import kconfig_syshw

logger = logging.getLogger('Gen-Machineconf')

class xsctGenerateMultiConfigFiles(multiconfigs.GenerateMultiConfigFiles):
    def MBTuneFeatures(self):
        if self.MBTunesDone:
            return
        logger.info('Generating microblaze processor tunes')

        SocTuneDict = {
              "zynqmp" : {
                           "microblaze-pmu" : "microblaze v9.2 barrel-shift pattern-compare reorder fpu-soft"
                         },
               "versal" : {
                           "microblaze-pmc" : "microblaze v10.0 barrel-shift pattern-compare reorder multiply-high divide-hard fpu-soft",
                           "microblaze-psm" : "microblaze v10.0 barrel-shift pattern-compare reorder multiply-high divide-hard fpu-soft"
                          },
               "versal-net" : {
                           "microblaze-pmc" : "microblaze v10.0 barrel-shift pattern-compare reorder multiply-high divide-hard fpu-soft",
                           "microblaze-psm" : "microblaze v10.0 barrel-shift pattern-compare reorder multiply-high divide-hard fpu-soft"
                              }
        }

        microblaze_inc_str = ""

        proc_type = self.args.soc_family
        for id in SocTuneDict.keys():
            if id == proc_type:
                for tune in SocTuneDict[id].keys():
                    microblaze_inc_str += 'AVAILTUNES += "%s"\n' % tune
                    microblaze_inc_str += 'TUNE_FEATURES:tune-%s = "%s"\n' % (tune, SocTuneDict[id][tune])
                    microblaze_inc_str += 'PACKAGE_EXTRA_ARCHS:tune-%s = "${TUNE_PKGARCH}"\n' % tune
                    microblaze_inc_str += '\n'

        if microblaze_inc_str:
            microblaze_inc_str += 'require conf/machine/include/xilinx-microblaze.inc\n'

            microblaze_inc = os.path.join(self.args.bbconf_dir, 'microblaze.inc')
            with open(microblaze_inc, 'w') as file_f:
                file_f.write(microblaze_inc_str)

        self.MBTunesDone = True

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

                if self.cpu == 'xlnx,microblaze':
                    self.MBTuneFeatures()
                elif self.cpu == 'pmu-microblaze':
                    self.MBTuneFeatures()
                elif self.cpu == 'pmc-microblaze':
                    self.MBTuneFeatures()
                elif self.cpu == 'psm-microblaze':
                    self.MBTuneFeatures()

    def GenerateMultiConfigs(self):
        multiconfigs.GenerateMultiConfigFiles.GenerateMultiConfigs(self)

        self.ParseCpuDict()

        return self.MultiConfDict

    def __init__(self, args, multi_conf_map, system_conffile=''):
        self.MBTunesDone = False

        multiconfigs.GenerateMultiConfigFiles.__init__(self, args, multi_conf_map, system_conffile=system_conffile)


def AddXsctUtilsPath(xsct_tool):
    if xsct_tool:
        if not os.path.isdir(xsct_tool):
            raise Exception('XSCT_TOOL path not found: %s' % xsct_tool)
        else:
            os.environ["PATH"] += os.pathsep + os.path.join(xsct_tool, 'bin')
    else:
        try:
            xilinx_xsct_tool = common_utils.Bitbake.getVar('XILINX_SDK_TOOLCHAIN')
        except KeyError:
            raise Exception('Unable to get XILINX_SDK_TOOLCHAIN path, please verify meta-xilinx-tools layer is available.')

        if xilinx_xsct_tool and not os.path.isdir(xilinx_xsct_tool):
            logger.info('Installing xsct...')
            common_utils.Bitbake.runBitbakeCmd('xsct-native')

        if xilinx_xsct_tool and not os.path.isdir(xilinx_xsct_tool):
            raise Exception('Looking for xsct in "%s" but the path does not exist. '
                         'Use --xsct-tool option to specify the SDK_XSCT path' % xilinx_xsct_tool)
        elif xilinx_xsct_tool:
            os.environ["PATH"] += os.pathsep + xilinx_xsct_tool + '/bin'

    # XSCT can only be extracted if we've enabled XSCT
    xsct_exe = common_utils.check_tool('xsct', 'xsct-native', 'xsct command not found, use --xsct-tool option to specify path')
    logger.debug('Using xsct from : %s' % xsct_exe)


def GetSocInfo(hw_file):
    genmachine_scripts = project_config.GenMachineScriptsPath()
    cmd = 'xsct -sdx -nodisp %s get_soc_info %s' % \
        (os.path.join(genmachine_scripts, 'hw-description.tcl'),
         hw_file)

    stdout, stderr = common_utils.RunCmd(cmd, os.getcwd(), shell=True)
    proc_type = ''
    for line in stdout.splitlines():
        try:
            line = line.decode('utf-8')
        except AttributeError:
            pass
        if re.search('{.+proc_name.+}', line):
            import json
            line_dict = json.loads(line)
            proc_type = line_dict['proc_name']
    return proc_type


def GenXsctSystemHwFile(genmachine_scripts,
                        Kconfig_syshw, hw_file, output):
    ipinfo_schema = os.path.join(
        genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(output, 'plnx_syshw_data')

    logger.info('Generating Kconfig for project')
    cmd = 'xsct -sdx -nodisp %s/hw-description.tcl plnx_gen_hwsysconf %s' % \
        (genmachine_scripts, hw_file)
    logger.debug('Generating System HW file')
    common_utils.RunCmd(cmd, output, shell=True)
    kconfig_syshw.GenKconfigSysHW(plnx_syshw_file, ipinfo_schema, Kconfig_syshw)
    if not os.path.exists(Kconfig_syshw):
        raise Exception('Failed to Generate Kconfig_syshw File')


def GetFlashInfo(genmachine_scripts, output, system_conffile, hw_file):
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    flashinfo_file = os.path.join(output, 'flash_parts.txt')
    # No need to run if system conf file(config) is doesnot change
    if common_utils.ValidateHashFile(output, 'SYSTEM_CONF', system_conffile, update=False) and \
            os.path.exists(flashinfo_file):
        return 0

    with open(flashinfo_file, 'w') as fp:
        pass
    cmd = 'xsct -sdx -nodisp %s get_flash_width_parts %s %s %s %s' % \
        (os.path.join(genmachine_scripts, 'petalinux_hsm.tcl'),
         system_conffile, ipinfo_file, hw_file,
         flashinfo_file)
    common_utils.RunCmd(cmd, output, shell=True)

# Mapping of DeviceId to CPU Dictionary
SocCpuDict = {
    'microblaze' : {
                 'microblaze'      : { 'cpu' : 'xlnx,microblaze', 'core': '0', 'domain': 'None', 'os_hint' : 'linux' }
                   },
    'zynq':    {
                 'ps7_cortexa9'    : { 'cpu' : 'arm,cortex-a9',   'core': '0', 'domain': 'None', 'os_hint' : 'None' }
               },
    'zynqmp' : {
                 'psu_cortexa53_0' : { 'cpu' : 'arm,cortex-a53',  'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psu_cortexa53_1' : { 'cpu' : 'arm,cortex-a53',  'core': '1', 'domain': 'None', 'os_hint' : 'None' },
                 'psu_cortexa53_2' : { 'cpu' : 'arm,cortex-a53',  'core': '2', 'domain': 'None', 'os_hint' : 'None' },
                 'psu_cortexa53_3' : { 'cpu' : 'arm,cortex-a53',  'core': '3', 'domain': 'None', 'os_hint' : 'None' },
                 'psu_cortexr5_0'  : { 'cpu' : 'arm,cortex-r5',   'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psu_cortexr5_1'  : { 'cpu' : 'arm,cortex-r5',   'core': '1', 'domain': 'None', 'os_hint' : 'None' },
                 'psu_pmu_0'       : { 'cpu' : 'pmu-microblaze',  'core': '0', 'domain': 'None', 'os_hint' : 'None' }
               },
    'versal' : {
                 'psv_cortexa72_0' : { 'cpu' : 'arm,cortex-a72',  'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexa72_1' : { 'cpu' : 'arm,cortex-a72',  'core': '1', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexa72_2' : { 'cpu' : 'arm,cortex-a72',  'core': '2', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexa72_3' : { 'cpu' : 'arm,cortex-a72',  'core': '3', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexr5_0'  : { 'cpu' : 'arm,cortex-r5',   'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexr5_1'  : { 'cpu' : 'arm,cortex-r5',   'core': '1', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_pmc_0'       : { 'cpu' : 'pmc-microblaze',  'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_psm_0'       : { 'cpu' : 'psm-microblaze',  'core': '0', 'domain': 'None', 'os_hint' : 'None' }
               },
    'versal-net': {
                 'psx_cortexa78_0' : { 'cpu' : 'arm,cortex-a78',  'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexa78_1' : { 'cpu' : 'arm,cortex-a78',  'core': '1', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexa78_2' : { 'cpu' : 'arm,cortex-a78',  'core': '2', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexa78_3' : { 'cpu' : 'arm,cortex-a78',  'core': '3', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexr52_0' : { 'cpu' : 'arm,cortex-r52',  'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_cortexr52_1' : { 'cpu' : 'arm,cortex-r52',  'core': '1', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_pmc_0'       : { 'cpu' : 'pmc-microblaze',  'core': '0', 'domain': 'None', 'os_hint' : 'None' },
                 'psv_psm_0'       : { 'cpu' : 'psm-microblaze',  'core': '0', 'domain': 'None', 'os_hint' : 'None' }
               },
    }

def ParseXsa(args):
    if args.hw_flow == 'sdt':
        raise Exception('Invalide HW source Specified for XSCT Flow.')

    if not 'PETALINUX' in os.environ.keys() and \
       not common_utils.Bitbake.disabled and common_utils.Bitbake.getVar('XILINX_WITH_ESW') != 'xsct':
        logger.debug('XILINX_WITH_ESW = %s' % common_utils.Bitbake.getVar('XILINX_WITH_ESW'))
        common_utils.Bitbake.prepare(prefile=[os.path.join(os.path.dirname(__file__),'../../gen-machine-scripts/data/yocto_esw_xsct.conf')])
        logger.debug('XILINX_WITH_ESW = %s' % common_utils.Bitbake.getVar('XILINX_WITH_ESW'))
        if common_utils.Bitbake.getVar('XILINX_WITH_ESW') != 'xsct':
            raise Exception('XILINX_WITH_ESW must be set to "xsct".  Add the following to your local.conf file: XILINX_WITH_ESW = "xsct"')

    def LookupCpuInfoFromSocFam(proc_type):
        for id in SocCpuDict.keys():
            if id == proc_type:
                return SocCpuDict[id]
        logger.error('Unable to find proc_type %s' % proc_type)
        return {}

    def gatherHWInfo(args):
        nonlocal Kconfig_syshw
        nonlocal plnx_syshw_file
        nonlocal project_cfgdir
        nonlocal genmachine_scripts

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

        # Generate Kconfig.syshw only when hw_file changes
        if not common_utils.ValidateHashFile(args.output, 'HW_FILE', args.hw_file, update=False) or \
            not os.path.exists(Kconfig_syshw):

            if not args.soc_family:
                hw_info['proc_type'] = GetSocInfo(args.hw_file)
                hw_info['soc_family'] = project_config.DetectSocFamily(hw_info['proc_type'])

            template_cfgfile = os.path.join(
                genmachine_scripts, 'configs', 'config_%s' % hw_info['soc_family'])

            if not os.path.isfile(template_cfgfile):
                raise Exception('Unsupported soc_family: %s' % hw_info['soc_family'])

            GenXsctSystemHwFile(genmachine_scripts, Kconfig_syshw,
                                args.hw_file, args.output)

        import yaml

        with open(plnx_syshw_file, 'r') as fp:
            syshw_data = yaml.safe_load(fp)

        if 'machine' not in hw_info:
            hw_info['machine'] = None

        hw_info['device_id'] = syshw_data['device_id']

        hw_info['model'] = ''

        processor = syshw_data['processor']
        if 'proc_type' not in hw_info:
            hw_info['proc_type'] = processor[list(processor.keys())[0]]['ip_name']
        if 'soc_family' not in hw_info:
            hw_info['soc_family'] = project_config.DetectSocFamily(hw_info['proc_type'])
        if 'soc_variant' not in hw_info:
            hw_info['soc_variant'] = project_config.DetectSocVariant(hw_info['device_id'])

        # Generate CPU list
        if hasattr(args, 'multiconfigenable') and args.multiconfigenable:
            hw_info['cpu_info_dict'] = LookupCpuInfoFromSocFam(hw_info['soc_family'])
        else:
            hw_info['cpu_info_dict'] = {}

        return hw_info


    #### Setup:

    AddXsctUtilsPath(args.xsct_tool)

    genmachine_scripts = project_config.GenMachineScriptsPath()

    project_cfgdir = os.path.join(args.output, 'configs')
    common_utils.CreateDir(project_cfgdir)

    Kconfig_syshw = os.path.join(project_cfgdir, 'Kconfig.syshw')
    Kconfig = os.path.join(project_cfgdir, 'Kconfig')
    ipinfo_file = os.path.join(genmachine_scripts, 'data', 'ipinfo.yaml')
    plnx_syshw_file = os.path.join(args.output, 'plnx_syshw_data')
    system_conffile = os.path.join(args.output, 'config')


    #### Gather:
    hw_info = gatherHWInfo(args)

    if hw_info['machine']:
        args.machine = hw_info['machine']
    args.soc_family = hw_info['soc_family']
    args.soc_variant = hw_info['soc_variant']

    #### Generate Kconfig:
    project_config.GenKconfigProj(args, system_conffile, hw_info)

    project_config.PrintSystemConfiguration(args, None, hw_info['device_id'], None)

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

    if args.petalinux:
        GetFlashInfo(genmachine_scripts, args.output,
                     system_conffile, args.hw_file)
        rootfs_config.GenRootfsConfig(args, system_conffile)

    #### Generate the configuration:
    MCObject = xsctGenerateMultiConfigFiles(args, hw_info['multiconfigs'], system_conffile=system_conffile)

    project_config.GenerateConfiguration(args, hw_info,
                                         system_conffile,
                                         plnx_syshw_file,
                                         MCObject=MCObject)

def register_commands(subparsers):
    parser_xsa = subparsers.add_parser('parse-xsa',
                                       help='Parse xsa file and generate Yocto/PetaLinux configurations.',
                                       usage='%(prog)s [--hw-description'
                                       ' <PATH_TO_XSA>/<xsa_name>.xsa] [other options]'
                                       )
    parser_xsa.add_argument('--xsct-tool', metavar='[XSCT_TOOL_PATH]',
                            default=common_utils.AddYamlDefaultValues('--xsct-tool'),
                            help='Vivado or Vitis XSCT path to use xsct commands (Optional if you are already have AMD tools in your path)')

    parser_xsa.add_argument('-l', '--localconf', metavar='<config_file>',
                            default=common_utils.AddYamlDefaultValues(['-l', '--localconf']),
                            help='Write local.conf changes to this file', type=os.path.realpath)

    parser_xsa.add_argument('--multiconfigfull', action='store_true',
                            default=common_utils.AddYamlDefaultValues('--multiconfigfull'),
                            help='Generate/Enable Full set of multiconfig .conf and .dts files. Default is minimal')

    parser_xsa.add_argument('--multiconfigenable', action='store_true',
                            default=common_utils.AddYamlDefaultValues('--multiconfigenable'),
                            help='Enable multiconfig support. default is disabled.')

    parser_xsa.set_defaults(func=ParseXsa)
