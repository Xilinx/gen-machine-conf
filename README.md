###### Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
###### Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.

###### SPDX-License-Identifier: MIT

# gen-machine-conf

This repo provides support to generate machine conf and plnxtool.conf 
files for the given HW file.

## Maintainers, Patches/Submissions, Community

Please open pull requests for any changes.

For more details follow the OE community patch submission guidelines, as described in:

https://www.openembedded.org/wiki/Commit_Patch_Message_Guidelines
https://www.openembedded.org/wiki/How_to_submit_a_patch_to_OpenEmbedded

> **Note:** When creating patches, please use below format. To follow best practice,
> if you have more than one patch use `--cover-letter` option while generating the
> patches. Edit the 0000-cover-letter.patch and change the title and top of the
> body as appropriate.

**Syntax:**
`git format-patch -s --subject-prefix="gen-machine-conf][<BRANCH_NAME>][PATCH" -1`

**Example:**
`git format-patch -s --subject-prefix="gen-machine-conf][xlnx_rel_v2023.1][PATCH" -1`

**Maintainers:**

	Mark Hatle <mark.hatle@amd.com>
	Sandeep Gundlupet Raju <sandeep.gundlupet-raju@amd.com>
	John Toomey <john.toomey@amd.com>
	Varalaxmi Bingi <varalaxmi.bingi@amd.com>
	Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
	Swagath Gadde <swagath.gadde@amd.com>
	Ashwini Lomate <ashwini.lomate@amd.com>


## Dependencies

This repo depends on:

	URI: https://git.yoctoproject.org/poky
	layers: meta, meta-poky
	branch: langdale

	URI: https://git.openembedded.org/meta-openembedded
	layers: meta-oe, meta-perl, meta-python, meta-filesystems, meta-gnome,
            meta-multimedia, meta-networking, meta-webserver, meta-xfce,
            meta-initramfs.
	branch: langdale

	URI:
        https://git.yoctoproject.org/meta-xilinx (official version)
        https://github.com/Xilinx/meta-xilinx (development and amd xilinx release)
	layers: meta-xilinx-core, meta-xilinx-microblaze, meta-xilinx-bsp,
            meta-xilinx-standalone, meta-xilinx-vendor.
	branch: langdale or amd xilinx release version (e.g. rel-v2023.1)

	URI:
        https://git.yoctoproject.org/meta-xilinx-tools (official version)
        https://github.com/Xilinx/meta-xilinx-tools (development and amd xilinx release)
	branch: langdale or amd xilinx release version (e.g. rel-v2023.1)

	URI: https://github.com/Xilinx/meta-petalinux
	branch: langdale or amd xilinx release version (e.g. rel-v2023.1)

## PetaLinux/Yocto XSA to Machine conf file generation using gen-machineconf tool

This repo supports PetaLinux/Yocto XSA to Machine conf file generation using
gen-machineconf tool. Below is the gen-machineconf tool usage and examples.

* gen-machineconf usage:

```bash
$ gen-machineconf --help
[INFO] Getting bitbake BBPATH
usage: gen-machineconf [--hw-description [<PATH_TO_XSA>/<xsa_name>.xsa] or <PATH_TO_SDTDIR>] [--soc-family] [--soc-variant] [--machine-name] [-c <config_dir>] [-r] [-O] [--output] [--native-sysroot]
                       [--menuconfig [{project,rootfs}]] [--petalinux] [--add-rootfsconfig] [-D] [-h]
                       <subcommand> ...

PetaLinux/Yocto Machine Configuration File generation tool

required arguments:
  --hw-description [<PATH_TO_XSA>/<xsa_name>.xsa] or <PATH_TO_SDTDIR>
                        Specify Hardware(xsa) file or System Device-tree Directory

options:
  --soc-family          SOC family type from choice list (usually auto detected).
  --soc-variant         SOC Variant: Ex: cg, dr, eg, ev, ai-prime, premium (usually auto detected).
  --machine-name        Provide a name to generate machine configuration
  -c <config_dir>, --config-dir <config_dir>
                        Location of the build conf directory
  -r , --require-machine
                        This machine will be required, instead of the generic machine if defined
  -O , --machine-overrides
                        Provide additional overrides to the generated machine
  --output              Output directory name
  --native-sysroot      Native sysroot path to use the mconf/conf or lopper commands.
  --menuconfig [{project,rootfs}]
                        UI menuconfig option to update configuration(default is project).
                        project - To update System Level configurations
                        rootfs  - To update Rootfs configurations
  --petalinux           Generate Rootfs and PetaLinux Tool conf files and update the build/local.conf file with generated .conf files.
  --add-rootfsconfig    Specify a file with list of package names to add into rootfs menu entry
  -D, --debug           Enable debug output
  -h, --help            show this help message and exit

subcommands:
  <subcommand>
    parse-xsa           Parse xsa file and generate Yocto/PetaLinux configurations.
    parse-sdt           Parse System devicet-tree file and generate Yocto/PetaLinux configurations.

Use gen-machineconf <subcommand> --help to get help on a specific command
$
```

