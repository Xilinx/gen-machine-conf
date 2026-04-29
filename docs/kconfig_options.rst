.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc.  All rights reserved.
.. SPDX-License-Identifier: MIT

========================================
gen-machine-conf Kconfig Options
========================================

This document provides comprehensive documentation for all Kconfig configuration
options available in gen-machine-conf.

.. contents:: Table of Contents
   :depth: 3
   :local:

Architecture Options
====================

SUBSYSTEM_ARCH_AARCH64
----------------------

:Type: bool
:Default: Depends on system configuration
:Description:
    Choose this option to specify AARCH64 (64-bit ARM) as the subsystem
    architecture. Used for Cortex-A53, Cortex-A72, Cortex-A78 processors.

SUBSYSTEM_ARCH_ARM
------------------

:Type: bool
:Default: y (for 32-bit ARM systems)
:Description:
    Choose this option to specify ARM (32-bit) as the subsystem architecture.
    Used for Cortex-A9 and other 32-bit ARM processors.

SUBSYSTEM_ARCH_MICROBLAZE
--------------------------

:Type: bool
:Default: Depends on system configuration
:Description:
    Choose this option to specify MicroBlaze as the subsystem architecture.
    Used for soft-core MicroBlaze processors in FPGA designs.

Boot Component Selection
=========================

PLM (Platform Loader and Manager)
----------------------------------

Available for: Versal, Versal 2VE/2VM

SUBSYSTEM_COMPONENT_PLM_FROM_SOURCE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:
    This config Uses the Embeddedsw source code to build the PLM. This compiles PLM from
    source within the build system.

SUBSYSTEM_COMPONENT_PLM_FROM_BASE_PDI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses the PLM from Base PDI instead of building one. No additional PLM ELF
    will be packed as part of boot.bin.

SUBSYSTEM_COMPONENT_PLM_FROM_SDT_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:
    This config Uses the PLM from SDT directory/artifactory instead of building one.
    Requires specifying PLM ELF filename.

SUBSYSTEM_COMPONENT_PLM_FROM_LOCAL_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:
    This config Uses the PLM from a specified local path instead of building one. Requires
    full path to PLM ELF.


PSMFW (Platform Security Manager Firmware)
-------------------------------------------

Available for: Versal

SUBSYSTEM_COMPONENT_PSMFW_FROM_SOURCE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses the Embeddedsw source code to build the PSMFW.

SUBSYSTEM_COMPONENT_PSMFW_FROM_BASE_PDI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses PSMFW from Base PDI. No additional PSMFW ELF will be packed as part
    of boot.bin.

SUBSYSTEM_COMPONENT_PSMFW_FROM_SDT_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses PSMFW from SDT directory/artifactory.

SUBSYSTEM_COMPONENT_PSMFW_FROM_LOCAL_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses PSMFW from specified local path.


ASU (Application Security Unit)
--------------------------------

Available for: Versal 2VE/2VM

SUBSYSTEM_COMPONENT_ASU_FROM_SOURCE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses the Embeddedsw source code to build the ASU.

SUBSYSTEM_COMPONENT_ASU_FROM_BASE_PDI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses ASU from Base PDI. No additional ASU ELF will be packed as part of
    boot.bin.

SUBSYSTEM_COMPONENT_ASU_FROM_SDT_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses ASU from SDT directory/artifactory.

SUBSYSTEM_COMPONENT_ASU_FROM_LOCAL_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses ASU from specified local path.


FSBL (First Stage Boot Loader)
-------------------------------

Available for: Zynq-7000, ZynqMP

SUBSYSTEM_COMPONENT_FSBL_FROM_SOURCE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses the Embeddedsw source code to build the FSBL.

SUBSYSTEM_COMPONENT_FSBL_FROM_SDT_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses FSBL from SDT directory/artifactory.

SUBSYSTEM_COMPONENT_FSBL_FROM_LOCAL_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

   This config Uses FSBL from specified local path.


PMUFW (Platform Management Unit Firmware)
------------------------------------------

Available for: ZynqMP

SUBSYSTEM_COMPONENT_PMUFW_FROM_SOURCE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses the Embeddedsw source code to build the PMUFW.

