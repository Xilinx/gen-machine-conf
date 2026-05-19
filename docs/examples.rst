.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _examples:

gen-machine-conf Examples
-------------------------

The below examples generally take one of five forms:

- parse-xsa Custom .xsa; This is an example of using the .xsa file
  output by AMD `Vivado <https://www.xilinx.com/products/design-tools/vivado.html>`_ Design Suite
- parse-xsa .xsa from AMD; This is an example of using an AMD™ provided xsa from our JFrog Artifactory.
  gen-machine-conf is capable of ingesting these directly from the web at https://edf.amd.com/sswreleases/rel-v<VERSION>/hdf-examples/<VERSION>
- parse-sdt Without pl overlay; This method is for when users want their programmable logic loaded at
  boot by the AMD™ bootloaders
- parse-sdt With full bitstream pl overlay; This method is used when users want to delay loading of
  their programmable logic until the software (e.g. U-Boot, Linux) can perform the load.
- parse-sdt With dfx static pl overlay; This method is used when users want some of their programmable
  logic loaded by the AMD™ bootloaders but still have some re-configurable regions in their PL.

Examples Using .xsa file (deprecated and will be removed in future releases)
----------------------------------------------------------------------------

.. code-block:: console

  # With template YAML file:
  $ gen-machine-conf --template <path_to_template_yaml>

.. code-block:: console

  # Custom xsa file:
  $ gen-machine-conf --soc-family <microblaze|zynq|zynqmp|versal> --hw-description <path_to_custom_xsa>/<project_name>.xsa --machine-name <your-custom-name>

.. code-block:: console

  # xsa file from AMD:
  $ gen-machine-conf --soc-family <microblaze|zynq|zynqmp|versal> --hw-description <path_to_hdf_artifactory>/<board_and_project_name>/system.xsa --machine-name <name_based_on_project>

System device tree(SDT) Based Examples
--------------------------------------

.. note::

  - Classic MicroBlaze is not supported in the system device tree generator flow at this time.
  - MicroBlaze-V is supported for Linux machine generation in the system device tree flow.

.. code-block:: console

  # With template YAML file
  $ gen-machine-conf --template <path_to_template_yaml>

.. code-block:: console

  # Without pl overlay
  $ gen-machine-conf --hw-description /<path_to_sdtdir>/ -c conf --machine-name <your-custom-name>

  # With full bitstream pl overlay
  $ gen-machine-conf --hw-description /<path_to_sdtdir>/ -c conf --machine-name <your-custom-name> -g full

  # With dfx static pl overlay
  $ gen-machine-conf --hw-description /<PATH_TO_SDTDIR>/ -c conf --machine-name zynqmp-zcu102-sdt -g dfx

  # Using a custom xsct install location
  $ gen-machine-conf parse-xsa --soc-family versal --hw-description /<path_to_hdf_artifactory>/vck190-versal/system.xsa --machine-name vck190-versal --xsct-tool /<Vitis_or_Petalinux_install_directory>/tools/xsct

Creating Yocto PL Firmware Recipes
----------------------------------

After generating PL overlays from an SDT design, you can package them into a
Yocto layer with ``create-fw-recipe``. For a full description of the helper,
see `Firmware Recipe Generation <firmware_recipes.rst>`_.

.. code-block:: console

  # Full overlay recipe from SDT output
  $ create-fw-recipe --hw-description /<path_to_sdtdir>/ -g full

  # DFX base plus partial recipes from SDT output
  $ create-fw-recipe --hw-description /<path_to_sdtdir>/ -g dfx --recipe-name vek385static

  # Explicit overlay and FPGA files
  $ create-fw-recipe --dtso /<path_to_pl.dtso> --fpga /<path_to_design.pdi> --recipe-name my-overlay

.. note::

  ``create-fw-recipe`` only supports local files. Remote URLs or network paths
  are not supported for input files.

Using gen-machine-conf with native sysroot
------------------------------------------

gen-machine-conf needs the additional host tools like conf, mconf and lopper tools. You can get these tools
by downloading and installing pre-built buildtools installer from https://edf.amd.com/sswreleases/<VERSION>/sdkupdate/buildtools.

