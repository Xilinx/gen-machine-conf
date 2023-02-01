# Copyright (C) 2016-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

proc plnx_output_kconfig {msg} {
	global plnx_kconfig
	puts ${plnx_kconfig} "${msg}"
}

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
	#puts "srchd : $srchd endname : $endname end_pin_type : $end_pin_type pin_name : $pin_name"
	set srcname [hsi get_property NAME ${srchd}]
	set searchednames [list ${srcname}]
	#puts "srcname : $srcname searchednames : $searchednames"
	set out_pins [hsi get_pins -filter "DIRECTION==O && NAME=~${pin_name}" -of_objects ${srchd}]

	#puts "srcname : $srcname searchednames : $searchednames out_pins : $out_pins"
	set sink_pins [hsi::utils::get_sink_pins ${out_pins}]
	#set sink_pins [hsi::utils::get_sink_pins [hsi get_pins -filter "DIRECTION==O && NAME=~${pin_name}" -of_objects ${srchd}]]
	#puts "sink_pins : $sink_pins"
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

proc plnx_gen_conf_processor {mapping kconfprefix} {
	set retcpus {processor}
	set cpukconfprefix "${kconfprefix}PROCESSOR_"
	set cpuchoicesstr ""
	set armknamelist {}
	set mbknamelist {}
	set aarch64namelist {}
	set armlist {}
	set mblist {}
	set aarch64list {}
	set kconfstr ""

	foreach m ${mapping} {
		#puts " m : ${m}"
		set index  0
		set ipname [lindex ${m} 0]
		set devinfo [get_ip_device_info processor ${m}]
		set archmapping [lindex [get_ip_property_info arch ${devinfo}] 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]
		set valid_instance_name [lindex [hsi get_cells -hier -filter IP_NAME==${ipname}] 0]
		#puts "ipname : $ipname devinfo : $devinfo archmapping : $archmapping valid_instance_name : $valid_instance_name"
		foreach hd ${hds} {
			#puts "hd : ${hd}"
			set name [hsi get_property NAME ${hd}]
			#puts "name : $name"
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
			set kconfstr [format "%s\n%s\n%s\n%s\n"  "${kconfstr}"\
			"config SUBSYSTEM_PROCESSOR${index}_IP_NAME" \
			"string"\
			"default ${name}" ]
			if {"${archmapping}" == "microblaze" && [llength $aarch64list] == 0 && [llength $armlist] == 0 } {
				set proc_inst_path [hsi get_property ADDRESS_TAG ${hd}]
				set kconfstr [format "%s\n%s\n%s\n%s\n"  "${kconfstr}"\
				"config SUBSYSTEM_PROCESSOR${index}_INSTANCE_PATH" \
				"string"\
				"default [lindex [split ${proc_inst_path} ":"] 1]" ]
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
		#puts "hd : $hd ipname : $ipname cpu : $cpu"
		foreach s [split [hsi get_property SLAVES ${hd}]] {
			if {[llength [hsi get_cell -hier ${s}]] == 0} {
				continue
			} else {
				lappend slaves_list ${s}
			}
		}
		#puts "slaves_list : slaves_list"
		set kname  ${cpuname}
		set ipkname ${ipname}
		set kname ${cpuname}
		if {"${archmapping}" == "arm"} {
			lappend armknamelist "${cpukconfprefix}${kname}_SELECT"
		} elseif {"${archmapping}" == "microblaze"} {
			lappend mbknamelist "${cpukconfprefix}${kname}_SELECT"
		} elseif {"${archmapping}" == "aarch64"} {
			lappend aarch64namelist "${cpukconfprefix}${kname}_SELECT"
		}
		set cpuchoicesstr [format "%s%s\n\t%s\n" "${cpuchoicesstr}" "config ${cpukconfprefix}${kname}_SELECT" \
			"bool \"${cpuname}\""]
		set cpudata [list "${cpuname}" [list arch ${archmapping}] [list ip_name ${ipname}] ${slaves_list}]
		#puts "cpudata : $cpudata"
		if { "${ipname}" == "microblaze"} {
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
	#puts "retcpus : $retcpus"
	if { "${cpuchoicesstr}" == "" } {
		puts stderr [format "%s\n%s\n%s\n" "No CPU can be found in the system."\
					"Please review your hardware system."\
					"Valid processors are: microblaze, ps7_cortexa9, psu_cortexa53, psv_cortexa72, psx_cortexa78."]
		error ""
	}
	set kconfstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n%s\n%s\n" "${kconfstr}" \
		"choice" \
		"prompt \"System Processor\"" \
		"help" \
		" Select a processor as the system processor" \
		"${cpuchoicesstr}" \
		"endchoice"]
	if {[llength ${armknamelist}] > 0} {
		set kconfstr [format "%s\n%s\n\t%s\n\t%s\n\t%s%s\n" "${kconfstr}" \
		"config SUBSYSTEM_ARCH_ARM" \
		"bool" \
		"default y" \
		"depends on " \
		[join ${armknamelist} " ||"] ]
	}
	if {[llength ${mbknamelist}] > 0} {
		set kconfstr [format "%s\n%s\n\t%s\n\t%s\n\t%s%s\n" "${kconfstr}" \
		"config SUBSYSTEM_ARCH_MICROBLAZE" \
		"bool" \
		"default y" \
		"depends on " \
		[join ${mbknamelist} " ||"] ]
	}
	if {[llength ${aarch64namelist}] > 0} {
		set kconfstr [format "%s\n%s\n\t%s\n\t%s\n\t%s%s\n" "${kconfstr}" \
		"config SUBSYSTEM_ARCH_AARCH64" \
		"bool" \
		"default y" \
		"depends on " \
		[join ${aarch64namelist} " ||"] ]
	}
	plnx_output_kconfig "${kconfstr}"
	return ${retcpus}
}

proc plnx_gen_memory_bank_kconfig {bankid bankbaseaddr bankhighaddr instance_name kconfig_prefix} {
	set baseaddrstr ""
	set sizestr ""
	set ubootoffsetstr ""
	set choicestr ""
	if { "${bankbaseaddr}" == "" || "${bankhighaddr}" == "" } {
		error "No memory base address and high address is provided"
	}
	set banksize [format 0x%x [expr ${bankhighaddr} - ${bankbaseaddr} + 1]]
	if {[expr ${banksize}] >= [expr 0x2000000]} {
		set kname [plnx_fix_kconf_name ${instance_name}]
		if {"${bankid}" == ""} {
			set bankkconf "BANKLESS"
			set promptname "${instance_name}"
		} else {
			set bankkconf "BANK${bankid}"
			set promptname "${instance_name} bank${bankid}"
		}
		set choicestr [format "%s\n\t%s\n" "config ${kconfig_prefix}${kname}_${bankkconf}_SELECT" \
			"bool \"${promptname}\""]
		set baseaddrstr [format "%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" \
			"config ${kconfig_prefix}${kname}_${bankkconf}_BASEADDR" \
			"hex \"System memory base address\"" \
			"default ${bankbaseaddr}" \
			"range ${bankbaseaddr} [format 0x%x [expr ${bankhighaddr} - 0x2000000 + 1]]" \
			"depends on ${kconfig_prefix}${kname}_${bankkconf}_SELECT" \
			"help" \
			"  Start address of the system memory." \
			"  It has to be within the selected primary memory physical address range." \
			"  Make sure the DT memory entry should start with provided address."]
		set sizestr [format "%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" \
			"config ${kconfig_prefix}${kname}_${bankkconf}_SIZE" \
			"hex \"System memory size\"" \
			"default ${banksize}" \
			"range 0x2000000 ${banksize}" \
			"depends on ${kconfig_prefix}${kname}_${bankkconf}_SELECT" \
			"help" \
			"  Size of the system memory. Minimum is 32MB, maximum is the size of" \
			"  the selected primary memory physical address range."]
		set kernelbaseaddrstr [format "%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" \
			"config ${kconfig_prefix}${kname}_${bankkconf}_KERNEL_BASEADDR" \
			"hex \"kernel base address\"" \
			"default ${bankbaseaddr}" \
			"range ${bankbaseaddr} [format 0x%x [expr ${bankbaseaddr} + ${banksize} - 0x2000000]]" \
			"depends on ${kconfig_prefix}${kname}_${bankkconf}_SELECT" \
			"depends on SUBSYSTEM_ARCH_ARM || SUBSYSTEM_ARCH_AARCH64" \
			"help" \
			"  kernel base address."]
		set ubootoffsetstr [format "%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" \
			"config ${kconfig_prefix}${kname}_${bankkconf}_U__BOOT_TEXTBASE_OFFSET" \
			"hex \"u-boot text base address offset to memory base address\"" \
			"default 0x100000" \
			"range 0x100000 [format 0x%x [expr ${banksize} - 0x2000000 + 0x100000]]" \
			"depends on ${kconfig_prefix}${kname}_${bankkconf}_SELECT" \
			"depends on !SUBSYSTEM_COMPONENT_U__BOOT_NAME_NONE" \
			"help" \
			"  u-boot offset to the memory base address. Minimum suggested is 1MB."]
		set ddripname [format "%s\n\t%s\n\t%s\n\t%s\n" \
			"config ${kconfig_prefix}IP_NAME" \
			"string" \
			"default $kname" \
			"depends on ${kconfig_prefix}${kname}_${bankkconf}_SELECT"]
		return [list "${choicestr}" "${baseaddrstr}" "${sizestr}" "${kernelbaseaddrstr}" "${ubootoffsetstr}" "${ddripname}"]
	} else {
		return ""
	}
}

proc plnx_gen_conf_memory {mapping kconfprefix cpuname cpuslaves} {
	set retmemories {}
	set devicetype "memory"
	set memorykconfprefix "${kconfprefix}MEMORY_"
	set choicestr ""
	set baseaddrstr ""
	set sizestr ""
	set baseaddrstr1 ""
	set sizestr1 ""
	set ubootoffsetstr ""
	set kernelbaseaddrstr ""
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
			#puts "ipname=${ipname} bank_baseaddr_property=${bank_baseaddr_property} bank_highaddr_property=${bank_highaddr_property}"
			#puts "bankidreplacement=${bankidreplacement} banks_property=${banks_property} bank_type_property=${bank_type_property} bankidreplacement=${bankidreplacement}"
		} else {
			set banks_property ""
			set bank_baseaddr_property [lindex [get_ip_property_info baseaddr ${devinfo}] 0]
			set bank_highaddr_property [lindex [get_ip_property_info highaddr ${devinfo}] 0]
			set bank_enabled_property ""
			#puts "ipname=${ipname} bank_baseaddr_property=${bank_baseaddr_property} bank_highaddr_property=${bank_highaddr_property}"
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
			set kname [plnx_fix_kconf_name ${name}]
			if {"${has_bank}" == "n"} {
				if {[regexp "axi_noc" "${ipname}" match]} {
					set addr_list [dict create]
					set strlist ""
					set interface_block_names [hsi get_property ADDRESS_BLOCK [hsi get_mem_ranges -of_objects [hsi get_cells -hier $cpuname] $hd]]
					set i 0
					foreach block_name $interface_block_names {
						set bankbaseaddr [common::get_property BASE_VALUE [lindex [hsi get_mem_ranges -of_objects [hsi get_cells -hier $cpuname] $hd] $i]]
						set bankhighaddr [common::get_property HIGH_VALUE [lindex [hsi get_mem_ranges -of_objects [hsi get_cells -hier $cpuname] $hd] $i]]
						if {"${bankbaseaddr}" != "" && "${bankhighaddr}" != ""} {
							dict set addr_list $block_name bankbaseaddr $bankbaseaddr
							dict set addr_list $block_name bankhighaddr $bankhighaddr
						}
						incr i
					}
					foreach block_name [dict keys $addr_list] {
						set baseaddr [dict get $addr_list $block_name bankbaseaddr]
						set highaddr [dict get $addr_list $block_name bankhighaddr]
						if {"${baseaddr}" != "" && "${highaddr}" != ""} {
							set strlist [plnx_gen_memory_bank_kconfig "" ${baseaddr} ${highaddr} "${block_name}" "${memorykconfprefix}"]
							set tmpchoicestr [lindex ${strlist} 0]
							if {"${tmpchoicestr}" != ""} {
								set choicestr [format "%s%s" "${choicestr}" "${tmpchoicestr}"]
								set baseaddrstr [format "%s\n%s\n" "${baseaddrstr}" [lindex ${strlist} 1]]
								set sizestr [format "%s\n%s\n" "${sizestr}" [lindex ${strlist} 2]]
								set kernelbaseaddrstr [format "%s\n%s\n" "${kernelbaseaddrstr}" [lindex ${strlist} 3]]
								set ubootoffsetstr [format "%s\n%s\n" "${ubootoffsetstr}" [lindex ${strlist} 4]]
								set ddripname [format "%s\n%s\n" "${ddripname}" [lindex ${strlist} 5]]
								set memnode [list "${name}_bankless" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr "${bankhighaddr}"]]
								lappend retmemories ${memnode}
							}
						}
					}
				} else {
					set bankbaseaddr [hsi get_property ${bank_baseaddr_property} ${hd}]
					set bankhighaddr [hsi get_property ${bank_highaddr_property} ${hd}]
					if {[regexp "ps[7]_ddr" "${ipname}" match]} {
						set bankbaseaddr "0x0"
					}
					set strlist [plnx_gen_memory_bank_kconfig "" ${bankbaseaddr} ${bankhighaddr} "${name}" "${memorykconfprefix}"]
					set tmpchoicestr [lindex ${strlist} 0]
					if {"${tmpchoicestr}" != ""} {
						set choicestr [format "%s%s" "${choicestr}" "${tmpchoicestr}"]
						set baseaddrstr [format "%s\n%s\n" "${baseaddrstr}" [lindex ${strlist} 1]]
						set sizestr [format "%s\n%s\n" "${sizestr}" [lindex ${strlist} 2]]
						set kernelbaseaddrstr [format "%s\n%s\n" "${kernelbaseaddrstr}" [lindex ${strlist} 3]]
						set ubootoffsetstr [format "%s\n%s\n" "${ubootoffsetstr}" [lindex ${strlist} 4]]
						set ddripname [format "%s\n%s\n" "${ddripname}" [lindex ${strlist} 5]]
						set memnode [list "${name}_bankless" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr "${bankhighaddr}"]]
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
						set banktype [hsi get_property ${typestrmap} ${hd}]
						if {"${banktype}" == "2" || "${banktype}" == "3"} {
							# It is flash
							continue
						}
					}
					set bankbaseaddr [hsi get_property ${basestrmap} ${hd}]
					set bankhighaddr [hsi get_property ${highstrmap} ${hd}]
					set strlist [plnx_gen_memory_bank_kconfig "${i}" ${bankbaseaddr} ${bankhighaddr} "${name}" "${memorykconfprefix}"]
					set tmpchoicestr [lindex ${strlist} 0]
					if {"${tmpchoicestr}" != ""} {
						set choicestr [format "%s%s" "${choicestr}" "${tmpchoicestr}"]
						set baseaddrstr [format "%s\n%s\n" "${baseaddrstr}" [lindex ${strlist} 1]]
						set sizestr [format "%s\n%s\n" "${sizestr}" [lindex ${strlist} 2]]
						set kernelbaseaddrstr [format "%s\n%s\n" "${kernelbaseaddrstr}" [lindex ${strlist} 3]]
						set ubootoffsetstr [format "%s\n%s\n" "${ubootoffsetstr}" [lindex ${strlist} 4]]
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
					set strlist [plnx_gen_memory_bank_kconfig "${i}" ${bankbaseaddr} ${bankhighaddr} "${name}" "${memorykconfprefix}"]
					set tmpchoicestr [lindex ${strlist} 0]
					if {"${tmpchoicestr}" != ""} {
						set choicestr [format "%s%s" "${choicestr}" "${tmpchoicestr}"]
						set baseaddrstr [format "%s\n%s\n" "${baseaddrstr}" [lindex ${strlist} 1]]
						set sizestr [format "%s\n%s\n" "${sizestr}" [lindex ${strlist} 2]]
						set kernelbaseaddrstr [format "%s\n%s\n" "${kernelbaseaddrstr}" [lindex ${strlist} 3]]
						set ubootoffsetstr [format "%s\n%s\n" "${ubootoffsetstr}" [lindex ${strlist} 4]]
						set memnode [list "${name}_bank${i}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr "${bankhighaddr}"]]
						lappend retmemories ${memnode}
					}
				}
			}
		}
	}
	set choicestr [format "%s\n%s\n\t%s\n" "${choicestr}" \
		"config ${memorykconfprefix}MANUAL_SELECT" \
		"bool \"manual\""]
	set baseaddrstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${baseaddrstr}" \
		"config ${memorykconfprefix}MANUAL_LOWER_BASEADDR" \
		"hex \"Lower memory base address\"" \
		"default 0x0" \
		"depends on ${memorykconfprefix}MANUAL_SELECT" \
		"help" \
		"  base address of the lower memory" \
		"  Make sure the DT memory entry should start with provided address."]
	set sizestr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${sizestr}" \
		"config ${memorykconfprefix}MANUAL_LOWER_MEMORYSIZE" \
		"hex \"Lower memory size\"" \
		"default 0x80000000" \
		"depends on ${memorykconfprefix}MANUAL_SELECT" \
		"help" \
		"  Size of the lower memory. Minimum is 32MB, maximum is the size of" \
		"  the selected primary memory physical address range." \
		"  If you specify 0x0 offset then it will skip generating lower memory node."]
	set baseaddrstr1 [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${baseaddrstr1}" \
		"config ${memorykconfprefix}MANUAL_UPPER_BASEADDR" \
		"hex \"Upper memory base address\"" \
		"default 0x800000000" \
		"depends on ${memorykconfprefix}MANUAL_SELECT" \
		"depends on SUBSYSTEM_ARCH_AARCH64" \
		"help" \
		"  base address of the upper memory" \
		"  Make sure the DT memory entry should start with provided address."]
	set sizestr1 [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${sizestr1}" \
		"config ${memorykconfprefix}MANUAL_UPPER_MEMORYSIZE" \
		"hex \"Upper memory size\"" \
		"default 0x80000000" \
		"depends on ${memorykconfprefix}MANUAL_SELECT" \
		"depends on SUBSYSTEM_ARCH_AARCH64" \
		"help" \
		"  Size of the upper memory. Minimum is 32MB, maximum is the size of" \
		"  the selected primary memory physical address range." \
		"  If you specify 0x0 offset then it will skip generating upper memory node."]
	set choicestr [format "%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" \
		"choice" \
		"prompt \"Primary Memory\"" \
		"help" \
		"  The configuration in this menu impacts the memory settings in the device tree" \
		"  autoconfig files." \
		"  If you select \'manual\', PetaLinux will auto generate memory node based on user inputs," \
		"  you will need to specify base address and memory size." \
		"  To skip generating lower or upper memory node specify 0x0 offset to the memory size." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n" \
		"menu \"Memory Settings\"" \
		"${choicestr}" \
		"${baseaddrstr}" \
		"${sizestr}" \
		"${baseaddrstr1}" \
		"${sizestr1}" \
		"${kernelbaseaddrstr}" \
		"${ubootoffsetstr}" \
		"${ddripname}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${retmemories}
}