SUBSYSTEM_COMPONENT_PMUFW_FROM_SDT_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses PMUFW from SDT directory/artifactory.

SUBSYSTEM_COMPONENT_PMUFW_FROM_LOCAL_PATH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Description:

    This config Uses PMUFW from specified local path.

Subsystem Hardware settings
===========================

Memory Settings
---------------

SUBSYSTEM_MEMORY_*_BASEADDR
~~~~~~~~~~~~~~~~~~~~~~~~~~~
:Type: hex
:Default: "" (empty)
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_MEMORY
:Description:
      This config is used to set the Start address of system memory.It has to be within the selected primary memory physical address range.

      Make sure the DT memory entry should start with provided address.

SUBSYSTEM_MEMORY_*_SIZE
~~~~~~~~~~~~~~~~~~~~~~~
:Type: hex
:Default: ""(empty)
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_MEMORY
:Description:

       This config is used to set the Size of system memory. Minimum is 32MB, maximum is the size of the selected primary memory physical address range.

SUBSYSTEM_MEMORY_*_U__BOOT_TEXTBASE_OFFSET
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:Type: hex
:Default: ""(empty)
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_MEMORY&&!SUBSYSTEM_COMPONENT
:Description:

        This config is set the u-boot text base address by specifying from the memory base address.

Ethernet Settings
-----------------

SUBSYSTEM_ETHERNET_GEM0_MAC_AUTO
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:Type: bool
:Default: n
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_ETHERNET
:Description:
        This config will  randomize MAC address for the primary ethernet.

SUBSYSTEM_ETHERNET_GEM0_MAC
~~~~~~~~~~~~~~~~~~~~~~~~~~~
:Type: string
:Default: n
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_ETHERNET
:Description:
       This config will  randomize MAC address for the primary ethernet.
       This config is used to set Default mac address from eeprom fru data

SUBSYSTEM_ETHERNET_GEM0_USE_DHCP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:Type: bool
:Default: n
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_ETHERNET
:Description:

      This config is used to set  SUBSYSTEM to use DHCP for obtaining an IP address.Enables DHCP for IP assignment.


Flash Settings
--------------

SUBSYSTEM_FLASH__ADVANCED_AUTOCONFIG:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool
:Default: n
:Dependencies: SUBSYSTEM_PROCESSOR && SUBSYSTEM_FLASH
:Description:

     This config enables advanced flash auto-configuration for the Flash subsystem (usually QSPI/OSPI) in PetaLinux.

     When this option is enabled, PetaLinux will automatically detect and generate the flash partitions, offsets, and sizes.

Boot Mode Settings
------------------

Available for: Zynq, ZynqMP, Versal, Versal Net, Versal 2VE/2VM

SUBSYSTEM_BOOTMODE_<value>
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Default: SoC-family specific default selected by the generated Kconfig menu
:Dependencies: ``SUBSYSTEM_SDT_FLOW``
:Description:

    Select the primary boot mode for the processor. The available primary boot modes are
    SoC-family specific (numeric values from SoC TRM):

    - **Zynq**: QSPI (1), NOR (2), NAND (4), SD (5)
    - **ZynqMP**: QSPI (24b) (1), QSPI (32b) (2), SD0 (2.0) (3), NAND (4), SD1 (2.0) (5), eMMC (1.8V) (6), SD1 LS (3.0) (14)
    - **Versal**: QSPI24 (1), QSPI32 (2), SD0 (v3.0) (3), SD1 (v2.0) (5), eMMC1 (v4.51) (6), OSPI (8), SD1 (v3.0) (14)
    - **Versal Net**: QSPI24 (1), QSPI32 (2), SD0 (v3.0) (3), SD1 (v2.0) (5), eMMC1 (v4.51) (6), OSPI (8), SD1 (v3.0) (14)
    - **Versal 2VE/2VM**: QSPI24 (1), QSPI32 (2), SD (v3.0) (3), SD (v2.0) (5), eMMC (v5.1) (6), OSPI (8), UFS (11), SD (v3.0) second (14)

    The selected boot mode value is written to ``DEFAULT_HW_BOOT_MODE`` in the
    generated machine configuration. This variable defaults ``HW_BOOT_MODE``, which
    controls Boot.BIN packaging and runqemu boot arguments. The ``SOC_ON_DISK_BOOT_BIN``
    variable determines whether Boot.BIN is included in the disk image based on
    whether ``HW_BOOT_MODE`` matches the SoC-specific ``SOC_DISK_BOOT_MODE_MAPPING``
    (e.g., SD-type and eMMC boot modes). When Boot.BIN is included, a combined WIC
    image (Boot.BIN + root filesystem) is automatically generated for direct SD card
    or eMMC flashing.

    **Secondary boot modes** (JTAG and others) are not primary boot modes and are
    handled by leaving ``DEFAULT_HW_BOOT_MODE`` blank/empty, which results in Boot.BIN
    not being included in the disk image by default.

    **Reference:** Zynq (UG585 "Flash-Devices-Master-Mode-Boot"), ZynqMP (UG1085 "Boot Modes"),
    Versal Gen1 (AM011 "Boot Modes and Interfaces"), Versal Gen2 (AM026 "Boot Mode and Interfaces").

