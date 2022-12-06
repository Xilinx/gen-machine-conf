# Copyright (C) 2014-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

proc partition_info_lookup {kconfig_dict media part_name key} {
	set part_no 0
	while {$part_no < 20} {
		if {[dict exists $kconfig_dict $media "part$part_no" "name"]} {
			set cur_part_name [dict get $kconfig_dict flash "part$part_no" "name"]
			if {[string equal $cur_part_name $part_name] && \
				[dict exists $kconfig_dict flash "part$part_no" $key]} {
				set key_value [dict get $kconfig_dict flash "part$part_no" $key]
				return $key_value
			}
		} else {
			break
		}
		incr part_no
	}
	# Maybe this should be a error, in theory this should be captured by plnx tools
	debug "partition_info_lookup" "Unable to determine the $key for partition '$part_name' from media '$media'"
}

proc set_serial_dict_data {inst_name conf_str data} {
	global kconfig_dict
	set lookup_string "serial"
	set property "baudrate"
	foreach p ${property} {
		set up_p [string toupper ${p}]
		regsub -- "_SELECT=y" $conf_str "_${up_p}_" up_p_prefix
		set p_line [lsearch -regexp -inline ${data} "^${up_p_prefix}.*=y"]
		if { "${p_line}" != "" } {
			regsub -- "${up_p_prefix}" ${p_line} "" p_line
			regsub -- "=y" ${p_line} "" p_val
			set p_val [string tolower "${p_val}"]
			dict set kconfig_dict $lookup_string ${p} ${inst_name} ${p_val}
		}
	}
}

