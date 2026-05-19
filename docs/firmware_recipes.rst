.. Copyright (C) 2022-2026, Advanced Micro Devices, Inc. All rights reserved.

.. SPDX-License-Identifier: MIT

.. _firmware_recipes:

Firmware Recipe Generation
==========================

The ``create-fw-recipe`` helper automates the creation of Yocto firmware recipe
directories for programmable logic overlays produced from a System Device Tree
(SDT) design. It complements the ``gen-machine-conf`` SDT overlay flow by
taking the generated overlay files and packaging them into
``recipes-firmware/<name>-pl-firmware`` content that can be added to a user
layer.

Prerequisites
-------------

Before using create-fw-recipe, ensure you have the following prerequisites installed
and configured:

- Valid SDT hardware description directory or individual overlay files
- Matching FPGA bitstream files (``.pdi``, ``.bit``, or ``.bit.bin``)

Use Cases
---------

Use ``create-fw-recipe`` after you have an SDT hardware description and want to:

- Create a firmware recipe for a full PL overlay generated with
  ``gen-machine-conf --hw-description <sdt-dir> -g full``
- Create a base DFX recipe plus per-partial recipes for designs generated with
  ``gen-machine-conf --hw-description <sdt-dir> -g dfx``
- Reuse an existing ``pl.dtso`` or partial ``*_partial.dtsi`` together with an
  explicit ``.pdi``, ``.bit``, or ``.bit.bin`` file
- Auto-generate default ``shell.json`` or ``accel.json`` metadata when a design
  does not already provide one

Input Modes
-----------

The script supports two input styles.

Hardware-description mode
~~~~~~~~~~~~~~~~~~~~~~~~~

Provide ``--hw-description`` and ``-g/--gen-pl-overlay``. In this mode the
script auto-discovers:

- ``pl.dtsi`` and converts it to ``pl.dtso`` using lopper
- ``system-top.dts`` to detect the processor family required by the lopper
  overlay assist
- Matching ``.pdi``, ``.bit``, or ``.bit.bin`` files using the
  ``firmware-name`` property from ``pl.dtsi`` or ``*_partial.dtsi``
- DFX partial overlays in ``*_partial.dtsi`` files and their matching partial
  FPGA images

This is the recommended mode when the SDT export directory still contains the
original generated files.

Explicit-file mode
~~~~~~~~~~~~~~~~~~

Provide the overlay and FPGA inputs directly:

- ``--dtso`` for the PL overlay source
- ``--fpga`` for the matching ``.pdi``, ``.bit``, or ``.bit.bin`` file
- ``--json`` optionally for design metadata

This mode is useful when the overlay files already exist, or when you want to
generate one recipe at a time from curated inputs.

Generated Output
----------------

The script creates a firmware recipe under the selected layer path, or under the
current working directory if ``--layer-path`` is not provided.

The generated structure is:

.. code-block:: text

   <layer-path>/
   `-- recipes-firmware/
       `-- <recipe-name>-pl-firmware/
           |-- <recipe-name>-pl-firmware.bb
           `-- files/
               |-- <fpga-image>
               |-- <overlay-file>
               `-- <shell.json or accel.json>

The recipe inherits ``dfx_user_dts`` and adds all copied files through
``SRC_URI``.

JSON Metadata Handling
----------------------

If ``--json`` points to an existing file, the script copies it into the
recipe's ``files/`` directory unchanged.

If ``--json`` is omitted, or the specified file is missing, the script creates
default metadata based on the overlay mode:

- ``full`` creates ``shell.json`` with ``shell_type`` set to ``XRT_FLAT``
- ``dfx`` base recipes create ``shell.json`` with ``shell_type`` set to
  ``PL_DFX``
- ``dfx`` partial recipes create ``accel.json`` with ``accel_type`` set to
  ``XRT_PL_DFX``

For DFX designs, review the generated JSON carefully. The defaults contain
placeholder values that may need to be updated, such as:

- ``num_slots``: Number of reconfigurable regions in your design
- ``auto_load``: Whether to load the base design automatically at boot
- Slot-specific configurations and resource allocations

