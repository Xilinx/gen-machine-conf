.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

Introduction
************

The gen-machine-conf tool is a comprehensive automation tool designed
for generating machine configuration files for embedded Linux platforms,
specifically targeting PetaLinux and Yocto build environments. Developed
to streamline the hardware-to-software integration process.

gen-machine-conf simplifies the conversion of hardware descriptions,
such as Xilinx System Architecture (.xsa) files or System Device-tree
directories into ready-to-use machine configuration files.
These files are essential for customizing and building Linux images
tailored to specific hardware platforms.

The tool features robust command-line argument parsing, template-driven
configuration, and dynamic output directory management. It integrates
seamlessly with Bitbake for Yocto workflows and offers a dedicated mode
for PetaLinux, ensuring compatibility and flexibility across different
development scenarios. Its plugin architecture allows for easy extension,
enabling users to add custom subcommands and processing logic as needed.

With strong error handling, detailed logging, and support for advanced
configuration options, gen-machine-conf empowers developers to automate
and manage complex build setups efficiently, reducing manual effort and
minimizing errors in the configuration process. Whether used for rapid
prototyping or production deployment, this tool provides a reliable
foundation for embedded Linux development.

Prerequisites
=============

Before using gen-machine-conf, ensure you have the following prerequisites installed
and configured:

System Requirements
-------------------

**Disk Space:**

- Minimum 100 GB free disk space for Yocto/PetaLinux builds
- Additional space for hardware description files and generated configurations

Required Software
-----------------

**Python:**

- Python 3.8 or later
- Python packages: PyYAML, argparse (usually included in standard library)

**Yocto Project:**

- Yocto Project setup with meta-xilinx layers
- Required meta layers (see Dependencies section in README.md)

**Configuration Tools (kconfig-frontends):**

- conf (command-line configuration tool)
- mconf (menu-based configuration tool)
- If not in your PATH, Yocto will automatically fetch kconfig-frontends from sources

**Lopper (System Device Tree Processing):**

- Required for SDT-based workflows
- Must be available in your PATH for SDT flow
- If not in your PATH, Yocto will automatically fetch lopper from sources
- See official documentation: https://github.com/devicetree-org/lopper

**XSCT (Xilinx Software Command-Line Tool):**

- Part of Vivado or Vitis installation
- Required only for legacy XSA-based workflows (deprecated)
- Specify path with ``--xsct-tool`` option if not in PATH

Hardware Description Files
---------------------------

Prepare one of the following hardware description formats:

**System Device Tree (SDT) - Recommended:**

- Directory containing system-top.dts and related device tree files
- Generated from Vivado flow
- Includes hardware configuration and IP block information

**XSA File - Deprecated:**

- Xilinx System Archive (.xsa) file exported from Vivado
- Contains hardware design, bitstream, and metadata
- Will be removed in future releases; migrate to SDT flow


Lopper Integration
==================

gen-machine-conf integrates deeply with Lopper, the System Device Tree manipulation
framework, to enable modern SDT-based hardware configuration workflows. This integration
is central to how the tool processes hardware descriptions and generates domain-specific
device trees.

What is Lopper?
---------------

Lopper is a device tree manipulation framework that provides:

- Device tree parsing, modification, and generation capabilities
- Domain-specific device tree extraction from system-level descriptions
- Hardware information queries and transformations
- Python-based scripting for custom device tree operations

Lopper serves as the bridge between Vivado-generated System Device Trees and the
domain-specific device trees needed for Linux, bare-metal, and RTOS builds.

Example Lopper invocation:

.. code-block:: console

   $ lopper -f --enhanced -i <lopper-script>.dts system-top.dts output.dts

Lopper Scripts Used by gen-machine-conf
----------------------------------------

gen-machine-conf leverages several Lopper assist scripts:

**Core Scripts:**

- ``lop-a53-imux.dts`` / ``lop-a72-imux.dts`` / ``lop-a78-imux.dts`` - Cortex-A interrupt muxing
- ``lop-r5-imux.dts`` / ``lop-r52-imux.dts`` - Cortex-R interrupt muxing
- ``lop-microblaze-yocto.dts`` - MicroBlaze CPU feature extraction
- ``lop-mbv-zephyr-intc.dts`` - MicroBlaze-V interrupt controller for Zephyr

**Python Assists:**

- ``baremetaldrvlist_xlnx.py`` - Generate embedded software driver list
- ``xlnx_overlay_pl_dt.py`` - Programmable logic overlay generation
- ``gen_domain_dts.py`` - Multi-OS domain device tree generation(linux_dt, zephyr_dt)

For more information on Lopper, visit: https://github.com/devicetree-org/lopper


When to Use gen-machine-conf
=============================

gen-machine-conf is the right tool for you if you're working in any of these scenarios:

**Use gen-machine-conf when:**

Custom Hardware Designs
-----------------------

You have created a **custom hardware design** in AMD Vivado and need to generate
Linux/RTOS configurations for your FPGA or SoC platform. The tool automatically
extracts hardware information from your design and creates appropriate machine
configurations.

Example use cases:

- Custom Zynq-7000, ZynqMP, Versal, or versal-2ve-2vm board designs
- FPGA designs with custom IP blocks and peripherals
- Custom memory maps and device configurations

Multi-Domain Embedded Systems
------------------------------

Your project requires **multiple processing domains** running different operating
systems or bare-metal applications on the same chip.

Example configurations:

- **ZynqMP**: Cortex-A53 running Linux + Cortex-R5 running FreeRTOS
- **Versal**: Cortex-A72 running Linux + Cortex-R5 running bare-metal + PLM firmware
- **versal-2ve-2vm**: Cortex-A78 running Linux + Cortex-R52 running Zephyr RTOS

The tool generates multiconfig targets for each domain automatically.

Automated Configuration Workflows
----------------------------------

You want to **automate your build process** and maintain consistency across multiple
projects or hardware revisions.

Benefits:

- Template YAML files for repeatable configurations
- Command-line interface for CI integration
- Version-controlled hardware configurations
- Reduce manual configuration errors

Getting Started
===============

If gen-machine-conf is right for your project, here's how to get started:

1. **Prepare your hardware description**: XSA file or System Device Tree directory
2. **Review examples**: See `gen-machine-conf Examples <examples.rst>`_ for common use cases
3. **Understand options**: Check `Gen Machine Conf: Detailed Options and Usage <options.rst>`_ for all available configurations
4. **Create configuration**: Use template YAML or command-line options
5. **Generate files**: Run gen-machine-conf to create your machine configuration
6. **Package PL overlays when needed**: Use `Firmware Recipe Generation <firmware_recipes.rst>`_ to turn SDT PL overlay outputs into Yocto firmware recipes
7. **Build**: Use the generated files with Yocto/PetaLinux

For detailed usage examples, see `gen-machine-conf Examples <examples.rst>`_.
