# Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT
#
import sys
import os
import re
import getopt
import subprocess


def read_config(config_file):
    global Lines_config
    Lines_config = []
    with open(config_file, 'r') as fp:
        for line in fp:
            line = line.splitlines()
            Lines_config += [line]
    fp.closed


def read_packages(xilinx_arch):
    packages = {}
    packages['image_features'] = []
    for line in Lines_config:
        line_str = str(line)
        if re.search("#|\n", line_str):
            continue
        elif re.search("ADD_EXTRA_USERS", line_str):
            extra_users = line_str.split('=')[1]
            packages['extra_users'] = re.sub(
                r'"|\]|\\', r'', extra_users).rstrip("'")
        elif re.search("CREATE_NEW_GROUPS", line_str):
            new_groups = line_str.split('=')[1]
            packages['new_groups'] = re.sub(
                r'"|\]|\\', r'', new_groups).rstrip("'")
        elif re.search("ADD_USERS_TO_GROUPS", line_str):
            users_groups = line_str.split('=')[1]
            packages['users_groups'] = re.sub(
                r'"|\]|\\', r'', users_groups).rstrip("'")
        elif re.search("ADD_USERS_TO_SUDOERS", line_str):
            sudo_users = line_str.split('=')[1]
            packages['sudo_users'] = re.sub(
                r'"|\]|\\', r'', sudo_users).rstrip("'")
        elif re.search("package-feed-uris", line_str):
            package_feeds = line_str.split('=')[1]
            packages['package_feeds'] = re.sub(
                r'"|\]|\\', r'', package_feeds).rstrip("'").rstrip('/')
        elif re.search("package-feed-archs", line_str):
            package_feed_archs = line_str.split('=')[1]
            packages['package_feed_archs'] = re.sub(
                r'"|\]|\\', r'', package_feed_archs).rstrip("'")
        else:
            if re.search("=y'\]", line_str):
                line_str = line_str.split('_')[1]
                line_str = line_str.split('=')[0]
                line_str = fix_config_name(line_str)
                if re.search("inherit-", line_str):
                    line_str = line_str.replace('inherit-', '')
                    line_str = line_str.replace('-', '_')
                    packages.setdefault('inherit_packages',
                                        []).append(line_str)
                if re.search("imageclass-", line_str):
                    line_str = line_str.replace('imageclass-', '')
                    line_str = line_str.replace('-', '_')
                    packages.setdefault('image_classes', []).append(line_str)
                elif re.search("mali-backend-", line_str):
                    line_str = line_str.replace('mali-backend-', '')
                    packages['mali_backend'] = line_str
                elif re.search("Init-manager-", line_str):
                    line_str = line_str.replace('Init-manager-', '')
                    packages['Init_manager'] = line_str
                elif re.search("default-tune-", line_str):
                    line_str = line_str.replace('default-tune-', '')
                    packages['default_tune'] = line_str
                elif re.search("imagefeature-", line_str):
                    line_str = line_str.replace('imagefeature-', '')
                    packages.setdefault('image_features', []).append(line_str)
                elif re.match("system-" + xilinx_arch, line_str):
                    # do nothing, skipp the package name with "system-<xilinx_arch>". Using to find system type
                    continue
                else:
                    packages.setdefault('image_packages', []).append(line_str)
    return packages


def write_list(bb_file, packages):
    for package in packages:
        package = "\t\t" + package + " " + "\\" + "\n"
        bb_file.write(package)
    bb_file.write('\t\t"\n')