.. code-block:: console

  # Locate and download the pre-built buildtools
  $ wget https://edf.amd.com/sswreleases/rel-v2025.2/sdkupdate/buildtools
  $ chmod a+x ./buildtools

  # Execute the installation script
  $ ./buildtools -d /<installation_dir>/x86-sysroot -y

  # Specify installed SDK to gen-machine-conf
  $ source /<installation_dir>/x86-sysroot/environment-setup-x86_64-petalinux-linux
  $ gen-machine-conf --hw-description /<path_to_sdtdir>/

  (OR)
  $ gen-machine-conf --hw-description /<path_to_sdtdir>/ --native-sysroot /<installation_dir>/x86-sysroot/sysroots/x86_64-petalinux-linux/


Customizing Domain DTS with Custom DTSI Files
----------------------------------------------

gen-machine-conf supports including custom DTSI (Device Tree Source Include) files into
the generated domain device tree files. This allows you to add custom hardware nodes,
modify existing nodes, or override device tree properties without manually editing the
generated DTS files.

When generating multiconfig targets (such as Linux, Baremetal, FreeRTOS, or Zephyr),
gen-machine-conf can automatically include custom DTSI files into the domain-specific
device tree. This is controlled through Kconfig options that can be set via:

- Template YAML file
- Command-line ``--add-config`` option
- Interactive menuconfig

Kconfig Options for Custom DTSI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following Kconfig options control custom DTSI inclusion:

**For Linux Domains:**

.. code-block:: kconfig

  CONFIG_YOCTO_BBMC_LINUX_DTSI="/path/to/custom-linux.dtsi"

**For Cortex-R5 Baremetal:**

.. code-block:: kconfig

  CONFIG_YOCTO_BBMC_CORTEXR5_0_BAREMETAL_DTSI="/path/to/custom-baremetal.dtsi"

Available Multiconfig Targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom DTSI can be included for any enabled multiconfig target:

- ``LINUX`` - ARM Cortex-A9/A53/A72/A78/MicroBlaze-V-RISC-V Linux
- ``CORTEXR5_<n>_BAREMETAL`` - ARM Cortex-R5 Baremetal
- ``CORTEXR5_<n>_FREERTOS`` - ARM Cortex-R5 FreeRTOS
- ``CORTEXR52_<n>_BAREMETAL`` - ARM Cortex-R52 Baremetal
- ``CORTEXR52_<n>_ZEPHYR`` - ARM Cortex-R52 Zephyr
- ``MICROBLAZEV_<n>_ZEPHYR`` - MicroBlaze-V Zephyr

Example 1: Using Template YAML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a template YAML file to specify custom DTSI files:

.. code-block:: yaml

  # template.yaml
  ---
  kconfig:
    # Include custom DTSI for Cortex-A53 Linux domain
    CONFIG_YOCTO_BBMC_LINUX_DTSI: "/path/to/custom-nodes.dtsi"

    # Include custom DTSI for Cortex-R5 FreeRTOS domain
    CONFIG_YOCTO_BBMC_CORTEXR5_0_FREERTOS_DTSI: "/path/to/custom-peripherals.dtsi"

Run gen-machine-conf with the template:

.. code-block:: console

  $ gen-machine-conf --template template.yaml --hw-description /path/to/sdt/

Example 2: Using Command-Line Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify custom DTSI files directly on the command line:

.. code-block:: console

  $ gen-machine-conf \
      --hw-description /path/to/sdt/ \
      --machine-name zynqmp-custom \
      --add-config CONFIG_YOCTO_BBMC_LINUX_DTSI=/path/to/custom.dtsi

For multiple targets:

.. code-block:: console

  $ gen-machine-conf \
      --hw-description /path/to/sdt/ \
      --machine-name versal-custom \
      --add-config CONFIG_YOCTO_BBMC_LINUX_DTSI=/path/to/linux-custom.dtsi \
      --add-config CONFIG_YOCTO_BBMC_CORTEXR5_0_BAREMETAL_DTSI=/path/to/baremetal-custom.dtsi

Example 3: Using Interactive Menuconfig
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Launch menuconfig to interactively select custom DTSI files:

.. code-block:: console

  $ gen-machine-conf \
      --hw-description /path/to/sdt/ \
      --machine-name zynqmp-custom \
      --menuconfig

