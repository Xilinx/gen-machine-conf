# meta-xilinx-internal

This layer provides support for internal device machine conf, apps and packages.

## Maintainers, Patches/Submissions, Community

Please open pull requests for any changes.

For more details follow the OE community patch submission guidelines, as described in:

https://www.openembedded.org/wiki/Commit_Patch_Message_Guidelines
https://www.openembedded.org/wiki/How_to_submit_a_patch_to_OpenEmbedded

When creating patches, please use below format.

**Syntax:**
`git format-patch -s --subject "meta-xilinx-internal][<release-version>][PATCH" -1`

**Example:**
`git format-patch -s --subject "meta-xilinx-internal][rel-v2022.1][PATCH" -1`

**Maintainers:**

	Mark Hatle <mark.hatle@amd.com>
	Sandeep Gundlupet Raju <sandeep.gundlupet-raju@amd.com>
	John Toomey <john.toomey@amd.com>

## Dependencies

This layer depends on:

	URI: https://git.openembedded.org/bitbake

	URI: https://git.openembedded.org/openembedded-core
	layers: meta, meta-poky

	URI: https://git.yoctoproject.org/meta-xilinx
	layers: meta-xilinx-microblaze, meta-xilinx-bsp, meta-xilinx-core,
		meta-xilinx-pynq, meta-xilinx-contrib, meta-xilinx-standalone,
		meta-xilinx-vendor.

	URI: https://github.com/Xilinx/meta-petalinux


	branch: master or xilinx current release version (e.g. hosister)

## Yocto XSA to Machine conf file generation using gen-machineconf tool

This layer supports Yocto XSA to Machine conf file generation using gen-machineconf tool. Below is the gen-machineconf tool usage and examples.

* gen-machineconf usage:

```bash
$ gen-machineconf -h
usage: gen-machineconf --soc-family [SOC_FAMILY] [--hw-description <PATH_TO_XSA>/<xsa_name>.xsa][--custom | --bsp zcu102-zynqmp]  [--machine-name] [other options]

Yocto xsa to Machine Configuration File generation tool

required arguments:
  --soc-family          Specify SOC family type from choice list.
  --hw-description      <PATH_TO_XSA>/<xsa_name>.xsa
                        Specify Hardware(xsa) file

  --custom              Specify whether BSP is for custom board.
  --bsp zcu102-zynqmp   Specify BSP name for Xilinx evaluation board, Use the
                        BSP name from choice list. For example: zcu102-zynqmp
                        or vck190-versal

optional arguments:
  -h, --help            show this help message and exit
  --custom              Specify whether BSP is for custom board.
  --bsp zcu102-zynqmp   Specify BSP name for Xilinx evaluation board, Use the
                        BSP name from choice list. For example: zcu102-zynqmp
                        or vck190-versal
  --machine-name        Provide a name for generated machine configuration
  --output              Output directory name
  --xsct-tool           Vivado or Vitis XSCT path to use xsct commands
  --native-sysroot      Native sysroot path to use the mconf/conf commands.
  --menuconfig          UI menuconfig option to update configuration.
```

* Microblaze gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family microblaze --hw-description /<PATH_TO_CUSTOM_XSA>/kc705-microblazeel/system.xsa --custom --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct

# BSP method:
$ gen-machineconf --soc-family microblaze --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/kc705-microblazeel/system.xsa --bsp kc705-microblazeel --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct
```


* Zynq-7000 gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family zynq --hw-description /<PATH_TO_CUSTOM_XSA>/zc702-zynq7/system.xsa --custom --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct

# BSP method:
$ gen-machineconf --soc-family zynq --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/zc702-zynq7/system.xsa --bsp zc702-zynq7 --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct
```

* ZynqMP gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family zynqmp --hw-description /<PATH_TO_CUSTOM_XSA>/zcu106-zynqmp/system.xsa --custom --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct

# BSP method:
$ gen-machineconf --soc-family zynqmp --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/zcu106-zynqmp/system.xsa --bsp zcu106-zynqmp --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct
```

* Versal gen-machineconf example:

```bash
# Custom xsa method
$ gen-machineconf --soc-family versal --hw-description /<PATH_TO_CUSTOM_XSA>/vck190-versal/system.xsa --custom --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct

# BSP method:
$ gen-machineconf --soc-family versal --hw-description /<PATH_TO_HDF_EXAMPLES>/hdf-examples/vck190-versal/system.xsa --bsp vck190-versal --xsct-tool /proj/petalinux/2022.2/petalinux-v2022.2_daily_latest/tool/petalinux-v2022.2-final/tools/xsct
```

