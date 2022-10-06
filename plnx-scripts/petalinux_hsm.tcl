proc get_ipinfo {ipinfofile} {

	if { [catch {open "${ipinfofile}" r} ipinfof] } {
		error "Failed to open IP information file ${ipinfofile}."
	}

	set ipinfodata ""
	set previous_indent_level -1
	set key {}
	set ipdict [dict create]
	while {1} {
		if { [eof ${ipinfof}] > 0} {
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
			set tmpkey [lindex [split ${trimline} ":"] 0]
			set tmpval [regsub "${tmpkey}:" "${trimline}" ""]
			set tmpkey [string trim "${tmpkey}"]
			set tmpval [string trim "${tmpval}"]
			set indent_level [regexp -all "(    )" ${line}]
			if { [llength ${key}] > ${indent_level}} {
				set key [lreplace ${key} ${indent_level} end]
			}
			lappend key ${tmpkey}
			if { "${tmpval}" != ""} {
				dict set ipdict [join ${key}] "${tmpval}"
			}
		}
	}
	return ${ipdict}
}

proc get_primary_ip_kconfig {sysconfig ipclass} {
	# get baudrate from sysconfig
	if { [catch {open "${sysconfig}" r} sysconfhd] } {
		error "Failed to open system config file \"${sysconfig}\"."
	}
	if {${ipclass} == ""} {
		return
	}
	set upipclass [string toupper "${ipclass}"]
	set data [read ${sysconfhd}]
	close "${sysconfhd}"
	set lines [split "${data}" "\n"]
	set idx [lsearch -regexp ${lines} "^CONFIG_SUBSYSTEM_${upipclass}_(.*)_SELECT=y"]
	if {${idx} < 0} {
		return
	}

	set selectip [lindex ${lines} ${idx}]
	set ipstrmap [list "CONFIG_SUBSYSTEM_${upipclass}_" "" "_SELECT=y" ""]
	set selectip [string map ${ipstrmap} "${selectip}"]
	if {"${selectip}" == "MANUAL"} {
		return
	} else {
		return "${selectip}"
	}
}

proc get_partitions {sysconfig flash_kname} {
	if { "${flash_kname}" == ""} {
		return
	}
	# get partitions info from sysconfig
	if { [catch {open "${sysconfig}" r} sysconfhd] } {
		error "Failed to open system config file \"${sysconfig}\"."
	}
	set data [read ${sysconfhd}]
	close "${sysconfhd}"
	set lines [split "${data}" "\n"]
	# setup part offset list
	set part_sizes [lsearch -all -inline -regexp ${lines} "^CONFIG_SUBSYSTEM_FLASH_${flash_kname}_PART(.*)_SIZE="]
	if {[llength ${part_sizes}] == 0} {
		return
	}
	set partlength [llength ${part_sizes}]
	set lpsizes {}
	for {set i 0} {$i < ${partlength}} {incr i} {
		lappend lpsizes 0
	}
	set poffsets {0}
	set psize {}
	for {set i 0} {$i < ${partlength}} {incr i} {
		set tmppsize [lsearch -inline -regexp ${lines} "^CONFIG_SUBSYSTEM_FLASH_${flash_kname}_PART${i}_SIZE="]
		if {[llength ${tmppsize}] == 0} {
			error "Failed to get the parition size of partition $i."
		}
		set tmppsize [regsub -all {.*=} "${tmppsize}" {}]
		set next_offset [format "0x%x" [expr [lindex ${poffsets} ${i}] + ${tmppsize}]]
		lappend poffsets ${next_offset}
		lappend psize ${tmppsize}
	}

	# get part name
	set ret_part_offsets {}
	foreach p {fpga boot kernel jffs2 dtb} {
		set upperp [string toupper "${p}"]
		set idx [lsearch -regexp ${lines} "^CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_${flash_kname}_PART_NAME="]
		set partname "${p}"
		if {${idx} >= 0} {
			set partname [lindex ${lines} ${idx}]
			set partname_rm_map [list "\"" "" "CONFIG_SUBSYSTEM_IMAGES_ADVANCED_AUTOCONFIG_${flash_kname}_PART_NAME=" ""]
			set partname [string map ${partname_rm_map} "${partname}"]
		}
		set part_id_str [lsearch -inline -regexp ${lines} "^CONFIG_SUBSYSTEM_FLASH_${flash_kname}_PART(.*)_NAME=\"(.*)${partname}\""]
		if { [llength ${part_id_str}] == 0} {
			continue
		}
		set act_part_name [lindex [split ${part_id_str} "\""] 1]
		set part_id_map [list "CONFIG_SUBSYSTEM_FLASH_${flash_kname}_PART" "" "_NAME=\"${act_part_name}\"" ""]
		set part_id [string map ${part_id_map} "${part_id_str}"]
		lappend ret_part_offsets "${partname}=[lindex ${poffsets} ${part_id}] [lindex ${psize} ${part_id}]"
	}
	return ${ret_part_offsets}
}