Command-Line Arguments
----------------------

.. code-block:: console

   $ create-fw-recipe -h

Core options:

- ``--hw-description``: Path to the SDT hardware description directory
- ``-g, --gen-pl-overlay {full,dfx}``: Required with ``--hw-description``;
  selects full or DFX overlay handling
- ``--dtso``: Path to an existing PL overlay file
- ``--fpga``: Path to the matching ``.pdi``, ``.bit``, or ``.bit.bin`` file
- ``--json``: Optional metadata JSON file
- ``--recipe-name``: Base name for the generated recipe
- ``--layer-path``: Output layer where ``recipes-firmware`` is created

Behavior notes:

- If ``--hw-description`` is used, ``-g`` is mandatory
- If ``--recipe-name`` is omitted, the recipe name is derived from the FPGA file
  name
- In DFX mode with ``--hw-description``, the script creates one static/base
  recipe first and then creates one recipe per discovered partial overlay

Examples
--------

Generate a full PL firmware recipe directly from an SDT export:

.. code-block:: console

   $ create-fw-recipe --hw-description /path/to/sdt-output -g full

Generate DFX firmware recipes from an SDT export into a custom layer:

.. code-block:: console

   $ create-fw-recipe \
       --hw-description /path/to/dfx-sdt-output \
       -g dfx \
       --recipe-name vek385static \
       --layer-path ../sources/meta-user

Generate a recipe from explicit files:

.. code-block:: console

   $ create-fw-recipe \
       --dtso /path/to/pl.dtso \
       --fpga /path/to/design.pdi \
       --json /path/to/shell.json \
       --recipe-name my-overlay \
       --layer-path ../sources/meta-user

Generate one DFX partial recipe from explicit files:

.. code-block:: console

   $ create-fw-recipe \
       --dtso /path/to/rp0rm0_partial.dtsi \
       --fpga /path/to/rp0rm0_partial.pdi \
       --recipe-name rp0rm0 \
       --layer-path ../sources/meta-user

.. note::

  ``create-fw-recipe`` only supports local files. Remote URLs or network paths
  are not supported for input files.

Recommended Workflow
--------------------

1. Generate SDT outputs and PL overlays with ``gen-machine-conf``.
2. For full or DFX overlay semantics, review the ``-g`` `option details <https://github.com/AMD-AECG-SSW-PUBLIC/gen-machine-conf/blob/master/docs/options.rst>`_.
3. Run ``create-fw-recipe`` to package the overlay and FPGA artifacts into a
   Yocto layer.
4. Inspect any generated ``shell.json`` or ``accel.json`` and replace
   placeholder values before building.
5. Add the generated ``recipes-firmware`` content to your layer and include the
   recipe in the intended image or package flow.


Custom Board Bring-Up with Dual PDI for Versal Boards
-----------------------------------------------------

This section walks through the first-time bring-up of a custom **Versal** or
**Versal-2VE/2VM** board whose Vivado design exports two separate PDI
artifacts — a PS-only boot image and a PL-only image — and shows how to
package the PL artifact as a Yocto firmware recipe.

Overview
~~~~~~~~

In the dual-PDI (also known as *segmented configuration*) flow, Vivado
produces two independent PDI artifacts:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Artifact
     - Purpose
   * - ``*_boot.pdi``
     - PS-only boot image (PLM, PSM, TF-A, U-Boot, etc.)
   * - ``*_pld.pdi``
     - PL-only image programmed at runtime from Linux

This split is commonly referred to as the *segmented PDI* or *dual PDI*
flow. The Vivado bitstream generator emits a PS-only boot image that the
Platform Loader and Manager (PLM) can execute without any PL content, plus
a separate PL-only image that is applied later, at runtime, through the
Linux FPGA manager subsystem.

Step 1 – Create the PL Firmware Recipe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``create-fw-recipe`` to package the PL PDI (``*_pld.pdi``) together with
the device-tree overlay (``pl.dtso``) into a Yocto recipe. The generated
recipe inherits the ``dfx_user_dts`` bbclass, which automatically handles
overlay compilation and FPGA-manager integration during the Yocto build.