Device Tree Settings
====================

Basic Configuration
-------------------

SUBSYSTEM_DT_XSCT_WORKSPACE
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: string
:Description:
    This config Provides the location to use as Device-tree XSCT workspace location for
    hardware software handoff processing.

SUBSYSTEM_DT_DOMAIN_ACCESS
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool
:Default: n
:Dependencies: SUBSYSTEM_SDT_FLOW
:Description:

    Enable this option to use the domain_access assist to generate
    domain-specific DTS files from the YAML files specified in
    YOCTO_MC_DOMAIN_FILEPATH configuration.


FPGA Manager
============

SUBSYSTEM_FPGA_MANAGER
----------------------

:Type: bool
:Dependencies: !SUBSYSTEM_ARCH_MICROBLAZE
:Description:

    This config Provides an interface to Linux for configuring the programmable logic (PL).
    Enables runtime FPGA reconfiguration.

SUBSYSTEM_PL_DT_OVERLAY_FULL
----------------------------

:Type: bool (choice)
:Dependencies: SUBSYSTEM_FPGA_MANAGER && SUBSYSTEM_SDT_FLOW
:Description:

    This config will Generate full PL device tree overlay for complete FPGA reconfiguration.

SUBSYSTEM_PL_DT_OVERLAY_DFX
---------------------------

:Type: bool (choice)
:Dependencies: SUBSYSTEM_FPGA_MANAGER && SUBSYSTEM_SDT_FLOW
:Description:

    This config will Generate DFX (Dynamic Function eXchange) PL device tree overlay for
    partial reconfiguration.

CONFIG_SUBSYSTEM_PL_INPUT_DTSI
------------------------------

:Type: string
:Default: "" (empty)
:Dependencies: SUBSYSTEM_FPGA_MANAGER && SUBSYSTEM_SDT_FLOW
:Description:

    Custom input DTSI file path(s) for PL overlay generation. Specify one or
    more ``.dtsi`` files separated by spaces. These files are passed to the
    ``xlnx_overlay_pl_dt`` lopper assist using the ``-i`` flag, and their
    contents are merged into the generated ``pl.dtso`` overlay.

**Usage:**

   Set this option to custom ``.dtsi`` file path(s) in system configuration.
   Leave empty to generate only the default ``pl.dtso`` without additional
   input.

**Usage Example:**

.. code-block:: kconfig

   CONFIG_SUBSYSTEM_PL_INPUT_DTSI="/path/to/pl-custom.dtsi"

**Multiple Files Example:**

.. code-block:: kconfig

   CONFIG_SUBSYSTEM_PL_INPUT_DTSI="/path/to/pl-custom1.dtsi /path/to/pl-custom2.dtsi"


TF-A (Trusted Firmware-A) Configuration
----------------------------------------

Available for: AArch64 platforms

SUBSYSTEM_TF-A_MEMORY_SETTINGS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool
:Default: n
:Dependencies: SUBSYSTEM_ARCH_AARCH64 && !SUBSYSTEM_COMPONENT_TRUSTED__FIRMWARE__ARM_NAME_NONE
:Description:

    This config will Modify TF-A memory base and size settings. These are already defined in
    TF-A source; use this option to override values.