proc get_flash_width {sysconfig ipinfof hdf} {
	set retlist {}

	set flash_kname [get_primary_ip_kconfig "${sysconfig}" flash]
	set flash_name [string tolower [regsub -all {_BANK.*} "${flash_kname}" {}]]
	set flash_bank [regsub -all {.*_BANK} "${flash_kname}" {}]
	if { "${flash_kname}" == "" || "${flash_kname}" == "MANUAL"} {
		return
	}

	if { [catch {openhw "${hdf}"} msg] } {
		error "Failed to open the hardware description file \"${hdf}\"."
	}

	set ipdict [get_ipinfo "${ipinfof}"]
	set ipname [hsi get_property IP_NAME [hsi get_cell -hier "${flash_name}"]]
	if { "${ipname}" == ""} {
		error "Flash IP ${flash_name} is not in the hardware."
	}
	set flash_type [dict get ${ipdict} "${ipname} device_type flash flash_type"]
	if { "${flash_type}" != ""} {
		lappend retlist "flash_type=${flash_type}"
	}

	if { [catch {dict get ${ipdict} "${ipname} device_type flash bank_property bank_width"} flash_width_property] } {
		set flash_width_property ""
	}
	if { "${flash_width_property}" != "" } {
		set flash_width [hsi get_property [regsub -all {<PLNXNUM>} "${flash_width_property}" "${flash_bank}"] [hsi get_cell -hier "${flash_name}"]]
		lappend retlist "flash_width=${flash_width}"
	}
	if { [catch {dict get ${ipdict} "${ipname} device_type flash bank_property bank_baseaddr"} flash_base_property] } {
		set flash_base_property ""
	}

	if { [catch {dict get ${ipdict} "${ipname} device_type flash bank_property bank_highaddr"} flash_high_property] } {
		set flash_high_property ""
	}
	if { "${flash_base_property}" != "" } {
		set flash_base [hsi get_property [regsub -all {<PLNXNUM>} "${flash_base_property}" "${flash_bank}"] [hsi get_cell -hier "${flash_name}"]]
		set flash_high [hsi get_property [regsub -all {<PLNXNUM>} "${flash_high_property}" "${flash_bank}"] [hsi get_cell -hier "${flash_name}"]]
		set flash_size [format "0x%x" [expr ${flash_high} - ${flash_base} + 1]]
		lappend retlist "flash_size=${flash_size}"
	}
	hsi close_hw_design [hsi current_hw_design]
	return ${retlist}
}

proc get_flash_width_parts {args} {
	set args [split [lindex ${args} 0]]
	set sysconfig [lindex ${args} 0]
	set ipinfof [lindex ${args} 1]
	set hdf [lindex ${args} 2]
	set outputf [lindex ${args} 3]

	set flash_kname [get_primary_ip_kconfig "${sysconfig}" flash]
	set flash_parts [get_partitions "${sysconfig}" "${flash_kname}"]
	set flash_widths [get_flash_width "${sysconfig}" "${ipinfof}" "${hdf}"]

	if { [catch {open "${outputf}" w} outputd] } {
		error "Failed to open output file \"${outputf}\" for capture Flash information."
	}
	foreach i ${flash_widths} {
		puts ${outputd} "${i}"
	}

	foreach i ${flash_parts} {
		puts ${outputd} "${i}"
	}
	close ${outputd}
}

proc get_search_path {proj} {
	set proj [file join [pwd] "${proj}"]
	if { [catch {open "${proj}/config.project" r} pconfd] } {
		error "Failed to get project search path, failed to open config file \"${proj}/config.project\"."
	}
	set searchpath_list {}
	while {[gets ${pconfd} line] >= 0} {
		if {[regexp -- "^CONFIG_PROJECT_ADDITIONAL_COMPONENTS_SEARCH_PATH=" "${line}"] > 0} {
			set replace_map [list "CONFIG_PROJECT_ADDITIONAL_COMPONENTS_SEARCH_PATH=" "" "\"" ""]
			set proj_searchpath [string map ${replace_map} ${line}]
			set searchpath_list [concat ${searchpath_list} [split "${proj_searchpath}" ":"]]
			break
		}
	}
	set ret_searchpath_list [list "${proj}/components"]
	foreach p ${searchpath_list} {
		set p [string trim "${p}"]
		if { "${p}" == "" } {
			continue
		}
		set p [file join "${proj}" "${p}"]
		lappend ret_searchpath_list "${p}"
	}
	return ${ret_searchpath_list}
}

set cmdline $argv
#set tclproc [shift cmdline]
set tclproc [lindex ${cmdline} 0]
set cmdline [lreplace ${cmdline} 0 0]
set plnx_kconfig 0
set plnx_data 0
set current_arch ""
set plnx_ips_record {}
if { "[info procs ${tclproc}]" eq "${tclproc}"} {
	${tclproc} ${cmdline}
} else {
	error "proc ${tclproc} doesn't exit."
}