**Hardware-description mode (recommended)**

Point at the SDT directory and let the tool discover the files automatically:

.. code-block:: console

   $ create-fw-recipe \
       --hw-description /home/user/my-board-sdt/ \
       -g full \
       --recipe-name my-custom-board \
       --layer-path /home/user/yocto/sources/meta-user/

**Generated structure**

.. code-block:: text

   meta-user/
   └── recipes-firmware/
       └── my-custom-board-pl-firmware/
           ├── my-custom-board-pl-firmware.bb
           └── files/
               ├── myboard_pld.pdi
               ├── pl.dtso
               └── shell.json

The generated ``.bb`` recipe looks like:

.. code-block:: bitbake

   SUMMARY = "static pl firmware using dfx_user_dts bbclass"
   DESCRIPTION = "my-custom-board static PL firmware application"
   LICENSE = "MIT"
   LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=..."

   inherit dfx_user_dts

   SRC_URI = "file://myboard_pld.pdi \
       file://pl.dtso \
       file://shell.json"

**Explicit-file mode**

If you want full control over which files go into the recipe (e.g., you have
already run ``gen-machine-conf`` and have the ``pl.dtso`` on hand), supply
them directly. This is also useful when the ``firmware-name`` property in
``pl.dtsi`` does not match the filename on disk:

.. code-block:: console

   $ create-fw-recipe \
       --fpga /home/user/my-board-sdt/myboard_pld.pdi \
       --dtso /home/user/my-board-sdt/output/dts/pl-overlay-full/pl.dtso \
       --json /home/user/my-board-sdt/shell.json \
       --recipe-name my-custom-board \
       --layer-path /home/user/yocto/sources/meta-user/

.. note::

   The ``--fpga`` argument must point to the PL PDI (``*_pld.pdi``), not the
   boot PDI. The boot PDI is referenced only through ``gen-machine-conf`` and
   the ``PDI_PATH`` variable in the machine conf; it should never appear in a
   firmware recipe.

Step 4 – Review the Generated shell.json
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open the generated ``shell.json`` and verify it matches your design intent:

.. code-block:: json

   {
     "shell_type": "XRT_FLAT",
     "num_slots": "1"
   }

The ``shell.json`` file is metadata consumed by the XRT (Xilinx Runtime)
shell infrastructure and the FPGA manager to understand how the PL image
should be treated at load time.

Step 5 – Add the Recipe to Your Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The firmware recipe produced by ``create-fw-recipe`` is not automatically
added to any image; you must explicitly install it. The most common approach
is to append it to your image recipe's ``IMAGE_INSTALL`` variable.

In your image recipe (e.g., a ``edf-platform-disk-image.bbappend`` file
inside ``meta-user``) add:

.. code-block:: bitbake

   IMAGE_INSTALL:append = " my-custom-board-pl-firmware"

Alternatively, if your project already uses a packagegroup to collect custom
packages, add the firmware package there:

.. code-block:: bitbake

   # In packagegroup-my-board.bb or similar:
   RDEPENDS:${PN} += "my-custom-board-pl-firmware"

The ``dfx_user_dts`` bbclass (inherited by the generated recipe) installs
the following files into the rootfs at build time:

Installed location in target:

.. code-block:: text

   /lib/firmware/xilinx/my-custom-board-pl-firmware/
    ├── myboard_pld.pdi
    ├── pl.dtso
    └── shell.json

Step 6 – Build the Yocto Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ensure the generated machine conf and multiconfig files are on ``BBLAYERS``'s
search path (either inside an existing layer or referenced via ``BBPATH``),
then source your Yocto build environment and build:

.. code-block:: console

   $ source sources/poky/oe-init-build-env build
   $ MACHINE=my-custom-board bitbake edf-platform-disk-image

Step 7 – Deploy and Test on the Custom Board
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Prepare the boot medium**