def add_user_params(packages, bb_file):
    extra_users = packages['extra_users']
    new_groups = packages['new_groups']
    image_features = packages['image_features']
    users_groups = packages['users_groups']
    user_params = ""
    groups = {}
    # Parse the user group and create list for it.
    # Ex: groups[user] = "group1,group2"
    if users_groups != "":
        for user_groups in users_groups.split(";"):
            if re.search(':', user_groups) and user_groups != "":
                user_groups = user_groups.split(":")
                groups[user_groups[0]] = user_groups[1]
    if new_groups != "":
        for group in new_groups.split(";"):
            if group:
                user_params += 'groupadd -r %s;' % (group)

    if extra_users != "":
        for param in extra_users.split(";"):
            if re.search(':', param) and param != "":
                param = param.split(":")
                # param[0]=userid
                # param[1]=passwd
                # param[2]=passwd-expire
                usercmd = "useradd"
                if param[0] == "root":
                    if not 'debug-tweaks' in image_features:
                        continue
                    if param[1] == "root":
                        print(
                            "Warning: Root password set to 'root', It is highly recommended to change Root password.")
                    usercmd = "usermod"

                if param[1]:
                    result = subprocess.check_output(
                        ["openssl", "passwd", "-6", "-salt", "xx", param[1]]).strip()
                    param[1] = str(result, "utf-8").replace('$', '\$')
                    param[1] = " -p '" + param[1] + "'"
                else:
                    param[1] = " -p ''"

                av_param = ''
                param_str = ''
                # Add groups if given for specific user
                if param[0] in groups and groups[param[0]]:
                    for group in groups[param[0]].split(","):
                        if group:
                            av_param += 'usermod -a -G ' + \
                                group + ' ' + param[0] + ';'

                # Check the count for passwd-expire
                if len(param) == 2:
                    param_str = usercmd + \
                        param[1] + ' ' + param[0] + ';' + av_param + ' \\\n'
                elif len(param) == 3:
                    param_str = usercmd + \
                        param[1] + ' ' + param[0] + ';' + param[2] + \
                        ' ' + param[0] + ';' + av_param + ' \\\n'
                else:
                    pass
                user_params += param_str
    user_params = 'EXTRA_USERS_PARAMS = "' + user_params + '"\n'
    bb_file.write(user_params)


def update_cfg(cfg_file, xilinx_arch):
    cfg_file = open(cfg_file, 'a')
    cfg_file.truncate()
    packages = read_packages(xilinx_arch)

    cfg_file.write('\n#Rootfs configs\n')
    # Add inherit packages into bb file
    inherit_str = 'INHERIT += "plnx-deploy extrausers'
    if 'inherit_packages' in packages.keys():
        inherit_str = inherit_str + ' '.join(packages['inherit_packages'])
    inherit_str = inherit_str + '" \n'
    cfg_file.write(inherit_str)

    # Add image inherit packages
    if 'image_classes' in packages.keys():
        image_class = '\nIMAGE_CLASSES += "' + \
            ' '.join(packages['image_classes']) + '"\n'
        cfg_file.write(image_class)

    # Add Init_manager variable
    if 'Init_manager' in packages.keys():
        init_managerstr = 'INIT_MANAGER_DEFAULT = "' + \
            packages['Init_manager'] + '"\n\n'
        cfg_file.write(init_managerstr)
    # Add Tune_feature variable
    if 'default_tune' in packages.keys():
        default_tunestr = 'DEFAULTTUNE = "cortexa72-cortexa53-crypto"\n'
        cfg_file.write(default_tunestr)
    # Add common features into bb file
    if 'image_features' in packages.keys():
        cfg_file.write('COMMON_FEATURES:pn-petalinux-image-minimal = "\\\n')
        write_list(cfg_file, packages['image_features'])
    cfg_file.write('IMAGE_LINGUAS:' + xilinx_arch + ' = " "\n\n')
    # Add image install packages into bb file
    cfg_file.write('IMAGE_INSTALL:pn-petalinux-image-minimal = "\\\n')
    cfg_file.write("\t\tkernel-modules \\\n")
    write_list(cfg_file, packages['image_packages'])
    if 'libmali-xlnx' in packages['image_packages']:
        machine_features = 'MACHINE_FEATURES:append = " mali400"\n'
        cfg_file.write(machine_features)
    if 'package_feeds' in packages.keys() and packages['package_feeds']:
        package_feedstr = 'PACKAGE_FEED_URIS = "' + \
            packages['package_feeds'] + '"\n\n'
        cfg_file.write(package_feedstr)
    if 'package_feed_archs' in packages.keys() and packages['package_feed_archs']:
        package_feed_archsstr = 'PACKAGE_FEED_ARCHS = "' + \
            packages['package_feed_archs'] + '"\n\n'
        cfg_file.write(package_feed_archsstr)
    add_user_params(packages, cfg_file)
    sudo_users_str = ''
    sudo_users_pre = 'USERADDEXTENSION:append = " plnx-useradd-sudoers"\n'
    for user in packages['sudo_users'].split():
        sudo_users_str += user + ' ALL=(ALL) ALL;'
    sudo_users_str = sudo_users_pre + 'EXTRA_USERS_SUDOERS = "' + sudo_users_str + '"\n'
    cfg_file.write(sudo_users_str)
    if 'mali_backend' in packages.keys():
        mali_backendstr = 'MALI_BACKEND_DEFAULT = "' + \
            packages['mali_backend'] + '"\n\n'
        cfg_file.write(mali_backendstr)
    cfg_file.close()


