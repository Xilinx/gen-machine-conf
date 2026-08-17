.. Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
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

SUBSYSTEM_ARCH_MICROBLAZE-V
----------------------------

:Type: bool
:Default: Depends on system configuration
:Description:
    Choose this option to specify MicroBlaze-V (RISC-V) as the subsystem architecture.
    Used for soft-core MicroBlaze-V processors in FPGA designs.

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

     This config enables advanced flash auto-configuration for the Flash subsystem (usually QSPI/OSPI).

     When this option is enabled, the tool will automatically detect and generate the flash partitions, offsets, and sizes.

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

Serial Settings
---------------

The Serial Settings menu provides one serial console selection per software
domain. A separate "stdin/stdout" choice is generated for each of the
following domains, when present in the design:

- **Linux/U-Boot** (always present)
- **TF-A** (AArch64 processors only, depends on ``SUBSYSTEM_ARCH_AARCH64``)
- **OP-TEE** (Cortex-A78 / Versal 2VE/2VM only)
- **One choice per enabled multiconfig target**, gated on its
  ``YOCTO_BBMC_<MC>`` enable symbol

The list of selectable serial IPs is detected automatically from the System
Device Tree (SDT). Each domain selects its console independently, so different
domains may use different UARTs.

Serial Console Resolution Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The console for a device-tree domain (Linux/U-Boot and each multiconfig
target) is resolved from several sources. They are applied in the order below,
so each later stage overrides the previous one (**last one wins**):

.. code-block:: text

   serial IPs detected from SDT ─┐
                                 ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │  Kconfig: SUBSYSTEM_<domain>_SERIAL_<IP>_SELECT   (per domain)         │
   │  domains: Linux/U-Boot · TF-A · OP-TEE · each multiconfig target       │
   └───────────────────────────────────────────────────────────────────────┘
                                 │
              ┌──────────────────┴───────────────────┐
              ▼                                       ▼
       "From SDT" / "manual"                   a specific UART (<IP>)
              │                                       │
              │                                       ▼
              │                     sdt_ipinfo.yaml lookup:
              │                       console_prefix · earlycon
              │                       firmware_console_alias · ip_name_aliases
              │                                       │
              │                                       ▼
              │                     GenSerialChosenDtsi() builds
              │                       <domain>-serial-chosen.dtsi  and
              │                       merges it into the SDT via lopper
              ▼                                       │
   ┌───────────────────────────────────────────────────────────────────────┐
   │  Priority 1: SDT /chosen node      Priority 2: serial-chosen overlay   │
   │  (baseline, untouched)             (stdout-path / bootargs / console=) │
   └───────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼  (overlay merged into base DTS)
   ┌───────────────────────────────────────────────────────────────────────┐
   │  Priority 3 (highest): Custom DTSI                                     │
   │  CONFIG_YOCTO_BBMC_<MC>_DTSI  #include-d last via IncludeCustomDtsi()  │
   │  a /chosen here overrides both the SDT and the Kconfig selection       │
   └───────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼  final per-domain DTS
   ┌───────────────────────────────────────────────────────────────────────┐
   │  yocto_machine.SerialConsoleSettings()                                 │
   │  • From SDT  → parse console= back from the DTS /chosen                │
   │               (fallback: serial0 + SoC-default tty if none)           │
   │  • explicit  → tty from IP type + selected baudrate → SERIAL_CONSOLES  │
   │  • TF-A/OP-TEE → TFA_CONSOLE / OPTEE_CONSOLE (not SERIAL_CONSOLES)     │
   └───────────────────────────────────────────────────────────────────────┘

1. **SDT** ``/chosen`` **node** *(baseline)*
   The console that ships in the System Device Tree. This is what is used when
   the Kconfig selection is ``From SDT`` (the default).