**Reference:** See ``trusted-firmware-arm/docs/plat/*.md`` for details.

SUBSYSTEM_TF-A_MEM_BASE
~~~~~~~~~~~~~~~~~~~~~~

:Type: hex
:Default: 0xFFFEA000
:Dependencies: SUBSYSTEM_TF-A_MEMORY_SETTINGS
:Description:

    This config ensure TF-A is placed in OCM memory by default. Alternatively, can be placed in
    DRAM by updating TF-A_MEM_BASE and TF-A_MEM_SIZE.

SUBSYSTEM_TF-A_MEM_SIZE
~~~~~~~~~~~~~~~~~~~~~~

:Type: hex
:Default: 0x16000
:Dependencies: SUBSYSTEM_TF-A_MEMORY_SETTINGS
:Description:

    This config will Specify TF-A size in bytes.

SUBSYSTEM_TF-A_EXTRA_COMPILER_FLAGS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: string
:Default: "" (empty)
:Description:

    This config provides TF-A extra compilation flags. Specify multiple flags separated with
    semicolon.

**Usage Examples:**

.. code-block:: kconfig

   # Special handling for AWDT recovery
   SUBSYSTEM_TF-A_EXTRA_COMPILER_FLAGS="ZYNQMP_WDT_RESTART=1"

   # Build with Trusted Secure Payload
   SUBSYSTEM_TF-A_EXTRA_COMPILER_FLAGS="MAKEARCH+=RESET_TO_BL31=1 SPD=tspd; ATF_BUILD_TARGET=bl31 bl32"


OP-TEE Configuration
--------------------

Available for: AArch64 platforms

SUBSYSTEM_OPTEE
~~~~~~~~~~~~~~~

:Type: bool
:Default: n
:Dependencies: SUBSYSTEM_ARCH_AARCH64
:Description:

   This config will Enable/disable OP-TEE (Trusted Execution Environment).

U-Boot Configuration
====================

Basic Configuration
-------------------

SUBSYSTEM_UBOOT_CONFIG_TARGET
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: string
:Default: Auto-detected
:Description:

    This config will Specify a U-Boot config target when building U-Boot. Keep empty or specify
    "auto"/"AUTO" to use default defconfig based on Yocto machine name.

**Usage:** Runs ``make XXX_config`` to configure U-Boot.

**Usage Example:**

.. code-block:: kconfig

   SUBSYSTEM_UBOOT_CONFIG_TARGET="xilinx_zynqmp_virt_defconfig"

U-Boot Script Configuration
----------------------------

SUBSYSTEM_UBOOT_APPEND_BASEADDR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool
:Default: y
:Description:

    This config will Append memory/DDR base address to the offsets specified in image offset
    configurations.


Linux Configuration
===================

SUBSYSTEM_LINUX_CONFIG_TARGET
------------------------------

:Type: string
:Default: Auto-detected
:Description:

    This config will Specify a Linux config target when building Linux kernel. Keep empty or
    specify "auto"/"AUTO" to use default defconfig based on Yocto machine
    name.

**Usage:** Runs ``make XXX_config`` to configure Linux kernel.

**Usage Example:**

.. code-block:: kconfig

   SUBSYSTEM_LINUX_CONFIG_TARGET="xilinx_zynqmp_defconfig"

 Yocto Machine Settings
=====================

YOCTO_MACHINE_NAME
------------------

:Type: string
:Default: Auto-detected based on architecture

    - ``versal-net-generic`` (for Versal NET)
    - ``versal-generic`` (for Versal)
    - ``versal-2ve-2vm-generic`` (for Versal 2VE/2VM)
    - ``zynqmp-generic`` (for ZynqMP)
    - ``zynq-generic`` (for Zynq-7000)
    - ``microblaze-generic`` (for MicroBlaze)

:Description:

    This config Specifies the Yocto MACHINE_NAME for your hardware platform. This name is
    used to organize output files and identifies your hardware platform in the
    Yocto build system. It can auto-append the device ID to the machine name
    if it matches INCLUDE_MACHINE_NAME.

**Usage Example:**

.. code-block:: kconfig

   YOCTO_MACHINE_NAME="zcu102-custom"

YOCTO_INCLUDE_MACHINE_NAME
--------------------------

:Type: string
:Default: Auto-set based on YOCTO_MACHINE_NAME
:Description:

    This config Specifies the machine name to be included in the Yocto machine file.
    Pre-configured for AMD-Xilinx evaluation boards including:

    - ac701-microblazeel
    - kc705-microblazeel
    - zc702-zynq7
    - zcu102-zynqmp
    - vck190-versal
    - vek280-versal
    - And many more...

YOCTO_ADD_OVERRIDES
-------------------

:Type: string
:Default: "" (empty)
:Description:

    This config will Specify additional overrides to the generated machine conf file. Multiple
    overrides can be specified with ':' separator.

**Usage Example:**

.. code-block:: kconfig

   YOCTO_ADD_OVERRIDES="custom:feature-a:feature-b"

Multiconfig Settings
====================

YOCTO_MC_DOMAIN_FILEPATH
------------------------

:Type: string
:Default: "" (empty)
:Dependencies: SUBSYSTEM_SDT_FLOW
:Description:

    This config will Specify the domain file path to use in the generation of multiconfig files.
    Domain files define CPU clusters, OS types, and core assignments for
    multi-processor configurations.

**Usage Example:**

.. code-block:: kconfig

   YOCTO_MC_DOMAIN_FILEPATH="/path/to/domain.yaml"

YOCTO_BBMC_*_DTSI
-----------------

:Type: string (dynamically generated)
:Description:

    Multiconfig-specific DTSI file paths for custom device tree includes.
    Available for each enabled multiconfig target:

    - ``YOCTO_BBMC_LINUX_DTSI`` - Linux domain DTSI
    - ``YOCTO_BBMC_CORTEXR5_0_BAREMETAL_DTSI`` - R5 core 0 baremetal DTSI
    - ``YOCTO_BBMC_CORTEXR5_0_FREERTOS_DTSI`` - R5 core 0 FreeRTOS DTSI
    - ``YOCTO_BBMC_CORTEXR52_0_ZEPHYR_DTSI`` - R52 core 0 Zephyr DTSI

**Usage Example:**

.. code-block:: kconfig

   YOCTO_BBMC_LINUX_DTSI="/path/to/custom-linux.dtsi"
   YOCTO_BBMC_CORTEXR5_0_BAREMETAL_DTSI="/path/to/r5-custom.dtsi"


Configuration Examples
======================

Example 1: Basic ZynqMP Configuration
--------------------------------------

.. code-block:: kconfig

   # Architecture
   SUBSYSTEM_ARCH_AARCH64=y

   # Machine
   YOCTO_MACHINE_NAME="zcu102-rev1.0"

   # Boot Components - Build from source
   SUBSYSTEM_COMPONENT_FSBL_FROM_SOURCE=y
   SUBSYSTEM_COMPONENT_PMUFW_FROM_SOURCE=y

   # U-Boot
   SUBSYSTEM_UBOOT_CONFIG_TARGET="xilinx_zynqmp_virt_defconfig"
   SUBSYSTEM_UBOOT_APPEND_BASEADDR=y

   # Device Tree
   SUBSYSTEM_BOOTARGS_AUTO=y
   SUBSYSTEM_BOOTARGS_EARLYPRINTK=y

Example 2: Versal with Custom Boot Components
----------------------------------------------

.. code-block:: kconfig

   # Architecture
   SUBSYSTEM_ARCH_AARCH64=y

   # Machine
   YOCTO_MACHINE_NAME="vck190-custom"

   # Boot Components - Use prebuilt from local path
   SUBSYSTEM_COMPONENT_PLM_FROM_LOCAL_PATH=y
   SUBSYSTEM_COMPONENT_PLM_ELF_PATH="/home/user/prebuilt/plm.elf"

   SUBSYSTEM_COMPONENT_PSMFW_FROM_LOCAL_PATH=y
   SUBSYSTEM_COMPONENT_PSMFW_ELF_PATH="/home/user/prebuilt/psmfw.elf"

   # TF-A Custom Memory
   SUBSYSTEM_TF-A_MEMORY_SETTINGS=y
   SUBSYSTEM_TF-A_MEM_BASE=0x1000000
   SUBSYSTEM_TF-A_MEM_SIZE=0x80000

Example 3: Multiconfig with Domain Files
-----------------------------------------

.. code-block:: kconfig

   # Enable SDT flow
   SUBSYSTEM_SDT_FLOW=y

   # Multiconfig domain file
   YOCTO_MC_DOMAIN_FILEPATH="/path/to/domain.yaml /path/to/openamp.yaml"

   # Enable multiconfig targets
   YOCTO_BBMC_CORTEXR52_0_ZEPHYR=y
   YOCTO_BBMC_CORTEXR52_1_BAREMETAL=y

   # Custom DTSI for multiconfigs
   YOCTO_BBMC_CORTEXR52_0_ZEPHYR_DTSI="/custom/r52-zephyr.dtsi"
   YOCTO_BBMC_CORTEXR52_1_BAREMETAL_DTSI="/custom/r52-baremetal.dtsi"

   # Domain access for DTS generation
   SUBSYSTEM_DT_DOMAIN_ACCESS=y

Example 4: FPGA Manager with Overlay
-------------------------------------

.. code-block:: kconfig

   # Enable FPGA Manager
   SUBSYSTEM_FPGA_MANAGER=y

   # Full overlay type
   SUBSYSTEM_PL_DT_OVERLAY_FULL=y

   # Separate PL DTB
   SUBSYSTEM_DTB_OVERLAY=y

   # Device tree compiler flags for overlays
   SUBSYSTEM_DEVICETREE_COMPILER_FLAGS="-@"

Example 5: Custom Build Optimization
-------------------------------------

.. code-block:: kconfig

   # Parallel build settings
   YOCTO_BB_NUMBER_THREADS="16"
   YOCTO_BB_NUMBER_PARSE_THREADS="16"
   YOCTO_PARALLEL_MAKE="-j 16"

   # Local sstate cache
   YOCTO_LOCAL_SSTATE_FEEDS_URL="/mnt/sstate-cache/"

   # Pre-mirror for source downloads
   PRE_MIRROR_URL="file:///mnt/downloads-mirror/"

   # Offline mode
   YOCTO_BB_NO_NETWORK=y

   # Custom layers
   USER_LAYER_0="${PROOT}/project-spec/meta-security"
   USER_LAYER_1="${PROOT}/project-spec/meta-custom"

Quick Reference Tables
======================

Architecture-Specific Defaults
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 25 35

   * - Architecture
     - SUBSYSTEM_ARCH
     - Default Machine
     - Default Kernel Image
   * - Zynq-7000
     - ARM
     - zynq-generic
     - uImage
   * - ZynqMP
     - AARCH64
     - zynqmp-generic
     - Image
   * - Versal
     - AARCH64
     - versal-generic
     - Image
   * - Versal NET
     - AARCH64
     - versal-net-generic
     - Image
   * - Versal 2VE/2VM
     - AARCH64
     - versal-2ve-2vm-generic
     - Image
   * - MicroBlaze
     - MICROBLAZE
     - microblaze-generic
     - linux.bin.ub

Boot Components by Platform
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 15 15 15

   * - Platform
     - PLM
     - PSMFW
     - ASU
     - FSBL
     - PMUFW
   * - Versal
     - ✓
     - ✓
     - ✗
     - ✗
     - ✗
   * - Versal 2VE/2VM
     - ✓
     - ✗
     - ✓
     - ✗
     - ✗
   * - ZynqMP
     - ✗
     - ✗
     - ✗
     - ✓
     - ✓
   * - Zynq-7000
     - ✗
     - ✗
     - ✗
     - ✓
     - ✗
   * - MicroBlaze
     - ✗
     - ✗
     - ✗
     - ✗
     - ✗

Common Image Offsets (QSPI/OSPI)
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Component
     - Versal
     - ZynqMP
     - Zynq-7000
   * - Kernel
     - 0xF00000
     - 0xF00000
     - 0xA00000
   * - Ramdisk
     - 0x2E00000
     - 0x4000000
     - 0x1000000
   * - FIT Image
     - 0xF40000
     - 0xF40000
     - 0xA80000
