.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _options:

Gen Machine Conf: Detailed Options and Usage
--------------------------------------------

This section provides a comprehensive overview of the Gen-Machine-Conf tool options.
It explains each available argument, configuration setting, and environment variable
in detail, along with usage examples.

--hw-description <XSA/SDT PATH>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The --hw-description option specifies the hardware description input for the tool.
It is a required argument and determines the hardware platform for which the
machine configuration will be generated.

The tool handles the process of validating, copying or unpacking the hardware
description file or directory. It ensures the provided path is absolute and exists,
and adapts its behavior depending on whether the workflow is for
PetaLinux (which does not use BitBake) or Yocto (which may use BitBake to fetch and unpack URIs).

The tool also ensures that only supported file types are processed.
It distinguishes between .xsa files and System Device-tree directories,
and can auto-select the appropriate flow if both are present. It also prevents ambiguous situations,
such as multiple .xsa or system-top.dts files in the same directory.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./design.xsa
    $ gen-machine-conf --hw-description ./sdt_output/
    $ gen-machine-conf --hw-description https://edf.amd.com/bsp.tar.gz
    $ gen-machine-conf --hw-description ./bsp.tar.gz
    $ gen-machine-conf --hw-description "git://github.com/sdt.git;branch=<BRANCH>;rev=<SRCREV>;S=<SUBDIR>"

--template <yaml_file>
~~~~~~~~~~~~~~~~~~~~~~

The --template option allows you to specify a YAML file containing default values
for various commandline arguments, Kconfigs and Yocto variables.
This makes it easy to reuse project settings and automate configuration for
different hardware or build environments.
When you provide a template YAML file, the tool will read default values from
it and apply them to arguments that are not explicitly set on the command line.

.. note::

   Below sample YAML is for only AMD eval board and for custom board user can have
   a similar one but make sure the QEMU DTB and other files needs to be constructed
   by user for custom board


**Sample YAML File**

.. code-block:: console

    args:
        - --hw-description https://edf.amd.com/sswreleases/rel-v<VERSION>/hdf-examples/<VERSION>.tar.gz
        - --machine-name versal-2ve-2vm-vek385-sdt-seg
        - -g full
        - --domain-file vek385.yaml openamp.yaml
    kconfig:
        CONFIG_YOCTO_BBMC_CORTEXR52_0_ZEPHYR: y
        CONFIG_YOCTO_BBMC_CORTEXR52_1_BAREMETAL: y
        CONFIG_SUBSYSTEM_SERIAL_OP-TEE_IP_NAME: '1'
        CONFIG_SUBSYSTEM_OPTEE: y
        CONFIG_SUBSYSTEM_TF-A_MEMORY_SETTINGS: y
        CONFIG_SUBSYSTEM_TF-A_MEM_BASE: '0x1600000'
        CONFIG_SUBSYSTEM_TF-A_MEM_SIZE: '0x200000'
        CONFIG_SUBSYSTEM_UBOOT_APPEND_BASEADDR: n
    machine:
        pre:
            UBOOT_ENTRYPOINT:
                op: '?='
                val: '0x20200000'
            UBOOT_LOADADDRESS:
                op: '?='
                val: '0x20200000'
        post:
            QEMU_HW_DTB_PS:
                op: '='
                val: "${QEMU_HW_DTB_PATH}/board-versal2-psxc-vek385.dtb"
            QEMU_HW_BOOT_MODE:
                op: '='
                val: "8"
            QEMU_HW_SERIAL:
                op: '='
                val: "-serial null -serial null -serial null -serial mon:stdio"

**Supported input methods**

- Args: Supported via command line and YAML.
  Command-line flags passed directly to ``gen-machine-conf``. The same flags
  can be pre-defined in YAML under ``args:`` to avoid repetition. Values
  provided on the command line are applied on top of the YAML defaults.

- Kconfig: Supported via command line and YAML.
  Low-level configuration macros (for Yocto, U-Boot, TF-A, etc.) that can be
  supplied using ``--add-config`` on the command line or under ``kconfig:``
  in YAML. Command-line Kconfig entries are merged after YAML entries, so
  they can override or extend them.