2. **Kconfig per-domain selection** ``SUBSYSTEM_<domain>_SERIAL_<IP>_SELECT``
   When a specific UART is selected (i.e. not ``From SDT``/``manual``),
   ``lopper_utils.GenSerialChosenDtsi`` generates a
   ``<domain>-serial-chosen.dtsi`` overlay and merges it into the SDT with
   lopper. The overlay rewrites the ``/chosen`` node for that domain:

   - ``stdout-path`` → ``serial<N>:<baud>n8``
   - ``bootargs`` → ``console=<tty><N>,<baud>`` (plus ``earlycon=...`` for
     Linux only, when an earlycon and base address are known)
   - for Zephyr, also ``zephyr,console`` / ``zephyr,shell-uart``

   The tty prefix, earlycon, and TF-A/OP-TEE console tokens are looked up in
   ``gen-machine-scripts/data/sdt_ipinfo.yaml`` (see the
   `Serial metadata in sdt_ipinfo.yaml`_ section below). ``From SDT``/``manual``/unset
   generate **no** overlay, leaving stage 1 in place.

3. **Custom DTSI** ``CONFIG_YOCTO_BBMC_<MC>_DTSI`` *(highest priority)*
   Any DTSI files listed for the domain are ``#include``-d into the final DTS
   **after** the serial overlay (``lopper_utils.IncludeCustomDtsi``), so a
   ``/chosen`` console set in a custom DTSI overrides both the SDT and the
   Kconfig selection. The custom DTSI must be a regular include file, not an
   overlay (``/plugin/;`` is rejected).

Machine-configuration side (``yocto_machine.SerialConsoleSettings``):

- For ``From SDT``, the console is parsed back out of the generated Linux DTS
  ``/chosen`` node to populate ``SERIAL_CONSOLES``. If the DTS carries no
  ``console=`` (e.g. ``stdout-path`` only), it falls back to ``serial0`` with
  the SoC-default tty (``ttyPS0`` for Zynq/ZynqMP, ``ttyAMA0`` for Versal
  family, ``ttyUL0`` for MicroBlaze-V) so the image always gets a login console.
- For an explicit UART selection, the tty is derived from the IP type
  (``axi_uartlite``/``mdm`` → ``ttyUL``, ``axi_uart16550`` → ``ttyS``,
  ``sbsauart`` → ``ttyAMA``, otherwise ``ttyPS``) and the selected baudrate.
- TF-A and OP-TEE consoles are written to the firmware recipe variables
  (``TFA_CONSOLE`` / ``OPTEE_CONSOLE``) instead of ``SERIAL_CONSOLES``.

Serial metadata in sdt_ipinfo.yaml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The per-IP serial metadata used by the resolution flow lives in
``gen-machine-scripts/data/sdt_ipinfo.yaml``. Each serial IP entry may define:

- ``console_prefix`` — the Linux tty name (e.g. ``ttyPS``, ``ttyAMA``,
  ``ttyUL``, ``ttyS``) used for ``console=`` bootargs and ``SERIAL_CONSOLES``.
- ``earlycon`` — the kernel ``earlycon`` driver token (e.g. ``cdns,mmio32``,
  ``pl011,mmio32``) added to the Linux bootargs.
- ``firmware_console_alias`` — per-port (``0``/``1``) console token for TF-A
  (e.g. ``cadence``, ``pl011``).
- ``ip_name_aliases`` — SoC-specific node names that map to a canonical entry
  (e.g. ``psv_sbsauart``/``psx_sbsauart`` → ``sbsauart``).

SUBSYSTEM_SERIAL_<IP>_SELECT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Default: ``SUBSYSTEM_SERIAL_FROM_SDT_SELECT``
:Dependencies: ``SUBSYSTEM_PROCESSOR``
:Description:
    Selects the serial device used as the **Linux/U-Boot** stdin/stdout.
    The choice lists one option per serial IP detected in the SDT, plus a
    ``From SDT`` option.

    - **From SDT** (default): use the console already defined in the SDT
      ``/chosen`` node as-is. No console override is generated.
    - **<serial IP>**: override the console to the selected UART. The
      matching ``console=`` bootarg and ``SERIAL_CONSOLES`` entry are
      generated from the IP's ``console_prefix`` in ``sdt_ipinfo.yaml``.

