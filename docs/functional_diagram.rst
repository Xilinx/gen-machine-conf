.. Copyright (C) 2022-2025, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _functional_diagram:

High-Level Architecture
=========================

This represents the complete flow from hardware description input to final
Yocto/PetaLinux build configuration output, including all major components,
their interactions, and the data transformations that occur at each stage.

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────────────────────┐
   │                         GEN-MACHINE-CONF TOOL                               │
   │                  Yocto/PetaLinux Machine Configuration Generator            │
   └─────────────────────────────────────────────────────────────────────────────┘
                                       |
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                          INPUT LAYER                                      │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  • Hardware Description:                                                  │
   │    - .xsa files (Vivado/Vitis)                                            │
   │    - System Device Tree (system-top.dts)                                  │
   │    - URIs/Local paths/Directories                                         │
   │  • Template YAML (optional)                                               │
   │  • Command Line Arguments                                                 │
   │  • Environment Variables                                                  │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                      INITIALIZATION & VALIDATION                          │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [gen-machine-conf (main)]                                                │
   │  ├─ Parse Arguments (argparse)                                            │
   │  ├─ Read Template YAML (yaml_utils.ReadTemplateYaml)                      │
   │  ├─ Initialize Bitbake (if available)                                     │
   │  ├─ Validate HW Description (ValidateHWFile)                              │
   │  │   ├─ Check .xsa or system-top.dts                                      │
   │  │   └─ Auto-detect hw_flow: 'xsct' or 'sdt'                              │
   │  ├─ Fetch/Copy HW Description (GetHWDescription)                          │
   │  │   ├─ Handle URIs with Bitbake                                          │
   │  │   └─ Copy local files to output directory                              │
   │  ├─ Load Plugins (from BBPATH + lib/gen-machineconf)                      │
   │  └─ Setup Logging                                                         │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                       ┌───────────────┴───────────────┐
                       │                               │
                       ▼                               ▼
       ┌───────────────────────────┐   ┌──────────────────────────┐
       │   PARSE-XSA FLOW          │   │   PARSE-SDT FLOW         │
       │   (xsct_flow.py)          │   │   (sdt_flow.py)          │
       │   [DEPRECATED]            │   │   [RECOMMENDED]          │
       └───────────────────────────┘   └──────────────────────────┘
                       │                               │
                       └───────────────┬───────────────┘
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                    HARDWARE INFORMATION GATHERING                         │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [gatherHWInfo()]                                                         │
   │  ├─ Extract Platform Information:                                         │
   │  │   ├─ Machine Name                                                      │
   │  │   ├─ Device ID                                                         │
   │  │   ├─ SoC Family (microblaze/zynq/zynqmp/versal/versal-2ve-2vm)         │
   │  │   ├─ SoC Variant (cg/dr/eg/ev/ai-prime/premium/net/hbm)                │
   │  │   └─ Model/Board Name                                                  │
   │  │                                                                        │
   │  ├─ Parse CPU Information (using Lopper for SDT):                         │
   │  │   ├─ Identify CPUs (Cortex-A9/A53/A72/A78/R5/R52, MicroBlaze, etc.)    │
   │  │   ├─ Core numbers and domains                                          │
   │  │   └─ OS hints (linux/baremetal/freertos/zephyr)                        │
   │  │                                                                        │
   │  ├─ Generate System HW Configuration:                                     │
   │  │   ├─ Run Lopper scripts (for SDT)                                      │
   │  │   ├─ Run XSCT commands (for XSA)                                       │
   │  │   └─ Generate Kconfig.syshw                                            │
   │  │                                                                        │
   │  └─ Detect Peripherals:                                                   │
   │      ├─ Memory configuration                                              │
   │      ├─ Serial/UART devices                                               │
   │      ├─ Ethernet controllers                                              │
   │      ├─ Flash devices                                                     │
   │      └─ Other IP blocks                                                   │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                     KCONFIG GENERATION & CONFIGURATION                    │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [project_config.py]                                                      │
   │  ├─ Generate Kconfig Files:                                               │
   │  │   ├─ Kconfig (main menu structure)                                     │
   │  │   ├─ Kconfig.syshw (hardware-specific)                                 │
   │  │   ├─ Kconfig.main (imported configs)                                   │
   │  │   ├─ Kconfig.dtgsettings                                               │
   │  │   ├─ Kconfig.yoctosettings                                             │
   │  │   └─ Kconfig.bootcomp* (boot components)                               │
   │  │                                                                        │
   │  ├─ Multiconfig Kconfig Generation:                                       │
   │  │   ├─ CONFIG_YOCTO_BBMC_<target>                                        │
   │  │   └─ CONFIG_YOCTO_BBMC_<target>_DTSI                                   │
   │  │                                                                        │
   │  ├─ Apply Template YAML Configurations                                    │
   │  ├─ Apply CLI --add-config Options                                        │
   │  ├─ PreProcess System Config (PreProcessSysConf)                          │
   │  │                                                                        │
   │  └─ Optional: Run Menuconfig UI                                           │
   │      ├─ Project configuration                                             │
   │      └─ Rootfs configuration                                              │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                  POST-PROCESSING & VALIDATION                             │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [post_process_config.py]                                                 │
   │  ├─ Validate Configuration Consistency                                    │
   │  ├─ Resolve Dependencies                                                  │
   │  ├─ Update Hardware-Specific Settings                                     │
   │  └─ Generate petalinux_config.yaml                                        │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                    MULTICONFIG GENERATION                                 │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [multiconfigs.py]                                                        │
   │  ├─ ParseMultiConfigFiles Class:                                          │
   │  │   ├─ Parse CPU Dictionary                                              │
   │  │   ├─ Identify Multiconfig Targets:                                     │
   │  │   │   ├─ Linux (default for Cortex-A)                                  │
   │  │   │   ├─ FSBL (Zynq/ZynqMP)                                            │
   │  │   │   ├─ Baremetal applications                                        │
   │  │   │   ├─ FreeRTOS                                                      │
   │  │   │   ├─ Zephyr                                                        │
   │  │   │   ├─ PMU/PLM/PSM firmware                                          │
   │  │   │   └─ ASU MicroBlaze                                                │
   │  │   └─ Build Multiconfig Map                                             │
   │  │                                                                        │
   │  └─ GenerateMultiConfigFiles Class:                                       │
   │      ├─ For each enabled multiconfig target:                              │
   │      │   ├─ Generate <machine>-<target>.conf                              │
   │      │   ├─ Set DISTRO and DEFAULTTUNE                                    │
   │      │   └─ Configure TMPDIR per multiconfig                              │
   │      └─ Set BBMULTICONFIG variable                                        │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │              DEVICE TREE GENERATION (SDT Flow Only)                       │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [sdt_flow.py - sdtGenerateMultiConfigFiles]                              │
   │  ├─ For each CPU/Domain:                                                  │
   │  │   ├─ Linux DTS Generation:                                             │
   │  │   │   ├─ Generate domain-specific DTS with YAML files                  │
   │  │   │   ├─ Handle PL Overlay (full/dfx):                                 │
   │  │   │   │   ├─ Run xlnx_overlay_pl_dt lopper script                      │
   │  │   │   │   └─ Generate pl.dtsi overlay file                             │
   │  │   │   ├─ Include Custom DTSI (IncludeCustomDtsi)                       │
   │  │   │   └─ Generate final Linux DTS                                      │
   │  │   │                                                                    │
   │  │   ├─ Baremetal/RTOS DTS:                                               │
   │  │   │   ├─ Generate domain DTS with lop-*-imux.dts                       │
   │  │   │   ├─ Run baremetaldrvlist_xlnx lopper script                       │
   │  │   │   ├─ Generate libxil.conf                                          │
   │  │   │   └─ Generate distro.conf → features.conf                          │
   │  │   │                                                                    │
   │  │   └─ Zephyr DTS:                                                       │
   │  │       ├─ Generate domain DTS                                           │
   │  │       ├─ Run gen_domain_dts with zephyr_dt                             │
   │  │       ├─ Generate Kconfig and Kconfig.defconfig                        │
   │  │       └─ Generate Zephyr board DTS                                     │
   │  │                                                                        │
   │  ├─ MicroBlaze Tune Features:                                             │
   │  │   ├─ Run lop-microblaze-yocto.dts                                      │
   │  │   └─ Generate microblaze.inc or microblaze-riscv.inc                   │
   │  │                                                                        │
   │  └─ Lopper Tool Invocations:                                              │
   │      ├─ RunLopperGenDomainDTS()                                           │
   │      ├─ RunLopperGenLinuxDts()                                            │
   │      ├─ RunLopperPlOverlaycommand()                                       │
   │      ├─ GetLopperBaremetalDrvList()                                       │
   │      └─ RunLopperSubcommand()                                             │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                   YOCTO MACHINE CONFIGURATION                             │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [yocto_machine.py]                                                       │
   │  ├─ Generate <machine>.conf:                                              │
   │  │   ├─ Machine metadata (@TYPE, @NAME, @DESCRIPTION)                     │
   │  │   ├─ Require generic machine conf (if specified)                       │
   │  │   ├─ Set SOC_FAMILY and SOC_VARIANT                                    │
   │  │   ├─ Configure DEFAULTTUNE                                             │
   │  │   ├─ Set MACHINEOVERRIDES                                              │
   │  │   ├─ Add BBMULTICONFIG targets                                         │
   │  │   └─ Include machine-specific settings:                                │
   │  │       ├─ Kernel configuration                                          │
   │  │       ├─ U-Boot configuration                                          │
   │  │       ├─ Device tree settings                                          │
   │  │       ├─ Boot firmware settings                                        │
   │  │       ├─ Serial console                                                │
   │  │       ├─ Memory settings                                               │
   │  │       └─ Image types                                                   │
   │  │                                                                        │
   │  ├─ Generate machine include files:                                       │
   │  │   └─ conf/machine/include/<machine>/                                   │
   │  │       ├─ <machine>-libxil.conf (per multiconfig)                       │
   │  │       ├─ <machine>-features.conf (per multiconfig)                     │
   │  │       ├─ microblaze.inc (if applicable)                                │
   │  │       └─ microblaze-riscv.inc (if applicable)                          │
   │  │                                                                        │
   │  ├─ Flow-Specific Configuration:                                          │
   │  │   ├─ XSCT Flow (YoctoXsctConfigs):                                     │
   │  │   │   ├─ HDF_MACHINE and HDF_BASE                                      │
   │  │   │   └─ XSCTH_* variables                                             │
   │  │   └─ SDT Flow (YoctoSdtConfigs):                                       │
   │  │       ├─ SYSTEM_DTFILE paths                                           │
   │  │       └─ CONFIG_DTFILE_DIR                                             │
   │  │                                                                        │
   │  └─ Firmware Dependencies (YoctoMCFimwareConfigs):                        │
   │      ├─ PMU firmware (ZynqMP)                                             │
   │      ├─ PLM firmware (Versal)                                             │
   │      ├─ PSM firmware (Versal)                                             │
   │      ├─ FSBL firmware (Zynq/ZynqMP)                                       │
   │      └─ ASU firmware (versal-2ve-2vm)                                     │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                  PETALINUX CONFIGURATION (Optional)                       │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [plnx_machine.py, rootfs_config.py]                                      │
   │  ├─ Generate plnxtool.conf:                                               │
   │  │   ├─ PETALINUX_PRODUCT                                                 │
   │  │   ├─ Platform-specific variables                                       │
   │  │   └─ Tool configurations                                               │
   │  │                                                                        │
   │  ├─ Generate Rootfs Configuration:                                        │
   │  │   ├─ Parse rootfsconfig_<soc_family>                                   │
   │  │   ├─ Generate Kconfig for rootfs packages                              │
   │  │   ├─ Apply --add-rootfsconfig                                          │
   │  │   └─ Optional: Run rootfs menuconfig                                   │
   │  │                                                                        │
   │  └─ Update User Layers (update_buildconf.py):                             │
   │      └─ Add/Remove layers from bblayers.conf                              │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                    BUILD CONFIGURATION UPDATE                             │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  [update_buildconf.py]                                                    │
   │  ├─ Update local.conf (if --localconf specified):                         │
   │  │   ├─ MACHINE setting                                                   │
   │  │   ├─ Include generated .conf files                                     │
   │  │   └─ PETALINUX specific settings                                       │
   │  │                                                                        │
   │  ├─ Generate auto.conf (optional):                                        │
   │  │   └─ Kconfig-derived configuration                                     │
   │  │                                                                        │
   │  └─ Update bblayers.conf:                                                 │
   │      └─ Add required layers                                               │
   └───────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                           OUTPUT LAYER                                    │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  Generated Files Structure:                                               │
   │  output/                                                                  │
   │  ├─ config                        # System configuration                  │
   │  ├─ gen-machineconf.log          # Tool log                               │
   │  ├─ memory.qemuboot.conf         # QEMU HW DDR map for qemuboot/runqemu  │
   │  ├─ petalinux_config.yaml        # Hardware info YAML                     │
   │  ├─ configs/                     # Kconfig files                          │
   │  │   ├─ Kconfig                                                           │
   │  │   ├─ Kconfig.syshw                                                     │
   │  │   └─ Kconfig.*                                                         │
   │  │                                                                        │
   │  build/conf/ (or --config-dir)                                            │
   │  ├─ machine/                                                              │
   │  │   ├─ <machine>.conf          # Main machine configuration, includes    │
   │  │   │                          # QB_MEM when memory.qemuboot.conf exists │
   │  │   └─ include/<machine>/       # Machine-specific includes              │
   │  │       ├─ microblaze.inc                                                │
   │  │       ├─ <machine>-<target>-libxil.conf                                │
   │  │       └─ <machine>-<target>-features.conf                              │
   │  │                                                                        │
   │  ├─ multiconfig/                  # Multiconfig files                     │
   │  │   ├─ <machine>-<target>.conf  # Per multiconfig target                 │
   │  │   └─ ...                                                               │
   │  │                                                                        │
   │  ├─ dts/                         # Device tree sources                    │
   │  │   ├─ <machine>/                                                        │
   │  │   │   ├─ cortexa*-linux.dts                                            │
   │  │   │   ├─ <machine>-<target>.dts                                        │
   │  │   │   └─ pl-overlay-{full|dfx}/pl.dtsi                                 │
   │  │   └─ system-conf.dtsi                                                  │
   │  │                                                                        │
   │  ├─ plnxtool.conf               # PetaLinux tool conf (if --petalinux)    │
   │  ├─ local.conf                  # Updated local.conf (if --localconf)     │
   │  └─ rootfs_config/              # Rootfs configs (if --petalinux)         │
   │      └─ ...                                                               │
   └───────────────────────────────────────────────────────────────────────────┘