- Machine (pre/post): Supported via YAML only.
  Yocto machine configuration overrides read exclusively from YAML. Use
  ``pre`` to inject variables before the generic machine include,
  and ``post`` to append or override settings afterward using
  explicit operations such as ``op: '='`` with ``val:``.

**Advanced YAML Example with Inherit and Merge Operations**

The template YAML supports advanced features including inheritance from other YAML files
and selective merging using append/prepend operations:

.. code-block:: yaml

    # base-board.yaml - Base configuration for a board family
    args:
        - --hw-description https://edf.amd.com/base-board.tar.gz
        - --soc-family versal
        - --machine-name base-versal-board
        - --domain-file base_domain.yaml
    kconfig:
        CONFIG_SUBSYSTEM_SERIAL_OP-TEE_IP_NAME: '1'
        CONFIG_SUBSYSTEM_OPTEE: y
        CONFIG_YOCTO_BBMC_LINUX_DTSI: 'base-system-conf.dtsi'
    machine:
        pre:
            UBOOT_ENTRYPOINT:
                op: '?='
                val: '0x20200000'

.. code-block:: yaml

    # custom-board.yaml - Inherits from base and extends with custom settings
    inherit: base-board.yaml

    # Override machine name
    args:
        - --machine-name custom-versal-board

    # Prepend domain files before inherited args
    args_prepend:
        - --domain-file vek385.yaml

    # Append additional domain files after inherited args
    args_append:
        - --domain-file openamp.yaml

    # Add kconfig on top of inherited settings
    kconfig:
        CONFIG_SUBSYSTEM_TF-A_MEMORY_SETTINGS: y
        CONFIG_SUBSYSTEM_TF-A_MEM_BASE: '0x1600000'
        CONFIG_SUBSYSTEM_TF-A_MEM_SIZE: '0x200000'

    # Prepend kconfig settings (higher priority - evaluated first)
    kconfig_prepend:
        CONFIG_YOCTO_BBMC_LINUX_DTSI: 'custom-early-system-conf.dtsi'

    # Append kconfig settings (evaluated after inherited values)
    kconfig_append:
        CONFIG_YOCTO_BBMC_LINUX_DTSI: 'board-system-conf.dtsi'

    # Override and extend machine configurations
    machine:
        pre:
            UBOOT_LOADADDRESS:
                op: '?='
                val: '0x20200000'
        post:
            QEMU_HW_DTB_PS:
                op: '='
                val: "${QEMU_HW_DTB_PATH}/board-versal2-psxc-vek385.dtb"
            QEMU_HW_BOOT_MODE:
                op: '='
                val: "8"

    # Prepend machine setting values
    machine_prepend:
        pre:
            KERNEL_IMAGETYPE:
                val: 'Image'

    # Append machine settings
    machine_append:
        post:
            QEMU_HW_SERIAL:
                val: "-serial null -serial null -serial null -serial mon:stdio"

**Merge Behavior**:

- **inherit**: Loads the specified YAML file(s) as a base. Multiple files can be space-separated.
  Supports environment variables and BitBake variables in paths. The inherit file is loaded first,
  then the current YAML file's values are merged on top.

- **args/kconfig/machine**: Direct keys in the current YAML override inherited values for the same key.

- **args_prepend/kconfig_prepend/machine_prepend**: Values are merged **before** inherited values
  (prepend → inherited → append order).

- **args_append/kconfig_append/machine_append**: Values are merged **after** inherited values
  (prepend → inherited → append order).

- **Merge order for same key**: When the same configuration key appears in multiple sections,
  the final value is space-concatenated in this order:

  1. Values from ``<key>_prepend`` (if present)
  2. Values from inherited YAML file's ``<key>`` section
  3. Values from current YAML file's ``<key>`` section
  4. Values from ``<key>_append`` (if present)

  In the example above, ``CONFIG_YOCTO_BBMC_LINUX_DTSI`` appears in:

  - ``kconfig_prepend`` with ``custom-early-system-conf.dtsi``
  - Inherited base-board.yaml ``kconfig`` with ``base-system-conf.dtsi``
  - ``kconfig_append`` with ``board-system-conf.dtsi``

  The final merged value will be:
  ``custom-early-system-conf.dtsi base-system-conf.dtsi board-system-conf.dtsi``

