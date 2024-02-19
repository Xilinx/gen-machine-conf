#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import os
import re
import shutil
import common_utils
import logging

logger = logging.getLogger('Gen-Machineconf')


def SearchStrInFile(filename, string, remove_if_exists=False):
    with open(filename, 'r') as filename_f:
        lines = filename_f.readlines()
    filename_f.close()
    str_found = ''
    lines_f = []
    for line in lines:
        _line = line.replace('\\', '').strip()
        if re.search(string, _line):
            str_found = True
            continue
        lines_f.append(line)
    if str_found and remove_if_exists:
        with open(filename, 'w') as file_f:
            file_f.writelines(lines_f)
    return str_found


def AddUserLayers(args):
    bb_layers = []
    proot = ''
    builddir = ''
    system_conffile = os.path.join(args.output, 'config')

    # Return if sysconf doesnot modified
    bitbake_layers = common_utils.check_tool('bitbake-layers')
    builddir = os.environ.get('BUILDDIR')

    if not bitbake_layers or not builddir or not \
            'UPDATE_USER_LAYERS' in os.environ.keys():
        logger.debug(
            'Skip adding layers as no bitbake-layers or builddir found')
        return
    layers_list = '%s/conf/layerslist' % builddir
    old_layers = []
    if os.path.exists(layers_list):
        with open(layers_list, 'r') as layers_list_f:
            old_layers = layers_list_f.read().splitlines()

    proot = os.environ.get('PROOT')
    if proot and args.petalinux:
        bb_layers += os.path.join(proot, 'project-spec', 'meta-user').split()

    layer_cnt = 0
    while True:
        # Read layers from configs
        user_layer = common_utils.GetConfigValue(
            'CONFIG_USER_LAYER_%s' % layer_cnt, system_conffile)
        if not user_layer:
            break
        if proot:
            user_layer = user_layer.replace('${PROOT}', proot)
        bb_layers += user_layer.split()
        layer_cnt += 1

    # Get the layers which to be add
    add_layers = list(set(bb_layers).difference(old_layers))
    # Get the layers which to be removed
    remove_layers = list(set(old_layers).difference(bb_layers))

    if add_layers:
        logger.info('Adding user layers')
    with open(layers_list, 'a') as layers_list_f:
        for layer in add_layers:
            if os.path.isdir(layer):
                common_utils.ShutdownBitbake()
                logger.debug('Adding layer: %s' % layer)
                command = 'bitbake-layers -F add-layer %s' % (layer)
                common_utils.RunCmd(command, builddir, shell=True)
                layers_list_f.write(layer + '\n')

    for layer in remove_layers:
        cmd = 'sed -i "\|%s|d"  "%s"' % (layer, layers_list)
        common_utils.RunCmd(cmd, os.getcwd(), shell=True)
        cmd = 'sed -i "\|%s|d"  "%s/conf/bblayers.conf"' % (layer, builddir)
        common_utils.RunCmd(cmd, os.getcwd(), shell=True)


def GenLocalConf(conf_file, machine_conf_file, multiconfigs_full, system_conffile, petalinux):
    sdt_conf_str  = '# Use the newly generated MACHINE\n'
    sdt_conf_str += 'MACHINE = "%s"\n' % machine_conf_file

    multiconfig_min = common_utils.GetConfigValue('CONFIG_YOCTO_BBMC_', system_conffile,
                                                  'choicelist', '=y').lower().replace('_', '-')
    if multiconfig_min:
        sdt_conf_str += '\n# Avoid errors in some baremetal configs as these layers may be present\n'
        sdt_conf_str += '# but are not used.  Note the following lines are optional and can be\n'
        sdt_conf_str += '# safetly disabled.\n'
        sdt_conf_str += 'SKIP_META_VIRT_SANITY_CHECK = "1"\n'
        sdt_conf_str += 'SKIP_META_SECURITY_SANITY_CHECK = "1"\n'
        sdt_conf_str += 'SKIP_META_TPM_SANITY_CHECK = "1"\n'

        sdt_conf_str += '\n# Each multiconfig will define it\'s own TMPDIR, this is the new default based\n'
        sdt_conf_str += '# on BASE_TMPDIR for the Linux build\n'
        sdt_conf_str += 'TMPDIR = "${BASE_TMPDIR}/tmp"\n'

        sdt_conf_str += '\n# All of the TMPDIRs must be in a common parent directory. This is defined\n'
        sdt_conf_str += '# as BASE_TMPDIR.\n'
        sdt_conf_str += '# Adjust BASE_TMPDIR if you want to move the tmpdirs elsewhere, such as /tmp\n'
        sdt_conf_str += 'BASE_TMPDIR ?= "${TOPDIR}"\n'

        sdt_conf_str += '\n# The following is the full set of multiconfigs for this configuration\n'
        if multiconfigs_full:
            sdt_conf_str += '# A large list can cause a slow parse.\n'
            sdt_conf_str += '#BBMULTICONFIG ?= "%s"\n' % (' '.join(multiconfigs_full))
        sdt_conf_str += '# Alternatively trim the list to the minimum\n'
        sdt_conf_str += 'BBMULTICONFIG = "%s"\n' % multiconfig_min

    if not conf_file:
        logger.note('To enable this, add the following to your local.conf:\n')
        logger.plain(sdt_conf_str)
    else:
        if not petalinux:
            logger.note('Configuration for local.conf written to %s' %
                        conf_file)
            logger.debug(sdt_conf_str)
        common_utils.CreateFile(conf_file)
        common_utils.AddStrToFile(conf_file, sdt_conf_str, 'a+')


def UpdateLocalConf(args, plnx_conf_file, machine_conf_file):
    builddir = ''
    hw_flow = args.hw_flow

    if 'BUILDDIR' in os.environ.keys():
        builddir = os.environ['BUILDDIR']
    if builddir:
        local_conf = os.path.join(builddir, 'conf', 'local.conf')
        if not os.path.isfile(local_conf):
            logger.debug('No local.conf file found in %s/conf directory to add .conf'
                         ' file' % builddir)
        else:
            # Check if the build/xsa directory exist or not.
            # Copy XSA from HDF_PATH to ${TOPDIR}/xsa/machine_conf_file
            # directory if not --petalinux
            if not args.petalinux and hw_flow == 'xsct':
                xsapath = os.path.join(builddir, 'xsa', machine_conf_file)
                common_utils.CreateDir(xsapath)
                common_utils.CopyFile(args.hw_file, xsapath)

            localconf_strs = []
            if hw_flow == 'sdt':
                localconf_strs += ['include conf/sdt-auto.conf']
            if args.petalinux:
                conf_dir = os.path.join(builddir, 'conf')
                # Copy plnxtool.conf file to ${TOPDIR}/conf directory
                localconf_strs += ['include conf/plnxtool.conf']
            for file_str in localconf_strs:
                SearchStrInFile(local_conf, file_str, remove_if_exists=True)
                with open(local_conf, 'a') as local_conf_f:
                    local_conf_f.write(file_str + '\n')
                local_conf_f.close()
