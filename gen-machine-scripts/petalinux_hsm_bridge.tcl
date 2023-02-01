#
# HSM bridge
#
# Copyright (C) 2014-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

proc debug {level message} {
	return
	puts ">> $level: $message"
}

proc get_primary_inst_name {ip} {
	global kconfig_dict
	set inst_name ""
	set str [dict filter [dict get $kconfig_dict subsys_conf] key primary_${ip}_*_select]
	if {[llength $str] > 0} {
		set inst_name [regsub -- "_select" [regsub -- "primary_${ip}_" [lindex $str 0] ""] ""]
	}
	if {[string equal -nocase $inst_name "manual"] == 1} {
		return ""
	}
	return $inst_name
}

proc plnx_error_exit {msg} {
	puts stderr "Error code: ${errorCode}."
	puts stderr "Error info: ${errorInfo}."
	error "ERROR: ${msg}"
}

proc load_hw_desc_file {hw_desc_file} {
	debug 1 "openhw $hw_desc_file"
	openhw $hw_desc_file
	set hw_design_obj [hsi current_hw_design]
	return $hw_design_obj
}

proc add_def_ip_list {} {
	global target_cpu def_ip_list dict_lut
	set cpu_arch [get_sw_proc_arch $target_cpu]
	# for arch arm, we should also check up ps7_slcr ps7_scuc ps7_dev_cfg ps7_scutimer
	if {[string equal -nocase $cpu_arch "armv7"] == 1} {
		set ip_lookup_list "ps7_slcr ps7_scuc ps7_dev_cfg ps7_scutimer processing_system7"
		foreach ip [hsi get_cells -hier] {
			set ip_type [hsi get_property "IP_NAME" [hsi get_cells -hier $ip]]
			if {[lsearch -exact $ip_lookup_list $ip_type] >= 0} {
				lappend def_ip_list $ip
				dict set dict_lut $ip type misc
			}
		}
	} elseif {[string equal -nocase $cpu_arch "armv8"] == 1} {
		set ip_lookup_list "psu_acpu_gic zynq_ultra_ps_e"
		foreach ip [hsi get_cells -hier] {
			set ip_type [hsi get_property "IP_NAME" [hsi get_cells -hier $ip]]
			if {[lsearch -exact $ip_lookup_list $ip_type] >= 0} {
				lappend def_ip_list $ip
				dict set dict_lut $ip type misc
			}
		}
	}
}

proc get_os_config_list {} {
	set prop_data [hsi report_property -all -return_string [hsi get_os] CONFIG.*]
	set conf_data [split $prop_data "\n"]
	set config_list {}
	foreach line $conf_data {
		if { [regexp "^CONFIG..*" $line matched] == 1 } {
			set config_name [split $line " "]
			set config_name [lindex $config_name 0]
			regsub -- "CONFIG." $config_name "" config_name
			lappend config_list $config_name
		}
	}
	return $config_list
}

proc Pop {varname {nth 0}} {
	upvar $varname args
	set r [lindex $args $nth]
	set args [lreplace $args $nth $nth]
	return $r
}

proc arg_parse { } {
	global argv0 argv argc hw_desc_file plnx_sys_conf_file out_dir db_dir sw_design function repo
	# required for hsi after 02.04 build
	set args [split [join $argv " " ] " "]
	while {[string match -* [lindex $args 0]]} {
		switch -glob -- [lindex $args 0] {
			-hdf* {set hw_desc_file [Pop args 1]}
			-c* {set plnx_sys_conf_file [Pop args 1]}
			-a* {set function [Pop args 1]}
			-o* {set out_dir [Pop args 1]}
			-data* {set db_dir [Pop args 1]}
			-repo* {set repo [Pop args 1]}
			-sw* {set sw_design [Pop args 1]}
			--    { Pop args ; break }
			default {
				set opts [join [lsort [array names state -*]] ", "]
				return -code error "bad option [lindex $args 0]: \
						must be one of $opts"
			}
		}
		Pop args
	}

	if {![file exists $hw_desc_file]} {
		error "Unable to located the HW description file - ${hw_desc_file}"
	}
	if {![file exists $plnx_sys_conf_file]} {
		error "Unable to located the PetaLinux sub system config file - ${plnx_sys_conf_file}"
	}
}