.. important::

    **Prepend/Append is designed for configs or variables that accept space-separated string values.**

    Suitable use cases:

    - ``CONFIG_YOCTO_BBMC_LINUX_DTSI`` - accepts multiple space-separated DTSI file paths
    - ``--domain-file`` - accepts multiple space-separated YAML file paths
    - Machine variables that support multiple values

    .. warning::

        **Do not use prepend/append for boolean configs or single-value settings.**

        Boolean configs (e.g., ``CONFIG_SUBSYSTEM_OPTEE=y``) or single-value numeric settings
        (e.g., ``CONFIG_SUBSYSTEM_TF-A_MEM_BASE='0x1600000'``) will be space-concatenated,
        resulting in invalid values like ``"y y"`` or ``"0x1600000 0x1800000"``.

        For such configs, use the direct ``kconfig:`` key in the current YAML file, which will
        override the inherited value completely.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --template custom-board.yaml --output ./custom_output

    This will first load base-board.yaml, then merge custom-board.yaml settings on top,
    with prepend/append operations applied in the appropriate order.

.. code-block:: console

    $ gen-machine-conf --template template.yaml --machine-name customboard --output ./custom_output

    In this example, all values except machine-name and output will be taken from template.yaml.
    The specified arguments will override the template.

.. note::

    Specifying --domain-file from command-line will append to the values specified in the template YAML file.

.. note::

    When using inherit with multiple YAML files, machine names from all files are automatically
    collected and added to MACHINEOVERRIDES, allowing your configuration to inherit settings
    from multiple base machines.

.. tip::

    Use templates to standardize builds across teams or projects, and to quickly switch between hardware configurations.


--machine-name <name>
~~~~~~~~~~~~~~~~~~~~~

This option allows you to specify a custom name for the generated machine configuration.
This name is used to organize output files and directories, and it becomes the identifier
for your hardware platform in the Yocto build system.

If not provided on the command line:
 - XSA flow: Uses the generic file name combined with the device ID extracted from the XSA file.
 - SDT flow: Uses the compatible string extracted from the System-Device-Tree (SDT) file.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --machine-name myboard

--soc-family <family>
~~~~~~~~~~~~~~~~~~~~~

Specifies the SoC family (microblaze, microblaze-v, zynq, zynqmp, versal, versal-2ve-2vm).
``microblaze-v`` is supported only in the system device tree (SDT) flow and
is not supported in the XSA/XSCT flow.
If not provided on the command line gen-machine-conf will be extracted from the System-Device-Tree (SDT) file
based on the Processor name.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --soc-family zynqmp

--soc-variant <variant>
~~~~~~~~~~~~~~~~~~~~~~~

Specify SoC variant (e.g., cg, dr, eg, ev, ai-prime, premium).
If not provided on the command line gen-machine-conf will be extracted from the System-Device-Tree (SDT) file
based on the Device-id.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --soc-variant cg

--output <dir>
~~~~~~~~~~~~~~

Output directory for generated files. If not specified, a directory is auto-generated.
The Output directory designed to be flexible based on user input and the context of
the hardware file being processed. If the user explicitly specifies an output directory,
the function resolves its absolute path using os.path.realpath. If no output directory
is provided, the function checks if a machine name is given; if so, it creates a
subdirectory named after the machine inside an output folder in the current working directory.

If neither an output directory nor a machine name is specified, the function generates a
unique subdirectory name by combining the base name of the hardware file (without its extension)
and the first ten characters of its SHA-256 hash, ensuring uniqueness and traceability.

.. note::

   If the same output directory is used for multiple designs with the same machine name,
   the tool will reuse the existing project configurations(config) for the new designs.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --output myoutdir

-c, --config-dir <dir>
~~~~~~~~~~~~~~~~~~~~~~