* gen-machineconf parse-xsa usage:

```bash
$ gen-machineconf parse-xsa --help
usage: gen-machineconf parse-xsa [--hw-description <PATH_TO_XSA>/<xsa_name>.xsa] [other options]

options:
  -h, --help            show this help message and exit
  --xsct-tool [XSCT_TOOL_PATH]
                        Vivado or Vitis XSCT path to use xsct commands
$

```

* gen-machineconf parse-sdt usage:

```bash
$ gen-machineconf parse-sdt --help
usage: gen-machineconf parse-sdt [--hw-description <PATH_TO_SDTDIR>] [other options]

options:
  -h, --help            show this help message and exit
  -g {full,dfx-static,dfx-partial}, --gen-pl-overlay {full,dfx-static,dfx-partial}
                        Generate pl overlay for full, dfx-static and dfx-partial configuration using xlnx_overlay_dt lopper script
  -d <domain_file>, --domain-file <domain_file>
                        Path to domain file (.yaml/.dts)
  -p <psu_init_path>, --psu-init-path <psu_init_path>
                        Path to psu_init files, defaults to system_dts path
  -i <pdi path>, --fpga <pdi path>
                        Path to pdi file
  -l <config_file>, --localconf <config_file>
                        Write local.conf changes to this file
  --dts-path <dts_path>
                        Absolute path or subdirectory of conf/dts to place DTS files in (usually auto detected from DTS)
$
```

> **NOTE:** You can find the default BSP machine conf file names at `<gen-machine-conf>/gen-machine-scripts/data/machineconf.json`

* MicroBlaze:

```bash
# Custom xsa method
$ gen-machineconf --soc-family microblaze --hw-description /<PATH_TO_CUSTOM_XSA>/kc705-microblazeel/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family microblaze --hw-description /<PATH_TO_HDF_ARTIFACTORY>/kc705-microblazeel/system.xsa --machine-name kc705-microblazeel --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct
```

* Zynq-7000:

```bash
# Custom xsa method
$ gen-machineconf --soc-family zynq --hw-description /<PATH_TO_CUSTOM_XSA>/zc702-zynq7/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family zynq --hw-description /<PATH_TO_HDF_ARTIFACTORY>/zc702-zynq7/system.xsa --machine-name zc702-zynq7 --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct
```

* ZynqMP:

```bash
# Custom xsa method
$ gen-machineconf --soc-family zynqmp --hw-description /<PATH_TO_CUSTOM_XSA>/zcu106-zynqmp/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family zynqmp --hw-description /<PATH_TO_HDF_ARTIFACTORY>/zcu106-zynqmp/system.xsa --machine-name zcu106-zynqmp --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct
```

* Versal:

```bash
# Custom xsa method
$ gen-machineconf --soc-family versal --hw-description /<PATH_TO_CUSTOM_XSA>/vck190-versal/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family versal --hw-description /<PATH_TO_HDF_ARTIFACTORY>/vck190-versal/system.xsa --machine-name vck190-versal --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct
```

