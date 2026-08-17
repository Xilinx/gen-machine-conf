.. Copyright (C) 2022-2026, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _usage:

Gen Machine Conf Usage Introduction
-----------------------------------

gen-machine-conf uses the parse-sdt sub command to parse System Device-tree
and generate Yocto configurations.

gen-machine-conf is capable of auto-detecting the subcommand based on
the file/URI specified with --hw-description.
If system-top.dts is specified, it uses the subcommand parse-sdt.

gen-machine-conf usage
----------------------

.. code-block:: console

  $ gen-machine-conf -h
  usage: gen-machine-conf [--template Template yaml file] [--hw-description <PATH_TO_SDTDIR>]
                          [--soc-family {microblaze-v,zynq,zynqmp,versal,versal-2ve-2vm,versal-2vp}]
                          [--soc-variant SOC_VARIANT] [--machine-name MACHINE]
                          [-c <config_dir>] [-r REQUIRE_MACHINE] [-O MACHINE_OVERRIDES] [--output OUTPUT] [--native-sysroot NATIVE_SYSROOT]
                          [--menuconfig] [--add-config [CONFIG_<macro>=y]] [-D] [--force]
                          [-h] [-v]
                          <subcommand> ...

  Yocto Machine Configuration File generation tool

  required arguments:
    --hw-description <PATH_TO_SDTDIR>
                          Specify System Device-tree Directory

  options:
    --template Template yaml file
                          Yaml template file
    --soc-family {microblaze-v,zynq,zynqmp,versal,versal-2ve-2vm,versal-2vp}
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
    --menuconfig          Launch menuconfig UI to update system level configurations.
    --add-config [CONFIG_<macro>=y]
                          Specify config macro or file containing config macros to be added on top of default configs
    -D, --debug           Enable debug output
    --force               Force regenerate all configuration files, ignoring the cached change-detection hashes
    -h, --help            show this help message and exit
    -v, --version         show version information and exit

  subcommands:
    <subcommand>
      parse-sdt           Parse System device-tree file and generate Yocto configurations.

  Use gen-machine-conf <subcommand> --help to get help on a specific command

gen-machine-conf parse-sdt usage
--------------------------------
The parse-sdt is the "newer" way of getting hardware configuration
information into Yocto. It uses the output of AMD Vivado™ Design Suite
after it has been processed by System Device Tree Generator.

For QEMU-capable designs, the SDT flow also derives the hardware DDR map
from the QEMU command line description. gen-machine-conf runs the lopper
``gen_qemu_mem_cfg`` subcommand, reads the generated
``memory.qemuboot.conf`` file, and appends the resulting ``QB_MEM``
setting to the generated machine override. This allows later tools such
as ``qemuboot-tool`` to merge the same memory map into the combined QEMU
configuration used by ``runqemu``.

.. code-block:: console

  $ gen-machine-conf parse-sdt -h
  usage: gen-machine-conf parse-sdt [--hw-description <PATH_TO_SDTDIR>] [other options]

  options:
    -h, --help            show this help message and exit
    -g {full,dfx}, --gen-pl-overlay {full,dfx}
                          Generate PL overlays for full or DFX configurations using
                          the xlnx_overlay_pl_dt lopper script.

                          Use this option only when PL is present in the design. Do
                          not use this option if the design does not include PL,
                          as no overlay is required.
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

Output Directory Layout
-----------------------

Persistent, user-facing state is kept at the root of the output directory,
while transient scratch is contained in a dedicated ``work/`` subdirectory:

- Persistent (output root): the generated project ``config``,
  ``configs/Kconfig*``, ``sys_hw_data.yaml``, the generated device trees under
  ``dts_path``, the cached hardware-derived platform info (``hw_info.yaml``)
  and the change-detection hashes (``.statistics``).
- Scratch (``<output>/work``): lopper byproducts and transient DTS/DTSI/conf
  files generated while parsing the System Device Tree. These are throwaway
  and safe to delete between runs.

Re-Run and Change Detection
---------------------------

When the same output directory is reused, gen-machine-conf skips regenerating
the configuration when none of its tracked inputs have changed. It records a
content hash of each tracked input under ``<output>/.statistics`` and compares
against it on the next run. The tracked inputs are:

- the hardware description (system device-tree)
- the generated project ``config``
- the template YAML
- domain files (``CONFIG_YOCTO_MC_DOMAIN_FILEPATH``)
- custom DTSI files referenced through Kconfig

When nothing changed, the tool logs that it is skipping regeneration and
reuses the cached hardware-derived platform info (``<output>/hw_info.yaml``) to
avoid re-running the expensive lopper queries. PDI/bitstream, ELF and psu_init
inputs are not content-tracked because only their paths, not their content, are
embedded into the generated output.

Use ``--force`` to ignore the cached hashes and regenerate all configuration
files from scratch.

.. note::

  These files are generated and can be overwritten on later runs:
  ``conf/machine/<machine>.conf``, the auto-generated ``.dts`` and ``.dtsi``
  files under ``conf/dts``, the generated multiconfig files and the generated
  machine include files.