Location of the build configuration directory. If not specified, it creates a conf directory
folder in the current working directory.
Tool will use the specified directory to create/modify files in dts, machine and
multiconfig directories.

.. note::

   The tool does not erase files but may overwrite them. For example, if you disable a
   multiconfig, the references to that multiconfig will be removed for generated conf files,
   but any previously generated machines/multiconfigs/dts files will remain in directories.


**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --config-dir /path/to/conf

-r, --require-machine <name>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Require a specific machine instead of the default generic one.

By default, gen-machine-conf includes the generic Yocto-specific
machine configuration files from layers into the generated
machine-conf files. Use this option to specify your own
generic machine configuration instead.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --require-machine my-generic-machine

-O, --machine-overrides <overrides>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This allows you to specify additional configuration overrides for the generated machine
configuration. These overrides are typically used to enable or customize specific features,
settings, or behaviors in the machine configuration file.
The value provided to --machine-overrides is a string containing one or more override tokens,
separated by colons.

This option lets you add extra override tokens to the generated machine configuration.
These overrides control how BitBake applies machine-specific settings, feature flags, and
.bbappend files during the build.

For More details see:

- `OVERRIDES variable <https://docs.yoctoproject.org/ref-manual/variables.html#term-OVERRIDES>`_
- `Conditional Syntax (Overrides) <https://docs.yoctoproject.org/bitbake/2.8/bitbake-user-manual/bitbake-user-manual-metadata.html#conditional-syntax-overrides>`_

Syntax
^^^^^^

.. code-block:: text

    --machine-overrides <override1:override2:...>

The value is a colon-separated list of tokens appended to BitBake's MACHINEOVERRIDES
variable in the generated <machine>.conf.

Purpose
^^^^^^^

gen-machine-conf automatically adds the machine name as an override. Use this option
when you want BitBake to additionally treat your machine as:

- An existing reference machine (inherit its BSP logic)
- A board revision or variant
- A feature-specific configuration

How overrides work in BitBake
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- BitBake evaluates overrides from left to right
- Later overrides take precedence over earlier ones
- Overrides added via this option appear after the machine name, allowing them to refine or
  supersede generic settings
- Only overrides that match entries in your layers have any effect; unused tokens are
  silently ignored

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --machine-overrides "feature1:feature2"
    $ gen-machine-conf --machine-name myboard --machine-overrides "versal-vck190:revB"

Generates in conf/machine/myboard-*.conf:

.. code-block:: text

    MACHINEOVERRIDES .= ":versal-vck190:revB"

Effective resolution order (assuming base overrides exist):

.. code-block:: text

    <base-overrides>:myboard:versal-vck190:revB

This allows myboard to inherit settings from versal-vck190 and further specialize with revB overrides.

--native-sysroot <path>
~~~~~~~~~~~~~~~~~~~~~~~

Path to native sysroot for gen-machine-conf tool execution.
The --native-sysroot option specifies the path to a native sysroot directory that contains
the necessary tools and libraries for configuration and build operations.
The value should be the absolute path to the sysroot directory.
The sysroot is used to locate tools like mconf, conf, or lopper that may not be available
in the default system path.
This option ensures that the tool uses the correct binaries and libraries for your target
build environment, avoiding compatibility issues.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --native-sysroot /opt/sysroots/x86_64

--menuconfig [project|rootfs]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option enables an interactive menu-based configuration interface for your project.
It allows you to update configuration settings using a graphical or text-based UI,
similar to the classic Linux kernel menuconfig tool.

The option accepts either project or rootfs as its value.
 - project: Launches menuconfig for system-level configuration (hardware, kernel, boot settings, etc.).
 - rootfs: Launches menuconfig for root filesystem configuration (packages, utilities, etc.).

If you use --menuconfig without a value, it defaults to project.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --menuconfig
    $ gen-machine-conf --hw-description ./system-top.dts --menuconfig project
    $ gen-machine-conf --hw-description ./system-top.dts --menuconfig rootfs

--add-config <macro_or_file>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option allows you to specify additional configuration macros or files to be included
on top of the default configuration. This is useful for enabling specific features,
settings, or customizations in your project configurations

