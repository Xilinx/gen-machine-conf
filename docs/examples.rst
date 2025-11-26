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

  - MicroBlaze is not supported in system device tree generator at this time.
  - Zinq-7000 does not support DFX static pl overlay

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