proc plnx_gen_conf_serial {mapping kconfprefix cpuname cpuslaves} {
	set retserials {}
	set devicetype "serial"
	set serialkconfprefix "${kconfprefix}SERIAL_"
	set choicestr ""
	set baudratechoicestr ""
	set serialipname ""
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
			set choicestr [format "%s %s" "${choicestr}" \
				"${name}"]
			if { "${baseaddr_property}" != "" } {
				set serialnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${uart_baseaddr}]]
			} else {
				set serialnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			}
			lappend retserials ${serialnode}
		}
	}
	set components_list ""
	if { [string match -nocase "*aarch64*" $current_arch ] } {
		if { [regexp "psv_cortexa72*" $cpuname matched] == 1 } {
			set components_list "PLM TF-A DTG"
		} elseif { [regexp "psx_cortexa78*" $cpuname matched] == 1 } {
			set components_list "PLM TF-A DTG"
		} elseif { [regexp "psu_cortexa53*" $cpuname matched] == 1 } {
			set components_list "PMUFW FSBL TF-A DTG"
		}
	} elseif { [regexp "arm*" $current_arch matched] == 1 } {
		set components_list "FSBL DTG"
	} elseif { [regexp "microblaze*" $current_arch matched] == 1 } {
		set components_list "FSBOOT DTG"
	}
	set tmpstr $choicestr
	set choicestr ""
	foreach component $components_list {
		set conf_comp $component
                if { "${component}" == "DTG" } {
                        set conf_comp ""
                } else {
                        set conf_comp "${component}_"
                }
		set choicestr [format "%s\n%s\n\t%s\n" "${choicestr}" \
			"choice" \
			"prompt \"${component} Serial stdin/stdout\"" ]
			set choicestr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${choicestr}" \
				"help" \
				"  Select a serial as the ${component}'s stdin,stdout." \
				"  If you select \'manual\', you will need to add this variable " \
				"  YAML_SERIAL_CONSOLE_STDIN:forcevariable:pn-${component} = \"<serial_ipname>\" " \
				"  YAML_SERIAL_CONSOLE_STDOUT:forcevariable:pn-${component} = \"<serial_ipname>\" " \
				"  in petalinuxbsp.conf file to specify the stdin/stdout." ]
			if { "${component}" == "TF-A" } {
				set choicestr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n" "${choicestr}" \
					"help" \
					"  Select a serial as the ${component}'s stdin,stdout." \
					"  If you select \'manual\', you will need to add this variable " \
					"  ATF_CONSOLE:forcevariable = \"<serial_ipname>\" in petalinuxbps.conf "]
			}
		foreach str $tmpstr {
			set kstr [plnx_fix_kconf_name ${str}]
			if { "${component}" != "DTG" && "${component}" != "FSBOOT" } {
				set prop [hsi get_property IS_PL [hsi::get_cells -hier ${str}]]
				if {$prop} {
					continue
				}
			}
			set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${kconfprefix}${conf_comp}SERIAL_${kstr}_SELECT" \
                "bool \"${str}\""]
		}
		set choicestr [format "%s%s\n%s\n\t%s\n" "${choicestr}" \
			"config ${kconfprefix}${conf_comp}SERIAL_MANUAL_SELECT" \
			"bool \"manual\"" \
			"endchoice"]
	}

	if { "${tmpstr}" != "" } {
		set baudratechoicestr ""
		foreach str $tmpstr {
			set kstr [plnx_fix_kconf_name ${str}]
			set baudratechoicestr [format "%s%s\n\t%s\n\t%s\n" "${baudratechoicestr}" \
				"choice" \
				"prompt \"System stdin/stdout baudrate for $str\"" \
				"default ${serialkconfprefix}${kstr}_BAUDRATE_115200"]

			foreach b $baudrates($kstr) {
				set baudratechoicestr [format "%s%s\n\t%s\t\n" "${baudratechoicestr}" \
					"config ${serialkconfprefix}${kstr}_BAUDRATE_${b}" \
					"bool \"${b}\""]
			}
			set baudratechoicestr [format "%s%s\n" "${baudratechoicestr}" \
				"endchoice"]
		}
	}

	foreach component $components_list {
		set conf_comp $component
		if { "${component}" == "DTG" } {
			set conf_comp ""
		} else {
			set conf_comp "${component}_"
		}
		set serialipname [format "%s\n%s\n%s\n" "${serialipname}" \
			"config ${serialkconfprefix}${conf_comp}IP_NAME" \
			"string"]
		foreach str $tmpstr {
			set kstr [plnx_fix_kconf_name ${str}]
			set atf_console ""
			if { "${component}" == "TF-A" } {
				if { [string match -nocase "*psu_uart_0*" ${str} ] } {
					set atf_console "cadence"
				} elseif { [string match -nocase "*psu_uart_1*" ${str} ] } {
					set atf_console "cadence1"
				} elseif { [string match -nocase "*psv_sbsauart_0*" ${str} ] || \
					[string match -nocase "*psx_sbsauart_0*" ${str} ] } {
					set atf_console "pl011"
				} elseif { [string match -nocase "*psv_sbsauart_1*" ${str} ] || \
					[string match -nocase "*psx_sbsauart_1*" ${str} ] } {
					set atf_console "pl011_1"
				}
				if { "${atf_console}" == "" } {
					set atf_console "dcc"
				}
			set str $atf_console
			}
			set serialipname [format "%s%s\n" "${serialipname}" \
				"default ${str} if ${kconfprefix}${conf_comp}SERIAL_${kstr}_SELECT"]
		}
	}

	set kconfigstr "menu \"Serial Settings\""
	set kconfigstr [format "%s\n%s\n" "${kconfigstr}" \
		"${choicestr}"]
	set kconfigstr [format "%s\n%s\n%s\n%s\n" "${kconfigstr}" \
		"${baudratechoicestr}" \
		"${serialipname}"\
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${retserials}
}