You can use --add-config multiple times to add several macros or files. Each value can be:
 - A single configuration macro (e.g., CONFIG_FEATURE_X=y)
 - A path to a file containing a list of configuration macros

These macros or files are appended to the default configuration, allowing you to customize
the build without modifying the base template.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --add-config CONFIG_FEATURE_X=y --add-config CONFIG_FEATURE_Y=y
    $ gen-machine-conf --hw-description ./system-top.dts --add-config ./extra_config.txt

--add-rootfsconfig <file>
~~~~~~~~~~~~~~~~~~~~~~~~~

This option allows you to specify a file containing a list of package names to be added to
the root filesystem configuration. This helps you customize which software packages are included
in the generated rootfs image.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./system-top.dts --add-rootfsconfig CONFIG_PACKAGE_X=y


parse-sdt subcommand
--------------------

The parse-sdt subcommand is used to process a System Device-tree (SDT) directory as the hardware description input.
It is part of the tool's subcommand architecture, allowing you to explicitly select the SDT flow for configuration generation.

When you use parse-sdt, the tool:
 - Searches the specified directory for a system-top.dts file, which describes the hardware in device-tree format.
 - Validates that the directory contains exactly one system-top.dts file (errors if none or multiple are found).
 - Uses the SDT flow to generate machine configuration files tailored for device-tree-based hardware descriptions.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ parse-sdt


-g {full,dfx}, --gen-pl-overlay {full,dfx}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option is used to invoke the Lopper tool for generating programmable logic (PL)
overlays in device tree source (DTS) files as part of the machine configuration process.
Generate overlay files or configuration fragments that can be used to program or manage the
FPGA portion during boot or runtime.

The two components represent different PL configuration approaches:

full Component
^^^^^^^^^^^^^^

**Purpose**: Generates a complete PL overlay that includes all programmable logic IP blocks.

**Use Case**:

- When you want all PL (FPGA fabric) IP blocks to be loaded as an overlay once Linux boot is completed
- Suitable for static FPGA designs where all PL resources are programmed together
- The entire PL configuration is treated as a single unit

**What it does**:

- Removes all PL device tree nodes from the main PS (Processing System) device tree
- Creates a separate pl.dtsi file containing all PL IP blocks
- This overlay can be applied to program the FPGA and register all PL peripherals with the kernel
- Stored in pl-overlay-full/pl.dtsi directory

**Usage Example**

.. code-block:: console

    # Generate full PL overlay
    $ gen-machine-conf --hw-description ./sdt_output/ -g full

dfx Component
^^^^^^^^^^^^^

**Purpose**: Generates a DFX (Dynamic Function eXchange) static overlay for partial reconfiguration designs.

**Use Case**:

- For designs using DFX/partial reconfiguration where parts of the FPGA can be reprogrammed at runtime
- Creates the static region overlay - the parts of the PL that remain constant
- Dynamic regions can be loaded separately at runtime without affecting the static logic

**What it does**:

- Extracts only the static (non-reconfigurable) PL IP blocks into the overlay
- Creates pl.dtsi with the static PL configuration
- Stored in pl-overlay-dfx/pl.dtsi directory and remaining pl dtsi files present under sdt_output_dir:

  - Static PL: <sdt_output_dir>/pl.dtsi
  - RP partials: <sdt_output_dir>/rp0rm0/rp0rm0_partial.dtsi, <sdt_output_dir>/rp1rm0/rp1rm0_partial.dtsi, etc.

- Copy these into the corresponding Yocto firmware recipe files/ folders, which then install the runtime overlays under:

  - Static base: /lib/firmware/xilinx/vek385static/
  - RPs: /lib/firmware/xilinx/vek385static/rp0rm0/rp0rm0_slot0/ and .../rp1rm0/rp1rm0_slot0/ (with the generated pl-overlay-dfx/pl.dtsi overlays)

- Allows dynamic partial bitstreams to be loaded later for the reconfigurable regions

**Usage Example**

.. code-block:: console

    # Generate DFX static overlay
    $ gen-machine-conf --hw-description ./sdt_output/ -g dfx

