# Copyright (C) 2016-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022-2023, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT


proc plnx_convert_list_to_yaml {datanode prefix} {
	set var [lindex ${datanode} 0]
	set str "${prefix}${var}:"
	foreach n [lreplace ${datanode} 0 0] {
		if {[llength ${n}] <= 1} {
			set str [format "%s %s" "${str}" "${n}"]
		} else {
			set substr [plnx_convert_list_to_yaml ${n} "${prefix}    "]
			set str [format "%s\n%s" "${str}" "${substr}"]
		}
	}
	return "${str}"
}

proc plnx_output_data {datanodes} {
	set msg [plnx_convert_list_to_yaml ${datanodes} ""]
	global plnx_data
	puts ${plnx_data} "${msg}"
}

proc plnx_fix_kconf_name {name} {
	set kconfname [string toupper "${name}"]
	set kconfname [string map {"+" "PLUS"} ${kconfname}]
	set kconfname [string map {"-" "__"} ${kconfname}]
	set kconfname [string map {"." "___"} ${kconfname}]
	set kconfname [string map {" " "_"} ${kconfname}]
	return "${kconfname}"
}

proc is_connect_to_end_from_source {srchd endname {end_pin_type ""} {pin_name "*"}} {
	set srcname [hsi get_property NAME ${srchd}]
	set searchednames [list ${srcname}]
	set out_pins [hsi get_pins -filter "DIRECTION==O && NAME=~${pin_name}" -of_objects ${srchd}]

	set sink_pins [hsi::utils::get_sink_pins ${out_pins}]
	while {[llength ${sink_pins}] > 0} {
		set out_cells {}
		foreach s ${sink_pins} {
			foreach c [hsi get_cells -of_objects ${s}] {
				set cname [hsi get_property NAME ${c}]
				if { "${cname}" == "${endname}" } {
					if {"${end_pin_type}" != ""} {
						set pin_type [hsi get_property TYPE ${s}]
						if {"${pin_type}" == "${end_pin_type}"} {
							return 1
						}
					} else {
						return 1
					}
				}
			}
		}
		foreach c [hsi get_cells -of_objects ${sink_pins}] {
			set cname [hsi get_property NAME ${c}]
			if {[lsearch ${searchednames} ${cname}] < 0} {
				lappend out_cells ${c}
				lappend searchednames ${cname}
			}
		}
		if {[llength ${out_cells}] <= 0} {
			break
		}
		set out_pins [hsi get_pins -filter "DIRECTION==O" -of_objects ${out_cells}]
		set sink_pins [hsi::utils::get_sink_pins ${out_pins}]
	}
	return -1
}

proc is_ip_interrupt_connected {srcname} {
	set intr_pins [hsi get_pins -filter "DIRECTION==O && TYPE==INTERRUPT" -of_objects [hsi get_cells -hier ${srcname}]]
	if {[llength ${intr_pins}] <= 0 } {
		return -1
	}
	return 1
}

proc is_ip_interrupt_to_target {srcname endname} {
	set intr_pins [hsi get_pins -filter "DIRECTION==O && TYPE==INTERRUPT" -of_objects [hsi get_cells -hier ${srcname}]]
	if {[llength ${intr_pins}] <= 0 } {
		return -1
	}
	set sink_pins [hsi::utils::get_sink_pins ${intr_pins}]
	set searchednames [list ${srcname}]
	while {[llength ${sink_pins}] > 0} {
		set out_cells {}
		foreach s ${sink_pins} {
			foreach c [hsi get_cells -of_objects ${s}] {
				set cname [hsi get_property NAME ${c}]
				if { "${cname}" == "${endname}" } {
					return 1
				}
			}
		}
		foreach c [hsi get_cells -of_objects ${sink_pins}] {
			set cname [hsi get_property NAME ${c}]
			if {[lsearch ${searchednames} ${cname}] < 0} {
				lappend out_cells ${c}
				lappend searchednames ${cname}
			}
		}
		if {[llength ${out_cells}] <= 0} {
			break
		}
		set out_pins [hsi get_pins -filter "DIRECTION==O" -of_objects ${out_cells}]
		set sink_pins [hsi::utils::get_sink_pins ${out_pins}]
	}
	return -1
}

