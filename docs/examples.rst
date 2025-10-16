.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

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
