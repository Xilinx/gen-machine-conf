#!/usr/bin/env python3

# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

from gen_config import *


def expand_mirrors(mirror_url):
    urls = '\\\n'
    urls += '\tcvs://.*/.*     %s \\\n' % mirror_url
    urls += '\tsvn://.*/.*     %s \\\n' % mirror_url
    urls += '\tgit://.*/.*     %s \\\n' % mirror_url
    urls += '\tgitsm://.*/.*   %s \\\n' % mirror_url
    urls += '\thg://.*/.*      %s \\\n' % mirror_url
    urls += '\tbzr://.*/.*     %s \\\n' % mirror_url
    urls += '\tp4://.*/.*      %s \\\n' % mirror_url
    urls += '\tosc://.*/.*     %s \\\n' % mirror_url
    urls += '\thttps?://.*/.*  %s \\\n' % mirror_url
    urls += '\tftp://.*/.*     %s \\\n' % mirror_url
    urls += '\tnpm://.*/?.*    %s \\\n' % mirror_url
    urls += '\ts3://.*/.*      %s \\\n' % mirror_url
    urls += '\tcrate://.*/.*   %s \\\n' % mirror_url
    return urls


def generate_siteconf(args, arch, xilinx_network):
    if xilinx_network and 'PETALINUX' in os.environ.keys():
        site_conf_path = os.path.join(args.output, 'site.conf')
        buildfile_path = os.path.realpath(os.path.join(
            os.environ['PETALINUX'], '../../commitids/dep.conf'))
        sstate_path = ''
        downloads_path = ''
        if os.path.exists(buildfile_path):
            with open(buildfile_path, 'r') as buildfile_path_f:
                lines = buildfile_path_f.readlines()
            buildfile_path_f.close()
            for line in lines:
                if re.search('^sstate_path', line):
                    sstate_path = line.split(':')[1]
                elif re.search('^downloads_path', line):
                    downloads_path = line.split(':')[1]

        siteconf_string = ''
        if sstate_path and downloads_path:
            siteconf_string += 'SSTATE_MIRRORS:prepend = " \\\n'
            siteconf_string += '\tfile://.* file://%s/PATH \\n \\\n' % (
                os.path.join(sstate_path.strip(), arch))
            if 'XILINX_INT_SSTATES' in os.environ.keys():
                siteconf_string += '\tfile://.* %s/PATH \\n"\n' % (
                    os.path.join(os.environ['XILINX_INT_SSTATES'], arch))
            siteconf_string += 'SOURCE_MIRROR_URL = "file://%s"\n' % downloads_path.strip()
            if 'XILINX_INT_DOWNLOADS' in os.environ.keys():
                siteconf_string += 'PREMIRRORS:prepend = "%s"\n' % expand_mirrors(
                    os.environ['XILINX_INT_DOWNLOADS'])
        else:
            if 'XILINX_INT_SSTATES' in os.environ.keys():
                siteconf_string += 'SSTATE_MIRRORS:prepend = "file://.* file://%s/PATH \\n"\n' % (
                    os.path.join(os.environ['XILINX_INT_SSTATES'], arch))
            if 'XILINX_INT_DOWNLOADS' in os.environ.keys():
                siteconf_string += 'SOURCE_MIRROR_URL = "file://%s"\n' % os.environ['XILINX_INT_DOWNLOADS']

        if siteconf_string:
            with open(site_conf_path, 'w') as site_conf_f:
                site_conf_f.write(siteconf_string)
            site_conf_f.close()


def generate_mirrors(args, arch):
    nslookup_exe = shutil.which('nslookup')
    default_cfgfile = os.path.join(args.output, 'config')
    if not nslookup_exe or not 'XILINX_INT_SITE' in os.environ.keys():
        xilinx_network = False
    else:
        cmd = 'nslookup -timeout=10 %s | grep "Address" | \
                awk \'{print $2}\' | sed -n 2p' % os.environ['XILINX_INT_SITE']
        stdout, stderr = run_cmd(cmd, args.output, args.logfile, shell=True)
        xilinx_network = False
        if stdout:
            xilinx_network = True
    mirrors_string = ''
    pre_mirror_url = get_config_value(
        'CONFIG_PRE_MIRROR_URL', default_cfgfile)
    if 'PETALINUX_MAJOR_VER' in os.environ.keys():
        plnx_major_ver = os.environ['PETALINUX_MAJOR_VER']
    else:
        plnx_major_ver = '2023'
    default_downloads_url = 'http://petalinux.xilinx.com/sswreleases/rel-v%s/downloads' % (
        plnx_major_ver)
    # Add Download mirrors
    if pre_mirror_url != default_downloads_url:
        # if user configured different premirrors than default
        if not xilinx_network:
            mirrors_string += 'SOURCE_MIRROR_URL = "%s"\n' % pre_mirror_url
            # Add Pre-mirrors from petalinux.xilinx.com
            # if user configured different downloads'
            mirrors_string += 'PREMIRRORS = "%s"\n' % expand_mirrors(
                default_downloads_url)
        else:
            mirrors_string += '# Add Pre-mirrors from config\n'
            mirrors_string += 'PREMIRRORS = "%s"\n' % expand_mirrors(
                pre_mirror_url)
            # Add Pre-mirrors from petalinux.xilinx.com
            # if user configured different downloads'
            mirrors_string += 'PREMIRRORS:append = "%s"\n' % expand_mirrors(
                default_downloads_url)
    else:
        if not xilinx_network:
            mirrrs_string += 'SOURCE_MIRROR_URL = "%s"\n' % pre_mirror_url
        else:
            mirrors_string += '# Add Pre-mirrors from config\n'
            mirrors_string += 'PREMIRRORS = "%s"\n' % expand_mirrors(
                pre_mirror_url)

    # Add SSTATE mirrors
    local_sstate_url = get_config_value(
        'CONFIG_YOCTO_LOCAL_SSTATE_FEEDS_URL', default_cfgfile)
    network_sstate = get_config_value(
        'CONFIG_YOCTO_NETWORK_SSTATE_FEEDS', default_cfgfile)
    network_sstate_url = get_config_value(
        'CONFIG_YOCTO_NETWORK_SSTATE_FEEDS_URL', default_cfgfile)
    if local_sstate_url:
        local_sstate_url = '\tfile://.* file://%s/PATH \\\n' % local_sstate_url
    else:
        local_sstate_url = ''

    if network_sstate == "y" and network_sstate_url:
        network_sstate_url = '\tfile://.* %s/PATH;downloadfilename=PATH \\n \\\n' % network_sstate_url
    else:
        local_sstate_url = ''

    mirrors_string += '# Sstate mirror settings\n'
    mirrors_string += 'SSTATE_MIRRORS = " \\\n%s%s"\n' % (
        local_sstate_url, network_sstate_url)

    generate_siteconf(args, arch, xilinx_network)
    return mirrors_string
