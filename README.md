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
$ gen-machineconf -h
usage: gen-machineconf --soc-family [SOC_FAMILY] [--hw-description <PATH_TO_XSA>/<xsa_name>.xsa] [--machine-name] [other options]

PetaLinux/Yocto xsa to Machine Configuration File generation tool

required arguments:
  --soc-family          Specify SOC family type from choice list.
  --hw-description      <PATH_TO_XSA>/<xsa_name>.xsa
                        Specify Hardware(xsa) file or System Device-tree Directory

optional arguments:
  -h, --help            show this help message and exit
  --machine-name        Provide a name to generate machine configuration
  --output              Output directory name
  --xsct-tool           Vivado or Vitis XSCT path to use xsct commands
  --native-sysroot      Native sysroot path to use the mconf/conf commands.
  --sdt-sysroot         Native sysroot path to use lopper utilities.
  --menuconfig {project,rootfs}
                        UI menuconfig option to update configuration.
                        project - To update System Level configurations
                        rootfs  - To update Rootfs configurations
  --petalinux           Update the build/local.conf file with generated .conf files.
  --debug               Output debug information on console
  --add-rootfsconfig    Specify a file with list of package names to add into rootfs menu entry

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

