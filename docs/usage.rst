.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

Gen Machine Conf Usage Introduction
-----------------------------------

gen-machine-conf has two sub commands parse-xsa and parse-sdt you must
use one or the other. Most options work for either sub command but some
are only available/required in one sub command or the other.

gen-machine-conf is capible of auto-detecting the subcommand based on
the file/URI specified with --hw-description.
If a .xsa file is specified, it uses the subcommand parse-xsa, and
if system-top.dts is specified, it uses the subcommand parse-sdt.

If a directory is specified and it contains both a .xsa file and
system-top.dts, the tool will use system-top.dts (therefore assuming parse-sdt).

gen-machine-conf usage
----------------------

.. code-block:: console

  $ gen-machine-conf -h
  usage: gen-machine-conf [--template Template yaml file] [--hw-description [<PATH_TO_XSA>/<xsa_name>.xsa] or <PATH_TO_SDTDIR>]
                          [--soc-family {microblaze,zynq,zynqmp,versal,versal-2ve-2vm}] [--soc-variant SOC_VARIANT] [--machine-name MACHINE]
                          [-c <config_dir>] [-r REQUIRE_MACHINE] [-O MACHINE_OVERRIDES] [--output OUTPUT] [--native-sysroot NATIVE_SYSROOT]
                          [--menuconfig [{project,rootfs}]] [--petalinux] [--add-config [CONFIG_<macro>=y]] [--add-rootfsconfig ADD_ROOTFSCONFIG] [-D]
                          [-h] [-v]
                          <subcommand> ...

  PetaLinux/Yocto Machine Configuration File generation tool

  required arguments:
    --hw-description [<PATH_TO_XSA>/<xsa_name>.xsa] or <PATH_TO_SDTDIR>
                          Specify Hardware(xsa) file or System Device-tree Directory

  options:
    --template Template yaml file
                          Yaml template file
    --soc-family {microblaze,zynq,zynqmp,versal,versal-2ve-2vm}
                          SOC family type from choice list (usually auto detected).
    --soc-variant SOC_VARIANT
                          SOC Variant: Ex: cg, dr, eg, ev, ai-prime, premium (usually auto detected).
    --machine-name MACHINE
                          Provide a name to generate machine configuration
    -c <config_dir>, --config-dir <config_dir>
                          Location of the build conf directory
    -r REQUIRE_MACHINE, --require-machine REQUIRE_MACHINE
                          This machine will be required, instead of the generic machine if defined
    -O MACHINE_OVERRIDES, --machine-overrides MACHINE_OVERRIDES
                          Provide additional overrides to the generated machine
    --output OUTPUT       Output directory name
    --native-sysroot NATIVE_SYSROOT
                          Native sysroot path to use the mconf/conf or lopper commands.
    --menuconfig [{project,rootfs}]
                          UI menuconfig option to update configuration(default is project).
                          project - To update System Level configurations
                          rootfs  - To update Rootfs configurations
    --petalinux           Generate Rootfs and PetaLinux Tool conf files and update the build/local.conf file with generated .conf files.
    --add-config [CONFIG_<macro>=y]
                          Specify config macro or file containing config macros to be added on top of default configs
    --add-rootfsconfig ADD_ROOTFSCONFIG
                          Specify a file with list of package names to add into rootfs menu entry
    -D, --debug           Enable debug output
    -h, --help            show this help message and exit
    -v, --version         show version information and exit

  subcommands:
    <subcommand>
      parse-sdt           Parse System devicet-tree file and generate Yocto/PetaLinux configurations.
      parse-xsa           Parse xsa file and generate Yocto/PetaLinux configurations.

  Use gen-machine-conf <subcommand> --help to get help on a specific command


gen-machine-conf parse-xsa usage
--------------------------------
The parse-xsa is the "older" way of getting hardware configuration
information into Yocto. It uses the output of AMD Vivado™ Design Suite
directly.

.. code-block:: console

  $ gen-machine-conf parse-xsa -h
  usage: gen-machine-conf parse-xsa [--hw-description <PATH_TO_XSA>/<xsa_name>.xsa] [other options]

  options:
    -h, --help            show this help message and exit
    --xsct-tool [XSCT_TOOL_PATH]
                          Vivado or Vitis XSCT path to use xsct commands (Optional if you are already have AMD tools in your path)
    -l <config_file>, --localconf <config_file>
                          Write local.conf changes to this file
    --multiconfigfull     Generate/Enable Full set of multiconfig .conf and .dts files. Default is minimal
    --multiconfigenable   Enable multiconfig support. default is disabled.

gen-machine-conf parse-sdt usage
--------------------------------
The parse-sdt is the "newer" way of getting hardware configuration
information into Yocto. It uses the output of AMD Vivado™ Design Suite
after it has been processed by System Device Tree Generator.

.. code-block:: console

  $ gen-machine-conf parse-sdt -h
  usage: gen-machine-conf parse-sdt [--hw-description <PATH_TO_SDTDIR>] [other options]

  options:
    -h, --help            show this help message and exit
    -g {full,dfx}, --gen-pl-overlay {full,dfx}
                          Generate pl overlay for full, dfx configuration using xlnx_overlay_pl_dt lopper script
    -d <domain_file>, --domain-file <domain_file>
                          Path to domain file (.yaml) to use for generating the device tree.
    -i <psu_init_path>, --psu-init-path <psu_init_path>
                          Path to psu_init or ps7_init files, defaults to system device tree output directory
    -p <pl_path>, --pl <pl_path>
                          Path to pdi or bitstream file
    -l <config_file>, --localconf <config_file>
                          Write local.conf changes to this file
    --multiconfigfull     Generate/Enable Full set of multiconfig .conf and .dts files. Default is minimal. Search for CONFIG_YOCTO_BBMC prefix in
                          --menuconfig to get the available multiconfig targets.
    --dts-path <dts_path>
                          Absolute path or subdirectory of conf/dts to place DTS files in (usually auto detected from DTS)


.. note::

  When using gen-machine-conf in Yocto the SDT builds
  --soc-family arguments is not mandatory as the needed information
  is provided by the system device tree.