proc plnx_gen_conf_ethernet {mapping kconfprefix cpuname cpuslaves} {
	set reteths {}
	set devicetype "ethernet"
	set ethkconfprefix "${kconfprefix}ETHERNET_"
	set choicestr ""
	set macstr ""
	set ipstr ""
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
			set kname [plnx_fix_kconf_name ${name}]
			set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
				"config ${ethkconfprefix}${kname}_SELECT" \
				"bool \"${name}\""]
			set ethernetnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend reteths ${ethernetnode}
			set macstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${macstr}" \
				"config ${ethkconfprefix}${kname}_MAC_AUTO" \
				"bool \"Randomise MAC address\"" \
				"default y if SUBSYSTEM_ARCH_MICROBLAZE" \
				"default n" \
				"depends on ${ethkconfprefix}${kname}_SELECT" \
				"help" \
				"  randomise MAC address for the primary ethernet."]
			set macstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${macstr}" \
				"config ${ethkconfprefix}${kname}_MAC_PATTERN" \
				"string \"Template for randomised MAC address\"" \
				"default \"00:0a:35:00:??:??\"" \
				"depends on ${ethkconfprefix}${kname}_SELECT && ${ethkconfprefix}${kname}_MAC_AUTO" \
				"help" \
				"  Pattern for generating random MAC addresses - question mark" \
				"  characters will be replaced by random hex digits"]
			set macstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${macstr}" \
				"config ${ethkconfprefix}${kname}_MAC" \
				"string \"Ethernet MAC address\"" \
				"default \"ff:ff:ff:ff:ff:ff\"" \
				"depends on ${ethkconfprefix}${kname}_SELECT && !${ethkconfprefix}${kname}_MAC_AUTO" \
				"help" \
				"  Default mac set to ff:ff:ff:ff:ff:ff invalid mac address to read from EEPROM" \
				"  if you want change with desired value you can change, example: 00:0a:35:00:22:01"]
			set ipstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${ipstr}" \
				"config ${ethkconfprefix}${kname}_USE_DHCP" \
				"bool \"Obtain IP address automatically\"" \
				"default y" \
				"depends on ${ethkconfprefix}${kname}_SELECT" \
				"help" \
				"  Set this option if you would like your SUBSYSTEM to use DHCP for" \
				"  obtaining an IP address."]
			set ipstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${ipstr}" \
				"config ${ethkconfprefix}${kname}_IP_ADDRESS" \
				"string \"Static IP address\"" \
				"default \"192.168.0.10\"" \
				"depends on ${ethkconfprefix}${kname}_SELECT && !${ethkconfprefix}${kname}_USE_DHCP" \
				"help" \
				"  The IP address of your main network interface when static network" \
				"  address assignment is used."]
			set ipstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${ipstr}" \
				"config ${ethkconfprefix}${kname}_IP_NETMASK" \
				"string \"Static IP netmask\"" \
				"default \"255.255.255.0\"" \
				"depends on ${ethkconfprefix}${kname}_SELECT && !${ethkconfprefix}${kname}_USE_DHCP" \
				"help" \
				"  Default netmask when static network address assignment is used." \
				"  In case of systemd please specify netmask value like CIDR notation Eg: 24 instead of 255.255.255.0" \
				"  In case of sysvinit please specify netmask value like dot-decimal notation Eg: 255.255.255.0 instead of 24 "]
			set ipstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${ipstr}" \
				"config ${ethkconfprefix}${kname}_IP_GATEWAY" \
				"string \"Static IP gateway\"" \
				"default \"192.168.0.1\"" \
				"depends on ${ethkconfprefix}${kname}_SELECT && !${ethkconfprefix}${kname}_USE_DHCP" \
				"help" \
				"  Default gateway when static network address assignment is used."]
		}
	}
	set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${ethkconfprefix}MANUAL_SELECT" \
		"bool \"manual\""]
	set kconfigstr "menu \"Ethernet Settings\""
	set kconfigstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n%s\n%s\n" "${kconfigstr}" \
		"choice" \
		"prompt \"Primary Ethernet\"" \
		"help" \
		"  Select a Ethernet used as primary Ethernet." \
		"  The primary ethernet will be used for u-boot networking if u-boot is" \
		"  selected and will be used as eth0 in Linux." \
		"  If your preferred primary ethernet is not on the list, please select" \
		"  \'manual\'." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n%s\n%s\n" "${kconfigstr}" \
		"${macstr}" \
		"${ipstr}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${reteths}
}