Navigate in menuconfig:

1. Select ``Multiconfig Targets  --->``
2. Select your target and enable (eg: cortexa72-0-freertos)
3. Set ``DTSI path for cortexa72-0-freertos`` to your DTSI file location (You can provide multiple dtsi files with space separation)
4. Save and exit


Verification
~~~~~~~~~~~~

After running gen-machine-conf, verify the custom DTSI inclusion:

.. code-block:: console

  # Check the generated DTS file
  $ cat build/conf/dts/zynqmp-custom/cortexa53-0-linux.dts

  # Verify multiconfig settings
  $ cat build/conf/multiconfig/zynqmp-custom-cortexa53-0-linux.conf

  You should be able to see the custom DTSI file changes reflected in the generated DTS.


Tips and Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~
1. **Use Absolute Paths**: Always use absolute paths for DTSI files to avoid path resolution issues
2. **Node Overrides**: Use ``&<node-label>`` syntax to override existing nodes rather than redefining them
3. **Multiple DTSI Files**: You can specify multiple DTSI files by separating them with spaces in the Kconfig option

Troubleshooting
~~~~~~~~~~~~~~~

**Issue: Custom DTSI not included in generated DTS**

- Verify the Kconfig option name matches the target exactly
- Check that the file path is absolute and the file exists
- Review gen-machineconf.log for any warnings or errors


Scripted WIC Image Generation with Transparent BOOT.BIN Packaging
-----------------------------------------------------------------

Applies to: **Zynq**, **ZynqMP**, **Versal**, **Versal Net**, and
**Versal 2VE/2VM**.

This section describes how to drive the primary boot-mode selection from the
``gen-machine-conf`` command line so that a WIC disk image is produced with
``BOOT.BIN`` packaged in automatically — no interactive menu required.

Overview
~~~~~~~~

The primary boot mode is selected through the ``SUBSYSTEM_BOOTMODE_<value>``
Kconfig option. Pass ``--add-config`` to ``gen-machine-conf`` to set the
option non-interactively (i.e. without launching ``menuconfig``):

- **Option:** ``--add-config CONFIG_SUBSYSTEM_BOOTMODE_<value>=y``
- **Type:** bool (choice)
- **Depends on:** ``SUBSYSTEM_SDT_FLOW``

Available Boot Modes
~~~~~~~~~~~~~~~~~~~~

The table below summarises the boot-mode values supported by each SoC family
and the corresponding Kconfig macro to pass via ``--add-config``.

.. list-table::
   :header-rows: 1
   :widths: 18 10 30 42

   * - SoC Family
     - Value
     - Boot Mode
     - ``CONFIG_`` Macro
   * - Zynq
     - 1
     - QSPI
     - ``CONFIG_SUBSYSTEM_BOOTMODE_1``
   * - Zynq
     - 2
     - NOR
     - ``CONFIG_SUBSYSTEM_BOOTMODE_2``
   * - Zynq
     - 4
     - NAND
     - ``CONFIG_SUBSYSTEM_BOOTMODE_4``
   * - Zynq
     - 5
     - SD
     - ``CONFIG_SUBSYSTEM_BOOTMODE_5``
   * - ZynqMP
     - 1–14
     - QSPI/SD/NAND/eMMC
     - ``CONFIG_SUBSYSTEM_BOOTMODE_<N>``
   * - Versal / Net
     - 1–14
     - QSPI/SD/eMMC/OSPI
     - ``CONFIG_SUBSYSTEM_BOOTMODE_<N>``
   * - Versal 2VE/2VM
     - 1–14
     - + UFS (11)
     - ``CONFIG_SUBSYSTEM_BOOTMODE_<N>``

.. note::

   JTAG (value ``0``) is *not* a primary boot mode. Selecting it leaves
   ``DEFAULT_HW_BOOT_MODE`` blank, and ``BOOT.BIN`` is therefore **not**
   included in the generated disk image.

Usage
~~~~~

Invoke ``gen-machine-conf`` with ``--add-config`` to bake the boot-mode
selection into the generated machine configuration:

.. code-block:: console

   $ gen-machine-conf --hw-description ./sdt_output/ \
       --add-config CONFIG_SUBSYSTEM_BOOTMODE_5=y

