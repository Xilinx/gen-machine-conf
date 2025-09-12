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