proc plnx_gen_conf_sd {mapping kconfprefix cpuname cpuslaves} {
	set retsds {}
	set devicetype "sd"
	set sdkconfprefix "${kconfprefix}PRIMARY_SD_"
	set choicestr ""
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
			set kname [plnx_fix_kconf_name ${name}]
			set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
				"config ${sdkconfprefix}${kname}_SELECT" \
				"bool \"${name}\""]
			set sdnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend retsds ${sdnode}
		}
	}
	set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${sdkconfprefix}MANUAL_SELECT" \
		"bool \"manual\""]
	set kconfigstr "menu \"SD/SDIO Settings\""
	set kconfigstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${kconfigstr}" \
		"choice" \
		"prompt \"Primary SD/SDIO\"" \
		"help" \
		"  Select a SD instanced used as primary SD/SDIO." \
		"  It allows you to select which SD controller is in the systems primary SD card interface." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n" "${kconfigstr}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	plnx_gen_conf_basic ${mapping} ${kconfprefix} ${cpuname} ${cpuslaves} "SD"
	return ${retsds}
}

proc plnx_gen_conf_timer {mapping kconfprefix cpuname cpuslaves} {
	set rettimers {}
	set devicetype "timer"
	set timerkconfprefix "${kconfprefix}TIMER_"
	set choicestr ""
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
			set kname [plnx_fix_kconf_name ${name}]
			set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
				"config ${timerkconfprefix}${kname}_SELECT" \
				"bool \"${name}\""]
			set timernode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend rettimers ${timernode}
		}
	}
	set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${timerkconfprefix}MANUAL_SELECT" \
		"bool \"manual\""]
	set kconfigstr "menu \"Timer Settings\""
	set kconfigstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n%s\n%s\n" "${kconfigstr}" \
		"choice" \
		"prompt \"Primary timer\"" \
		"help" \
		"  Select a timer instance used as primary timer for Linux kernel." \
		"  If your preferred timer is not on the list, please select \'manual\'." \
		"  If \'manual\' is selected, you will be responsible to enable property" \
		"  kernel driver for your timer." \
		"  Please note that MicroBlaze system must have a timer." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n" "${kconfigstr}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${rettimers}
}