-d <domain_file>, --domain-file <domain_file>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The --domain-file option is used to specify the path to one or more domain YAML files that describe
domain-specific hardware and software configuration for your platform.
These files are used during device tree generation to customize the configuration for
different processor domains (e.g., Linux, baremetal, FreeRTOS, Zephyr).

These domain-files can be used to enable the multi-config targets based on the os,type and cpu fields.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ --domain-file domain_linux.yaml --domain-file domain_r5.yaml


-i <psu_init_path>, --psu-init-path <psu_init_path>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The --psu-init-path option specifies the path to initialization files for the processor system (PS),
such as psu_init.c, psu_init.h, or ps7_init.c/h. These files are required for proper hardware initialization,
especially in baremetal and FSBL (First Stage Boot Loader) configurations.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ --psu-init-path /path/to/psu_init_files

-p <pl_path>, --pl <pl_path>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The --pl option specifies the path to the Programmable Logic (PL) file, such as a PDI (Platform Device Image)
or bitstream file, for your hardware platform. This file is used to configure the FPGA portion of Xilinx or AMD SoCs.
If not specified, the tool defaults to using the directory of the hardware file.
The PL file is referenced during configuration generation, especially when generating overlays
or device tree fragments for the programmable logic.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ --pl /path/to/bitstream.bit

-l <config_file>, --localconf <config_file>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The --localconf option in the parse-sdt command allows you to specify a path to a file where
changes to the Yocto local.conf configuration will be written.
This is useful for customizing build settings, machine features, or other project-specific
parameters that need to be reflected in the Yocto build environment.

.. note::

   Using this option users may encounter an issue where MACHINE=<machine-name> is hardcoded
   in the local.conf file. In such cases, when a user specifies the MACHINE variable on the
   command line, the value from local.conf takes precedence instead of the command-line input.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ --localconf /path/to/auto.conf

--multiconfigfull
~~~~~~~~~~~~~~~~~

The --multiconfigfull option in the parse-sdt command enables the generation of a full set of
multiconfig .conf and .dts files for your Yocto/PetaLinux project.
By default, only a minimal set of multiconfig files is generated.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ --multiconfigfull

--dts-path <dts_path>
~~~~~~~~~~~~~~~~~~~~~

The --dts-path option in the parse-sdt command specifies the absolute path or subdirectory where
the generated Device Tree Source (DTS) files will be placed.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./sdt_output/ --dts-path /path/to/dts


parse-xsa subcommand: (deprecated)
----------------------------------

The parse-xsa subcommand is used to process a XSA file contains the hardware description exported
from Xilinx/AMD tools (like Vivado).

When you use parse-xsa, the tool:
 - Reads the XSA file and extracts hardware details needed for generating device trees, configuration files, and build settings.
 - Validates that the directory contains exactly one .xsa file (errors if none or multiple are found).
 - Uses the xsct flow to generate machine configuration files tailored for device-tree-based hardware descriptions.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./design.xsa parse-xsa

--xsct-tool [XSCT_TOOL_PATH]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The --xsct-tool option is used to specify the path to the XSCT (Xilinx Software Command-line Tool) executable.
XSCT is a scripting tool provided by Xilinx for automating hardware/software workflows,
such as exporting hardware, generating device trees, and running TCL scripts.
By default, the tool may try to auto-detect XSCT, but with --xsct-tool <path>,
you can explicitly set the location of the XSCT binary to use.
This is useful if you have multiple Xilinx installations or need to use a specific version of XSCT for compatibility.

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./design.xsa --xsct-tool /opt/Xilinx/Vitis/2023.1/bin/xsct

--multiconfigenable
~~~~~~~~~~~~~~~~~~~

The --multiconfigenable option is used to enable the generation and use of multiple configuration
files (multiconfigs) in your Yocto/PetaLinux project with XSA flow.
When you specify --multiconfigenable, the tool will activate support for building multiple configurations

**Usage Example**

.. code-block:: console

    $ gen-machine-conf --hw-description ./design.xsa --multiconfigenable
