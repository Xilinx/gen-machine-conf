###### Copyright (C) 2021-2022, Xilinx, Inc.  All rights reserved.
###### Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.

###### SPDX-License-Identifier: MIT

# gen-machine-conf

This repo provides support to generate machine conf and plnxtool.conf 
files for the given HW file.

## Maintainers, Patches/Submissions, Community

Please open pull requests for any changes.

For more details follow the OE community patch submission guidelines, as described in:

https://www.openembedded.org/wiki/Commit_Patch_Message_Guidelines
https://www.openembedded.org/wiki/How_to_submit_a_patch_to_OpenEmbedded

When creating patches, please use below format.

**Syntax:**
`git format-patch -s --subject "gen-machine-conf][<release-version>][PATCH" -1`

**Example:**
`git format-patch -s --subject "gen-machine-conf][rel-v2023.1][PATCH" -1`

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

	URI: https://git.openembedded.org/bitbake

	URI: https://git.openembedded.org/openembedded-core
	layers: meta, meta-poky

	URI: https://git.yoctoproject.org/meta-xilinx
	layers: meta-xilinx-microblaze, meta-xilinx-bsp, meta-xilinx-core,
		meta-xilinx-pynq, meta-xilinx-contrib, meta-xilinx-standalone,
		meta-xilinx-vendor.

	URI: https://github.com/Xilinx/meta-petalinux


	branch: master or xilinx current release version (e.g. hosister)

## PetaLinux/Yocto XSA to Machine conf file generation using gen-machineconf tool

This layer supports PetaLinux/Yocto XSA to Machine conf file generation using 
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

* Microblaze gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family microblaze --hw-description /<PATH_TO_CUSTOM_XSA>/kc705-microblazeel/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family microblaze --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/kc705-microblazeel/system.xsa --machine-name kc705-microblazeel --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

```
NOTE: You can find the default BSP machine conf file names at <gen-machine-conf>/gen-machine-scripts/data/machineconf.json

* Zynq-7000 gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family zynq --hw-description /<PATH_TO_CUSTOM_XSA>/zc702-zynq7/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family zynq --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/zc702-zynq7/system.xsa --machine-name zc702-zynq7 --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

```
NOTE: You can find the default BSP machine conf file names at <gen-machine-conf>/gen-machine-scripts/data/machineconf.json

* ZynqMP gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family zynqmp --hw-description /<PATH_TO_CUSTOM_XSA>/zcu106-zynqmp/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family zynqmp --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/zcu106-zynqmp/system.xsa --machine-name zcu106-zynqmp --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

```
NOTE: You can find the default BSP machine conf file names at <gen-machine-conf>/gen-machine-scripts/data/machineconf.json

* Versal gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family versal --hw-description /<PATH_TO_CUSTOM_XSA>/vck190-versal/system.xsa --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

# BSP method:
$ gen-machineconf --soc-family versal --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/vck190-versal/system.xsa --machine-name vck190-versal --xsct-tool /<PETALINUX_INSTALLATION_DIR>/tools/xsct

```
NOTE: You can find the default BSP machine conf file names at <gen-machine-conf>/gen-machine-scripts/data/machineconf.json