proc get_conf_list {db_dict ip_list} {
	set tconf_list ""
	foreach ip_var "$ip_list" {
		if {![dict exist $db_dict $ip_var]} {continue}
		foreach conf_type [get_db_type_list $db_dict $ip_var] {
			if {![dict exist $db_dict $ip_var $conf_type]} {continue}
			dict for {conf conf_data} [dict get $db_dict $ip_var $conf_type] {
				set rt_code [catch {dict keys [dict get $db_dict $ip_var $conf_type $conf]}]
				if {$rt_code == 0} {
					if {[lsearch -exact $tconf_list $conf] >= 0} {
						continue
						}
					lappend tconf_list "$conf"
				}
			}
		}
	}
	return $tconf_list
}

proc get_sw_proc_arch {name} {
	# processor arch mapping
	set armv7_string {cortexa9}
	set armv8_string {cortexa53 cortexa57 cortexa72 cortexa78}
	set mb_string {microblaze}

	# two different method of using get_cells -hier
	foreach cpu_str $armv7_string {
		if { [regexp $cpu_str [hsi report_property [eval hsi get_cells -hier -filter "NAME==$name"] -return_string -regexp "VLNV"] matched] == 1 } {
			return {armv7}
		}
	}
	foreach cpu_str $armv8_string {
		if { [regexp $cpu_str [hsi report_property [eval hsi get_cells -hier -filter "NAME==$name"] -return_string -regexp "VLNV"] matched] == 1 } {
			return {armv8}
		}
	}
	foreach cpu_str $mb_string {
		if { [regexp $cpu_str [hsi report_property [hsi get_cells -hier -regexp "$name"] -return_string -regexp "VLNV"] matched] == 1 } {
			return {microblaze}
		}
	}
	error "Unsupported CPU architecture"
}

proc rnd_name len {
	set s "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ23456789"
	for {set i 0} {$i <= $len} {incr i} {
		append p [string index $s [expr {int([string length $s]*rand())}]]
	}
	return $p
}

# generated a system config settings
proc report_sys_property {} {
	global kconfig_dict dict_lut def_ip_list out_dir conf_prefix
	set conf_prefix ""
	set sys_property "${out_dir}/sys-property"
	set fid [open "$sys_property" "w+"];

	foreach ip $def_ip_list {
		if {[dict exist $dict_lut $ip]} {
			set dict_name [dict get $dict_lut $ip type]
			eval "global ${dict_name}_dict"
			eval "set mapping_dict \$${dict_name}_dict"
		} else {
			global misc_dict
			set mapping_dict misc_dict
		}
		db_gen_config $fid $ip $mapping_dict "sys_property"
	}
	close $fid
}

proc add_dtsi {main_dts dtsi} {
	global out_dir
	if {[file exists "${out_dir}/${main_dts}"]} {
		set fd [open "${out_dir}/${main_dts}" "a"]
		puts "$fd" "#include \"${dtsi}\""
		close $fd
	} else {
		debug "add_dtsi" "$main_dts not found "
	}
}

proc update_alias_node {main_dts} {
	global out_dir kconfig_dict
	if {[file exists "${out_dir}/${main_dts}"]} {
		set eeprom_alias ""
		set rtc_alias ""
		if {[dict exists $kconfig_dict subsys_conf add_eeprom_alias]} {
			set eeprom_alias [dict get $kconfig_dict subsys_conf add_eeprom_alias]
		}
		if {[dict exists $kconfig_dict subsys_conf add_rtc_alias]} {
			set rtc_alias [dict get $kconfig_dict subsys_conf add_rtc_alias]
		}
		if {[llength $eeprom_alias] || [llength $rtc_alias]} {
			set fd [open "${out_dir}/${main_dts}" "r"]
			set data_read [split [read "$fd"] "\n"]
			close $fd
			foreach line $data_read {
				if {[string match -nocase "*aliases \{*" $line]} {
					if { ![dict exists $kconfig_dict subsys_conf enable_no_alias]} {
						regsub -all "aliases \{" $line "/delete-node/ aliases; \n\taliases \{" line
					}
					if {[llength $eeprom_alias]} {
						regsub -all "aliases \{" $line "aliases \{\n\t\tnvmem0 = \\&eeprom;" line
					}
					if {[llength $rtc_alias]} {
						regsub -all "aliases \{" $line "aliases \{\n\t\trtc0 = \\&rtc;" line
					}
				}
				set append_data [append append_data "$line" "\n"]
			}
		set data_write [open "${out_dir}/${main_dts}" "w"]
		puts "$data_write" "$append_data"
		close $data_write
		}
	}
}
#
# === main ===
#

package require yaml

