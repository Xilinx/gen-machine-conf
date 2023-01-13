# Copyright (C) 2014-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

proc uboot_memory_config args {
	set fid [lindex $args 0]
        set kconfig_fid [lindex $args 1]
	global target_cpu kconfig_dict out_dir
	set cpu_arch [get_sw_proc_arch $target_cpu]

	puts $fid "\n/* Memory testing handling */"
	uboot_conf_define $fid CONFIG_SYS_MEMTEST_START [dict get $kconfig_dict memory baseaddr]
	uboot_conf_define $fid CONFIG_SYS_MEMTEST_END "([dict get $kconfig_dict memory baseaddr] + 0x1000)"

	set size "0x400000"

	# Set the TEXT_BASE
	set mem_base [dict get $kconfig_dict memory baseaddr]
	set uboot_offset [dict get $kconfig_dict memory "u__boot_textbase_offset"]
	set uboot_textbase [format "0x%08x" [expr $mem_base + $uboot_offset]]
	if {[string equal -nocase $cpu_arch "armv7"] == 1} {
		uboot_set_kconfig_value $kconfig_fid CONFIG_TEXT_BASE ${uboot_textbase}
		uboot_conf_define $fid CONFIG_SYS_LOAD_ADDR   "[dict get $kconfig_dict memory baseaddr] /* default load address */"
	} elseif {[string equal -nocase $cpu_arch "armv8"] == 1} {
		uboot_conf_define $fid CONFIG_SYS_LOAD_ADDR "([dict get $kconfig_dict memory baseaddr] + ${uboot_offset}) /* default load address */"
		uboot_conf_define $fid CONFIG_SYS_INIT_SP_ADDR "(CONFIG_SYS_LOAD_ADDR - GENERATED_GBL_DATA_SIZE)"
	} else {
		uboot_conf_define $fid CONFIG_SYS_LOAD_ADDR   "[dict get $kconfig_dict memory baseaddr] /* default load address */"
	}

	if {[string equal -nocase $cpu_arch "microblaze"] == 1} {
		puts $fid "\n/* global pointer options */"
		set size "0x100000"
	} elseif {"${cpu_arch}" == "armv7"} {
		# PetaLinux u-boot auto config generation supports one bank only for Zynq
		set main_mem_bank 1
		puts $fid "#define CONFIG_NR_DRAM_BANKS	${main_mem_bank}"
		set size "0xC00000"
	} else {
		# PetaLinux u-boot auto config generation supports one bank only for Zynq
		set main_mem_bank 2
		puts $fid "#define CONFIG_NR_DRAM_BANKS	${main_mem_bank}"
		set size "0x2000000"
	}

	puts $fid "\n/* Size of malloc() pool */"
	if {[string equal -nocase $cpu_arch "microblaze"] == 1} {
		puts $fid "\n/* stack */"
		uboot_conf_define $fid CONFIG_SYS_INIT_SP_OFFSET "(CONFIG_TEXT_BASE - CONFIG_SYS_MALLOC_F_LEN)"
		puts $fid "\n/* No of_control support yet*/"
	}

	if {[string equal -nocase $cpu_arch "armv7"] == 1} {
	# FIXME: check target cpu is arm before inserter
		puts $fid "\n/* Physical Memory Map */"
		# use OCM3 - 4KB
		uboot_conf_define $fid CONFIG_SYS_INIT_RAM_ADDR 0xFFFF0000
		uboot_conf_define $fid CONFIG_SYS_INIT_RAM_SIZE 0x2000
		puts $fid {#define CONFIG_SYS_INIT_SP_ADDR	(CONFIG_SYS_INIT_RAM_ADDR + \
				CONFIG_SYS_INIT_RAM_SIZE - \
				GENERATED_GBL_DATA_SIZE)}
	}
}

proc uart_get_baudrate args {
	set fid [lindex $args 0]
	global kconfig_dict
	set baudrate 115200
	if {[dict exists $kconfig_dict serial]} {
		dict for {key value} [dict get $kconfig_dict serial] {
			if {[regexp "baudrate_(600|9600|28800|115200|230400|460800|921600)" $key matched] && \
				[string equal "y" $value]} {
					set baudrate [regsub -all {baudrate_} $key {}]
			}
		}
		uboot_conf_define $fid "CONFIG_BAUDRATE" $baudrate
	}
}

proc spi_flash_get_cs args {
	set fid [lindex $args 0]
	global kconfig_dict
	set cs 0
	if {[dict exists $kconfig_dict flash]} {
		dict for {key value} [dict get $kconfig_dict flash] {
			if {[regexp "cs[0-3]" $key matched] && \
				[string equal "y" $value]} {
					set cs [regsub -all {cs} $key {}]
			}
		}
		uboot_conf_define $fid "XILINX_SPI_FLASH_CS" $cs
	}
}