Format an SD card with at least two partitions:

- Partition 1 (FAT32, ~256 MB): boot files
- Partition 2 (ext4): root filesystem

Copy the boot files to the FAT partition:

.. code-block:: console

   $ cp BOOT.BIN image.ub boot.scr /media/BOOT/

Flash the root filesystem to the ext4 partition:

.. code-block:: console

   $ sudo dd if=edf-platform-disk-image-my-custom-board.rootfs.wic \
       of=/dev/sdX bs=4M status=progress

Or use ``bmaptool`` for faster writes if available.

**Initial power-on**

Insert the SD card and power on the board. The PLM loads
``myboard_boot.pdi``, initialises the PS fabric (DDR, peripherals), starts
TF-A, then hands off to U-Boot and Linux. A serial console at 115200 baud
lets you monitor the boot sequence.

At this point the PL fabric is not yet programmed. Any Linux driver that
depends on PL IP will probe but find its hardware absent. This is the
expected behaviour in the dual-PDI flow.

**Load the PL firmware at runtime**

Once Linux is running, load the PL firmware on the target board (as root)
using ``fpgautil``:

.. code-block:: console

   # fpgautil -b /lib/firmware/xilinx/my-custom-board-pl-firmware/myboard_pld.pdi \
       -o /lib/firmware/xilinx/my-custom-board-pl-firmware/pl.dtso

or, equivalently, using the ``dfx-mgr`` client:

.. code-block:: console

   # dfx-mrng-client load my-custom-board-pl-firmware


Updating PL.PDI / PL.DTSI in Existing Yocto Projects
----------------------------------------------------

This section explains how to update both the PL firmware
(``design_pld.pdi``) and the PL device-tree overlay (``pl.dtsi``) when they
are delivered as individual files by the hardware team, and how to rebuild
*only* the firmware recipe — without rebuilding the full image.

Step 1 — Create a New Firmware Recipe Using Explicit Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``create-fw-recipe`` and explicitly point it at the new PL PDI and DTSI
files:

.. code-block:: console

   $ create-fw-recipe \
       --fpga ~/hw-export/design_pld.pdi \
       --dtso ~/hw-export/pl.dtsi \
       --json ~/hw-export/shell.json \
       --recipe-name my-board \
       --layer-path ~/yocto/sources/meta-user/

This command generates a new firmware recipe under:

.. code-block:: text

   meta-user/recipes-firmware/my-board-pl-firmware/

Step 2 — Verify Recipe Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confirm that the recipe files were generated correctly:

.. code-block:: console

   $ ls ~/yocto/sources/meta-user/recipes-firmware/my-board-pl-firmware/files/

Expected output:

.. code-block:: text

   design_pld.pdi
   pl.dtsi
   shell.json

Step 3 — Review the Generated Recipe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generated recipe (``my-board-pl-firmware.bb``) should look similar to the
following:

.. code-block:: bitbake

   SUMMARY = "static pl firmware using dfx_user_dts bbclass"
   DESCRIPTION = "my-board-pl-firmware static PL firmware application"
   LICENSE = "MIT"
   LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
   inherit dfx_user_dts
   SRC_URI = "file://design_pld.pdi \
       file://pl.dtsi \
       file://shell.json"

.. note::

   **Add ``COMPATIBLE_MACHINE`` to the .bb file.** Always set
   ``COMPATIBLE_MACHINE`` so this firmware recipe is restricted to the
   intended target board only.

Step 4 — Rebuild Only the Firmware Recipe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**4.1 Clear the sstate cache**

Clean the recipe so BitBake does not reuse previously built artifacts:

.. code-block:: console

   $ bitbake my-board-pl-firmware -c cleanall

**4.2 Build only the firmware recipe**

Rebuild only the PL firmware recipe (no full image rebuild):

.. code-block:: console

   $ MACHINE=my-board bitbake my-board-pl-firmware

Expected output ends with:

.. code-block:: text

   NOTE: Tasks Summary:
   NOTE: recipe my-board-pl-firmware-1.0-r0 do_deploy: ...