set scripts_path [ file dirname [ file normalize [ info script ] ] ]
# source libs
foreach lib_file [glob -directory $scripts_path/libs/ *] {
	source $lib_file
}

#source tools script which are not longer exported to user
set xsct_path [exec which xsct]
set xsct_root_dir [file dirname [file dirname "${xsct_path}"]]

variable hw_desc_file


variable kconfig_dict [dict create] *
variable dict_lut [dict create]
variable ps7_mapping [dict create]
variable def_ip_list ""

# xml files
#variable xml_file "hw/zc706.xml"
variable xml_file "kc705.xml"
# system configuration files (setting to software apps/bsp)

# this target_os can be remove as the app usually have default bsp
variable target_os "standalone"

# type of application
#variable target_app "zynq_fsbl"

# TODO: allow os config to be override with additional args or file
#variable plnx_sys_conf_file "config"
variable plnx_sys_conf_file

# TODO: target_proc should get it from config file
variable target_cpu
variable sw_design
variable repo
variable out_dir ""
variable db_dir "."
variable find_ip_cmd "$scripts_path/petalinux-find-ipaddr"
variable sata_count 0
variable i2c_count 0
variable usb_count 0
variable eth_count 0
variable ethlite_count 0
variable ethfull_count 0
variable ps7eth_count 0
variable uart_count 0
variable ps_uart_count 0
variable uartfull_count 0
variable uartlite_count 0
variable gpio_count 0
variable ps_sdio_count 0
variable spiflash_count 0
variable func_called_list ""

variable conf_prefix "#define "

# list of partition that we care about
variable sys_part_list "boot bootenv jffs2 kernel dtb fpga"


variable function

arg_parse
load_hw_desc_file $hw_desc_file
foreach fn "processor intc memory serial reset_gpio flash ethernet" {
	eval "variable ${fn}_dict {[simple_yaml_parser ${db_dir}/${fn}.yaml]}"
	eval "set temp_dict \$${fn}_dict"
	debug "petalinux_hsm_bridge" "temp_dict : $temp_dict"
}

read_config
hsi get_property DEVICE [hsi get_hw_designs]
if {[string equal -nocase $function "u-boot_bsp"]} {
	add_def_ip_list
	uboot_config_gen
} elseif {[string equal -nocase $function "soc_mapping"]} {
	if { ![ file isdirectory $db_dir ] } {
		puts "Unable to find output directory - $db_dir"
	}
	if { ![file isdirectory $sw_design] } {
		puts "Unable to find sw_design - $sw_design"
	}
	if { ![file isdirectory $repo] } {
                puts "Unable to find repo - $repo"
        }
	hsi set_repo_path $repo
	set target_os "device_tree"
	set dtsifile ""
	hsi open_sw_design "$sw_design/device-tree.mss"
	# copy device tree out of here
	foreach tmpdts {skeleton.dtsi versal.dtsi zynq-7000.dtsi zynqmp.dtsi \
		pcw.dtsi pl.dtsi zynqmp-clk-ccf.dtsi versal-clk.dtsi \
		versal-net.dtsi versal-net-clk-ccf.dtsi versal-net-clk.dtsi \
		} {
		if {[file exists "${out_dir}/${tmpdts}"]} {
			lappend dtsifile "${tmpdts}"
			if { \
				[string equal -nocase "zynq-7000.dtsi" ${tmpdts}] \
				|| [string equal -nocase "zynqmp.dtsi" ${tmpdts}] \
				|| [string equal -nocase "versal.dtsi" ${tmpdts}] \
				|| [string equal -nocase "versal-net.dtsi" ${tmpdts}] \
				} {
				create_soc_mapping_from_dts_file ${out_dir}/${tmpdts}
			}
		}
	}
	if {[file exists "${out_dir}/system.dts"]} {
		file delete -force "${out_dir}/system.dts"
	}
	# now generate the system config dtsi
	set machinename [dict get $kconfig_dict subsys_conf machine_name]
	set dtsifile ""
	if {[file exists "${out_dir}/${machinename}.dtsi"]} {
		set dtsifile "${out_dir}/${machinename}.dtsi"
	}
	generate_system_dtsi ${out_dir}/system-conf.dtsi ${dtsifile}
	update_alias_node "system-top.dts"
	add_dtsi "system-top.dts" "system-user.dtsi"
} elseif {[string equal -nocase $function "sys-property"]} {
	report_sys_property
} else {
	debug 1 "function name is not valid"
}

exit 0