proc plnx_gen_conf_rtc {mapping kconfprefix cpuname cpuslaves} {
	set retrtcs {}
	set devicetype "rtc"
	set rtckconfprefix "${kconfprefix}RTC_"
	set choicestr ""
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
			set kname [plnx_fix_kconf_name ${name}]
			set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
				"config ${rtckconfprefix}${kname}_SELECT" \
				"bool \"${name}\""]
			set rtcnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend retrtcs ${rtcnode}
		}
	}
	set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${rtckconfprefix}MANUAL_SELECT" \
		"bool \"manual\""]
	set kconfigstr "menu \"RTC Settings\""
	set kconfigstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n%s\n" "${kconfigstr}" \
		"choice" \
		"prompt \"Primary RTC\"" \
		"help" \
		"  Select a RTC instance used as primary timer for Linux kernel." \
		"  If your preferred RTC is not on the list, please select \'manual\'." \
		"  If \'manual\' is selected, you will be responsible to enable property" \
		"  kernel driver for your RTC." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n" "${kconfigstr}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${retrtcs}
}


proc plnx_gen_conf_sata {mapping kconfprefix cpuname cpuslaves} {
	set retsatas [plnx_gen_conf_basic ${mapping} ${kconfprefix} ${cpuname} ${cpuslaves} "SATA"]
	return ${retsatas}
}

proc plnx_gen_conf_usb {mapping kconfprefix cpuname cpuslaves} {
	set retusbs [plnx_gen_conf_basic ${mapping} ${kconfprefix} ${cpuname} ${cpuslaves} "USB"]
	return ${retusbs}
}
proc plnx_gen_conf_i2c {mapping kconfprefix cpuname cpuslaves} {
	set reti2cs [plnx_gen_conf_basic ${mapping} ${kconfprefix} ${cpuname} ${cpuslaves} "I2C"]
	return ${reti2cs}
}

proc plnx_gen_conf_dp {mapping kconfprefix cpuname cpuslaves} {
	set retdps [plnx_gen_conf_basic ${mapping} ${kconfprefix} ${cpuname} ${cpuslaves} "DP"]
	return ${retdps}
}

proc plnx_gen_conf_basic {mapping kconfprefix cpuname cpuslaves devicetype} {
	set retdev {}
	set devkconfprefix "${kconfprefix}${devicetype}_"
	set devicetype [string tolower ${devicetype}]
	set choicestr ""
	set kconfstr ""
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
			set kname [plnx_fix_kconf_name ${name}]
			set choicestr [format "%s%s\n\t%s\n\t%s\n" "${choicestr}" \
				"config ${devkconfprefix}${kname}_SELECT" \
				"bool" \
				"default y"]
			set devnode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend retdev ${devnode}
		}
	}
	set kconfigstr [format "%s\n" "${choicestr}" ]
	plnx_output_kconfig "${kconfigstr}"
	return ${retdev}
}

proc plnx_gen_conf_reset_gpio {mapping kconfprefix cpuname cpuslaves} {
	set retrstgpios {}
	set devicetype "reset_gpio"
	set rstgpiokconfprefix "${kconfprefix}RESET_GPIO_"
	set choicestr ""
	set on2instancestr ""
	set channelstr ""
	foreach m ${mapping} {
		#puts "m : $m"
		set ipname [lindex ${m} 0]
		set devinfo [get_ip_device_info reset_gpio ${m}]
		set gpioinfo [get_ip_property_info gpio_property ${devinfo}]
		set direction_property [lindex [get_ip_property_info is_all_input ${gpioinfo}] 0]
		set isdural_property [lindex [get_ip_property_info is_dual ${devinfo}] 0]
		set width_property [lindex [get_ip_property_info gpio_width ${gpioinfo}] 0]
		set gpioidreplacement [lindex [get_ip_property_info instanceip_replacement_str ${devinfo}] 0]
		set hds [hsi get_cells -hier -filter IP_NAME==${ipname}]

		foreach hd ${hds} {
			set name [hsi get_property NAME ${hd}]
			if {[lsearch ${cpuslaves} ${name}] < 0} {
				continue
			}
			set kname [plnx_fix_kconf_name ${name}]
			if {"${ipname}" == "axi_gpio"} {
				set isdual [hsi get_property ${isdural_property} ${hd}]
				set replacementmap1 [list "${gpioidreplacement}" ""]
				set replacementmap2 [list "${gpioidreplacement}" "2"]
				set dir1stproperty [string map ${replacementmap1} "${direction_property}"]
				set dir2ndproperty [string map ${replacementmap2} "${direction_property}"]
				if {[hsi get_property ${dir1stproperty} ${hd}] == 1} {
					set is1stouput 0
				} else {
					set is1stouput 1
				}
				set is2ndoutput 0
				if {${isdual} == 1 && [hsi get_property ${dir2ndproperty} ${hd}] == 0} {
					set is2ndoutput 1
				}
				if {${is1stouput} == 1 || ${is2ndoutput} == 1} {
					if { [is_connect_to_end_from_source ${hd} ${cpuname} "rst" "*gpio*"] < 0 } {
						continue
					}
					set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
						"config ${rstgpiokconfprefix}${kname}_SELECT" \
						"bool \"${name}\""]
					if {${is1stouput} == 0} {
						set choicestr [format "%s\t%s\n" "${choicestr}" \
						"select ${rstgpiokconfprefix}${kname}_INSTANCE2_SELECT"]
					}
					if {${is1stouput} == 1} {
						set channelstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${channelstr}" \
							"choice" \
							"prompt \"Channel\"" \
							"depends on ${rstgpiokconfprefix}${kname}_SELECT && !${rstgpiokconfprefix}${kname}_INSTANCE2_SELECT" \
							"help" \
							"  Select a channel on the GPIO instance for the Reset GPIO."]
						set channelnum [hsi get_property [string map ${replacementmap1} "${width_property}"] ${hd}]
						for {set i 0} {$i < ${channelnum}} {incr i} {
							set channelstr [format "%s%s\n\t%s\n" "${channelstr}" \
								"config ${rstgpiokconfprefix}${kname}_CHANNEL${i}_SELECT" \
								"bool \"${i}\""]
						}
						set channelstr [format "%s%s\n" "${channelstr}" "endchoice"]
					}
					if {${is2ndoutput} == 1} {
						set channelstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${channelstr}" \
							"choice" \
							"prompt \"Channel\"" \
							"depends on ${rstgpiokconfprefix}${kname}_SELECT && ${rstgpiokconfprefix}${kname}_INSTANCE2_SELECT" \
							"help" \
							"  Select a channel on the GPIO instance for the Reset GPIO."]
						set channelnum [hsi get_property [string map ${replacementmap2} "${width_property}"] ${hd}]
						for {set i 0} {$i < ${channelnum}} {incr i} {
							set channelstr [format "%s%s\n\t%s\n" "${channelstr}" \
								"config ${rstgpiokconfprefix}${kname}_CHANNEL${i}_SELECT" \
								"bool \"${i}\""]
						}
						set channelstr [format "%s%s\n" "${channelstr}" "endchoice"]
					}
					if {${is2ndoutput} == 1} {
						set on2instancestr [format "%s\n%s\n\t%s\n\t%s\n" "${on2instancestr}" \
							"config ${rstgpiokconfprefix}${kname}_INSTANCE2_SELECT" \
							"bool \"Reset GPIO is on 2nd GPIO\"" \
							"default n"]
					}
				}
			} else {
				error "Invalid Reset GPIO."
			}

			set gpionode [list "${name}" [list device_type ${devicetype}] [list ip_name ${ipname}]]
			lappend retrstgpios ${gpionode}
		}
	}
	set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${rstgpiokconfprefix}NONE" \
		"bool \"none\""]
	set kconfigstr "menu \"Reset GPIO Settings\""
	set kconfigstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n%s\n%s\n" "${kconfigstr}" \
		"choice" \
		"prompt \"Reset GPIO\"" \
		"help" \
		"  Select a GPIO instance used as reset GPIO." \
		"  If you don't have reset GPIO in your system, please select \'none\'." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n%s\n%s\n" "${kconfigstr}" \
		"${on2instancestr}" \
		"${channelstr}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${retrstgpios}
}