The PL firmware recipe can now be built and deployed independently.

Deploying the Updated Firmware to the Board (No Reflash Required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After rebuilding, deploy the updated PL firmware to a running system without
reflashing the SD card.

**Step 5 — Copy firmware files to the target board**

From the host system, copy the deployed firmware files to the board:

.. code-block:: console

   $ scp tmp/deploy/images/<machine>/lib/firmware/xilinx/my-board-pl-firmware/* \
       root@<board-ip>:/lib/firmware/xilinx/my-board-pl-firmware/

**Step 6 — Load the new PL firmware at runtime**

*Option A — Using the* ``dfx-mgr`` *daemon*

If your platform uses the ``dfx-mgr`` service, reload the PL firmware
without rebooting:

.. code-block:: console

   # dfx-mgr-client unload my-board-pl-firmware
   # dfx-mgr-client load my-board-pl-firmware


Adding Multiple PL Images to an Existing Project for Runtime Updates
--------------------------------------------------------------------

This section explains how to add and keep multiple programmable-logic (PL)
images — each consisting of a ``PL.PDI`` and a ``PL.DTSI`` — in an existing
Yocto/PetaLinux project, and how to package them so they are all available
in the root filesystem for runtime PL updates while continuing to use the
same ``BOOT.BIN``.

Step 1: Prepare PL Artifacts (per PL image)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each PL image, prepare the following files.

**Example — PL Image A**

.. code-block:: text

   pl_A.dtso
   pl_A.pdi
   pl_A.json

**Example — PL Image B**

.. code-block:: text

   pl_B.dtso
   pl_B.pdi
   pl_B.json

Each set represents one PL image variant.

Step 2: Create a Firmware Recipe for Each PL Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``create-fw-recipe`` in the Yocto environment once per PL image.

**Create the firmware recipe for PL Image A:**

.. code-block:: console

   $ create-fw-recipe \
       --dtso <path to pl.dtso/dtsi> \
       --fpga <path to pl_A.pdi> \
       --json <path to pl_A.json> \
       --recipe-name pl-image-a-firmware \
       --layer-path ../sources/meta-user

**Create the firmware recipe for PL Image B:**

.. code-block:: console

   $ create-fw-recipe \
       --dtso <path to pl_B.dtso/pl.dtsi> \
       --fpga <path to pl_B.pdi> \
       --json <path to pl_B.json> \
       --recipe-name pl-image-b-firmware \
       --layer-path ../sources/meta-user

Step 3: Resulting Recipe Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each PL image gets its own recipe and file set.

.. code-block:: text

   meta-user/
   └── recipes-firmware/
       ├── pl-image-a-firmware/
       │   ├── pl-image-a-firmware.bb
       │   └── files/
       │       ├── pl_A.dtso
       │       ├── pl_A.pdi
       │       └── pl_A.json
       └── pl-image-b-firmware/
           ├── pl-image-b-firmware.bb
           └── files/
               ├── pl_B.dtso
               ├── pl_B.pdi
               └── pl_B.json

Step 4: Add All PL Images to the Root Filesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To keep multiple PL images available at runtime, install all firmware
recipes by appending them to ``IMAGE_INSTALL`` in ``local.conf``:

.. code-block:: bitbake

   IMAGE_INSTALL:append = " pl-image-a-firmware pl-image-b-firmware"

Step 5: Build the Image
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   $ bitbake <image-name>

Both PL images are built and installed in the resulting image.

Step 6: Runtime File Placement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After boot, the PL files are available in the root filesystem, typically
under ``/lib/firmware/``:

Example layout:

.. code-block:: text

   /lib/firmware/pl-image-a-firmware/
    ├── pl_A.pdi
    ├── pl_A.dtbo
    └── pl_A.json

   /lib/firmware/pl-image-b-firmware/
    ├── pl_B.pdi
    ├── pl_B.dtbo
    └── pl_B.json

This structure makes runtime PL selection clear and simple. Deploying and
copying the PL firmware to the target follows the same procedure described
in the previous section.