SUBSYSTEM_SERIAL_IP_NAME
~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: string (hidden)
:Description:
    Internal string holding the selected Linux/U-Boot serial IP name. It is
    set from the active ``SUBSYSTEM_SERIAL_<IP>_SELECT`` option and consumed
    by the machine configuration generators. ``From SDT`` produces no value
    (no override).

SUBSYSTEM_SERIAL_<IP>_BAUDRATE_<rate>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Default: ``SUBSYSTEM_SERIAL_<IP>_BAUDRATE_115200``
:Dependencies: ``SUBSYSTEM_PROCESSOR``
:Description:
    Baudrate for the Linux/U-Boot serial console. One choice is generated per
    detected serial IP. Supported rates are ``600``, ``9600``, ``28800``,
    ``115200`` (default), ``230400``, ``460800`` and ``921600``. This setting
    applies only to the U-Boot/Linux serial console.

SUBSYSTEM_TF-A_SERIAL_<IP>_SELECT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Default: First detected serial console
:Dependencies: ``SUBSYSTEM_ARCH_AARCH64``
:Description:
    Selects the serial device used as the **TF-A** console. The choice lists
    one option per serial IP detected in the SDT, plus a ``manual`` fallback.
    Unlike the device-tree domains, TF-A has no ``/chosen`` node, so it
    defaults to the first detected console.

    - **<serial IP>**: use the selected UART. The TF-A console token
      (e.g. ``cadence``, ``pl011``, ``dcc``) is resolved from the IP's
      ``firmware_console_alias`` in ``sdt_ipinfo.yaml``.
    - **manual**: do not override the console; use the TF-A recipe's own
      default (settable via ``TFA_CONSOLE`` in ``local.conf``).

SUBSYSTEM_OP-TEE_SERIAL_<IP>_SELECT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Default: First detected serial console
:Dependencies: ``SUBSYSTEM_ARCH_AARCH64`` (Cortex-A78 / Versal 2VE/2VM only)
:Description:
    Selects the serial device used as the **OP-TEE** console. Behaves like the
    TF-A choice, but the console token is the serial port number (``0`` or
    ``1``). Select ``manual`` to use the OP-TEE recipe's own default
    (settable via ``OPTEE_CONSOLE`` in ``local.conf``).

SUBSYSTEM_<MC>_SERIAL_<IP>_SELECT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: bool (choice)
:Default: ``SUBSYSTEM_<MC>_SERIAL_FROM_SDT_SELECT``
:Dependencies: ``YOCTO_BBMC_<MC>``
:Description:
    Per-multiconfig-target serial console selection. One choice is generated
    for each enabled multiconfig target, using a target-specific symbol infix
    (``SUBSYSTEM_<MC>_SERIAL_...``) so it does not collide with the Linux
    selection. Options and defaults match the Linux/U-Boot choice: ``From SDT``
    (default) plus each detected serial IP. The selected IP name is exposed
    via the hidden ``SUBSYSTEM_SERIAL_<MC>_IP_NAME`` string.

Device Tree Settings
====================

Basic Configuration
-------------------

SUBSYSTEM_DT_WORKSPACE
~~~~~~~~~~~~~~~~~~~~~~

:Type: string
:Description:
    This config Provides the location to use as Device-tree workspace location for
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
:Dependencies: !SUBSYSTEM_ARCH_MICROBLAZE-V
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
    - ``versal-2vp-generic`` (for Versal 2VP)
    - ``zynqmp-generic`` (for ZynqMP)
    - ``zynq-generic`` (for Zynq-7000)
    - ``microblaze-v-generic`` (for MicroBlaze-V)

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
    - ``YOCTO_BBMC_CORTEXR5_0_ZEPHYR_DTSI`` - R5 core 0 Zephyr DTSI
    - ``YOCTO_BBMC_CORTEXA72_0_ZEPHYR_DTSI`` - A72 core 0 Zephyr DTSI
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
   * - Versal 2VP
     - AARCH64
     - versal-2vp-generic
     - Image
   * - MicroBlaze-V
     - MICROBLAZE-V
     - microblaze-v-generic
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
   * - MicroBlaze-V
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
