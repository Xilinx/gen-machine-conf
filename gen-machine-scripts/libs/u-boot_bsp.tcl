# Copyright (C) 2014-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

proc uboot_common {kconfig_fid} {
	uboot_set_kconfig_value $kconfig_fid "BOOTARGS" "n"
	uboot_set_kconfig_value $kconfig_fid "USE_BOOTARGS" "n"
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
	set kconfig_fid [open "${kconfig_f}" "w+"]
	set cpu_arch [get_sw_proc_arch $target_cpu]

	uboot_hw_config_gen ${kconfig_fid}
	uboot_common ${kconfig_fid}

	uboot_set_kconfig_value $kconfig_fid BOOTDELAY 4
	if { "${cpu_arch}" == "microblaze" } {
		# set uboot text base
		set mem_base [dict get $kconfig_dict memory baseaddr]
		set uboot_offset [dict get $kconfig_dict memory "u__boot_textbase_offset"]
		set uboot_textbase $uboot_offset
		# get cpu version
		set vlnv [hsi get_property "VLNV" [hsi get_cells -hier $target_cpu]]
		set cpu_ver [lindex [split $vlnv ":"] 3]
		uboot_set_kconfig_value $kconfig_fid XILINX_MICROBLAZE0_HW_VER "\\\"$cpu_ver\\\""
		uboot_set_kconfig_value $kconfig_fid TEXT_BASE $uboot_textbase
		uboot_set_kconfig_value $kconfig_fid SYS_PROMPT "\\\"U-Boot>\\\""
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
	close $kconfig_fid
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
	set mapping_list {serial_dict flash_dict ethernet_dict processor_dict}
	global serial_dict processor_dict
	global flash_dict ethernet_dict
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


proc uboot_hw_config_gen {kconfig_fid} {
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
			db_gen_config ${kconfig_fid} $ip $mapping_dict "uboot_config"
		}
	}
	db_gen_config ${kconfig_fid} "chip_device" $mapping_dict "uboot_config"

}