proc gen_jffs2_config {fid db_dict ip main_key config_cat config_var} {
	# FIXME: i don't think we need this.
	# TODO: check if jffs2 used and fetch the partition name and mtdparts
	set data {
/* JFFS2 partitions */
#define CONFIG_MTD_DEVICE /* needed for mtdparts commands */
#define CONFIG_FLASH_CFI_MTD
#define MTDIDS_DEFAULT "nor0=@mtdpartsname@"

/* default mtd partition table */
#define MTDPARTS_DEFAULT "mtdparts=@mtdparts@"
#endif}

	#puts $fid $data
}

proc report_partition_layout {part_name} {
	global kconfig_dict
	#lassign {"-" "-" "-" "-"}
	set media {null}
	set image {null}
	set offset {null}
	set size {null}
	set cntl_base {null}
	if {[dict exists $kconfig_dict adv_partition $part_name]} {
		if {[dict exists $kconfig_dict adv_partition $part_name "media"]} {
			set media [dict get $kconfig_dict adv_partition $part_name "media"]
		}
		if {[dict exists $kconfig_dict adv_partition $part_name "image"]} {
			set image [dict get $kconfig_dict adv_partition $part_name "image"]
		}
		if {[dict exists $kconfig_dict adv_partition $part_name "offset"]} {
			set offset [dict get $kconfig_dict adv_partition $part_name "offset"]
		}
		if {[dict exists $kconfig_dict adv_partition $part_name "size"]} {
			set size [dict get $kconfig_dict adv_partition $part_name "size"]
		}
		if {[dict exists $kconfig_dict adv_partition $part_name "flash_type"]} {
			set media [dict get $kconfig_dict adv_partition $part_name "flash_type"]
		}
		if {[dict exists $kconfig_dict adv_partition $part_name "cntl_base"]} {
			set cntl_base [dict get $kconfig_dict adv_partition $part_name "cntl_base"]
		}
		return "$media $image $offset $size $cntl_base"
	}
}

proc uboot_preboot_cmd {fid} {
	global kconfig_dict eth_count
	set hostname "Xilinx-U-BOOT"
	if {[dict exist $kconfig_dict subsys_conf hostname]} {
		set hostname [dict get $kconfig_dict subsys_conf hostname]
	}
	# preboot command
	set dhcp_cmd ""
	puts $fid "\n/* PREBOOT */"
	set data "#define CONFIG_PREBOOT	\"echo U-BOOT for ${hostname};setenv preboot; echo; @dhcp@\""
	if {[dict exists $kconfig_dict ethernet use_dhcp]} {
		set use_dhcp [dict get $kconfig_dict ethernet use_dhcp]
		if {[string equal $use_dhcp "y"] && $eth_count > 0} {
			set dhcp_cmd "dhcp"
		}
	}
	regsub -all {@dhcp@} $data $dhcp_cmd data
	puts $fid $data
}

proc uboot_bootcmd {} {
	global eth_count

	set kernel_in [lindex [report_partition_layout kernel] 0]
	set data2ram_cmd ""
	set bootcmd {bootm}
	set dtb_in [lindex [report_partition_layout dtb] 0]
	if {[regexp "(nor|spi|nand|sd|ethernet)" $dtb_in matched]} {
		set bootcmd {booti}
	}
	if {![string equal "" $kernel_in]} {
		if {[info exists kernel_in]} {
			switch -exact $kernel_in {
				"nor" -
				"spi" -
				"nand" -
				"ethernet" {
					set data2ram_cmd {run cp_kernel2ram}
					append bootcmd { ${netstart}}
				}
				"sd" {
					set data2ram_cmd {run uenvboot; run cp_kernel2ram}
					append bootcmd { ${netstart}}
				}
			}
		}
	}
	if {[string equal "bootm" $bootcmd] || [string equal "booti" $bootcmd]} {
		if {$eth_count > 0} {
			set data2ram_cmd {tftpboot ${netstart} ${kernel_img}}
			set bootcmd { ${netstart}}
		}
	}
	if {[string equal "bootm" $bootcmd] || [string equal "booti" $bootcmd]} {
		set bootcmd {echo No boot method defined!!!}
	} else {
		if {![string equal "" ${dtb_in}]} {
			switch -exact ${dtb_in} {
				"nor" {
					append bootcmd " - " {${dtbstart}}
				}
				"spi" -
				"nand" -
				"sd" -
				"ethernet" {
					if {[string equal "" "${data2ram_cmd}"]} {
						set data2ram_cmd {run cp_data2ram}
					} else {
						append data2ram_cmd { && run cp_dtb2ram}
					}
					append bootcmd " - " {${dtbnetstart}}
				}
			}
		}
		if {![string equal "" "${data2ram_cmd}"]} {
			set bootcmd "${data2ram_cmd} && ${bootcmd}"
		}
	}
	set data "\n/* BOOTCOMMAND */"
	append data "\n" {#define CONFIG_BOOTCOMMAND	} "\"run default_bootcmd\""
	return [list "${data}" "${bootcmd}"]
}

proc uboot_bootenv {fid kconfig_fid} {
	global target_cpu eth_count ps_sdio_count kconfig_dict sys_part_list

	set cpu_arch [get_sw_proc_arch $target_cpu]
	set got_sd 0
	set got_flash 0
	set got_flash_type "null"
	set sdbootdev 0
	set primary_sd [get_primary_inst_name "sd"]
	if {[string length $primary_sd] > 0} { set got_sd 1 }
	if {[dict exists $kconfig_dict flash inst_name]} { set got_flash 1}
	if {[dict exists $kconfig_dict flash flash_type]} {
		set got_flash_type [dict get $kconfig_dict flash flash_type]
	}
	gen_bootenv_define $fid $kconfig_fid
	uboot_preboot_cmd $fid
	if {$got_sd == 1 && $ps_sdio_count >1 } {
		if {[regexp "ps[7u]_sd_1" $primary_sd matched]} { set sdbootdev 1 }
	}

	set bootenv_in "nowhere"
	foreach part_tmp $sys_part_list {
		set part_info [report_partition_layout $part_tmp]
		if {[string equal "" $part_info]} {continue}
		eval "lassign \{$part_info\} ${part_tmp}_in ${part_tmp}_image ${part_tmp}_offset ${part_tmp}_size ${part_tmp}_cntl_base"
	}

	puts $fid "\n/* Extra U-Boot Env settings */"
	puts $fid "#define CONFIG_EXTRA_ENV_SETTINGS \\"
	# common setting for serial multi
	if {[dict exists $kconfig_dict serial]} {
	puts $fid {	SERIAL_MULTI \
	CONSOLE_ARG \ }
	}
	if {[dict exists $kconfig_dict usb]} {
		puts $fid {	DFU_ALT_INFO_RAM \ }
		if { $got_sd == 1 } {
			puts $fid {	DFU_ALT_INFO_MMC \ }
			uboot_set_kconfig_value $kconfig_fid "DFU_MMC" "y"
		}
	}
	set count_list "ps_uart_count@PSSERIAL uartfull_count@ESERIAL uartlite_count@TTYUL"
	foreach data_string $count_list {
		set fields [split $data_string "@"]
		set count_var_namne [lindex $fields 0]
		set uart_string [lindex $fields 1]
		eval global $count_var_namne
		eval set uart_count_tmp $$count_var_namne
		set tmp 0
		while {$tmp < $uart_count_tmp} {
			puts $fid "	$uart_string$tmp \\ "
			incr tmp
		}
	}

	# netconsole args if ethernet available
	if {$eth_count > 0} {
		set data {	"nc=setenv stdout nc;setenv stdin nc;\0" \ }
			puts $fid $data
	if { [ llength [ gen_eth_env_data ] ] > 0 } {
		set data "\t[ gen_eth_env_data ]"
			puts $fid $data
	}
	}
	# removed
	# NETCONSOLE NCIP
	#	"ncip=@serverip@\0" \

	set netoffset [dict get $kconfig_dict subsys_conf netboot_offset]
	# check memory based address
	set mem_base [dict get $kconfig_dict memory baseaddr]
	set nstart [format "0x%08x" [expr $mem_base + 0x0]]
	set dtbnstart [format "0x%08x" [expr $nstart + 0x1E00000]]
	set rfsnstart [format "0x%08x" [expr $nstart + 0x2E00000]]
	set loadbootenv [format "0x%08x" [expr $mem_base + 0x100000]]
	set nstartaddr [format "0x%08x" [expr $nstart + $netoffset]]
	set data {	"autoload=no\0" \
	"sdbootdev=@sdbootdev@\0" \
	"clobstart=@nstart@\0" \
	"netstart=@nstart@\0" \
	"dtbnetstart=@dtbnstart@\0" \
	"netstartaddr=@nstartaddr@\0" \
	"bootcmd=bootm @nstart@ @rfsnstart@ @dtbnstart@\0" \
	"loadaddr=@nstart@\0" \ }
	regsub -all {@nstart@} $data $nstart data
	regsub -all {@sdbootdev@} $data $sdbootdev data
	regsub -all {@rfsnstart@} $data $rfsnstart data
	regsub -all {@nstartaddr@} $data $nstartaddr data

	# check if initrd is used and set initrd_high env
	if {[dict exists $kconfig_dict subsys_conf rootfs_initrd]} {
		set initrd_high [dict get $kconfig_dict subsys_conf initrd_ramdisk_loadaddr]
		append data "\n" {	"initrd_high=@initrd_high@\0" \ }
		regsub -all {@initrd_high@} $data $initrd_high data
	}
	# what about sd based system (no flash)
	# TODO: clean up
	if {$got_flash == 1 || $got_sd == 1} {
		foreach part_tmp $sys_part_list {
			eval "set rt [info exists ${part_tmp}_size]"
			if {$rt == 0} {continue}
			eval "set tmp_part_size \$${part_tmp}_size"
			set test_crc "test_img"
			if {![string equal "null" $tmp_part_size]} {
				# output partition info and commands
				# FIXME: use eval to simplified the code
				switch -exact $part_tmp {
					"kernel" {
						set test_crc "test_crc"
					}
					"dtb" {
						if {$eth_count > 0} {
							# FIXME: this is will not work correctly
							if {[string equal "null" $dtb_offset]} {
								set dtb_offset "0x180000"
								set rdtb_offset $dtb_offset
							} else {
								set cntl_base "0x0"
								if {![string equal "null" $dtb_offset] && \
									[string equal "nor" $dtb_in]} {
									set cntl_base $dtb_cntl_base
								}
								set rdtb_offset [format "0x%x" [expr $dtb_offset - $cntl_base]]
							}
							set dtbnstart [format "0x%x" [expr $rdtb_offset + $nstart]]
						}
						append data "\n" { "get_dtb=run cp_dtb2ram; fdt addr ${dtbnetstart}\0" \ }
					}
				}

				eval "append data \"\\n\" \{	\"${part_tmp}size=@tsize@\\0\" \\
	\"${part_tmp}start=@tstart@\\0\" \\ \}"
				eval regsub -all {@tsize@} \$data \$${part_tmp}_size data
				eval regsub -all {@tstart@} \$data \$${part_tmp}_offset data
			}
			# this should also handle the files
			eval "set rt [info exists ${part_tmp}_image]"
			if {$rt == 1} {
				eval set var_tmp \$${part_tmp}_image
				if {![string equal "null" $var_tmp]} {
					append data "\n" {	"@filevar@=@imagefile@\0" \ }
					if {$eth_count > 0} {
						append data "\n" {	"load_@part_type@=tftpboot ${clobstart} ${@filevar@}\0" \ }
						append data "\n" {	"update_@part_type@=setenv img @part_type@; setenv psize ${@part_type@size}; setenv installcmd \"install_@part_type@\"; run load_@part_type@ @test_crc@; setenv img; setenv psize; setenv installcmd\0" \ }
					}
					eval set part_in \$${part_tmp}_in
					if {$got_sd == 1 && ! [string equal ${part_in} "sd"] } {
						append data "\n" {	"sd_update_@part_type@=echo Updating @part_type@ from SD; mmcinfo && fatload mmc ${sdbootdev}:1 ${clobstart} ${@filevar@} && run install_@part_type@\0" \ }
					}
					# no crc test for SD card
					if {[string equal ${part_in} "sd"] } {
						set test_crc "\${installcmd}"
					}
					regsub -all {@part_type@} $data "${part_tmp}" data
					eval regsub -all {@imagefile@} \$data \$${part_tmp}_image data
					regsub -all {@filevar@} $data "${part_tmp}_img" data
					regsub -all {@test_crc@} $data ${test_crc} data
				}
			}
			eval "set flash_typ \$${part_tmp}_in"
			set flash_opt_cmd [gen_flash_env $flash_typ $part_tmp $got_sd]
			if {![string equal "null" $flash_opt_cmd]} {
				append data "\n" $flash_opt_cmd
			}
		}
		regsub -all {@dtbnstart@} $data $dtbnstart data
		if {$got_sd == 1} {
			append data "\n" {	"loadbootenv_addr=@loadbootenv@\0" \ }
			regsub -all {@loadbootenv@} $data $loadbootenv data
			puts $fid {	"bootenv=uEnv.txt\0" \ }
			puts $fid {	"importbootenv=echo \"Importing environment from SD ...\"; " \ }
			puts $fid {		"env import -t ${loadbootenv_addr} $filesize\0" \ }
			puts $fid {	"loadbootenv=load mmc $sdbootdev:$partid ${loadbootenv_addr} ${bootenv}\0" \ }
			puts $fid {	"sd_uEnvtxt_existence_test=test -e mmc $sdbootdev:$partid /uEnv.txt\0" \ }
			puts $fid {	"uenvboot=" \ }
			puts $fid {		"if run sd_uEnvtxt_existence_test; then " \ }
			puts $fid {			"run loadbootenv; " \ }
			puts $fid {			"echo Loaded environment from ${bootenv}; " \ }
			puts $fid {			"run importbootenv; " \ }
			puts $fid {			"fi; " \ }
			puts $fid {		"if test -n $uenvcmd; then " \ }
			puts $fid {			"echo Running uenvcmd ...; " \ }
			puts $fid {			"run uenvcmd; " \ }
			puts $fid {		"fi\0" \ }
		}
		append data "\n" {	"fault=echo ${img} image size is greater than allocated place - partition ${img} is NOT UPDATED\0" \
	"test_crc=if imi ${clobstart}; then run test_img; else echo ${img} Bad CRC - ${img} is NOT UPDATED; fi\0" \
	"test_img=setenv var \"if test ${filesize} -gt ${psize}\\; then run fault\\; else run ${installcmd}\\; fi\"; run var; setenv var\0" \ }
	}

	if {[string equal "nowhere" $bootenv_in] && \
		$got_flash == 0 && $got_sd == 0} {
		#FIXME: this is not ready yet
		set bootfile "u-boot-s.bin"
		if {[string equal -nocase $cpu_arch "armv7"] == 1} {
			set bootfile "BOOT.BIN"
		}
		set netoffset [dict get $kconfig_dict subsys_conf netboot_offset]
		set mem_base [dict get $kconfig_dict memory baseaddr]
		set nstart [format "0x%08x" [expr $mem_base + $netoffset]]
		set dtbnstart [format "0x%08x" [expr $mem_base + 0x1E00000]]
		# check arch for bootfile
		append data "\n" {	"boot_img=@bootfile@\0" \
	"kernel_img=image.ub\0" \
	"dtb_img=system.dtb\0" \
	"netstart=@nstart@\0" \
	"dtbnetstart=@dtbnstart@\0" \
	"loadaddr=@nstart@\0" \ }
		regsub -all {@bootfile@} $data $bootfile data
		regsub -all {@nstart@} $data $nstart data
		regsub -all {@dtbnstart@} $data $dtbnstart data
	}

	# check if kernel_img is in the data if not add it as it is required
	# sdboot and netboot
	if {${eth_count} > 0 || ${got_sd} == 1} {
		if {[regexp "kernel_img=" $data] == 0} {
			puts "Warning: kernel_img variable not set. Set to kernel_img=image.ub"
			append data "\n" {	"kernel_img=image.ub\0" \ }
		}
	}

	if {${eth_count} > 0} {
		append data "\n" {	"netboot=tftpboot ${netstartaddr} ${kernel_img} && bootm\0" \ }
	}

	set uboot_cmd_list [ uboot_bootcmd ]
	set default_bootcmd [lindex ${uboot_cmd_list} 1]
	set uboot_cmd_data [lindex ${uboot_cmd_list} 0]
	append data "\n" "	\"default_bootcmd=bootcmd\\0\"" { \ }
	append data "\n" "\"\""
	append data "\n" ${uboot_cmd_data}
	puts $fid $data
}

proc gen_flash_env {flash_typ part_tmp got_sd} {
	set data {null}
	switch -exact $flash_typ {
		"nor" {
			set data {	"install_@part_tmp@=protect off ${@part_tmp@start} +${@part_tmp@size} && erase ${@part_tmp@start} +${@part_tmp@size} && " \
		"cp.b ${clobstart} ${@part_tmp@start} ${filesize}\0" \ }
			switch -exact $part_tmp {
				"bootenv" {
					set data {	"eraseenv=protect off ${bootenvstart} +${bootenvsize} && erase ${bootenvstart} +${bootenvsize}\0" \ }
				}
				"dtb" {
					append data "\n" {	"cp_dtb2ram=cp.b ${dtbstart} ${dtbnetstart} ${dtbsize}\0" \ }
				}
				"kernel" {
					append data "\n" {	"cp_kernel2ram=cp.b ${kernelstart} ${netstart} ${@part_tmp@size}\0" \ }
				}
			}
		}
		"spi" {
			set data {	"install_@part_tmp@=sf probe 0 && sf erase ${@part_tmp@start} ${@part_tmp@size} && " \
		"sf write ${clobstart} ${@part_tmp@start} ${filesize}\0" \ }
			switch -exact $part_tmp {
				"bootenv" {
					set data {	"eraseenv=sf probe 0 && sf erase ${bootenvstart} ${bootenvsize}\0" \ }
				}
				"dtb" {
					append data "\n" {	"cp_dtb2ram=sf probe 0 && sf read ${dtbnetstart} ${dtbstart} ${dtbsize}\0" \ }
				}
				"kernel" {
					append data "\n" {	"cp_kernel2ram=sf probe 0 && sf read ${netstart} ${kernelstart} ${kernelsize}\0" \ }
				}
			}
		}
		"nand" {
			set data {	"install_@part_tmp@=nand erase ${@part_tmp@start} ${@part_tmp@size} && " \
		"nand write ${clobstart} ${@part_tmp@start} ${@part_tmp@size}\0" \ }
			switch -exact $part_tmp {
				"bootenv" {
					set data {	"eraseenv=nand erase ${bootenvstart} ${bootenvsize}\0" \ }
				}
				"dtb" {
					append data "\n" {	"cp_dtb2ram=cp.b ${dtbstart} ${dtbnetstart} ${dtbsize}\0" \ }
				}
				"kernel" {
					append data "\n" {	"cp_kernel2ram=nand read ${netstart} ${kernelstart} ${kernelsize}\0" \ }
				}
			}
		}
		"sd" {
			set data {	"install_@part_tmp@=mmcinfo && fatwrite mmc ${sdbootdev} ${clobstart} ${@part_tmp@_img} ${filesize}\0" \ }
			switch -exact $part_tmp {
				"dtb" {
					append data "\n" {	"cp_dtb2ram=mmcinfo && fatload mmc ${sdbootdev}:1 ${dtbnetstart} ${dtb_img}\0" \ }
				}
				"kernel" {
					append data "\n" {	"cp_kernel2ram=mmcinfo && fatload mmc ${sdbootdev} ${netstart} ${kernel_img}\0" \ }
				}
			}
		}
		"ethernet" {
			switch -exact $part_tmp {
				"dtb" {
					set data {	"cp_dtb2ram=tftpboot ${dtbnetstart} ${dtb_img}\0" \ }
				}
				"kernel" {
					set data {	"cp_kernel2ram=tftpboot ${netstart} ${kernel_img}\0" \ }
				}
			}
		}
	}
	regsub -all {@part_tmp@} $data $part_tmp data
	return $data
}

proc uboot_common {fid kconfig_fid} {
	global kconfig_dict target_cpu
	set cpu_arch [get_sw_proc_arch $target_cpu]
	# TODO: check if nor flash present in the system
	# spi only - define CONFIG_SYS_NO_FLASH

	set data "

/* BOOTP options */
#define CONFIG_BOOTP_SERVERIP
#define CONFIG_BOOTP_BOOTFILESIZE
#define CONFIG_BOOTP_BOOTPATH
#define CONFIG_BOOTP_GATEWAY
#define CONFIG_BOOTP_HOSTNAME
#define CONFIG_BOOTP_MAY_FAIL
#define CONFIG_BOOTP_DNS
#define CONFIG_BOOTP_SUBNETMASK
#define CONFIG_BOOTP_PXE

/*Command line configuration.*/
#define CONFIG_CMDLINE_EDITING
#define CONFIG_AUTO_COMPLETE

#define CONFIG_SUPPORT_RAW_INITRD

/* Miscellaneous configurable options */
#define CONFIG_SYS_CBSIZE	2048/* Console I/O Buffer Size      */
#define CONFIG_SYS_PBSIZE	(CONFIG_SYS_CBSIZE +\
					sizeof(CONFIG_SYS_PROMPT) + 16)
#define CONFIG_SYS_BARGSIZE CONFIG_SYS_CBSIZE

/* Use the HUSH parser */
#define CONFIG_SYS_PROMPT_HUSH_PS2 \"> \"

#define CONFIG_ENV_VARS_UBOOT_CONFIG
#define CONFIG_ENV_OVERWRITE	/* Allow to overwrite the u-boot environment variables */

#define CONFIG_LMB

/* FDT support */
#define CONFIG_DISPLAY_BOARDINFO_LATE

"
	uboot_set_kconfig_value $kconfig_fid "BOOTARGS" "n"
	uboot_set_kconfig_value $kconfig_fid "USE_BOOTARGS" "n"
	if {[string equal -nocase $cpu_arch "microblaze"] == 1} {
		append data "
/* architecture dependent code */
#define CONFIG_XILINX_MICROBLAZE0_USR_EXCEP    /* user exception */
#define CONFIG_SYS_HZ   1000

/* Boot Argument Buffer Size */
#define CONFIG_SYS_MAXARGS     32      /* max number of command args */
#define CONFIG_SYS_LONGHELP 1

"
	} elseif {[string equal -nocase $cpu_arch "armv7"] == 1} {
		append data "
/* architecture dependent code */
#define CONFIG_SYS_HZ   1000

/* Boot Argument Buffer Size */
#define CONFIG_SYS_MAXARGS      32      /* max number of command args */
#define CONFIG_SYS_LONGHELP


#undef CONFIG_BOOTM_NETBSD
"
	} elseif {[string equal -nocase $cpu_arch "armv8"] == 1} {
		uboot_set_kconfig_value $kconfig_fid EFI_LOADER "n"
		uboot_set_kconfig_value $kconfig_fid PANIC_HANG "y"

		append data "
/* Boot Argument Buffer Size */
#define CONFIG_SYS_MAXARGS      64      /* max number of command args */
#define CONFIG_SYS_LONGHELP
"
}


# CONFIG_SYS_BOOTMAPSZ
# For booting Linux, the fdt_blob, other bd_info have to be in the first
# 256 MB of memory, since this is the maximum mapped by the Linux kernel
# during initialization. We set it to 128MB for Zynq and MicroBlaze
	set bootmapsz "0x8000000"
	set maim_mem_size [dict get $kconfig_dict memory size]
	if {[string equal -nocase $cpu_arch "armv7"] == 1} {
		set kernel_baseaddr [dict get $kconfig_dict memory kernel_baseaddr]
		set mem_baseaddr [dict get $kconfig_dict memory baseaddr]
		set kern_baddr_offset [expr $kernel_baseaddr - $mem_baseaddr]
		set bootmapsz [format "0x%08x" [expr $bootmapsz + $kern_baddr_offset]]
	}
	# check if memory size is smaller
	if {[expr $maim_mem_size > "0x8000000" ]} {
		append data "\n" "/* Initial memory map for Linux */
#define CONFIG_SYS_BOOTMAPSZ ${bootmapsz}"
	}
	puts $fid $data
}

proc gen_bootenv_define {fid kconfig_fid} {
	global ps_sdio_count
	set got_sd 0
	set sdbootdev 0
	set primary_sd [get_primary_inst_name "sd"]
	if {[string length $primary_sd] > 0} { set got_sd 1 }
	# generate the bootenv partition info
	set part_tmp "bootenv"
	set part_info [report_partition_layout $part_tmp]

	if {$got_sd == 1 && $ps_sdio_count >1 } {
		if {[regexp  "ps[7u]_sd_1" $primary_sd matched]} { set sdbootdev 1 }
        }
	set data "
/* Environment settings*/"
	puts $fid $data

	# check if it is null string
	eval "lassign \{$part_info\} ${part_tmp}_in ${part_tmp}_image ${part_tmp}_offset ${part_tmp}_size ${part_tmp}_cntl_base"
	uboot_set_kconfig_value $kconfig_fid "ENV_IS_IN_FLASH" "n"
	uboot_set_kconfig_value $kconfig_fid "ENV_IS_IN_SPI_FLASH" "n"
	uboot_set_kconfig_value $kconfig_fid "ENV_IS_NOWHERE" "n"
	uboot_set_kconfig_value $kconfig_fid "CONFIG_ENV_IS_IN_NAND" "n"
	uboot_set_kconfig_value $kconfig_fid "ENV_IS_IN_FAT" "n"

	if {[regexp "(nor|spi|nand)" $bootenv_in matched]} {
		set config_addr_name "CONFIG_ENV_OFFSET"
		switch -exact $bootenv_in {
			"spi" {
				uboot_set_kconfig_value $kconfig_fid "ENV_IS_IN_SPI_FLASH" "y"
				uboot_conf_define $fid "CONFIG_ENV_SPI_MAX_HZ" "30000000"
			}
			"nor" {
				uboot_set_kconfig_value $kconfig_fid "ENV_IS_IN_FLASH" "y"
				uboot_set_kconfig_value $kconfig_fid "CONFIG_ENV_SIZE" "$bootenv_size"
				uboot_set_kconfig_value $kconfig_fid "CONFIG_ENV_ADDR" "$bootenv_offset"
				uboot_set_kconfig_value $kconfig_fid "CONFIG_ENV_SECT_SIZE" "0x20000"
				set config_addr_name "CONFIG_ENV_ADDR"
			}
			"nand" {
				uboot_set_kconfig_value $kconfig_fid "CONFIG_ENV_IS_IN_NAND" "y"
			}
		}
		uboot_conf_define $fid "${config_addr_name}" "$bootenv_offset"
		uboot_conf_define $fid "CONFIG_ENV_SIZE" "$bootenv_size"
		uboot_conf_define $fid "CONFIG_ENV_SECT_SIZE" "0x20000"
	} elseif {[regexp "sd" $bootenv_in matched]} {
		uboot_conf_define $fid "CONFIG_ENV_SIZE" "0x80000"
		uboot_set_kconfig_value $kconfig_fid "ENV_IS_IN_FAT" "y"
		uboot_set_kconfig_value $kconfig_fid "ENV_FAT_DEVICE_AND_PART" "\\\"$sdbootdev:auto\\\""
		uboot_set_kconfig_value $kconfig_fid "ENV_FAT_FILE" "\\\"uboot.env\\\""
		uboot_set_kconfig_value $kconfig_fid "ENV_FAT_INTERFACE" "\\\"mmc\\\""
	} else {
		uboot_set_kconfig_value $kconfig_fid "ENV_IS_NOWHERE" "y"
		puts $fid "\n/* ram env */
#define CONFIG_ENV_SIZE 0x4000"
	}
}

proc gen_axi_qspi_clk args {
	set fid [lindex $args 0]
	set ip [lindex $args 2]
	set def_clk_pin "S_AXI_ACLK"

	# FIXME: correct detection for XIP mode is required as XIP mode has both
	# S_AXI_ACLK and S_AXI4_ACLK clock pins
	if {[hsi get_property CONFIG.C_XIP_MODE [hsi get_cells -hier $ip]] == 1} {
		set def_clk_pin "S_AXI_ACLK"
	} elseif {[hsi get_property CONFIG.C_TYPE_OF_AXI4_INTERFACE [hsi get_cells -hier $ip]] == 1} {
		set def_clk_pin "S_AXI4_ACLK"
	}
	set bus_freq [hsi::utils::get_clk_pin_freq [hsi get_cells -hier $ip] $def_clk_pin]
	uboot_conf_define $fid "XILINX_SPI_FLASH_ACLK" $bus_freq

}

proc gen_timer_define args {
	set fid [lindex $args 0]
	set ip [lindex $args 2]

	set intr_pin_name [hsi get_pins -of_objects [hsi get_cells -hier $ip] -filter {TYPE==INTERRUPT}]
	# in theory there should only be one pin name
	if { [llength $intr_pin_name] != 1} {
		error "Unable to detect the interrupt for timer($ip) !!!"
	}

	if {[catch {set irq_id [hsi::utils::get_interrupt_id $ip $intr_pin_name]}]} {
		error "Unable to detect the interrupt IRQ !!!"
	}

	# if interrupt id is -1 this mean it is not working
	if {[string match -nocase $irq_id "-1"]} {
		error "Unable to detect the interrupt!!!"
	}

	# FIXME: hard codeing clock pot name "S_AXI_ACLK" is not good
	# these assumption is for AXI_TIMER
	set timer_freq [hsi::utils::get_clk_pin_freq [hsi get_cells -hier $ip] "S_AXI_ACLK"]
	uboot_conf_define $fid "CONFIG_SYS_TIMER_0_IRQ" $irq_id
	uboot_conf_define $fid "FREQUENCE" $timer_freq
	uboot_conf_define $fid "XILINX_CLOCK_FREQ" $timer_freq

}

proc gen_uartns_define args {
	set fid [lindex $args 0]
	set ip [hsi get_cells -hier [lindex $args 2]]

	set has_xin [hsi::utils::get_ip_param_value $ip C_HAS_EXTERNAL_XIN]
	set clock_port "S_AXI_ACLK"
	if { [string match -nocase "$has_xin" "1"] } {
		set value [hsi::utils::get_property CONFIG.C_EXTERNAL_XIN_CLK_HZ $ip]
	} else {
		set freq [hsi::utils::get_clk_pin_freq $ip "$clock_port"]
	}
	uboot_conf_define $fid "CONFIG_SYS_NS16550_CLK" $freq
}

proc gen_eth_env_data {} {
	# generate the network config based on subsys configs
	global kconfig_dict

	set data ""
	if {[dict exists $kconfig_dict ethernet mac]} {
		set data "\"ethaddr=[dict get $kconfig_dict ethernet mac]\\0\" \\"
	}
	return "${data}"
}

proc gen_eth_define args {
	# generate the network config based on subsys configs
	set fid [lindex $args 0]
	global kconfig_dict

	if {[dict exists $kconfig_dict subsys_conf u__boot_tftpserver_ip]} {
		set tftpserver_ip [dict get $kconfig_dict subsys_conf u__boot_tftpserver_ip]
		if {[string equal -nocase $tftpserver_ip "auto"]} {
			global find_ip_cmd
			set rt_code [catch [exec $find_ip_cmd] output]
			if {$rt_code != 0} {
				debug "gen_eth_define" "Unable to determine the IP"
			} else {
				set tftpserver_ip [exec $find_ip_cmd]
			}
		}
		uboot_conf_define ${fid} "CONFIG_SERVERIP" $tftpserver_ip
	}

	if {[dict exists $kconfig_dict ethernet use_dhcp]} {
		uboot_conf_define $fid "CONFIG_IPADDR" ""
	} else {
		uboot_conf_define $fid "CONFIG_IPADDR" [dict get $kconfig_dict ethernet ip_address]
		uboot_conf_define $fid "CONFIG_GATEWAYIP" [dict get $kconfig_dict ethernet ip_gateway]
		uboot_conf_define $fid "CONFIG_NETMASK" [dict get $kconfig_dict ethernet ip_netmask]

	}
}

proc get_dma_slave {fid db_dict ip main_key config_cat config_var} {
	# only works with one dma engine
	# and assume it is axi_dma ip type
	set slave_list [hsi get_property "SLAVES" [hsi get_cells -hier $ip]]
	foreach slave $slave_list {
		set ip_type [hsi get_property "IP_NAME" [hsi get_cells -hier $slave]]
		if {[regexp -all {axi_dma} $ip_type ] == 1 } {
			set dma_slaves [hsi get_property "SLAVES" [hsi get_cells -hier $slave]]
			if {[regexp -all $ip $dma_slaves ] == 1 } {
				set tconf_list [get_conf_list $db_dict "axi_dma"]
				foreach conf_cat $tconf_list {
					db_gen_prop_wrapper $fid $db_dict $slave $ip_type $conf_cat $config_var
				}
				return
			}
		}
	}
	# this does not work with XPS based project as the slaves is missing
	# HACK to workaround this
	# loop through all IPs and uses the first DMA founded
	set ip_list [hsi get_cells -hier]
	foreach ip $ip_list {
		set ip_type [hsi get_property "IP_NAME" [hsi get_cells -hier $ip]]
		if {[regexp -all {axi_dma} $ip_type ] == 1 } {
			set tconf_list [get_conf_list $db_dict "axi_dma"]
			foreach conf_cat $tconf_list {
				db_gen_prop_wrapper $fid $db_dict $ip $ip_type $conf_cat $config_var
			}
			return
		}
	}
}

# get the interrupt controller that is connected to the
proc get_current_ip_intc {target_ip} {
	set proc_handle [hsi get_cells -hier $target_ip]
	set proc_ips [hsi::utils::get_proc_slave_periphs $proc_handle]
	foreach ip $proc_ips {
		if { [hsi::utils::is_intr_cntrl $ip] == 1 } {
			set intr_pin [hsi get_pins -of_objects $ip "Irq"]
			if { [llength $intr_pin] != 0} {
				set sink_pins [hsi::utils::get_sink_pins $intr_pin]
				foreach sink_pin $sink_pins {
					set connected_ip [hsi get_cells -of_objects $sink_pin]
					set ip_name [hsi get_property NAME $connected_ip]
					if { [string match -nocase "ip_name" "$target_ip"] == 0 } {
						return $ip
					}
				}
			}
		}
	}
	return ""
}

proc uboot_config_gen {} {
	global target_app target_cpu
	global out_dir
	global kconfig_dict
	set platform_config_h "$out_dir/platform-auto.h"
	set kconfig_f "$out_dir/config.cfg"
	set fid [open "$platform_config_h" "w+"];
	set kconfig_fid [open "${kconfig_f}" "w+"]

	puts $fid "/*\n * This file is auto-generated by PetaLinux SDK ";
	puts $fid " * DO NOT MODIFY this file, the modification will not persist\n */\n";
	puts $fid "#ifndef __PLNX_CONFIG_H"
	puts $fid "#define __PLNX_CONFIG_H\n"
	set cpu_arch [get_sw_proc_arch $target_cpu]
	puts $fid {/* The following table includes the supported baudrates */
}
	if { "${cpu_arch}" == "microblaze" || "${cpu_arch}" == "armv7"} {
	puts $fid {
#define CONFIG_SYS_BAUDRATE_TABLE \
{ 300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400 }

}
	} else {
	puts $fid {
#define CONFIG_SYS_BAUDRATE_TABLE \
{ 4800, 9600, 19200, 38400, 57600, 115200 }

}
}

	uboot_hw_config_gen $fid ${kconfig_fid}
	uboot_memory_config ${fid} ${kconfig_fid}
	gen_platform_config $fid

	uboot_common $fid ${kconfig_fid}

	uboot_set_kconfig_value $kconfig_fid BOOTDELAY 4
	if { "${cpu_arch}" == "microblaze" } {
		set config_mk "$out_dir/config.mk"
		set confmk_fid [open "${config_mk}" "w+"]
		uboot_config_mk_gen ${confmk_fid} ${kconfig_fid}
		uboot_set_kconfig_value $kconfig_fid SYS_PROMPT "\\\"U-Boot>\\\""
		close ${confmk_fid}
	}
	if { [dict exists $kconfig_dict subsys_conf autoconfig_u__boot]} {
		uboot_set_kconfig_value $kconfig_fid SYS_CONFIG_NAME "\\\"platform-top\\\""
		uboot_set_kconfig_value $kconfig_fid BOOT_SCRIPT_OFFSET "0x1F00000"
	} else {
		uboot_set_kconfig_value $kconfig_fid SYS_CONFIG_NAME 0 1
	}

	foreach config "SPL I2C_EEPROM CMD_EEPROM SYS_I2C_EEPROM_ADDR_OVERFLOW SYS_I2C_EEPROM_ADDR" {
		uboot_set_kconfig_value $kconfig_fid $config "n"
	}
	puts $fid "\n#endif /* __PLNX_CONFIG_H */"
	close $kconfig_fid
	close ${fid}
}

proc gen_platform_config {fid} {
	global target_cpu spiflash_count
	set cpu_arch [get_sw_proc_arch $target_cpu]
	if {"${cpu_arch}" == "armv8" || "${cpu_arch}" == "armv7"} {
		if { ${spiflash_count} == 0} {
			puts $fid "\n\#ifdef CONFIG_DM_SPI_FLASH
\# define CONFIG_SPI_GENERIC
\# define CONFIG_SF_DEFAULT_SPEED	30000000
\# define CONFIG_ENV_SPI_MAX_HZ		30000000
\# define CONFIG_SF_DUAL_FLASH
\# define CONFIG_CMD_SPI
\# define CONFIG_CMD_SF
\#endif
"
		}
	}
}

proc uboot_conf_define {fid name value} {
	global conf_prefix
	if {[string equal -nocase $name ""]} {
		puts $fid "${conf_prefix}$value"
	} elseif {[string equal -nocase $value ""]} {
		puts $fid "${conf_prefix}$name"
	} else {
		puts $fid "${conf_prefix}$name\t$value"
	}
}

proc uboot_conf_undefine {fid name} {
	puts $fid "#ifdef $name"
	puts $fid "# undef $name"
	puts $fid "#endif"
}

proc uboot_config_mk_gen {fid kconfig_fid} {
	global target_cpu
	global kconfig_dict

	puts $fid "#\n# CAUTION: This file is automatically generated by PetaLinux SDK\n#\n"
	# set uboot text base
	set mem_base [dict get $kconfig_dict memory baseaddr]
	set uboot_offset [dict get $kconfig_dict memory "u__boot_textbase_offset"]
	set uboot_textbase [format "0x%08x" [expr $mem_base + $uboot_offset]]
	puts $fid "TEXT_BASE = $uboot_textbase"
	puts $fid "CONFIG_TEXT_BASE = $uboot_textbase\n"

	uboot_set_kconfig_value $kconfig_fid TEXT_BASE $uboot_textbase
	# set compiler flags for microblaze
	set cpu_arch [get_sw_proc_arch $target_cpu]
	if {[string equal -nocase $cpu_arch "microblaze"] == 1} {
		global processor_dict
		db_gen_config $fid $target_cpu $processor_dict "uboot_configmk"
		# get cpu version
		set vlnv [hsi get_property "VLNV" [hsi get_cells -hier $target_cpu]]
		set cpu_ver [lindex [split $vlnv ":"] 3]
		puts $fid "PLATFORM_CPPFLAGS += -mcpu=v$cpu_ver"
		puts $fid "PLATFORM_CPPFLAGS += -fgnu89-inline"
	}
}

proc uboot_set_kconfig_value {fid names {vals y} {del 0}} {
	seek ${fid} 0 start
	set lines [split [read ${fid}] "\n"]
	if { "${vals}" == "y" } {
		set len [llength ${names}]
		set vals [lrepeat $len y]
		debug "uboot_set_kconfig_value" "len : $len"
	}
	debug "uboot_set_kconfig_value" "vals : $vals $names : $names"
	foreach n ${names} v ${vals} {
		set n [regsub "^CONFIG_" $n ""]
		set idx [lsearch -regex -all ${lines} "CONFIG_${n}\[ =\]"]
		if { [llength ${idx}] > 0 } {
			set i [lindex ${idx} 0]
			set lines [lreplace $lines $i $i]
		}
		if { "${v}" == "n" } {
			set rline "\# CONFIG_${n} is not set"
		} elseif {$del == 1} {
			#DO nothing
		} else {
			set rline "CONFIG_${n}=${v}"
		}
		if {$del == 0} {
			set lines [lappend lines "${rline}"]
		}
	}
	seek ${fid} 0 start
	chan truncate ${fid} 0
	puts ${fid} [join ${lines} "\n"]
}

proc uboot_data_find_kconfig {dict_var} {
	if { [catch {set tmp_keys [dict keys ${dict_var}]}]} {
		return
	}
	set opt_list {}
	foreach k ${tmp_keys} {
		if { "${k}" == "uboot_config" } {
			foreach o [dict get ${dict_var} "${k}"] {
				set o [lindex [split $o "="] 0]
				lappend opt_list ${o}
			}
		} else {
			foreach o [uboot_data_find_kconfig [dict get ${dict_var} "${k}"]] {
				lappend opt_list ${o}
			}
		}
	}
	return ${opt_list}
}

proc uboot_kconfig_disable {fid} {
	set opt_list {}
	set mapping_list {serial_dict timer_dict
			  flash_dict ethernet_dict sd_dict rtc_dict
			  sata_dict i2c_dict usb_dict processor_dict timer_dict}
	global serial_dict timer_dict processor_dict
	global flash_dict ethernet_dict sd_dict rtc_dict sata_dict usb_dict i2c_dict timer_dict
	foreach iptype ${mapping_list} {
		eval "set mapping_dict \$${iptype}"
		foreach o [uboot_data_find_kconfig ${mapping_dict}] {
			lappend opt_list ${o}
		}
	}
		seek ${fid} 0 start
		set lines [split [read ${fid}] "\n"]
		foreach o ${opt_list} {
			set idx [lsearch -regex -all ${lines} "${o}="]
			if { [llength ${idx}] > 0 } {
				foreach d ${idx} {
					set lines [lreplace $lines $idx $idx ]
				}
			}
			set idx [lsearch -regex -all ${lines} "${o} is not"]
			if { [llength ${idx}] > 0 } {
				continue
			} else {
				set lines [lappend lines "\# ${o} is not set"]
			}
		}
		seek ${fid} 0 start
		chan truncate ${fid} 0
		puts ${fid} [join ${lines} "\n"]
}


proc uboot_hw_config_gen {auto_h_fid kconfig_fid} {
	global timer_dict dict_lut def_ip_list

	uboot_kconfig_disable ${kconfig_fid}
	foreach ip $def_ip_list {
		if {[string equal -nocase "simple" $ip]} {
			set ip_name simple
		} elseif {[string equal -nocase "chip_device" $ip]} {
			set ip_name $ip
		} else {
			set ip_obj [hsi get_cell -hier $ip]
			set ip_name [hsi get_property IP_NAME $ip_obj]
		}
		if {[dict exist $dict_lut $ip]} {
			set dict_name [dict get $dict_lut $ip type]
			eval "global ${dict_name}_dict"
			eval "set mapping_dict \$${dict_name}_dict"
		} else {
			global misc_dict
			set mapping_dict misc_dict
		}

		if {[dict exist $mapping_dict $ip_name]} {
			debug "1" "got ip $ip_name"
			#config_mapping
			if {[dict exist $mapping_dict $ip_name ip_type]} {
				set ins_type [dict get $mapping_dict $ip_name ip_type]
				puts ${auto_h_fid} "\n/* $ins_type - $ip */"
			} else {
				puts ${auto_h_fid} "\n/* $ip */"
				set ins_type ""
			}
			db_gen_config ${kconfig_fid} $ip $mapping_dict "uboot_config"
			db_gen_config ${auto_h_fid} $ip $mapping_dict "uboot_header"
		}
	}
	puts ${auto_h_fid} "\n/* FPGA */"
	db_gen_config ${kconfig_fid} "chip_device" $mapping_dict "uboot_config"
	db_gen_config ${auto_h_fid} "chip_device" $mapping_dict "uboot_header"

}
