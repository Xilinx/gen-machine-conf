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