proc is_interrupt_required {ipinfo devtype} {
	set ipdev_info [get_ip_device_info "${devtype}" ${ipinfo}]
	set required_intr_property [lindex [get_ip_property_info interrupt_required ${ipdev_info}] 0]
	if {"${required_intr_property}" == "y" } {
		return 1
	} else {
		return -1
	}
}

proc interrupt_validation {ipinfo devtype iphd procname} {
	if {[is_interrupt_required ${ipinfo} ${devtype}] < 0} {
		return 1
	}
	set srcname [hsi get_property NAME ${iphd}]
	return [is_ip_interrupt_connected ${srcname}]
}

proc plnx_gen_conf_processor {mapping} {
	set retcpus {processor}
	set cpuinfofound ""
	set armlist {}
	set mblist {}
	set aarch64list {}

	foreach m ${mapping} {
		set index  0
		set ipname [lindex ${m} 0]
		set devinfo [get_ip_device_info processor ${m}]
		set archmapping [lindex [get_ip_property_info arch ${devinfo}] 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		set valid_instance_name [lindex [hsi get_cells -hier -filter IP_NAME==${ipname}] 0]
		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			if {"${valid_instance_name}" != "" && "${name}" != "${valid_instance_name}"} {
				continue
			}
			if {"${archmapping}" == "aarch64"} {
				lappend aarch64list "${name}:aarch64"
			} elseif {"${archmapping}" == "arm"} {
				lappend armlist "${name}:arm"
			} elseif {"${archmapping}" == "microblaze"} {
				lappend mblist "${name}:microblaze"
			}
			incr index
		}
	}
	if {[llength ${aarch64list}] > 0} {
		set armlist {}
		set mblist {}
	} elseif {[llength ${armlist}] > 0} {
		set mblist {}
	}

	foreach cpu [concat ${aarch64list} ${armlist} ${mblist}] {
		set cpuname [lindex [split ${cpu} ":"] 0]
		set archmapping [lindex [split ${cpu} ":"] 1]
		set hd [hsi get_cell -hier ${cpuname}]
		set ipname [hsi get_property IP_NAME ${hd}]
		set slaves_list {"slaves_strings"}
		foreach s [split [hsi get_property SLAVES ${hd}]] {
			if {[llength [hsi get_cell -hier ${s}]] == 0} {
				continue
			} else {
				lappend slaves_list ${s}
			}
		}
		set cpuinfofound "1"
		set cpudata [list "${cpuname}" [list arch ${archmapping}] [list ip_name ${ipname}] ${slaves_list}]
		if { "${ipname}" == "microblaze"} {
			set proc_inst_path [hsi get_property ADDRESS_TAG ${hd}]
			lappend cpudata [list instance_path [lindex [split ${proc_inst_path} ":"] 1]]
			set kparams [get_ip_property_info linux_kernel_properties ${m}]
			set koptions {linux_kernel_properties}
			foreach p ${kparams} {
				set kpname [lindex ${p} 0]
				set ipproperty [lindex ${p} 1]
				set kptype [lindex ${p} 2]
				set kval [hsi get_property ${ipproperty} ${hd}]
				if { "${kval}" != "" } {
					if {"${kpname}" == "XILINX_MICROBLAZE0_HW_VER"} {
						set verlist [split ${kval} ":"]
						set verindex [expr [llength ${verlist}] - 1]
						set kval [lindex ${verlist} ${verindex}]
					}
					lappend koptions [list ${kpname} ${kval} "${kptype}"]
				}
			}
			lappend cpudata ${koptions}
		}
		lappend retcpus ${cpudata}
	}
	if { "${cpuinfofound}" == "" } {
		puts stderr [format "%s\n%s\n%s\n" "No CPU can be found in the system."\
					"Please review your hardware system."\
					"Valid processors are: microblaze, ps7_cortexa9, psu_cortexa53, psv_cortexa72, psx_cortexa78."]
		error ""
	}
	return ${retcpus}
}


