.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _flowcharts:

===========================================
Gen-Machine-Conf Flowcharts
===========================================

This page provides detailed flowcharts illustrating the internal workflows and processes
of the Gen-Machine-Conf tool. Each flowchart represents a specific component or phase
of the configuration generation pipeline.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

The Gen-Machine-Conf tool follows a multi-stage pipeline to transform hardware descriptions
into Yocto/PetaLinux machine configurations. The following flowcharts provide visual
representations of each stage and component interaction.

Argument Parsing
================

The initial stage processes command-line arguments and validates input parameters.

.. figure:: ../images/parseargs.svg
   :name: fig-parseargs
   :align: center
   :width: 30%
   :alt: Argument parsing flowchart

   **Figure 1:** Command-line argument parsing and validation workflow. This diagram
   shows how the tool processes input arguments, validates hardware descriptions,
   and sets up the initial configuration context.

Hardware Information Processing
================================

After argument parsing, the tool extracts and processes hardware information from
the provided hardware description files (XSA or System Device Tree).

.. figure:: ../images/hardware_info_processing.svg
   :name: fig-hardware-info
   :align: center
   :width: 30%
   :alt: Hardware information processing flowchart

   **Figure 2:** Hardware information gathering and processing workflow. This
   flowchart illustrates the extraction of platform details, CPU configurations,
   peripheral detection, and generation of hardware-specific Kconfig files.

Project Configuration Generation
=================================

The project configuration stage generates Kconfig files and processes system
configurations based on the extracted hardware information.

.. figure:: ../images/project_config_generation.svg
   :name: fig-project-config
   :align: center
   :width: 30%
   :alt: Project configuration generation flowchart

   **Figure 3:** Project configuration generation workflow. Shows the creation
   of Kconfig files, multiconfig targets, and the optional menuconfig interface
   for user customization.

Multiconfig Target Processing
==============================

The tool identifies and processes multiple configuration targets based on CPU
types and operating system requirements.

.. figure:: ../images/multiconfig_target_processing.svg
   :name: fig-multiconfig-processing
   :align: center
   :width: 60%
   :alt: Multiconfig target processing flowchart

   **Figure 4:** Multiconfig target identification and processing. This diagram
   shows how the tool analyzes CPU configurations and determines appropriate
   multiconfig targets (Linux, baremetal, FreeRTOS, Zephyr, etc.).

Multiconfig Setup Workflows
============================

Different processor architectures require specific multiconfig setup procedures.
The following flowcharts detail the setup process for each architecture.

.. note::

   **Back to Target Loop:** In the following flowcharts, you'll notice a "Back to Target Loop"
   node that represents the iterative nature of multiconfig processing. After completing
   configuration for one multiconfig target (Linux, baremetal, FreeRTOS, Zephyr, or firmware),
   the workflow returns to process the next enabled target. This allows the tool to generate
   configurations for multiple targets across different CPUs and cores in a single execution.

ARM Cortex-A/R Multiconfig Setup
---------------------------------

.. figure:: ../images/arm_multiconfig_setup.svg
   :name: fig-arm-multiconfig
   :align: center
   :width: 80%
   :alt: ARM multiconfig setup flowchart

   **Figure 5:** ARM Cortex-A multiconfig setup workflow. Illustrates the
   configuration generation for ARM Cortex-A processors, including Linux,
   FSBL, and optional baremetal/RTOS targets.

ARM Cortex-R Multiconfig Setup
-------------------------------

.. figure:: ../images/arm_cortex-r-multiconfig_setup.svg
   :name: fig-arm-cortex-r-multiconfig
   :align: center
   :width: 60%
   :alt: ARM Cortex-R multiconfig setup flowchart

   **Figure 6:** ARM Cortex-R multiconfig setup workflow. Shows the specific
   configuration requirements for ARM Cortex-R processors, typically used for
   real-time processing and firmware components.

MicroBlaze Multiconfig Setup
-----------------------------

.. figure:: ../images/microblaze_multiconfig.svg
   :name: fig-microblaze-multiconfig
   :align: center
   :width: 50%
   :alt: MicroBlaze multiconfig setup flowchart

   **Figure 7:** MicroBlaze multiconfig setup workflow. Details the configuration
   process for Xilinx MicroBlaze soft processors, including tune features and
   baremetal/Linux variants.

Firmware Multiconfig
====================

Platform Management Unit (PMU), Platform Loader and Manager (PLM), and other
firmware components require specialized multiconfig handling.

.. figure:: ../images/firmware_multiconfig.svg
   :name: fig-firmware-multiconfig
   :align: center
   :width: 50%
   :alt: Firmware multiconfig flowchart

   **Figure 8:** Firmware multiconfig generation workflow. Shows how the tool
   generates configurations for PMU firmware (ZynqMP), PLM firmware (Versal),
   PSM firmware (Versal), FSBL (Zynq/ZynqMP), and ASU firmware (Versal-2v-2vm).

Yocto Machine Setup
===================

The final stage generates Yocto machine configuration files with all necessary
settings and dependencies.

.. figure:: ../images/yocto_machine_setup.svg
   :name: fig-yocto-machine
   :align: center
   :width: 30%
   :alt: Yocto machine setup flowchart

   **Figure 9:** Yocto machine configuration generation workflow. Illustrates
   the creation of machine.conf files, multiconfig files, device tree sources,
   and machine-specific include files.

PetaLinux Machine Configuration
================================

When operating in PetaLinux mode, additional configuration files and rootfs
settings are generated.

.. figure:: ../images/petalinux_machine_config.svg
   :name: fig-petalinux-machine
   :align: center
   :width: 30%
   :alt: PetaLinux machine configuration flowchart

   **Figure 10:** PetaLinux-specific machine configuration workflow. Shows the
   generation of plnxtool.conf, rootfs configuration files, and PetaLinux-specific
   build settings.


Image Format Notes
==================

.. note::

   All flowcharts are provided in SVG (Scalable Vector Graphics) format, which
   ensures crisp rendering at any zoom level. The flowcharts can be viewed
   directly in the source ``images/`` directory or through this documentation.

.. tip::

   When viewing the documentation in HTML format, you can click on the flowcharts
   to view them at full size. The SVG format also allows for searching text
   within the diagrams in most modern browsers.