def fix_kconfig_name(packg):
    plus_str = re.escape("+")
    if (re.search(plus_str, packg)):
        packg = str(packg)
        packg = re.sub(plus_str, "PLUS", packg)
    return packg


def fix_config_name(packg):
    plus_str = re.escape("PLUS")
    if (re.search(plus_str, packg)):
        packg = str(packg)
        packg = re.sub(plus_str, "+", packg)
    return packg


def generate_kconfig_menu(packg):
    if packages_dict[packg]:
        line = ""
        for sub_packg in packages_dict[packg]:
            line += "config " + fix_kconfig_name(sub_packg) + "  \n"
            line += "\t bool \"" + sub_packg + "\"\n"
            line += "\t help\n"
            if sub_packg in summary_dict:
                line += "\t" + summary_dict[sub_packg] + "\n"
            line += "\t\n"
    return line
#  kconf_file.write(line)


def generate_config(packgs, file_path):
    minimal_file = open(file_path + '/minimal_packages', 'w')
    minimal_file.truncate()
    for p in packgs:
        line = "CONFIG_" + p + "=y\n"
        minimal_file.write(line)
    minimal_file.close()


def generate_kconfig_part(kconf_file, section_key):
    for sub_section_key in sorted(packages_section[section_key]):
        if packages_section[section_key][sub_section_key]:
            line = "menu \"" + sub_section_key + " \" \n"
            kconf_file.write(line)
            for packg in packages_section[section_key][sub_section_key]:
                lines = generate_kconfig_menu(packg)
                kconf_file.write(lines)
            line = "endmenu\n"
            kconf_file.write(line)
        else:
            packg = str(sub_section_key)
            lines = generate_kconfig_menu(packg)
            kconf_file.write(lines)


def generate_kconfig(kconf_file_path):
    kconf_file = open(kconf_file_path + '/Kconfig.user', 'w')
    kconf_file.truncate()

    for section_key in sorted(packages_section):
        if section_key == "PETALINUX":
            generate_kconfig_part(kconf_file, section_key)

    line = "menu \"" + "user packages" + " \" \n"
    kconf_file.write(line)
    for section_key in sorted(packages_section):
        if section_key != "PETALINUX":
            generate_kconfig_part(kconf_file, section_key)
    line = "endmenu\n"
    kconf_file.write(line)

    kconf_file.close()


def parse_packages_to_sections(packages_dict):
    global packages_section
    packages_section = {}
    my_regx = re.escape("/")
    for packg in sorted(packages_dict):
        if packg in sections_dict:
            section_value = sections_dict[packg]
            if (re.search(my_regx, section_value)):
                string0 = section_value.split('/')[0]
                string1 = section_value.split('/')[1]
                if string0 in packages_section:
                    if string1 in packages_section[string0]:
                        packages_section[string0][string1] += [packg]
                    else:
                        packages_section[string0][string1] = [packg]
                else:
                    packages_section[string0] = {}
                    packages_section[string0][string1] = [packg]
            else:
                if section_value in packages_section:
                    packages_section[section_value][packg] = []
                else:
                    packages_section[section_value] = {}
                    packages_section[section_value][packg] = []
        else:
            section_value = "misc"
            if re.search('^lib', packg):
                section_value = "libs"
            if section_value in packages_section:
                packages_section[section_value][packg] = []
            else:
                packages_section[section_value] = {}
                packages_section[section_value][packg] = []