proc plnx_get_conf_flash_partition {prefix flashname bankid advdepends flash_prefix} {
	set partitionstr ""
	set choicestr ""
	set flashipname ""
	set kname [plnx_fix_kconf_name ${flashname}]
	if {"${bankid}" == ""} {
		set bankprompt ""
		set bankkconf "BANKLESS"
	} else {
		set bankprompt " bank${bankid}"
		set bankkconf "BANK${bankid}"
	}
	set choicestr [format "%s\n\t%s\n" \
		"config ${prefix}${kname}_${bankkconf}_SELECT" \
		"bool \"${flashname}${bankprompt}\""]
	set defaultlist {}
	global current_arch
	if {"${current_arch}" == "aarch64"} {
		if {[llength ${flash_prefix}]} {
			lappend defaultlist [list ${flash_prefix}-boot 0x100000]
			lappend defaultlist [list ${flash_prefix}-kernel 0x1600000]
			lappend defaultlist [list ${flash_prefix}-bootenv 0x40000]
			if {[string match -nocase "*nand*" $flashname]} {
				puts "flashname:$flashname"
				lappend defaultlist [list ${flash_prefix}-device-tree 0x400000]
				puts "flash_prefix:$flash_prefix"
				lappend defaultlist [list ${flash_prefix}-rootfs 0x3C00000]
			}
		} else {
			lappend defaultlist [list boot 0x100000]
			lappend defaultlist [list kernel 0x1600000]
			lappend defaultlist [list bootenv 0x40000]
			if {[string match -nocase "*nand*" $flashname]} {
				lappend defaultlist [list device-tree 0x400000]
				lappend defaultlist [list rootfs 0x3C00000]
			}
		}
	} elseif {"${current_arch}" == "arm"} {
		if {[llength ${flash_prefix}]} {
			lappend defaultlist [list ${flash_prefix}-boot 0x500000 ]
			lappend defaultlist [list ${flash_prefix}-kernel 0xA80000]
			lappend defaultlist [list ${flash_prefix}-bootenv 0x20000]
			if {[string match -nocase "*nand*" $flashname]} {
				puts "flashname:$flashname"
				lappend defaultlist [list ${flash_prefix}-device-tree 0x400000]
				puts "flash_prefix:$flash_prefix"
				lappend defaultlist [list ${flash_prefix}-rootfs 0x3C00000]
			}
		} else {
			lappend defaultlist [list boot 0x500000]
			lappend defaultlist [list kernel 0xA80000]
			lappend defaultlist [list bootenv 0x20000]
			if {[string match -nocase "*nand*" $flashname]} {
				lappend defaultlist [list device-tree 0x400000]
				lappend defaultlist [list rootfs 0x3C00000]
			}
		}
		#puts "flashname: ${flashname}"
	} elseif {"${current_arch}" == "microblaze"} {
		if {[llength ${flash_prefix}]} {
			lappend defaultlist [list ${flash_prefix}-fpga 0xB00000]
			lappend defaultlist [list ${flash_prefix}-boot 0x40000]
			lappend defaultlist [list ${flash_prefix}-bootenv 0x20000]
			lappend defaultlist [list ${flash_prefix}-kernel 0xC00000]
		} else {
			lappend defaultlist [list fpga 0xB00000]
			lappend defaultlist [list boot 0x40000]
			lappend defaultlist [list bootenv 0x20000]
			lappend defaultlist [list kernel 0xC00000]
			}
		}
	for {set i 0} {${i} < 20} {incr i} {
		set defaultmap [lindex ${defaultlist} ${i}]
		if {[llength ${defaultmap}] > 0} {
			set defaultname [lindex ${defaultmap} 0]
			set defaultsize [lindex ${defaultmap} 1]
		} else {
			set defaultname ""
			set defaultsize 0x0
		}
		if {${i} == 0} {
			set namedepends "${prefix}${kname}_${bankkconf}_SELECT"
		} else {
			set namedepends "${prefix}${kname}_${bankkconf}_PART[expr ${i} - 1]_NAME != \"\""
		}
		set partitionstr [format "%s\n%s\n\t%s\n" "${partitionstr}" \
			"comment \"partition ${i}\"" \
			"depends on ${namedepends}"]

		set partitionstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n" "${partitionstr}" \
			"config ${prefix}${kname}_${bankkconf}_PART${i}_NAME" \
			"string \"name\"" \
			"default \"${defaultname}\"" \
			"depends on ${namedepends}"]
		set partitionstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n" "${partitionstr}" \
			"config ${prefix}${kname}_${bankkconf}_PART${i}_SIZE" \
			"hex \"size\"" \
			"default ${defaultsize}" \
			"depends on ${prefix}${kname}_${bankkconf}_PART${i}_NAME != \"\""]
		set partitionstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n" "${partitionstr}" \
			"config ${prefix}${kname}_${bankkconf}_PART${i}_FLAGS" \
			"string \"flash partition flags\"" \
			"default \"\"" \
			"depends on ${prefix}${kname}_${bankkconf}_PART${i}_NAME != \"\" && ${advdepends}" \
			"help" \
			"  Pass the flash partition flags to DTS. Use comma separatioon for" \
			"  multiple flags, e.g. abc,def,...,xyz" \
			"  Currently, the supported string is RO (\"read-only\" string) flag" \
			"  which marks the partition read-only"]
		set flashipname [format "%s\n%s\n%s\n%s\n%s\n" "${flashipname}"\
			"config ${prefix}IP_NAME"\
			"string"\
			"default ${flashname}"\
			"depends on ${namedepends}"]
	}
	return [list "${choicestr}" "${partitionstr}" "${flashipname}"]
}