#proc to add bank address to dict
proc set_bank_addr {cpuname hd addr_list block_name i} {
	upvar addr_list localaddrlist
	set bankbaseaddr [common::get_property BASE_VALUE [lindex [hsi get_mem_ranges -of_objects [hsi get_cells -hier $cpuname] $hd] $i]]
	set bankhighaddr [common::get_property HIGH_VALUE [lindex [hsi get_mem_ranges -of_objects [hsi get_cells -hier $cpuname] $hd] $i]]
	if {"${bankbaseaddr}" != "" && "${bankhighaddr}" != ""} {
		dict set localaddrlist $block_name bankbaseaddr $bankbaseaddr
		dict set localaddrlist $block_name bankhighaddr $bankhighaddr
	}
}

proc plnx_gen_conf_memory {mapping cpuname cpuslaves} {
	set retmemories {}
	set devicetype "memory"
	set baseaddrstr ""
	set sizestr ""
	set baseaddrstr1 ""
	set sizestr1 ""
	set ubootoffsetstr ""
	set ddripname ""

	foreach m ${mapping} {
		set ipname [lindex ${m} 0]
		set devinfo [get_ip_device_info memory ${m}]
		set has_bank [lindex [get_ip_property_info has_bank ${devinfo}] 0]
		if { "${has_bank}" == "y" } {
			set banks_property [lindex [get_ip_property_info number_of_banks ${devinfo}] 0]
			set bankinfo [get_ip_property_info bank_property ${devinfo}]
			set bankidreplacement [lindex [get_ip_property_info bankid_replacement_str ${bankinfo}] 0]
			if {"banks_property" != "" } {
				set bank_enabled_property [lindex [get_ip_property_info bank_enabled ${bankinfo}] 0]
			}
			set bank_baseaddr_property [lindex [get_ip_property_info bank_baseaddr ${bankinfo}] 0]
			set bank_highaddr_property [lindex [get_ip_property_info bank_highaddr ${bankinfo}] 0]
			set bank_type_property [lindex [get_ip_property_info bank_type ${bankinfo}] 0]
		} else {
			set banks_property ""
			set bank_baseaddr_property [lindex [get_ip_property_info baseaddr ${devinfo}] 0]
			set bank_highaddr_property [lindex [get_ip_property_info highaddr ${devinfo}] 0]
			set bank_enabled_property ""
		}
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		foreach hd ${hds} {
			if {[llength ${bank_baseaddr_property}]} {
				set bankbaseaddr [hsi get_property ${bank_baseaddr_property} ${hd}]
				if {![llength $bankbaseaddr]} {
					set bank_baseaddr_property [lindex [get_ip_property_info baseaddr1 ${devinfo}] 0]
				}
			}
			if {[llength ${bank_highaddr_property}]} {
				set bankhighaddr [hsi get_property ${bank_highaddr_property} ${hd}]
				if {![llength $bankhighaddr]} {
					set bank_highaddr_property [lindex [get_ip_property_info highaddr1 ${devinfo}] 0]
				}
			}
			set name [hsi get_property NAME ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			if {"${has_bank}" == "n"} {
				if {[regexp "axi_noc" "${ipname}" match]} {
					set ddr [dict create is_ddr_low_0 0 is_ddr_low_1 0 is_ddr_low_2 0 is_ddr_low_3 0 is_ddr_ch_0 0 is_ddr_ch_1 0 is_ddr_ch_2 0 is_ddr_ch_3 0]
					set addr_list [dict create]
					set strlist ""
					set interface_block_names [hsi get_property ADDRESS_BLOCK [hsi get_mem_ranges -of_objects [hsi get_cells -hier $cpuname] $hd]]
					set i 0
					foreach block_name $interface_block_names {
						#filtering duplicate ddr banks
						if {[string match "C*_DDR_LOW0*" $block_name]} {
							if {[dict get $ddr is_ddr_low_0] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_low_0 1
						} elseif {[string match "C*_DDR_LOW1*" $block_name]} {
							if {[dict get $ddr is_ddr_low_1] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_low_1 1
						} elseif {[string match "C*_DDR_LOW2*" $block_name]} {
							if {[dict get $ddr is_ddr_low_2] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_low_2 1
						} elseif {[string match "C*_DDR_LOW3*" $block_name]} {
							if {[dict get $ddr is_ddr_low_3] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_low_3 1
						} elseif {[string match "C*_DDR_CH0*" $block_name]} {
							if {[dict get $ddr is_ddr_ch_0] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_ch_0 1
						} elseif {[string match "C*_DDR_CH1*" $block_name]} {
							if {[dict get $ddr is_ddr_ch_1] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_ch_1 1
						} elseif {[string match "C*_DDR_CH2*" $block_name]} {
							if {[dict get $ddr is_ddr_ch_2] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_ch_2 1
						} elseif {[string match "C*_DDR_CH3*" $block_name]} {
							if {[dict get $ddr is_ddr_ch_3] == 0} {
								set_bank_addr $cpuname $hd $addr_list $block_name $i
							}
							dict set ddr is_ddr_ch_3 1
                                                } else {
                                                        set_bank_addr $cpuname $hd $addr_list $block_name $i
                                                }
						incr i
					}
					foreach block_name [dict keys $addr_list] {
						set baseaddr [dict get $addr_list $block_name bankbaseaddr]
						set highaddr [dict get $addr_list $block_name bankhighaddr]
						if {"${baseaddr}" != "" && "${highaddr}" != ""} {
							set memnode [list "${name}_${block_name}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${baseaddr}] [list highaddr "${highaddr}"]]
							lappend retmemories ${memnode}
						}
					}
				} else {
					set bankbaseaddr [hsi get_property ${bank_baseaddr_property} ${hd}]
					set bankhighaddr [hsi get_property ${bank_highaddr_property} ${hd}]
					if {[regexp "ps[7]_ddr" "${ipname}" match]} {
						set bankbaseaddr "0x0"
					}
					if {"${bankbaseaddr}" != "" && "${bankhighaddr}" != ""} {
						set memnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr "${bankhighaddr}"]]
						lappend retmemories ${memnode}
					}
				}
			} elseif {"${has_bank}" == "y" && "${banks_property}" != ""} {
				set bankcount [hsi get_property ${banks_property} ${hd}]
				if { "${ipname}" == "axi_emc" } {
					set bankcount_emc [llength [hsi list_property ${hd} CONFIG.C_S_AXI_MEM*_BASEADDR]]
					set bank_baseaddr_property [lindex [get_ip_property_info bank_baseaddr ${bankinfo}] 0]
					set bank_highaddr_property [lindex [get_ip_property_info bank_highaddr ${bankinfo}] 0]
					set bank_type_property [lindex [get_ip_property_info bank_type ${bankinfo}] 0]
					set bankcount $bankcount_emc
				}

				for {set i 0} {$i < ${bankcount}} {incr i} {
					set idmap [list "${bankidreplacement}" ${i}]
					set basestrmap [string map ${idmap} "${bank_baseaddr_property}"]
					set highstrmap [string map ${idmap} "${bank_highaddr_property}"]
					set typestrmap [string map ${idmap} "${bank_type_property}"]
					if {"${ipname}" == "axi_emc"} {
						set isflash [hsi get_property CONFIG.EMC_BOARD_INTERFACE ${hd}]
						# Assume Custom as flash
						if {"${isflash}" == "linear_flash" || "${isflash}" == "Custom"} {
							# It is flash
							continue
						}
					}
					set bankbaseaddr [hsi get_property ${basestrmap} ${hd}]
					set bankhighaddr [hsi get_property ${highstrmap} ${hd}]
					if {"${bankbaseaddr}" != "" && "${bankhighaddr}" != ""} {
						set memnode [list "${name}_bank${i}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr "${bankhighaddr}"]]
						lappend retmemories ${memnode}
					}
				}
			} else {
				for {set i 0} {$i < 32} {incr i} {
					set idmap [list "${bankidreplacement}" ${i}]
					set basestrmap [string map ${idmap} "${bank_baseaddr_property}"]
					set highstrmap [string map ${idmap} "${bank_highaddr_property}"]
					set typestrmap [string map ${idmap} "${bank_type_property}"]
					set bankenablemap [string map ${idmap} "${bank_enabled_property}"]
					set bankenabled [hsi get_property ${bankenablemap} ${hd}]
					if {"${bankenabled}" == ""} {
						break
					} elseif {"${bankenabled}" == "0"} {
						continue
					}
					set bankbaseaddr [hsi get_property ${basestrmap} ${hd}]
					set bankhighaddr [hsi get_property ${highstrmap} ${hd}]
					if {"${bankbaseaddr}" != "" && "${bankhighaddr}" != ""} {
						set memnode [list "${name}_bank${i}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr "${bankhighaddr}"]]
						lappend retmemories ${memnode}
					}
				}
			}
		}
	}
	return ${retmemories}
}

proc plnx_gen_conf_serial {mapping cpuname cpuslaves} {
	set retserials {}
	set devicetype "serial"
	global current_arch
	foreach m ${mapping} {
		set ipname [lindex ${m} 0]
		set devinfo [get_ip_device_info serial ${m}]
		set baudrateproperty [lindex [get_ip_property_info default_baudrate ${devinfo}] 0]
		set hcbaudrate [lindex [get_ip_property_info default_baudrate_value ${devinfo}] 0]
		set is_baudrate_editable [lindex [get_ip_property_info baudrate_editable ${devinfo}] 0]
		set baseaddr_property [lindex [get_ip_property_info baseaddr ${devinfo}] 0]
		set is_config_uart_property [lindex [get_ip_property_info is_serial_property ${devinfo}] 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			set is_pl [hsi get_property IS_PL ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			if { "${is_config_uart_property}" != "" } {
				set is_config_uart [hsi get_property ${is_config_uart_property} ${hd}]
				if { "${is_config_uart}" == "" || "${is_config_uart}" == "0" } {
					continue
				}
			}
			if { "${baseaddr_property}" != "" } {
				set uart_baseaddr [hsi get_property ${baseaddr_property} ${hd}]
			}
			if {[interrupt_validation ${m} ${devicetype} ${hd} ${cpuname}] < 0} {
				continue
			}
			set kname [plnx_fix_kconf_name ${name}]
			if {"${baudrateproperty}" != "" && "${is_baudrate_editable}" == "n"} {
				set baudrates($kname) [list [hsi get_property ${baudrateproperty} ${hd}]]
			} elseif {"${hcbaudrate}" != "" } {
				set baudrates($kname) [list "${hcbaudrate}"]
			} else {
				set baudrates($kname) {600 9600 28800 115200 230400 460800 921600}
			}
			if { "${baseaddr_property}" != "" } {
				set serialnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${uart_baseaddr}] [list is_pl ${is_pl}]]
			} else {
				set serialnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list is_pl ${is_pl}]]
			}
			lappend retserials ${serialnode}
		}
	}

	return ${retserials}
}

proc plnx_gen_conf_ethernet {mapping cpuname cpuslaves} {
	set reteths {}
	set devicetype "ethernet"
	foreach m ${mapping} {
		set ipname [lindex ${m} 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			if {[interrupt_validation ${m} ${devicetype} ${hd} ${cpuname}] < 0} {
				continue
			}
			set ethernetnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend reteths ${ethernetnode}
		}
	}
	return ${reteths}
}

proc plnx_gen_conf_sd {mapping cpuname cpuslaves} {
	set retsds {}
	set devicetype "sd"
	foreach m ${mapping} {
		set ipname [lindex ${m} 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			if {[interrupt_validation ${m} ${devicetype} ${hd} ${cpuname}] < 0} {
				continue
			}
			set sdnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend retsds ${sdnode}
		}
	}
	plnx_gen_conf_basic ${mapping} ${cpuname} ${cpuslaves} "SD"
	return ${retsds}
}


proc plnx_gen_conf_usb {mapping cpuname cpuslaves} {
	set retusbs [plnx_gen_conf_basic ${mapping}  ${cpuname} ${cpuslaves} "USB"]
	return ${retusbs}
}

proc plnx_gen_conf_basic {mapping cpuname cpuslaves devicetype} {
	set retdev {}
	set devicetype [string tolower ${devicetype}]
	foreach m ${mapping} {
		set ipname [lindex ${m} 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			if {[interrupt_validation ${m} ${devicetype} ${hd} ${cpuname}] < 0} {
				continue
			}
			set devnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend retdev ${devnode}
		}
	}
	return ${retdev}
}


proc plnx_gen_conf_flash {mapping cpuname cpuslaves} {
	set retflashs {}
	set devicetype "flash"
	foreach m ${mapping} {
		set ipname [lindex ${m} 0]
		set devinfo [get_ip_device_info flash ${m}]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			if {[interrupt_validation ${m} ${devicetype} ${hd} ${cpuname}] < 0} {
				continue
			}
			set kname [plnx_fix_kconf_name ${name}]
			set flash_type [lindex ${m} 1]
			set flash_type1 [lindex ${flash_type} 1]
			set flash_prefix [lindex $flash_type1 [lsearch $flash_type1 "*flash_prefix*"] 1]
			# TODO: add psu flash support
			if {"${ipname}" == "axi_emc"} {
				set banks_property [lindex [get_ip_property_info number_of_banks ${devinfo}] 0]
				set bankinfo [get_ip_property_info bank_property ${devinfo}]
				set bankidreplacement [lindex [get_ip_property_info bankid_replacement_str ${bankinfo}] 0]
				set bank_baseaddr_property [lindex [get_ip_property_info bank_baseaddr ${bankinfo}] 0]
				set bank_highaddr_property [lindex [get_ip_property_info bank_highaddr ${bankinfo}] 0]
				set bank_type_property [lindex [get_ip_property_info bank_type ${bankinfo}] 0]
				set bankcount [hsi get_property ${banks_property} ${hd}]
				for {set i 0} {$i < ${bankcount}} {incr i} {
					set idmap [list "${bankidreplacement}" ${i}]
					set basestrmap [string map ${idmap} "${bank_baseaddr_property}"]
					set highstrmap [string map ${idmap} "${bank_highaddr_property}"]
					set typestrmap [string map ${idmap} "${bank_type_property}"]
					set isflash [hsi get_property CONFIG.EMC_BOARD_INTERFACE ${hd}]
					# Assume Custom as flash
					if {"${isflash}" != "linear_flash" && "${isflash}" != "Custom"} {
						# It is memory
						continue
					}
					set bankbaseaddr [hsi get_property ${basestrmap} ${hd}]
					set bankhighaddr [hsi get_property ${highstrmap} ${hd}]
					set flashnode [list "${name}_bank${i}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr ${bankhighaddr}]]
					lappend retflashs ${flashnode}
				}
			} elseif {"${flash_type}" == "spi"} {
				set cs_bits_property [lindex [get_ip_property_info number_cs ${devinfo}] 0]
				if {"${cs_bits_property}" != ""} {
					set cs_bits [hsi get_property ${cs_bits_property} ${hd}]
				} else {
					set cs_bits 0
				}
				set flashnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list cs_bits ${cs_bits}]
				lappend retflashs ${flashnode}
			} elseif {"${ipname}" == "ps7_sram"} {
				if {"${name}" == "ps7_sram_0"} {
					set nor_cs [hsi get_property CONFIG.C_NOR_CHIP_SEL0 [hsi get_cell -hier "ps7_smcc_0"]]
				} else {
					set nor_cs [hsi get_property CONFIG.C_NOR_CHIP_SEL1 [hsi get_cell -hier "ps7_smcc_0"]]
				}
				if {"${nor_cs}" == "0"} {
					continue
				}
				set flashnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
				lappend retflashs ${flashnode}
			} else {
				set flashnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
				lappend retflashs ${flashnode}
			}
		}
	}
	return ${retflashs}
}

proc get_ipinfo {args} {
	global scripts_path
	set ipinfofile "${scripts_path}/data/ipinfo.yaml"
	if { [catch {open "${ipinfofile}" r} ipinfof] } {
		error "Failed to open IP information file ${ipinfofile}."
	}

	set ipinfodata ""
	set previous_indent_level -1
	set linenum 0
	while {1} {
		if { [eof ${ipinfof}] > 0} {
			for {set i ${previous_indent_level}} {${i} >= 0} {incr i -1} {
				set ipinfodata "${ipinfodata}\}"
			}

			close ${ipinfof}
			break
		}
		set line [gets ${ipinfof}]
		incr linenum
		#regsub -all {\s+} $line { } line
		if { [regexp "^#.*" $line matched] == 1 || \
			[regexp "^\s+#.*" $line matched] == 1 || \
			[string compare -nocase [string trim $line] ""] <= 0 } {
			continue
		}
		set trimline [string trim ${line}]
		if { [regexp {^(    )*[A-Za-z0-9_]+:.*} "${line}" matched] == 1} {
			set tmpline [string map {: " "} ${trimline}]
			set indent_level [regexp -all "(    )" ${line}]
			if {${indent_level} < ${previous_indent_level}} {
				for {set i ${indent_level}} {${i} <= ${previous_indent_level}} {incr i} {
					set ipinfodata "${ipinfodata}\}"
				}
				set ipinfodata "${ipinfodata} \{${tmpline}"
			} elseif {${indent_level} > ${previous_indent_level}} {
				if {[expr ${indent_level} - ${previous_indent_level}] > 1} {
					error "Wrong indentation in line ${linenum} of ${ipinfofile}"
				}
				set ipinfodata "${ipinfodata} \{${tmpline}"
			} else {
				set ipinfodata "${ipinfodata}\} \{${tmpline}"
			}
			set previous_indent_level ${indent_level}
		}
	}
	set ip_list {}
	eval set ip_list "\{${ipinfodata}\}"
	return "${ip_list}"
}

proc is_ip_valid_for_device_type {devtype ipinfo} {
	set e [lsearch -index 0 -inline ${ipinfo} "device_type"]
	return [lsearch -index 0 ${e} "${devtype}"]
}

proc get_devices_nodes {devinfo} {
	set devicenode [lsearch -index 0 -inline ${devinfo} "devices"]
	return [lreplace ${devicenode} 0 0]
}

proc get_ip_device_info {devtype ipinfo} {
	set e [lsearch -index 0 -inline ${ipinfo} "device_type"]
	set deve [lsearch -index 0 -inline ${e} "${devtype}"]
	return [lreplace ${deve} 0 0]
}

proc get_ip_property_info {property ipinfo} {
	set e [lsearch -index 0 -inline ${ipinfo} "${property}"]
	return [lreplace ${e} 0 0]
}

proc generate_mapping_list {args} {
	set ipinfolist [get_ipinfo]
	set devicetypes {processor memory serial ethernet flash sd usb}
	set mappinglist {}
	foreach devtype ${devicetypes} {
		set devtype_mapping {}
		lappend devtype_mapping "${devtype}"
		if {"${devtype}" == "sd"} {
			lappend devtype_mapping "processor_ip ps7_cortexa9 psu_cortexa53 psv_cortexa72 psx_cortexa78"
		} elseif {"${devtype}" == "timer"} {
			lappend devtype_mapping "processor_ip microblaze"
		} elseif {"${devtype}" == "reset_gpio"} {
			lappend devtype_mapping "processor_ip microblaze"
		}
		set ips {devices}
		foreach ipinfo ${ipinfolist} {
			if {[is_ip_valid_for_device_type "${devtype}" ${ipinfo}] >= 0} {
				lappend ips ${ipinfo}
			}
		}
		lappend devtype_mapping ${ips}
		lappend mappinglist ${devtype_mapping}
	}
	return ${mappinglist}
}

proc get_soc_info {args} {
	set args [split [lindex ${args} 0]]
	set hdf [lindex ${args} 0]
	if { "${hdf}" == "" } {
		error "No Hardware description file is specified."
	}
	if { [catch {openhw "${hdf}"} res] } {
		error "Failed to open hardware design from ${hdf}"
	}
	# getting device_id from hw file
	set current_proc_list [hsi get_cells -hier -filter {IP_NAME==psx_cortexa78 || \
				IP_NAME==psv_cortexa72 || IP_NAME==psu_cortexa53 || \
				IP_NAME==ps7_cortexa9 || IP_NAME==microblaze}]
	set current_proc [hsi get_property IP_NAME [lindex $current_proc_list 0]]
	puts "{\"proc_name\": \"$current_proc\"}"
}

proc plnx_gen_hwsysconf {args} {
	set args [split [lindex ${args} 0]]
	set hdf [lindex ${args} 0]
	if { "${hdf}" == "" } {
		error "No Hardware description file is specified."
	}
	if { [catch {openhw "${hdf}"} res] } {
		error "Failed to open hardware design from ${hdf}"
	}
	global plnx_data
	if { [catch {open "plnx_syshw_data" w} plnx_data] } {
		error "Failed to open output Kconfig data file ${plnx_data}"
	}

	# getting device_id from hw file
	set current_design [hsi get_property DEVICE [hsi current_hw_design]]
	plnx_output_data "device_id $current_design"

	# getting bitfile name from hw file
	set bitfile_name [hsi get_property NAME [hsi current_hw_design]]
	plnx_output_data "hw_design_name $bitfile_name"

	set mapping [generate_mapping_list]

	set cpumapping [get_devices_nodes [lindex ${mapping} 0]]

	set retcpus [plnx_gen_conf_processor ${cpumapping}]
	global current_arch
	set cpus_nodes {processor}
	foreach c [lreplace ${retcpus} 0 0] {
		set cpuname [lindex ${c} 0]
		set cpuarch [lindex [get_ip_property_info "arch" ${c}] 0]
		set current_arch ${cpuarch}
		set cpuipname [lindex [get_ip_property_info "ip_name" ${c}] 0]
		set cpuslaves [get_ip_property_info "slaves_strings" ${c}]
		set retsd {}
		set retflash {}
		set retslaves {slaves}
		foreach m [lreplace ${mapping} 0 0] {
			set class [lindex ${m} 0]
			set classcpuipnames [get_ip_property_info "processor_ip" ${m}]
			if { [llength ${classcpuipnames}] > 0 && [lsearch ${classcpuipnames} "${cpuipname}"] < 0 } {
				continue
			}
			set elements [get_devices_nodes ${m}]
			set pproc "plnx_gen_conf_${class}"
			if { "[info procs ${pproc}]" eq "${pproc}"} {
				set ret${class} [${pproc} ${elements} "${cpuname}" "${cpuslaves}"]
				foreach r [set ret${class}] {
					lappend retslaves ${r}
				}
			}
		}
		global plnx_ips_record
		foreach s [split ${cpuslaves}] {
			if { [lsearch -index 0 ${retslaves} "${s}"] < 0 } {
				set sipname [hsi get_property IP_NAME [hsi get_cell -hier "${s}"]]
				lappend retslaves [list ${s} [list ip_name ${sipname}]]
			}
		}
		lappend c ${retslaves}
		lappend cpus_nodes ${c}
	}
	plnx_output_data ${cpus_nodes}
	close ${plnx_data}
}

proc plnx_shift {ls} {
	upvar 1 $ls LIST
	set ret [lindex $LIST 0]
	set LIST [lreplace $LIST 0 0]
	return $ret
}

# source xsct tools script which are no longer exported to user
set xsct_path [exec which xsct]
set xsct_root_dir [file dirname [file dirname "${xsct_path}"]]

set scripts_path [ file dirname [ file normalize [ info script ] ] ]
# source libs
foreach lib_file [glob -directory $scripts_path/libs/ *] {
        source $lib_file
}

set cmdline $argv
set tclproc [plnx_shift cmdline]
set plnx_kconfig 0
set plnx_data 0
set current_arch ""
set plnx_ips_record {}
if { "[info procs ${tclproc}]" eq "${tclproc}"} {
	${tclproc} ${cmdline}
} else {
	error "proc ${tclproc} doesn't exit."
}