Examples by SoC Family
~~~~~~~~~~~~~~~~~~~~~~

Quick reference for the most common boot media on each SoC family:

- **Zynq** — SD (5): ``--add-config CONFIG_SUBSYSTEM_BOOTMODE_5=y``
- **ZynqMP** — SD0 2.0 (3): ``--add-config CONFIG_SUBSYSTEM_BOOTMODE_3=y``
- **Versal / Versal Net** — eMMC1 (6): ``--add-config CONFIG_SUBSYSTEM_BOOTMODE_6=y``
- **Versal 2VE/2VM** — UFS (11): ``--add-config CONFIG_SUBSYSTEM_BOOTMODE_11=y``

Effect on the Generated Machine Config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Selecting a boot mode causes ``gen-machine-conf`` to emit the corresponding
``DEFAULT_HW_BOOT_MODE`` assignment in the machine override, for example:

.. code-block:: bitbake

   DEFAULT_HW_BOOT_MODE = "5"

The variables driven by this setting are:

- ``HW_BOOT_MODE`` — defaults from ``DEFAULT_HW_BOOT_MODE`` and controls
  ``BOOT.BIN`` packaging as well as the ``runqemu`` arguments.
- ``SOC_ON_DISK_BOOT_BIN`` — determines whether ``BOOT.BIN`` is embedded in
  the disk image. SD and eMMC boot modes trigger a combined WIC image that
  contains both the boot artifacts and the root filesystem.


Creating Multiple Machine Configurations for Different PL Variants Using ``--output``
-------------------------------------------------------------------------------------

When the same base SoC is used with several different programmable logic (PL)
designs, it is convenient to generate one machine per PL variant and select
between them at build time using ``MACHINE=...``. The ``--output`` flag lets
each invocation of ``gen-machine-conf`` write into a dedicated directory
while still sharing the same Yocto layer layout.

Step 1: Prepare Handoff Directories (per PL variant)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each PL variant, ensure you have a valid handoff (SDT) directory exported
from Vivado. For example:

.. code-block:: text

   /path/to/sdt-video/
   /path/to/sdt-network/
   /path/to/sdt-dsp/

Each directory contains the PL-specific design data for that variant.

Step 2: Generate One Machine per PL Variant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the ``gen-machine-conf`` utility once per PL variant. Each invocation
should use:

- A unique ``--machine-name``.
- A unique ``--output`` directory.
- Its own handoff (SDT) directory passed via ``--hw-description``.

**PL Variant 1 — Video Pipeline**

.. code-block:: console

   $ gen-machine-conf \
       --hw-description /path/to/sdt-video/ \
       --machine-name zcu104-video \
       --output /path/to/output/zcu104

**PL Variant 2 — Network Offload**

.. code-block:: console

   $ gen-machine-conf \
       --hw-description /path/to/sdt-network/ \
       --machine-name zcu104-network \
       --output /path/to/output/zcu104-network \
       -c conf -g full

**PL Variant 3 — DSP Accelerator**

.. code-block:: console

   $ gen-machine-conf \
       --hw-description /path/to/sdt-dsp/ \
       --machine-name zcu104-dsp \
       --output /path/to/output/zcu104-dsp \
       -c conf -g full

Step 3: Resulting Configuration Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After running all three commands, the shared ``conf/`` tree contains one
entry per PL variant under ``machine/``, ``dts/``, and ``multiconfig/``:

.. code-block:: text

   conf/
   ├── machine/
   │   ├── zcu104-video.conf
   │   ├── zcu104-network.conf
   │   └── zcu104-dsp.conf
   ├── dts/
   │   ├── zcu104-video/
   │   ├── zcu104-network/
   │   └── zcu104-dsp/
   └── multiconfig/
       ├── zcu104-video-cortexa53-0-fsbl.conf
       ├── zcu104-network-cortexa53-0-fsbl.conf
       ├── zcu104-dsp-cortexa53-0-fsbl.conf
       └── ...

Step 4: Build a Specific PL Variant in Yocto
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To build with a specific PL image, simply select the corresponding machine
at the BitBake command line:

.. code-block:: console

   $ MACHINE=zcu104-video bitbake <image>