proc plnx_gen_conf_flash {mapping kconfprefix cpuname cpuslaves} {
	set retflashs {}
	set devicetype "flash"
	set flashkconfprefix "${kconfprefix}FLASH_"
	set choicestr ""
	set partitionsstr ""
	set spicsstr ""
	set flashipname ""
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
					set banktype [hsi get_property ${typestrmap} ${hd}]
					if {"${banktype}" == "0" || "${banktype}" == "1" || "${banktype}" == "4"} {
						# It is memory
						continue
					}
					set bankbaseaddr [hsi get_property ${basestrmap} ${hd}]
					set bankhighaddr [hsi get_property ${highstrmap} ${hd}]
					set strlist [plnx_get_conf_flash_partition "${flashkconfprefix}" "${name}" "${i}" "${flashkconfprefix}_ADVANCED_AUTOCONFIG" "${flash_prefix}"]
					set choicestr [format "%s%s" "${choicestr}" [lindex ${strlist} 0]]
					set partitionsstr [format "%s\n%s\n" "${partitionsstr}" [lindex ${strlist} 1]]
					set flashipname [format "%s\n%s\n" "${flashipname}" [lindex ${strlist} 2]]
					set flashnode [list "${name}_bank${i}" [list device_type ${devicetype}] [list ip_name ${ipname}] [list baseaddr ${bankbaseaddr}] [list highaddr ${bankhighaddr}]]
					lappend retflashs ${flashnode}
				}
			} elseif {"${flash_type}" == "spi"} {
				set cs_bits_property [lindex [get_ip_property_info number_cs ${devinfo}] 0]
				if {"${cs_bits_property}" != ""} {
					set cs_bits [hsi get_property ${cs_bits_property} ${hd}]
					if {${cs_bits} > 0} {
						set spicsstr [format "%s\n%s\n\t%s\n\t%s\n" "${spicsstr}" \
							"choice" \
							"prompt \"Chip select of the SPI Flash\"" \
							"depends on ${flashkconfprefix}${kname}_BANKLESS_SELECT"]
						for {set i 0} {$i < ${cs_bits}} {incr i} {
							set spicsstr [format "%s\n%s\n\t%s\n" "${spicsstr}" \
								"config ${flashkconfprefix}${kname}_CS${i}" \
								"bool \"${i}\""]
						}
						set spicsstr [format "%s%s\n" "${spicsstr}" \
							"endchoice"]
					}
				} else {
					set cs_bits 0
				}
				set strlist [plnx_get_conf_flash_partition "${flashkconfprefix}" "${name}" "" "${flashkconfprefix}_ADVANCED_AUTOCONFIG" "${flash_prefix}"]
				set choicestr [format "%s%s" "${choicestr}" [lindex ${strlist} 0]]
				set partitionsstr [format "%s\n%s\n" "${partitionsstr}" [lindex ${strlist} 1]]
				set flashipname [format "%s\n%s\n" "${flashipname}" [lindex ${strlist} 2]]
				set flashnode [list "${name}_bankless" [list device_type ${devicetype}] [list ip_name ${ipname}]]
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
				set strlist [plnx_get_conf_flash_partition "${flashkconfprefix}" "${name}" "" "${flashkconfprefix}_ADVANCED_AUTOCONFIG" "${flash_prefix}"]
				set choicestr [format "%s%s" "${choicestr}" [lindex ${strlist} 0]]
				set partitionsstr [format "%s\n%s\n" "${partitionsstr}" [lindex ${strlist} 1]]
				set flashipname [format "%s\n%s\n" "${flashipname}" [lindex ${strlist} 2]]
				set flashnode [list "${name}_bankless" [list device_type ${devicetype}] [list ip_name ${ipname}]]
				lappend retflashs ${flashnode}
			} else {
				set strlist [plnx_get_conf_flash_partition "${flashkconfprefix}" "${name}" "" "${flashkconfprefix}_ADVANCED_AUTOCONFIG" "${flash_prefix}"]
				set choicestr [format "%s%s" "${choicestr}" [lindex ${strlist} 0]]
				set partitionsstr [format "%s\n%s\n" "${partitionsstr}" [lindex ${strlist} 1]]
				set flashipname [format "%s\n%s\n" "${flashipname}" [lindex ${strlist} 2]]
				set flashnode [list "${name}_bankless" [list device_type ${devicetype}] [list ip_name ${ipname}]]
				lappend retflashs ${flashnode}
			}
		}
	}
	set choicestr [format "%s%s\n\t%s\n" "${choicestr}" \
		"config ${flashkconfprefix}MANUAL_SELECT" \
		"bool \"manual\""]
	set partitionsstr [format "%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n%s\n" \
		"config ${flashkconfprefix}_ADVANCED_AUTOCONFIG" \
		"bool \"Advanced Flash Auto Configuration\"" \
		"default n" \
		"depends on !${flashkconfprefix}MANUAL_SELECT" \
		"help" \
		"  Select this option to enabled " \
		"${partitionsstr}"]
	set kconfigstr "menu \"Flash Settings\""
	set kconfigstr [format "%s\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n%s\n%s\n" "${kconfigstr}" \
		"choice" \
		"prompt \"Primary Flash\"" \
		"help" \
		"  Select a Flash instance used as Primary Flash." \
		"  PetaLinux auto config will apply the flash partition table settings" \
		"  to the primary flash." \
		"  If you preferred flash is not on the list or you don't want PetaLinux" \
		"  to manage your flash partition, please select manual." \
		"${choicestr}" \
		"endchoice"]
	set kconfigstr [format "%s\n%s\n" "${kconfigstr}" "${spicsstr}"]
	set kconfigstr [format "%s\n%s\n%s\n%s\n" "${kconfigstr}" \
		"${partitionsstr}" \
		"${flashipname}" \
		"endmenu"]
	plnx_output_kconfig "${kconfigstr}"
	return ${retflashs}
}

