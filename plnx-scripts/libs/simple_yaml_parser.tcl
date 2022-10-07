# Copyright (C) 2014-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

proc simple_yaml_parser {ip_data_file} {
	set mapping_dict [dict create]
	set fp [open $ip_data_file r]
	set file_data [read $fp]
	set data [split $file_data "\n"]
	foreach line $data {
		#regsub -all {\s+} $line { } line
		if { [regexp "^#.*" $line matched] == 1 || \
			[regexp "^\s+#.*" $line matched] == 1 || \
			[string compare -nocase $line ""] <= 0 } {
			continue
		}
		# TODO: use first none_string started line for tab space(number) detection
		# FIXME: use auto detection
		regsub -all {    } $line {-~#%@} line
		#regsub -all { } $line {} line
		set data [split $line "@ "]
		set data_depth [llength [lsearch -all "$data" "-~#%"]]
		eval "set data_depth_$data_depth [lindex $data $data_depth]"
		if {$data_depth == 0} {
			continue
		}

		set tmp 0
		set eval_dict_arg ""
		while {$tmp <= $data_depth} {
			eval "set eval_dict_arg \"$eval_dict_arg \$data_depth_$tmp\""
			set tmp [expr {$tmp + 1}]
		}
		regsub -all {:} $eval_dict_arg {} eval_dict_arg
		regsub -all {^ } $eval_dict_arg {} eval_dict_arg

		# FIXME: use set instead of while loop to get value
		#set value [lrange $data [expr $data_depth + 1] [llength $data]]
		set tmp [expr $data_depth + 1]
		set tmp_depth [expr [llength $data] + 1]
		set value ""
		while {$tmp <= $tmp_depth} {
			eval "set value {$value [lindex $data $tmp]}"
			set tmp [expr {$tmp + 1}]
		}
		regsub -all {^\s+} $value {} value
		regsub -all {\s+$} $value {} value
		if { [string compare -nocase $value ""] == 0 } {
			continue
		}
		#regsub -all {\\n} $value "\n" value
		#regsub -all {\\t} $value "\t" value
		debug "yaml_parser" "puts dict set mapping_dict $eval_dict_arg {$value}"
		eval "dict set mapping_dict $eval_dict_arg {$value}"
	}
	close $fp
	return $mapping_dict
}

proc get_db_type_list {db_dict main_key} {
	set db_type_list ""
	if {![dict exist $db_dict $main_key]} {return}
	dict for {db_type conf_data} [dict get $db_dict $main_key] {
		set rt_code [catch {dict keys [dict get $db_dict $main_key $db_type]}]
		if {$rt_code == 0} {
			if {[lsearch -exact $db_type_list $db_type] >= 0} {
				continue
				}
			set db_type_list "$db_type_list $db_type"
		}
	}
	return $db_type_list
}

proc db_gen_prop_wrapper {fid db_dict ip main_key config_cat config_var} {
	set db_type_list [get_db_type_list $db_dict $main_key]
	foreach db_type $db_type_list {
		db_gen_prop $fid $db_dict $ip $main_key $db_type $config_cat $config_var
	}
}

proc db_gen_prop {fid db_dict ip main_key db_type config_cat config_var} {
	debug "db_gen_prop" "$ip main_key : $main_key db_type : $db_type config_cat : $config_cat config_var : $config_var"
	if {[dict exist $db_dict $main_key $db_type $config_cat]} {
		debug "db_gen_prop1" [dict get $db_dict $main_key $db_type $config_cat]
	} else {
		return
	}

	if {[string equal "kconfig" $db_type]} {
		global kconfig_dict
	}

	# ensure key exist
	set rt_code [catch {dict key [dict get $db_dict $main_key $db_type $config_cat]}]
	if {$rt_code != 0} {return}

	dict for {prop prop_mapping} [dict get $db_dict $main_key $db_type $config_cat] {
		set real_prop $prop
		debug "db_gen_prop" "prop : $prop prop_mapping : $prop_mapping"
		if {[regexp -all {%bn%} $prop ] == 1 } {
			# FIXME: bank id should read from kconfig
			set bank_id 0
			set real_prop [regsub -all {%bn%} $prop $bank_id]
		}
		if {! [dict exist $db_dict $main_key $db_type $config_cat $prop $config_var]} {
			continue
		}
		if {[string equal -nocase "chip_device" $ip]} {
			set target_obj [hsi get_hw_designs]
		} else {
			set target_obj [hsi get_cells -hier $ip]
		}

		set key_value [dict get $db_dict $main_key $db_type $config_cat $prop $config_var]
		if {[string compare -nocase $key_value ""] <= 0} {
			debug "Unknown $config_var" [hsi report_property $target_obj]
			continue
		}

		# handle different way of getting key_value
		if {[string equal "kconfig" $db_type]} {
			global kconfig_dict
			set kconf_ip_type [lindex [split $prop "?"] 0]
			set prop_list [split $prop "?"]
			set list_tsize [expr [llength $prop_list] - 1]
			set kconf_key [lindex [split $prop "?"] $list_tsize]
			set tmp 0
			set kconf_path ""
			while {$tmp < $list_tsize} {
				lappend kconf_path [lindex [split $prop "?"] $tmp]
				incr tmp
			}
			eval set param_value [dict get $kconfig_dict $kconf_path $kconf_key]
		} else {
			set param_value [hsi get_property $real_prop $target_obj]
		}
		if {[string compare -nocase $param_value ""] <= 0} {
			continue
		}
		if { "${config_var}" != "uboot_config" } {
			# ensure the same ip only been processed once only
			if {[dict exist $db_dict $main_key var_count]} {
				set var_name_list [dict get $db_dict $main_key var_count]
				foreach var_name $var_name_list {
					eval global $var_name
					eval set tmp $var_name
					eval set tmp_value $$var_name
					set tmp_value1 ${tmp_value}
					eval regsub -all {\%$tmp\%} {$key_value} {$tmp_value} key_value
					eval regsub -all {\%$tmp\%} {$param_value} {$tmp_value} param_value
					if { $tmp_value == 0 } {
						eval regsub -all {\~$tmp\~} {$key_value} {""} key_value
						eval regsub -all {\~$tmp\~} {$param_value} {""} param_value
					} else {
						eval regsub -all {\~$tmp\~} {$key_value} {$tmp_value} key_value
						eval regsub -all {\~$tmp\~} {$param_value} {$tmp_value} param_value
					}
				}
				# check if primary string exists in the $config_cat
				if {[regexp "^primary_.*" $config_cat matched] == 1} {
					if {$tmp_value != 0} {
						continue
					}
				}
			}
		}

		set striped_config_cat [regsub -all {primary_} $config_cat {}]
		debug "db_gen_prop" "striped_config_cat : $striped_config_cat"
		#TODO: Clean up
		switch -regexp $striped_config_cat {
			"config([0-9]|)_value_plus_" {
				debug "db_gen_prop" "config([0-9]|)_value_plus_"
				set inc_value [regsub -all {config([0-9]|)_value_plus_} $striped_config_cat {} ]
				set param_value [format "0x%08x" [expr $param_value + $inc_value]]
			}
			"config([0-9]|)_chk_.*_str" {
				debug "db_gen_prop" "([0-9]|)_chk_.*_str"
				set desired_value [regsub -all {config([0-9]|)_chk_} $striped_config_cat {} ]
				regsub -all {_str} $desired_value {} desired_value
				if {![string equal -nocase $param_value $desired_value]} {
					continue
				}
				puts $fid "$key_value"
				continue
			}
			"config([0-9]|)_chk_.*_custom_define" {
				debug "db_gen_prop" "config([0-9]|)_chk_.*_custom_define"
				set desired_value [regsub -all {config([0-9]|)_chk_} $striped_config_cat {} ]
				regsub -all {_custom_define} $desired_value {} desired_value
				if {![string equal -nocase $key_value $desired_value]} {
					continue
				}
				set param_value $key_value
				set key_value "remove_me"
			}
			"config([0-9]|)_chk_.*" {
				debug "db_gen_prop" "config([0-9]|)_chk_.*"
				set desired_value [regsub -all {config([0-9]|)_chk_} $striped_config_cat {} ]
				if {![string equal -nocase $desired_value $param_value]} {
					continue
				}
			}
			"custom_define([0-9]|)_chk_.*" {
				debug "db_gen_prop" "custom_define([0-9]|)_chk_.*"
				set desired_value [regsub -all "custom_define([0-9]|)_chk_" $striped_config_cat {} ]
				if {![string equal -nocase $desired_value $param_value]} {
					continue
				}
				set param_value $key_value
				set key_value "remove_me"
			}
			"custom_define([0-9]|)" {
				debug "db_gen_prop" "custom_define([0-9]|)"
				# check if key define founded
				set param_value $key_value
				set key_value "remove_me"
			}
			"undefine([0-9]|)" {
				foreach k $key_value {
						uboot_conf_undefine $fid $k
				}
				continue
			}
			"get_clk" {
				continue
			}
			"define([0-9]|)_chk_not_.*" {
				set desired_value [regsub -all {define([0-9]|)_chk_not_} $striped_config_cat {} ]
				if {![string equal -nocase $desired_value $param_value]} {
					set param_value ""
				} else {
					continue
				}
			}
			"define_chk([0-9]|)_.*" {
				set desired_value [regsub -all "define_chk([0-9]|)_" $striped_config_cat {} ]
				if {![string equal -nocase $desired_value $param_value]} {
					continue
				}
				set param_value ""
			}
			"define([0-9]|)_zero" {
				set param_value 0
			}
			"define([0-9]|)_.*" {
				set desired_value [regsub -all "define([0-9]|)_" $striped_config_cat {} ]
				set param_value $desired_value
			}
			"define([0-9]|)" {
				set param_value ""
			} default { }
		}
		if { "${config_var}" == "uboot_config" } {
			debug "db_gen_prop" "param_value : $param_value key_value : $key_value"
			seek ${fid} 0 start
			set lines [split [read ${fid}] "\n"]
			if {[llength ${param_value}] > 0} {
				#remove me or value from hsi property
				if {[string compare -nocase $key_value "remove_me"] == 0} {
					set first [lindex [split $param_value "="] 0]
					set second [lindex [split $param_value "="] 1]
					uboot_set_kconfig_value $fid $first $second
				} else {
					#param_value got from hsi
					uboot_set_kconfig_value $fid $key_value $param_value
				}
			} else {
				#only "=y" configs here
				uboot_set_kconfig_value $fid $key_value
			}
		} else {
			foreach k $key_value {
				debug "db_gen_prop" "set $k to $param_value [string compare -nocase $k "remove_me"]"
				if {[string compare -nocase $k "remove_me"] == 0} {
					uboot_conf_define $fid "" $param_value
				} else {
					uboot_conf_define $fid $k $param_value
				}
			}
		}
	}
}


proc call_dict_functions {fid ip_name db_dict ip ins_type config_cat config_var} {
	global func_called_list
	foreach ip_var "$ip_name $ins_type" {
		foreach call_t "call call_once" {
			if {[dict exist $db_dict $ip_var $call_t]} {
				if {![dict exist $db_dict $ip_var $call_t $config_var]} {
					continue
				}
				set func_list [dict get $db_dict $ip_var $call_t $config_var]
				foreach func $func_list {
					if {[lsearch -exact [info procs] $func] < 0} {continue}
					if {[string equal "call_once" $call_t]} {
						if {[lsearch -exact $func $func_called_list] >= 0} {
							continue
						}
					}
					eval "$func \$fid \$db_dict \$ip $ins_type $config_cat $config_var"
					lappend func_called_list $func
				}
			}
		}
	}
}


proc db_gen_config {fid ip_list db_dict tconf_name} {
	set config_var $tconf_name

	foreach ip $ip_list {
		# special handle for chip_device
		if {[string equal -nocase "simple" $ip]} {
			set ip_name simple
		} elseif {[string equal -nocase "chip_device" $ip]} {
			set ip_name $ip
		} else {
			set ip_obj [hsi get_cell -hier $ip]
			set ip_name [hsi get_property IP_NAME $ip_obj]
		}

		if {[dict exist $db_dict $ip_name]} {
			debug "1" "got ip $ip_name"
			if {[dict exist $db_dict $ip_name ip_type]} {
				set ins_type [dict get $db_dict $ip_name ip_type]
			} else {
				set ins_type ""
			}

			# get config list
			set tconf_list [get_conf_list $db_dict "$ip_name $ins_type"]

			# start fetch data and write to file
			foreach config_cat $tconf_list {
				db_gen_prop_wrapper $fid $db_dict $ip $ip_name $config_cat $config_var
			}

			# get common data for the ip
			foreach db_type [get_db_type_list $db_dict $ins_type] {
				foreach config_cat $tconf_list {
					if {[dict exist $db_dict $ins_type $db_type $config_cat]} {
						db_gen_prop_wrapper $fid $db_dict $ip $ins_type $config_cat $config_var
					}
				}
			}

			if { "${config_var}" == "uboot_config" } {
				continue
			}

			# call functions -- only called once
			foreach config_cat $tconf_list {
				call_dict_functions $fid $ip_name $db_dict $ip $ins_type $config_cat $config_var
				break
			}

			# now increase the var_count variables
			if {[dict exist $db_dict $ip_name var_count]} {
				set var_name_list [dict get $db_dict $ip_name var_count]
				foreach var_name $var_name_list {
					eval global $var_name
					eval incr $var_name
					eval set mytest $$var_name
				}
			}
		}
	}
}
