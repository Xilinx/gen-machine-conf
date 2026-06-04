.. Copyright (C) 2026, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _changelog:

gen-machine-conf 2026.1 Changelog
----------------------------------

This changelog summarizes the changes introduced between ``xilinx_v2025.2``
and the current ``2026.1`` state on ``master``.

Release Metadata
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Value
   * - Repository
     - ``gen-machine-conf``
   * - Repository Location
     - ``https://github.com/Xilinx/gen-machine-conf``
   * - Previous Release Tag
     - ``xilinx_v2025.2``
   * - Previous Release Revision
     - ``e1bc2ac323a92fe3c2b87f11044010351cd79b25``
   * - Current Release Branch
     - ``master``
   * - Current Release Revision
     - ``266aaf4f183fd9caf5b92df239cbcd6d4cc17b4e``
   * - Release Scope
     - Changes introduced between ``xilinx_v2025.2`` and the current ``2026.1`` code state
   * - Summary
     - 53 files changed, 4213 insertions, 1002 deletions

Contributors
~~~~~~~~~~~~

Thanks to the following people who contributed to this release:

* Altaf Patel
* Ashwini Lomate
* Mark Hatle
* Parthiban Kanchipuram
* Raju Kumar Pothuraju
* Sandeep Gundlupet Raju
* Sandeep Raju Konduru

New Features and Enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Added SDT domain access configuration support.
* Added MicroBlaze RISC-V Linux DTS generation in the SDT flow.
* Added SPL binary type configuration support.
* Added OP-TEE TZDRAM configuration support.
* Added serial console support in the SDT flow.
* Added full YAML template inheritance support with a new YAML utility module.
* Added YAML-based machine inheritance and machine override support.
* Added EFI machine feature configuration.
* Added KBUILD_DEFCONFIG assignment support in Yocto machine generation.
* Added SDT boot mode selection and propagation into machine configs.
* Added MicroBlaze RISC-V SoC family support.
* Added chosen-node support from YAML files.
* Added QEMU memory configuration support.

Architecture and Flow Improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Refactored MicroBlaze-V tune feature generation.
* Split lopper command execution in domain DTS generation path.
* Enhanced MB-V tune feature handling.
* Split OpenAMP DTS generation for clearer flow handling.
* Consolidated MB-V tune features and standardized naming.
* Optimized CPU type checking.
* Improved OpenAMP domain detection.
* Extracted BitBake initialization into a separate function.
* Added dedicated BitBake utility module.
* Refactored common utilities to use the BitBake utility layer.
* Updated main flow to use BitBake utilities.
* Updated flow modules to use BitBake utility layer.
* Switched PL overlay generation from ``pl.dtsi`` to ``pl.dtso``.
* Added dedicated Lopper utility module and separated helper logic.

Fixes
~~~~~

* Revised error messaging for missing components.
* Fixed CPU name parsing for versioned CPU names in multiconfig generation.
* Fixed ``pl_overlay`` attribute reference bug.
* Fixed firmware typo-related issue in Yocto machine path.
* Fixed typo-related issues in the main tool.
* Fixed file handling, encoding, and general error handling issues.
* Fixed TF-A debug handling.
* Fixed ``plnx_tool.conf`` handling.
* Disabled XSCT blocking dependency checks in XSCT flow.
* Fixed parsing of config values containing multiple ``=`` characters.
* Fixed serial console numbering for single-serial configurations.
* Fixed MicroBlaze-V SDT flow behavior and improved FPGA image type handling.
* Fixed custom DTSI handling.

Configuration Updates
~~~~~~~~~~~~~~~~~~~~~

* Removed U-Boot defconfig from config files where it was no longer required.
* Restricted Ethernet MAC/IP Kconfig option selection.
* Updated Yocto machine settings and Kconfig fragments to support the new options.
* Updated rootfs Kconfig fragments and rootfs config handling for the new release behavior.
* Updated machine configuration defaults for MicroBlaze-V and related flows.

Documentation Updates
~~~~~~~~~~~~~~~~~~~~~

* Updated options docs to include ``git://`` usage in ``--hw-description``.
* Added flowcharts in the documentation.
* Added supporting SVG flowchart images.
* Updated README for release usage.
* Added custom DTSI inclusion guide.
* Added prerequisites, Lopper integration, and expanded usage guidance.
* Added comprehensive Kconfig options documentation.
* Expanded command-line, Kconfig, and machine YAML option descriptions.
* Clarified machine override behavior and precedence.
* Added comprehensive YAML inheritance documentation.
* Added detailed PL overlay generation documentation.
* Added Yocto reference documentation for machine overrides.
* Clarified ``--gen-pl-overlay`` usage text.

Changed Files
~~~~~~~~~~~~~

Major code changes were made in:

* ``gen-machine-conf``
* ``yocto_machine.py``
* ``sdt_flow.py``
* ``common_utils.py``
* ``bitbake_utils.py``
* ``yaml_utils.py``
* ``lopper_utils.py``
* ``kconfig_syshw.py``
* ``project_config.py``
* ``xsct_flow.py``

Major documentation changes were made in:

* ``README.md``
* ``intro.rst``
* ``functional_diagram.rst``
* ``flowcharts.rst``
* ``kconfig_options.rst``
* ``options.rst``
* ``examples.rst``
* ``usage.rst``