proc plnx_gen_conf_images_location {kconfigprefix sds flashes} {
	set imagestr ""
	set imagesautoconfig "${kconfigprefix}IMAGES_ADVANCED_AUTOCONFIG"
	set imageconfigprefix "${kconfigprefix}IMAGES_ADVANCED_AUTOCONFIG_"
	set imagesmap {}
	# name arch flash/sd_only flash_part_name image_name prompt
	#lappend imagesmap [list fpga {} {} fpga "microblaze:system.bin" "fpga bitstream BIN file"]
	lappend imagesmap [list boot {} {} boot "microblaze:u-boot-s.bin arm:BOOT.BIN aarch64:BOOT.BIN" "boot image"]
	#lappend imagesmap [list fpga {} {} fpga "arm:system.bin" "fpga bitstream BIN file"]
	lappend imagesmap [list bootenv {} {} bootenv "" "u-boot env partition"]
	lappend imagesmap [list kernel {} {flash sd ethernet} kernel image.ub "kernel image"]
	lappend imagesmap [list jffs2 {} {flash} jffs2 "rootfs.jffs2" "jffs2 rootfs image"]
	lappend imagesmap [list dtb {} {flash sd ethernet} dtb system.dtb "dtb image"]
	global current_arch
	foreach i ${imagesmap} {
		set name [lindex ${i} 0]
		set kname [plnx_fix_kconf_name ${name}]
		set valid_arch [lindex ${i} 1]
		set valid_media [lindex ${i} 2]
		set flash_part_name [lindex ${i} 3]
		set commentprompt [lindex ${i} 5]

		if {[llength ${valid_arch}] > 0} {
			set isvalid 0
			foreach a ${valid_arch} {
				if {"${a}" == "${current_arch}"} {
					set isvalid 1
					break;
				}
			}
			if {${isvalid} == 0} {
				continue
			}
		}

		if {[llength ${valid_media}] == 0 } {
			set valid_media [list flash sd]
		}
		set nomedia {}
		if {[llength ${sds}] <= 0} {
			lappend nomedia "sd"
		}
		if {[llength ${flashes}] <= 0} {
			lappend nomedia "flash"
		}
		foreach m ${nomedia} {
			set mindex [lsearch ${valid_media} ${m}]
			set valid_media [lreplace ${valid_media} ${mindex} ${mindex}]
		}
		#if {[llength ${valid_media}] <= 0} {
		#	continue
		#}

		set imagestr [format "%s\n\t%s\n" "${imagestr}" \
			"menu \"${commentprompt} settings\""]
		set imagestr [format "%s\n\t%s\n\t\t%s\n" "${imagestr}" \
			"choice" \
			"prompt \"image storage media\""]
		if { "${name}" == "dtb" } {
			set imagestr [format "%s\n\t\t%s\n\t\t\t%s\n\t\t\t%s\n\t\t\t%s\n" "${imagestr}" \
			"config ${imageconfigprefix}${kname}_MEDIA_BOOTIMAGE_SELECT" \
			"bool \"from boot image\"" \
			"help" \
			"  Do not use extern DTB. DTB is inside the boot image."]
		}

		foreach s ${valid_media} {
			set kmedia [plnx_fix_kconf_name ${s}]
			set tmpprompstr "primary ${s}"
			if { "${s}" == "ethernet" } {
				set tmpprompstr "ethernet"
			}
			set imagestr [format "%s\n\t\t%s\n\t\t\t%s\n\t\t\t%s\n" "${imagestr}" \
			"config ${imageconfigprefix}${kname}_MEDIA_${kmedia}_SELECT" \
			"bool \"${tmpprompstr}\"" \
			"depends on !${kconfigprefix}${kmedia}_MANUAL_SELECT"]
			if { "${kmedia}" == "ETHERNET" } {
				set imagestr [format "%s\t\t\t%s\n\t\t\t%s\n\t\t\t%s\n\t\t\t%s\n" "${imagestr}" \
				"help" \
				"  If \"ethernet\" is selected, PetaLinux autoconfiged u-boot will" \
				"  get the ${name} image from tftp server when it boots kernel if" \
				"  primary ethernet has been selected." \
				]
			}
		}
		set imagestr [format "%s\n\t\t%s\n\t\t\t%s\n" "${imagestr}" \
			"config ${imageconfigprefix}${kname}_MEDIA_MANUAL_SELECT" \
			"bool \"manual\""]

		set imagestr [format "%s\t\t\t%s\n\t\t\t%s\n\t\t\t%s\n\t\t\t%s\n" "${imagestr}" \
		"help" \
		"  If \"manual\" is selected, petalinux autconfiged u-boot will" \
		"  not auto generate command to get/update the image. You will be" \
		"  responsible to define u-boot commands to access the image." \
		]
		set imagestr [format "%s\t%s\n" "${imagestr}" \
			"endchoice"]
		set imagestr [format "%s\n\t%s\n\t\t%s\n\t\t%s\n\t\t%s\n" "${imagestr}" \
			"config ${imageconfigprefix}${kname}_PART_NAME" \
			"string \"flash partition name\"" \
			"default \"${flash_part_name}\"" \
			"depends on ${imageconfigprefix}${kname}_MEDIA_FLASH_SELECT"]
		set default_image_uname_str [lindex ${i} 4]
		if {"${default_image_uname_str}" != ""} {
			set default_nameslist [split "${default_image_uname_str}" " "]
			if {[llength ${default_nameslist}] > 1} {
				foreach n ${default_nameslist} {
					set namepair [split "${n}" ":"]
					set arch_img_name [lindex ${namepair} 0]
					if {"${arch_img_name}" == "${current_arch}"} {
						set default_image_uname [lindex ${namepair} 1]
						break
					}
				}
			} else {
				set default_image_uname "${default_image_uname_str}"
			}
			set imagestr [format "%s\n\t%s\n\t\t%s\n\t\t%s\n\t\t%s\n" "${imagestr}"\
				"config ${imageconfigprefix}${kname}_IMAGE_NAME" \
				"string \"image name\"" \
				"default \"${default_image_uname}\""\
				"depends on !${imageconfigprefix}${kname}_MEDIA_MANUAL_SELECT"]
		}

		set imagestr [format "%s\n\t%s\n" "${imagestr}" "endmenu"]
	}
	set images_config_depends {}
	if {[llength ${sds}] > 0} {
		lappend images_config_depends "!${kconfigprefix}SD_MANUAL_SELECT"
	}
	lappend images_config_depends "!${kconfigprefix}FLASH_MANUAL_SELECT"
	lappend images_config_depends "!${kconfigprefix}ETHERNET_MANUAL_SELECT"
	set images_config_depends_str [join ${images_config_depends} " || "]
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
			#puts "value tmpline=${tmpline} indent_level=${indent_level} previous_indent_level=${previous_indent_level}"
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
	#puts "ipinfodata ${ipinfodata}"
	set ip_list {}
	eval set ip_list "\{${ipinfodata}\}"
	#set iplistlen [llength ${ip_list}]
	#puts "ip_list=${ip_list} length=${iplistlen}"
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
	set devicetypes {processor memory serial ethernet flash sd rtc sata i2c usb dp timer reset_gpio}
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

proc plnx_gen_hwsysconf {args} {
	set args [split [lindex ${args} 0]]
	set hdf [lindex ${args} 0]
	set syshwconfname [lindex ${args} 1]
	if { "${hdf}" == "" } {
		error "No Hardware description file is specified."
	}
	if { "${syshwconfname}" == "" } {
		error "No output kconfig file is specified."
	}
	if { [catch {openhw "${hdf}"} res] } {
		error "Failed to open hardware design from ${hdf}"
	}
	if { [catch {open "${syshwconfname}" w} kconffile] } {
		error "Failed to open output Kconfig file ${syshwconfname}"
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

	global plnx_kconfig
	set plnx_kconfig ${kconffile}
	set hwmenustr "menuconfig SUBSYSTEM_HARDWARE_AUTO\n"
	set hwmenustr [format "%s\t%s\n" "${hwmenustr}" "bool \"Subsystem AUTO Hardware Settings\""]
	set hwmenustr [format "%s\t%s\n" "${hwmenustr}" "default y"]
	set hwmenustr [format "%s\t%s\n" "${hwmenustr}" "help"]
	set hwmenustr [format "%s\t%s\n" "${hwmenustr}" "  This menu is to configure system hardware."]
	set hwmenustr [format "%s\n%s\n" "${hwmenustr}" "if SUBSYSTEM_HARDWARE_AUTO"]
	plnx_output_kconfig "${hwmenustr}"

	set hwkconfprefix "SUBSYSTEM_"

	set mapping [generate_mapping_list]

	set cpumapping [get_devices_nodes [lindex ${mapping} 0]]

	#puts "mapping : $mapping"
	#puts "cpumapping : $cpumapping"
	set retcpus [plnx_gen_conf_processor ${cpumapping} "${hwkconfprefix}"]
	global current_arch
	set cpus_nodes {processor}
	#puts "retcpus : $retcpus"
	foreach c [lreplace ${retcpus} 0 0] {
		set cpuname [lindex ${c} 0]
		set cpuarch [lindex [get_ip_property_info "arch" ${c}] 0]
		set cpukname ${cpuname}
		set current_arch ${cpuarch}
		set cpuipname [lindex [get_ip_property_info "ip_name" ${c}] 0]
		set cpuslaves [get_ip_property_info "slaves_strings" ${c}]
		#puts "cpuname : $cpuname cpuarch : $cpuarch cpukname : $cpukname current_arch : $current_arch cpuipname : $cpuipname cpuslaves : $cpuslaves"
		plnx_output_kconfig "if ${hwkconfprefix}PROCESSOR_${cpukname}_SELECT"
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
			set pkconfprefix "${hwkconfprefix}"
			if { "[info procs ${pproc}]" eq "${pproc}"} {
				set ret${class} [${pproc} ${elements} "${pkconfprefix}" "${cpuname}" "${cpuslaves}"]
				foreach r [set ret${class}] {
					lappend retslaves ${r}
				}
			}
		}
		plnx_gen_conf_images_location ${hwkconfprefix} ${retsd} ${retflash}
		plnx_output_kconfig "endif"
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
	plnx_output_kconfig "endif"
	plnx_output_data ${cpus_nodes}
	close ${kconffile}
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