proc read_config {} {
	# TODO: Clean up
	global plnx_sys_conf_file kconfig_dict dict_lut

	set fp [open $plnx_sys_conf_file r]
	set file_data [read $fp]
	set data [split $file_data "\n"]
	global target_cpu def_ip_list

	# check list
	set lookup_list "processor memory serial timer reset_gpio flash ethernet sd rtc sata i2c usb"
	foreach line [lsearch -regexp -all -inline $data "^CONFIG_SUBSYSTEM_.*_SELECT=y"] {
		foreach lookup_string $lookup_list {
			eval "global ${lookup_string}_dict"
			eval "set mapping_dict \$${lookup_string}_dict"
			set lookup_string [string toupper $lookup_string]
			set lookup_regexp "^CONFIG_SUBSYSTEM_${lookup_string}.*_SELECT=y"
			if {[regexp $lookup_regexp $line matched] == 1 } {
				set ch_regexp "^CONFIG_SUBSYSTEM_${lookup_string}.*CHANNEL[0-9]_SELECT=y"
				if {[regexp $ch_regexp $line matched] == 1 } {continue}
				set value [string tolower [regsub -- "CONFIG_SUBSYSTEM_${lookup_string}_" $line ""]]
				regsub -- "_select=y" $value "" value
				if {[string equal "manual" $value]} {
					continue
				}
				set lookup_string [string tolower $lookup_string]
				if { "${lookup_string}" == "memory" } {
				}
				dict set kconfig_dict $lookup_string ip_str $value
				# TODO: check up bank no
				if {[regexp [string toupper "^CONFIG_SUBSYSTEM_${lookup_string}.*_BANK.*="] $line matched] == 1} {
					set bank_no [regsub -- ".*_bank" $value ""]
					# FIXME: is this a good idea to set bankless to 0
					if {[regexp "less" $bank_no matched] == 1} {
						dict set kconfig_dict $lookup_string bank ""
					} else {
						dict set kconfig_dict $lookup_string bank $bank_no
					}
				}
				regsub -- "_bankless" $value "" value
				regsub -- "_bank[0-9]" $value "" value
				# get the real ip name in the system
				foreach real_ip_name [hsi get_cells -hier] {
					if {[regexp -nocase -- $value $real_ip_name match]} {
						set value $real_ip_name
						break
					}
				}
				dict set kconfig_dict $lookup_string inst_name $value
				lappend def_ip_list $value
				dict set dict_lut $value type $lookup_string
				if {[string equal "simple" $value]} {
					continue
				}
				# now check if flash_type exists
				if { ![regexp "(^hbm.*)|(.*ddr.*)" $value matched] } {
					set ip_name [hsi get_property IP_NAME [hsi get_cells -hier $value]]
					if {[dict exists $mapping_dict $ip_name flash_type]} {
						set flash_typ [dict get $mapping_dict $ip_name flash_type]
						dict set kconfig_dict $lookup_string flash_type $flash_typ
					}
				}
				# now check if uart baudrate exists
				if { "${lookup_string}" == "serial" } {
					set_serial_dict_data "${value}" "${line}" ${data}
				}
				break
			}
		}
	}

	set target_cpu [dict get $kconfig_dict processor inst_name]
	if {[string compare ${target_cpu} ""] == 0} {
		error "No cpu detected."
	}
	set cpu_arch [get_sw_proc_arch $target_cpu]
	if {[string equal -nocase $cpu_arch "microblaze"] == 1} {
		set proc_intc [get_current_ip_intc $target_cpu]
		if {![string equal "$proc_intc" ""]} {
			lappend def_ip_list $proc_intc
			dict set dict_lut $proc_intc type intc
		}
	}

	# separate into second loop to ensure that the _select=y is not at the end(unlikely)
	foreach line $data {
		if {[regexp [string toupper "^#.*"] $line matched]} {
			continue
		}
		foreach lookup_string $lookup_list {
			if {![dict exists $kconfig_dict $lookup_string inst_name]} {
				continue
			}
			set ip_str [dict get $kconfig_dict $lookup_string ip_str]
			set inst_name [dict get $kconfig_dict $lookup_string inst_name]
			set lookup_regexp [string toupper "^CONFIG_SUBSYSTEM_${lookup_string}_${inst_name}_.*=" ]
			if { [regexp $lookup_regexp $line matched] == 1 } {
				set prop_data [string tolower [regsub -- [string toupper "CONFIG_SUBSYSTEM_${lookup_string}_(${ip_str}|${inst_name})_"] $line ""]]
				set prop_data [split $prop_data "="]
				set prop_key [lindex $prop_data 0]
				set prop_value [lindex $prop_data 1]
				regsub -all {"} $prop_value "" prop_value
				# FIXME: flash spi - CS, emc bank
				# handle partition tables
				if {[regexp "part[0-1]?[0-9]_.*" $prop_key]} {
					if {[string equal $prop_value ""]} {continue}
					set part_key_data [split $prop_key "_"]
					set prop_pri_key [lindex $part_key_data 0]
					set prop_sec_key [lindex $part_key_data 1]
					dict set kconfig_dict $lookup_string $prop_pri_key $prop_sec_key $prop_value
				} else {
					dict set kconfig_dict $lookup_string $prop_key $prop_value
				}
			}
		}
		# check for adv partition
		if {[regexp "^CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_.*" $line matched] == 1} {
			set prop_data [regsub -- [string toupper "CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_"] $line ""]
			set prop_data [split $prop_data "="]
			set prop_value [lindex $prop_data 1]
			regsub -all {"} $prop_value "" prop_value
			set prop_key [string tolower [lindex $prop_data 0]]
			set primary_key [lindex [split $prop_key "_"] 0]
			set option [lindex [split $prop_key "_"] 1]
			switch -exact $option {
				"media" {
					set prop_value [lindex [split $prop_key "_"] 2]
					if {[string equal "flash" $prop_value]} {
						set flash_typ [dict get $kconfig_dict flash flash_type]
						dict set kconfig_dict adv_partition $primary_key flash_type $flash_typ
					}
				}
				default { }
			}
			dict set kconfig_dict adv_partition $primary_key $option $prop_value
		}
		if {[regexp "^CONFIG_SUBSYSTEM_.*" $line matched] == 1} {
			set prop_data [regsub -- [string toupper "CONFIG_SUBSYSTEM_"] $line ""]
			set prop_data [split $prop_data "="]
			set prop_key [string tolower [lindex $prop_data 0]]
			set prop_value [join [lrange $prop_data 1 end] "="]
			if {[regexp "^user_cmdline" $prop_key matched] == 1} {
				set prop_value [string range $prop_value 1 end-1]
			} else {
				regsub -all {"} $prop_value "" prop_value
			}
			dict set kconfig_dict subsys_conf $prop_key $prop_value
		}
	}

	if {[dict exists $kconfig_dict subsys_conf images_advanced_autoconfig]} {
		set adv_partition_used 1
	} else {
		set adv_partition_used 0
	}
	# update partition offset and target image file (no adv_partition setting)
	set part_no 0
	set offset 0x0
	while {$part_no < 20} {
		if {[dict exists $kconfig_dict flash "part$part_no" "size"]} {
			set size [dict get $kconfig_dict flash "part$part_no" "size"]
			set flash_type [dict get $kconfig_dict flash flash_type]
			if {[string equal "nor" $flash_type]} {
				set flash_inst [dict get $kconfig_dict flash inst_name]
				set flash_bank [dict get $kconfig_dict flash bank]
				set cntl_base [get_ip_property $flash_inst $flash_bank BASEADDR]
				set p_offset [format "0x%08x" [expr $cntl_base + $offset]]
				dict set kconfig_dict flash "part$part_no" "cntl_base" $cntl_base
			} else {
				set p_offset $offset
			}
			dict set kconfig_dict flash "part$part_no" "offset" $p_offset
			if {$adv_partition_used == 0} {
				set part_name [dict get $kconfig_dict flash "part$part_no" "name"]
				set image_file ""
				# boot is arch dependent
				switch -exact $part_name {
					"boot" {
						if {[string equal -nocase $cpu_arch "microblaze"] == 1} {
							set image_file "u-boot-s.bin"
						} else {
							set image_file "BOOT.BIN"
						}
					}
					"kernel" {
						set image_file [dict get $kconfig_dict "subsys_conf" "uimage_name"]
					}
					"jffs2" {set image_file "rootfs.jffs2"}
					"dtb" {set image_file "system.dtb"}
					"fpga" {set image_file "system.bit.bin"}
					default { }
				}
				if {![string equal $image_file ""]} {
					dict set kconfig_dict flash "part$part_no" "image_file" $image_file
					# create adv_partition image key
					dict set kconfig_dict adv_partition $part_name image $image_file
					dict set kconfig_dict adv_partition $part_name flash_type $image_file
				}
				# create adv_partition keys
				dict set kconfig_dict adv_partition $part_name media flash
				dict set kconfig_dict adv_partition $part_name part $part_name
				dict set kconfig_dict adv_partition $part_name size $size
				#
				dict set kconfig_dict adv_partition $part_name flash_type $flash_type
			}
			set offset [format "0x%x" [expr $size + $offset]]
		} else {
			break
		}
		incr part_no
	}
	# for adv partition we need workout the off set and size
	if {[dict exists $kconfig_dict adv_partition]} {
		dict for {prop prop_mapping} [dict get $kconfig_dict adv_partition] {
			set media [dict get $kconfig_dict adv_partition $prop media]
			if {![string equal "flash" $media]} {continue}
			set part_name [dict get $kconfig_dict adv_partition $prop part]
			set offset [partition_info_lookup $kconfig_dict $media $part_name "offset"]
			set size [partition_info_lookup $kconfig_dict $media $part_name "size"]
			if {[string equal $offset ""]} {continue}
			dict set kconfig_dict adv_partition $prop offset $offset
			dict set kconfig_dict adv_partition $prop size $size
			set cntl_base [partition_info_lookup $kconfig_dict $media $part_name "cntl_base"]
			if {[string equal $cntl_base ""]} {continue}
			dict set kconfig_dict adv_partition $prop cntl_base $cntl_base
		}
	}

	if {! [dict exists $kconfig_dict subsys_conf netboot_offset]} {
		dict set kconfig_dict subsys_conf netboot_offset 0x1000000
	}
	close $fp
}