def filter_packages(black_list_file):
    global block_packages_full
    global block_packages_single
    block_packages = []
    block_packages_full = []
    block_packages_single = []
    with open(black_list_file, 'r') as fp:
        for line in fp:
            line = line.strip()
            line = str(line)
            if line.startswith('FULL_'):
                line = line.replace("FULL_", "")
                block_packages_full += [line]
            if line.startswith('SINGLE_'):
                line = line.replace("SINGLE_", "")
                block_packages_single += [line]

    fp.closed
#  print block_packages


def extract_packages(Lines_packages):
    global packages_dict
    global sub_block_packgs
    packages_dict = {}
    sub_block_packgs = []
    my_regx = "CONFIG_"
    my_regx1 = re.escape("(")
    for line in Lines_packages:
        line_str = str(line)
        if (re.search(my_regx, line_str)):
            packg = line_str.split("_")[1]
            packg = packg.split("'")[0]
# getting the packages
            packages_dict[packg] = [packg]
#  print packages_dict
    parse_packages_to_sections(packages_dict)


def extract_value(Layers, value):
    value_dict = {}
    for layer in Layers:
        for root, directories, files in os.walk(layer):
            for filename in files:
                if filename.endswith((".bb", ".inc", ".bbclass")):
                    files_bb = open(os.path.join(root, filename), 'r')
                    for line in files_bb.readlines():
                        if re.search(value, line):
                            line = re.sub('"|\n', '', line)
                            line = line.split('=')[1]
                            strg = re.sub(
                                '\.bb$|\.inc$|\.bbclass$', '', filename)
                            strg = strg.split('_')[0]
                            value_dict[strg] = line.strip()
                    files_bb.close()
    return value_dict


def extract_packages_dot(packages_dot):
    global Lines_packages_dot
    Lines_packages_dot = []
    with open(packages_dot, 'r') as fp:
        for line in fp:
            line = line.splitlines()
            Lines_packages_dot += [line]
    fp.closed
    extract_packages(Lines_packages_dot)


def extract_bblayers(user_layer):
    global summary_dict
    global sections_dict
    Layers = [user_layer]
    summary_dict = extract_value(Layers, "^SUMMARY =")
    sections_dict = extract_value(Layers, "^SECTION =")


def parse_args(argv):
    try:
        opts, args = getopt.getopt(
            argv, "hk:b:", ["generate_kconfig=", "update_cfg="])
    except getopt.GetoptError:
        print('ERROR: valid options --generate_kconfig or --update_cfg')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('HELP: ')
            print(
                "Usage: python3 rootfs_config.py --generate_kconfig <user_rootfsconfig> <Kconfig Out path>")
            print(
                "Usage: python3 rootfs_config.py --update_cfg config <cfg_file> <xilinx_arch>")
            sys.exit()
        elif opt in ("-k", "--generate_kconfig"):
            packages_user = argv[1]
            kconf_file_path = argv[2]
            user_layer = ''
            if len(sys.argv) > 4:
                user_layer = argv[3]
            extract_bblayers(user_layer)
            extract_packages_dot(packages_user)
            generate_kconfig(kconf_file_path)

        elif opt in ("-b", "--update_cfg"):
            config = argv[1]
            cfg_file = argv[2]
            xilinx_arch = argv[3]
            read_config(config)
            update_cfg(cfg_file, xilinx_arch)
        else:
            print("Error:")
            print(
                "Usage: python3 rootfs_config.py --generate_kconfig <user_rootfsconfig> <Kconfig Out path>")
            print(
                "Usage: python3 rootfs_config.py --generate_bb config <cfg_file> <xilinx_arch>")


parse_args(sys.argv[1:])
