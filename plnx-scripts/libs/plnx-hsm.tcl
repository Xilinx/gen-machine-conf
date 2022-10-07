# Copyright (C) 2014-2022, Xilinx, Inc.  All rights reserved.
# Copyright (C) 2022, Advanced Micro Devices, Inc.  All rights reserved.
#
# SPDX-License-Identifier: MIT

namespace eval ::hsi::utils {
}

#
# It will retrun the connected interface to and IP interface
#

proc ::hsi::utils::get_connected_intf { periph_name intf_name} {
    set ret ""
    set periph [::hsi::get_cells -hier "$periph_name"]
    if { [llength $periph] == 0} {
        return $ret
    }
    set intf_pin [::hsi::get_intf_pins -of_objects $periph  "$intf_name"]
    if { [llength $intf_pin] == 0} {
        return $ret
    }
    set intf_net [::hsi::get_intf_nets -of_objects $intf_pin]
    if { [llength $intf_net] == 0} {
        return $ret
    }
    # set connected_intf [::hsi::get_intf_pins -of_objects $intf_net -filter "TYPE!=[common::get_property TYPE $intf_pin]"]

    set connected_intf [::hsi::utils::get_other_intf_pin $intf_net $intf_pin ]
    set intf_type [common::get_property TYPE $intf_pin]
    set conn_busif_handle [::hsi::utils::get_intf_pin_oftype $connected_intf $intf_type 0]
    return $conn_busif_handle
}
#
# it will return the net name connected to ip pin
#
proc ::hsi::utils::get_net_name {ip_inst ip_pin} {
    set ret ""
    if { [llength $ip_pin] != 0 } {
    set port [::hsi::get_pins -of_objects $ip_inst -filter "NAME==$ip_pin"]
    if { [llength $port] != 0 } {
        set pin [::hsi::get_nets -of_objects $port ]
        set ret [common::get_property NAME $pin]
    }
    }
   return $ret
}

#
# It will return the interface net name connected to IP interface.
#
proc ::hsi::utils::get_intfnet_name {ip_inst ip_busif} {
    set ret ""
    if { [llength $ip_busif] != 0 } {
    set bus_if [::hsi::get_intf_pins -of_objects $ip_inst -filter "NAME==$ip_busif"]
    if { [llength $bus_if] != 0 } {
       set intf_net [::hsi::get_intf_nets -of_objects $bus_if]
       set ret [common::get_property NAME $intf_net]
    }
    }
    return $ret
}


#
# It will return all the peripheral objects which are connected to processor
#
proc ::hsi::utils::get_proc_slave_periphs {proc_handle} {
   set periphlist [common::get_property slaves $proc_handle]
   if { $periphlist != "" } {
       foreach periph $periphlist {
        set periph1 [string trim $periph]
        set handle [::hsi::get_cells -hier $periph1]
        lappend retlist $handle
       }
    return $retlist
   } else {
       return ""
   }
}
#
# It will return the clock frequency value of IP clock port.
# it will first check the requested pin should be be clock type.
#
proc ::hsi::utils::get_clk_pin_freq { cell_obj clk_port} {
    set clk_port_obj [::hsi::get_pins $clk_port -of_objects $cell_obj]
    if {$clk_port_obj ne "" } {
        set port_type [common::get_property TYPE $clk_port_obj]
        if { [string compare -nocase $port_type  "CLK"] == 0 } {

            set clockValue [common::get_property CLK_FREQ $clk_port_obj]
            # Temp solution handle to exponential representaion
            set isExponentFormate "e"
            if {[string first $isExponentFormate $clockValue] != -1} {
              set retVal [format { %.0f} $clockValue]
              return $retVal
            }

            return [common::get_property CLK_FREQ $clk_port_obj]
        } else {
            error "ERROR:Trying to access frequency value from non-clock port \"$clk_port\" of IP \"$cell_obj\""
        }
    } else {
        error "ERROR:\"$clk_port\" port does not exist in IP \"$cell_obj\""
    }
    return ""
}

#
# It will check the pin object is external or not. If pin_object is
# associated to a cell then it is internal otherise it is external
#
proc ::hsi::utils::is_external_pin { pin_obj } {
    set pin_class [common::get_property CLASS $pin_obj]
    if { [string compare -nocase "$pin_class" port] == 0 } {
        set ip [::hsi::get_cells -of_objects $pin_obj]
        if {[llength $ip]} {
            return 0
        } else {
            return 1
        }
    } else {
        error "ERROR:is_external_pin Tcl proc expects port class type object $pin_obj. Whereas $pin_class type object is passed."
    }
}
#
# Get the width of port object. It will return width equal to 1 when
# port does not have width property
#
proc ::hsi::utils::get_port_width { port_handle} {
    set left [common::get_property LEFT $port_handle]
    set right [common::get_property RIGHT $port_handle]
    if {[llength $left] == 0 && [llength $right] == 0} {
        return 1
    }

    if {$left > $right} {
      set width [expr $left - $right + 1]
    } else {
      set width [expr $right - $left + 1]
    }
    return $width
}

#
# Remove the pin specified from the list of pins
#
proc ::hsi::utils::remove_pin_from_list { pinList pin } {
    lappend returnList

    foreach pinInList $pinList {
        # set pin_type [common::get_property TYPE $pinInList]
        # if { $pin_type == "MONITOR"} {
            # continue
        # }
        set givenCell [::hsi::get_cells -of_objects $pin]
        set newCell [::hsi::get_cells -of_objects $pinInList]
        if { $givenCell != $newCell } {
            lappend returnList $pinInList
        }
    }

    return $returnList
}

#
# Given an interface pin and one of the interface net, this functions
# returns the net which is on the other side of the boundary
#
proc ::hsi::utils::get_other_intf_net { intf_pin given_intf_net} {
    if { [llength $intf_pin] == 0 } {
        return ""
    }

    if { [llength $given_intf_net] == 0 } {
        return ""
    }

    set lower_intf_net [hsi::get_intf_nets -boundary_type lower -of_objects $intf_pin]
    set upper_intf_net [hsi::get_intf_nets -boundary_type upper -of_objects $intf_pin]
    if { [llength $lower_intf_net] != 0 && $lower_intf_net != $given_intf_net } {
         return $lower_intf_net
    } elseif { [llength $upper_intf_net] != 0 && $upper_intf_net != $given_intf_net } {
        return $upper_intf_net
    }

    return ""
}

#
# Given an interface net and one of the interface pins, this functions recursively traverses block containers
# to return the interface pin which is on the other end of the net
#
proc ::hsi::utils::get_other_intf_pin { intf_net given_intf_pin} {
    lappend return_pin_list
    if { [llength $intf_net] == 0 } {
        return ""
    }

    if { [llength $given_intf_pin] == 0 } {
        return ""
    }

    set intf_pins_list [::hsi::get_intf_pins -of_objects $intf_net]
    if { [llength $intf_pins_list] == 0 } {
        return ""
    }
    set other_intf_pins [::hsi::utils::remove_pin_from_list $intf_pins_list $given_intf_pin]
    if { [llength $other_intf_pins] == 0 } {
        return ""
    }

    foreach other_intf_pin $other_intf_pins {
        set other_cell [::hsi::get_cells -of_objects $other_intf_pin]
        if { [llength $other_cell] == 0 } {
            lappend return_pin_list $other_intf_pin
        }

        #set cell_type [common::get_property IP_NAME $other_cell]
        set cell_type [common::get_property BD_TYPE $other_cell]
        if { [ string match -nocase $cell_type "block_container" ] } {
            set other_bdry_intf_net [::hsi::utils::get_other_intf_net $other_intf_pin $intf_net]
            if { [llength $other_bdry_intf_net] == 0 } {
                continue
            }
            set result_pins [::hsi::utils::get_other_intf_pin $other_bdry_intf_net $other_intf_pin]
            if { [llength $result_pins] == 0 } {
                continue
            }
            foreach result_pin $result_pins {
                lappend return_pin_list $result_pin
            }
        } else {
            lappend return_pin_list $other_intf_pin
        }

    }

    return $return_pin_list
}

#
# Returns the pins that match the given type or does not match the given type based on the third argument
# isOf takes bool value. If isOf is true, the proc returns all the pins of the type given
# If isOF is false, the proc returns all the pins that not the type given
#
proc ::hsi::utils::get_intf_pin_oftype { given_intf_pins type isOf} {
    if { [llength $given_intf_pins] == 0 } {
        return $given_intf_pins
    }
    if { [ string match -nocase $type "" ] } {
        return $given_intf_pins
    }

    lappend return_pin_list
    foreach given_intf_pin $given_intf_pins {
        if { $isOf } {
            set given_pin_type [common::get_property TYPE $given_intf_pin]
            if { [ string match -nocase $$given_pin_type $type ]} {
                lappend return_pin_list $given_intf_pin
            }
        } else {
            set given_pin_type [common::get_property TYPE $given_intf_pin]
            if { ![ string match -nocase $$given_pin_type $type ]} {
                lappend return_pin_list $given_intf_pin
            }
        }
    }

    return $return_pin_list
}

proc ::hsi::utils::prepend { src_list dest_list } {
    set temp_list $dest_list
    set dest_list {}
    foreach itr $src_list {
	    lappend dest_list $itr
    }
    foreach itr $temp_list {
	    lappend dest_list $itr
    }
    return $dest_list
}

#
# Get handles for all ports driving the interrupt pin of a peripheral
#
proc ::hsi::utils::get_interrupt_sources {periph_handle } {
   lappend interrupt_sources
   lappend interrupt_pins
   set interrupt_pins [::hsi::get_pins -of_objects $periph_handle -filter {TYPE==INTERRUPT && DIRECTION==I}]
   foreach interrupt_pin $interrupt_pins {
       set source_pins [::hsi::utils::get_intr_src_pins $interrupt_pin]
       foreach source_pin $source_pins {
           lappend interrupt_sources $source_pin
       }
   }
   return $interrupt_sources
}
#
# Get the interrupt source pins of a periph pin object
#
proc ::hsi::utils::get_intr_src_pins {interrupt_pin} {
    lappend interrupt_sources
    set source_pins [::hsi::utils::get_source_pins $interrupt_pin]
    foreach source_pin $source_pins {
        set source_cell [::hsi::get_cells -of_objects $source_pin]
        if { [llength $source_cell ] } {
            #For concat IP, we need to bring pin source for other end
            set ip_name [common::get_property IP_NAME $source_cell]
            if { [string match -nocase $ip_name "xlconcat" ] } {
                set interrupt_sources [list {*}$interrupt_sources {*}[::hsi::__internal::get_concat_interrupt_sources $source_cell]]
            } elseif { [string match -nocase $ip_name "xlslice"] } {
                set interrupt_sources [list {*}$interrupt_sources {*}[::hsi::__internal::get_slice_interrupt_sources $source_cell]]
            } elseif { [string match -nocase $ip_name "util_reduced_logic"] } {
                set interrupt_sources [list {*}$interrupt_sources {*}[::hsi::__internal::get_util_reduced_logic_interrupt_sources $source_cell]]
            } else {
                lappend interrupt_sources $source_pin
            }
        } else {
            lappend interrupt_sources $source_pin
        }
    }
    return $interrupt_sources
}
#
# Get the source pins of a periph pin object
#
proc ::hsi::utils::get_source_pins {periph_pin} {
   set net [::hsi::get_nets -of_objects $periph_pin]
   set cell [::hsi::get_cells -of_objects $periph_pin]
   if { [llength $net] == 0} {
       return [lappend return_value]
   } else {
        set signals [split [common::get_property NAME $net] "&"]
        lappend source_pins
        if { [llength $signals] == 1 } {
          foreach signal $signals {
            set signal [string trim $signal]
            set sig_net [::hsi::get_nets -of_objects $cell $signal]
            if { [llength $sig_net] == 0 } {
                continue
            }
            set source_pin [::hsi::get_pins -of_objects $sig_net -filter { DIRECTION==O}]
            if { [ llength $source_pin] != 0 } {

                set source_pins [linsert $source_pins 0 $source_pin ]
            }
            set source_port [::hsi::get_ports -of_objects $sig_net -filter {DIRECTION==I}]
            if { [llength $source_port] != 0 } {

                set source_pins [linsert $source_pins 0 $source_port]
            }

            lappend real_source_pins
            if { [ llength $source_pins] == 0 } {

              set all_pins [::hsi::get_pins -of_objects $sig_net ]
              foreach pin $all_pins {
                set real_source_pin [::hsi::utils::get_real_source_pin_traverse_out $pin]
                if { [ llength $real_source_pin] != 0 } {
		    set real_source_pins [::hsi::utils::prepend $real_source_pin $real_source_pins]
                }
              }
        if { [llength $real_source_pins] != 0 } {
              return $real_source_pins
        }
            } else {

                foreach source_pin $source_pins {
                    set real_source_pin [::hsi::utils::get_real_source_pin_traverse_in $source_pin]
                    if { [ llength $real_source_pin] != 0 } {
		    set real_source_pins [::hsi::utils::prepend $real_source_pin $real_source_pins]
                    }
                }
        if { [llength $real_source_pins] != 0 } {
                  return $real_source_pins
        }
            }
          }
        } else {
            foreach signal $signals {
                set signal [string trim $signal]
                set sig_nets [::hsi::get_nets $signal]
                set got_net [get_net_of_perifh_pin $periph_pin $sig_nets]
                set source_pin [::hsi::get_pins -of_objects $got_net -filter { DIRECTION==O}]
                if { [ llength $source_pin] != 0 } {
                    set source_pins [linsert $source_pins 0 $source_pin ]
                }
                set source_port [::hsi::get_ports -of_objects $got_net -filter {DIRECTION==I}]
                if { [llength $source_port] != 0 } {
                    set source_pins [linsert $source_pins 0 $source_port]
                }
            }
        }
        return $source_pins
    }
}

proc ::hsi::utils::get_real_source_pin_traverse_out { pin } {

    lappend source_pins
      set lower_net [hsi::get_nets -boundary_type lower -of_objects $pin]
      set upper_net [hsi::get_nets -boundary_type upper -of_objects $pin]

      if { [ llength $lower_net] != 0  && [ llength $upper_net] != 0 } {

          set real_source_pin [::hsi::get_pins -of_objects $upper_net -filter "DIRECTION==O" ]
          # removing the pin from where the traversal started or from where the funtion is called
          set real_source_pin [::hsi::utils::remove_pin_from_list $real_source_pin $pin]

          set real_source_port [::hsi::get_ports -of_objects $upper_net -filter "DIRECTION==I" ]
          # removing the pin from where the traversal started or from where the funtion is called
          set real_source_port [::hsi::utils::remove_pin_from_list $real_source_port $pin]

          if { [ llength $real_source_pin] != 0 } {
              set source_pins [linsert $source_pins 0 $real_source_pin ]
          }
          if { [llength $real_source_port] != 0 } {
              set source_pins [linsert $source_pins 0 $real_source_port]
          }
          #if { [ llength $source_pins] != 0 } {
          #       return [::hsi::utils::get_real_source_pin_traverse_out $source_pins]
          #}
      }
    return $source_pins
}

proc ::hsi::utils::get_real_source_pin_traverse_in { pin } {

    lappend source_pins

    set hasCells [::hsi::get_cells -of_objects $pin]
    if { [ llength $hasCells] == 0 } {
      return $source_pins
    }

    #set source_type [common::get_property IP_NAME [::hsi::get_cells -of_objects $pin]]
    set source_type [common::get_property BD_TYPE [::hsi::get_cells -of_objects $pin]]
    if { [ string match -nocase $source_type "block_container" ] } {

        set lower_net [hsi::get_nets -boundary_type lower -of_objects $pin]
        set upper_net [hsi::get_nets -boundary_type upper -of_objects $pin]

        if { [ llength $lower_net] != 0  && [ llength $upper_net] != 0 } {

            set real_source_pin [::hsi::get_pins -of_objects $lower_net -filter "DIRECTION==O" ]

            # removing the pin from where the traversal started or from where the funtion is called
            set real_source_pin [::hsi::utils::remove_pin_from_list $real_source_pin $pin]

            set real_source_port [::hsi::get_ports -of_objects $lower_net -filter "DIRECTION==I" ]
            # removing the pin from where the traversal started or from where the funtion is called
            set real_source_port [::hsi::utils::remove_pin_from_list $real_source_port $pin]

            if { [ llength $real_source_pin] != 0 } {
                set source_pins [linsert $source_pins 0 $real_source_pin ]
            }
            if { [llength $real_source_port] != 0 } {
                set source_pins [linsert $source_pins 0 $real_source_port]
            }
            #if { [ llength $source_pins] != 0 } {
            #       return [::hsi::utils::get_real_source_pin_traverse_in $source_pins]
            #}
        }
    }

    if { [ llength $source_pins] == 0 } {
            return $pin
    }

    return $source_pins
}

#
# Find net of a peripheral pin object
#
proc ::hsi::utils::get_net_of_perifh_pin {periph_pin sig_nets} {

    if { [ llength $sig_nets ] == 1 } {
        set got_net [lindex $sig_nets 0]
        return $got_net
    }

    set found 0
    set got_net ""
    set cell [::hsi::get_cells -of_objects $periph_pin]
    foreach sig_net $sig_nets {
        if {$sig_net != ""} {
            set both_cells [::hsi::get_cells -of_objects $sig_net]
            foreach single_cell $both_cells {
                if {$single_cell == $cell } {
                    set got_net $sig_net
                    set found 1
                    break;
                }
            }
            if {$found} {
            break;
            }
        }
    }
    return $got_net
}


#
# Get the sink pins of a peripheral pin object
#
proc ::hsi::utils::get_sink_pins {periph_pin} {
   set net [::hsi::get_nets -of_objects $periph_pin]
   set cell [::hsi::get_cells -of_objects $periph_pin]
   if { [llength $net] == 0} {
       return [lappend return_value]
   } else {
       set signals [split [common::get_property NAME $net] "&"]
       lappend source_pins
       if { [llength $signals] == 1 } {
       foreach signal $signals {
           set signal [string trim $signal]
           if { $cell == "" } {
               set sig_net [::hsi::get_nets $signal]
           } else {
               set sig_net [::hsi::get_nets -of_objects $cell $signal]
           }

           #Direct out pins
           set pins [::hsi::get_pins -of_objects $sig_net -filter { DIRECTION==I}]
           if { [ llength $pins] != 0 } {
               foreach source_pin $pins {
                   set source_pins [linsert $source_pins 0 $source_pin ]
               }
           }
           set source_ports [::hsi::get_ports -of_objects $sig_net -filter {DIRECTION==O}]
           if { [llength $source_ports] != 0 } {
               foreach source_port $source_ports {
                   set source_pins [linsert $source_pins 0 $source_port]
               }
           }

           lappend real_sink_pins
           if { [ llength $source_pins] != 0 } {
               foreach test_pin $source_pins {
                    set real_sink_pin [::hsi::utils::get_real_sink_pins_traverse_in $test_pin]
                    if { [ llength $real_sink_pin] != 0 } {
                        foreach real_pin $real_sink_pin {
                          set real_sink_pins [linsert $real_sink_pins end $real_pin]
                        }
                    }
               }
            }
            set real_sink_pin [::hsi::utils::get_real_sink_pins_traverse_out $periph_pin]
            if { [ llength $real_sink_pin] != 0 } {
                foreach real_pin $real_sink_pin {
                  set real_sink_pins [linsert $real_sink_pins end $real_pin]
                }
            }
        if { [llength $real_sink_pins] != 0 } {
                return $real_sink_pins
        }
         }
       } else {

        foreach signal $signals {
            set signal [string trim $signal]
            set sig_nets [::hsi::get_nets $signal]
            set got_net [get_net_of_perifh_pin $periph_pin $sig_nets]
            set pins [::hsi::get_pins -of_objects $got_net -filter { DIRECTION==I}]
            if { [ llength $pins] != 0 } {
                foreach source_pin $pins {
                    set source_pins [linsert $source_pins 0 $source_pin ]
                }
            }
            set source_ports [::hsi::get_ports -of_objects $got_net -filter {DIRECTION==O}]
            if { [llength $source_ports] != 0 } {
                foreach source_port $source_ports {
                   set source_pins [linsert $source_pins 0 $source_port]
                }
            }
        }
       }

       return $source_pins

   }
}

proc ::hsi::utils::get_real_sink_pins_traverse_in { test_pin } {

    lappend source_pins
    set hasCells [::hsi::get_cells -of_objects $test_pin]
    if { [ llength $hasCells] == 0 } {
      return $source_pins
    }
    #set source_type [common::get_property IP_NAME [::hsi::get_cells -of_objects $test_pin]]
    set source_type [common::get_property BD_TYPE [::hsi::get_cells -of_objects $test_pin]]
    if { [ string match -nocase $source_type "block_container" ] } {

        set lower_net [hsi::get_nets -boundary_type lower -of_objects $test_pin]
        set upper_net [hsi::get_nets -boundary_type upper -of_objects $test_pin]

        if { [ llength $lower_net] != 0  && [ llength $upper_net] != 0 } {

            set real_sink_pins [::hsi::get_pins -of_objects $lower_net -filter "DIRECTION==I" ]
            # removing the pin form where the traversal started or from where the funtion is called
            set real_sink_pins [::hsi::utils::remove_pin_from_list $real_sink_pins $test_pin]

            if { [ llength $real_sink_pins] != 0 } {
                foreach source_pin $real_sink_pins {
                    set source_pins [linsert $source_pins 0 $source_pin ]
                }
            }

            set real_sink_ports [::hsi::get_ports -of_objects $lower_net -filter "DIRECTION==O" ]
            # removing the pin form where the traversal started or from where the funtion is called
            set real_sink_ports [::hsi::utils::remove_pin_from_list $real_sink_ports $test_pin]

            if { [llength $real_sink_ports] != 0 } {
                foreach source_port $real_sink_ports {
                    set source_pins [linsert $source_pins 0 $source_port]
                }
            }
        }
    } else {
         set source_pins [linsert $source_pins 0 $test_pin]
    }

    return $source_pins
}

proc ::hsi::utils::get_real_sink_pins_traverse_out { periph_pin } {

    #InDirect out pins
    lappend source_pins
    set sig_net [::hsi::get_nets -of_objects $periph_pin]
    set pins [::hsi::get_pins -of_objects $sig_net -filter {DIRECTION==O}]
    if { [ llength $pins] != 0 } {
        foreach source_pin $pins {
            set source_pins [linsert $source_pins 0 $source_pin ]
        }
    }
    set source_ports [::hsi::get_ports -of_objects $sig_net -filter {DIRECTION==I}]
    if { [llength $source_ports] != 0 } {
        foreach source_port $source_ports {
            set source_pins [linsert $source_pins 0 $source_port]
        }
    }
    lappend sink_pins
    if { [ llength $source_pins] != 0 } {
        foreach test_pin $source_pins {
            set hasCells [::hsi::get_cells -of_objects $test_pin]
            if { [ llength $hasCells] == 0 } {
              continue
            }
            #set source_type [common::get_property IP_NAME [::hsi::get_cells -of_objects $test_pin]]
            set source_type [common::get_property BD_TYPE [::hsi::get_cells -of_objects $test_pin]]
            if { [ string match -nocase $source_type "block_container" ] } {

               set lower_net [hsi::get_nets -boundary_type lower -of_objects $test_pin]
               set upper_net [hsi::get_nets -boundary_type upper -of_objects $test_pin]

               if { [ llength $lower_net] != 0  && [ llength $upper_net] != 0 } {

                   set real_sink_pins [::hsi::get_pins -of_objects $upper_net -filter "DIRECTION==I" ]
                   # removing the pin from where the traversal started or from where the funtion is called
                   set real_sink_pins [::hsi::utils::remove_pin_from_list $real_sink_pins $test_pin]
                   if { [ llength $real_sink_pins] != 0 } {
                       foreach source_pin $real_sink_pins {
                           set sink_pins [linsert $sink_pins 0 $source_pin ]
                       }
                   }

                   set real_sink_ports [::hsi::get_ports -of_objects $upper_net -filter "DIRECTION==O" ]
                   # removing the pin from where the traversal started or from where the funtion is called
                   set real_sink_ports [::hsi::utils::remove_pin_from_list $real_sink_ports $test_pin]
                   if { [llength $real_sink_ports] != 0 } {
                       foreach source_port $real_sink_ports {
                           set sink_pins [linsert $sink_pins 0 $source_port]
                       }
                   }
               }
            }
         }
     }
     if { [ llength $sink_pins] != 0 } {
         return $sink_pins
     }
}


#
# get the pin count which are connected to peripheral pin
#
proc ::hsi::utils::get_connected_pin_count { periph_pin } {
    set total_width 0
    set cell [::hsi::get_cells -of_objects $periph_pin]
    set connected_nets [::hsi::get_nets -of_objects $periph_pin]
    set signals [split $connected_nets "&"]
    if { [llength $signals] == 1 } {
     foreach signal $signals {
        set width 0
        set signal [string trim $signal]
      set sig_nets [::hsi::get_nets -of_object $cell $signal]
      if { [llength $sig_nets] == 0 } {
            continue
        }
      set signal [string trim $signal]
      set got_net [get_net_of_perifh_pin $periph_pin $sig_nets]
      set source_port [::hsi::get_ports -of_objects $got_net]
        if {[llength $source_port] != 0 } {
            set width [::hsi::utils::get_port_width $source_port]
        } else {
            set source_pin [::hsi::get_pins -of_objects $got_net -filter {DIRECTION==O}]
            if { [llength $source_pin] ==0 } {
                # handling team BD case
                set source_pin [::hsi::utils::get_source_pins $periph_pin]
                if { [llength $source_pin] ==0 } {
                    continue
                }
            }
            set width [::hsi::utils::get_port_width $source_pin]
        }
        set total_width [expr {$total_width + $width}]
     }
    } else {
     foreach signal $signals {
        set width 0
        set signal [string trim $signal]
      set sig_nets [::hsi::get_nets $signal]
      if { [llength $sig_nets] == 0 } {
            continue
        }
      set signal [string trim $signal]
      set got_net [get_net_of_perifh_pin $periph_pin $sig_nets]
      set source_port [::hsi::get_ports -of_objects $got_net]
        if {[llength $source_port] != 0 } {
            set width [::hsi::utils::get_port_width $source_port]
        } else {
            set source_pin [::hsi::get_pins -of_objects $got_net -filter {DIRECTION==O}]
            if { [llength $source_pin] ==0 } {
                continue
            }
            set width [::hsi::utils::get_port_width $source_pin]
        }
        set total_width [expr {$total_width + $width}]
     }
    }
    return $total_width
}

#
# get the parameter value. It has special handling for DEVICE_ID parameter name
#
proc ::hsi::utils::get_param_value {periph_handle param_name} {
        if {[string compare -nocase "DEVICE_ID" $param_name] == 0} {
            # return the name pattern used in printing the device_id for the device_id parameter
            return [::hsi::utils::get_ip_param_name $periph_handle $param_name]
        } else {
            set value [common::get_property CONFIG.$param_name $periph_handle]
            set value [string map {_ ""} $value]
            return $value
    }
}

#
# Returns name of the p2p peripheral if arg is present
#
proc ::hsi::utils::get_p2p_name {periph arg} {
   set p2p_name ""

   # Get all point2point buses for periph
   set p2p_busifs_i [::hsi::get_intf_pins -of_objects $periph -filter "TYPE==INITIATOR"]

   # Add p2p periphs
   foreach p2p_busif $p2p_busifs_i {
       set intf_net [::hsi::get_intf_nets -of_objects $p2p_busif]
       if { $intf_net ne "" } {
           # set conn_busif_handle [::hsi::get_intf_pins -of_objects $intf_net -filter "TYPE==TARGET"]
           set intf_type "TARGET"
           set conn_busif_handles [::hsi::utils::get_other_intf_pin $intf_net $p2p_busif]
           set conn_busif_handle [::hsi::utils::get_intf_pin_oftype $conn_busif_handles $intf_type 1]
           if { [string compare -nocase $conn_busif_handle ""] != 0} {
               set p2p_periph [::hsi::get_cells -of_objects $conn_busif_handle]
               if { $p2p_periph ne "" } {
                   set value [common::get_property $arg $p2p_periph]
                   if { [string compare -nocase $value ""] != 0} {
                       return [::hsi::utils::get_ip_param_name $p2p_periph $arg]
                   }
               }
           }
       }
    }

   return $p2p_name
}

#
# it returns all the processor instance object in design
#
proc ::hsi::utils::get_procs { } {
   return [::hsi::get_cells  -hier -filter { IP_TYPE==PROCESSOR}]
}

#
# Get the interrupt ID of a peripheral interrupt port
#
proc ::hsi::utils::get_port_intr_id { periph_name intr_port_name } {
    return [::hsi::utils::get_interrupt_id $periph_name $intr_port_name]
}
#
# It will check the is peripheral is interrupt controller or not
#
proc ::hsi::utils::is_intr_cntrl { periph_name } {
    set ret 0
    if { [llength $periph_name] != 0 } {
    set periph [::hsi::get_cells -hier -filter "NAME==$periph_name"]
    if { [llength $periph] == 1 } {
        set special [common::get_property CONFIG.EDK_SPECIAL $periph]
        set ip_type [common::get_property IP_TYPE $periph]
        if {[string compare -nocase $special "interrupt_controller"] == 0  ||
            [string compare -nocase $special "INTR_CTRL"] == 0 ||
            [string compare -nocase $ip_type "INTERRUPT_CNTLR"] == 0 } {
                set ret 1
        }
    }
    }
    return $ret
}

#
# It needs IP name and interrupt port name and it will return the connected
# interrupt controller
# for External interrupt port, IP name should be empty
#
proc ::hsi::utils::get_connected_intr_cntrl { periph_name intr_pin_name } {
    lappend intr_cntrl
    if { [llength $intr_pin_name] == 0 } {
        return $intr_cntrl
    }

    if { [llength $periph_name] != 0 } {
        #This is the case where IP pin is interrupting
        set periph [::hsi::get_cells -hier -filter "NAME==$periph_name"]
        if { [llength $periph] == 0 } {
            return $intr_cntrl
        }
        set intr_pin [::hsi::get_pins -of_objects $periph -filter "NAME==$intr_pin_name"]
        if { [llength $intr_pin] == 0 } {
            return $intr_cntrl
        }
        set pin_dir [common::get_property DIRECTION $intr_pin]
        if { [string match -nocase $pin_dir "I"] } {
          return $intr_cntrl
        }
    } else {
        #This is the case where External interrupt port is interrupting
        set intr_pin [::hsi::get_ports $intr_pin_name]
        if { [llength $intr_pin] == 0 } {
            return $intr_cntrl
        }
        set pin_dir [common::get_property DIRECTION $intr_pin]
        if { [string match -nocase $pin_dir "O"] } {
          return $intr_cntrl
        }
    }

    set intr_sink_pins [::hsi::utils::get_sink_pins $intr_pin]
    foreach intr_sink $intr_sink_pins {
        #changes made to fix CR 933826
        set sink_periph [lindex [::hsi::get_cells -of_objects $intr_sink] 0]
        if { [llength $sink_periph ] && [::hsi::utils::is_intr_cntrl $sink_periph] == 1 } {
            lappend intr_cntrl $sink_periph
        } elseif { [llength $sink_periph] && [string match -nocase [common::get_property IP_NAME $sink_periph] "xlconcat"] } {
            #this the case where interrupt port is connected to XLConcat IP.
            #changes made to fix CR 933826
            set intr_cntrl [list {*}$intr_cntrl {*}[::hsi::utils::get_connected_intr_cntrl $sink_periph "dout"]]
        } elseif { [llength $sink_periph] && [string match -nocase [common::get_property IP_NAME $sink_periph] "xlslice"] } {
            set intr_cntrl [list {*}$intr_cntrl {*}[::hsi::utils::get_connected_intr_cntrl $sink_periph "Dout"]]
        } elseif { [llength $sink_periph] && [string match -nocase [common::get_property IP_NAME $sink_periph] "util_reduced_logic"] } {
            set intr_cntrl [list {*}$intr_cntrl {*}[::hsi::utils::get_connected_intr_cntrl $sink_periph "Res"]]
        }
    }
    return $intr_cntrl
}

#
# It will get the version information from IP VLNV property
#
proc ::hsi::utils::get_ip_version { ip_name } {
    set version ""
    set ip_handle [::hsi::get_cells -hier $ip_name]
    if { [llength $ip_handle] == 0 } {
        error "ERROR:IP $ip_name does not exist in design"
        return ""
    }
    set vlnv [common::get_property VLNV $ip_handle]
    set splitted_vlnv [split $vlnv ":"]
    if { [llength $splitted_vlnv] == 4 } {
        set version [lindex $splitted_vlnv 3]
    } else {
        #TODO: Keeping older EDK xml support. It should be removed
        set version [common::get_property HW_VER $ip_handle]
    }
    return $version
}

#
# It will return IP param value
#
proc ::hsi::utils::get_ip_param_value { ip param} {
    set value [common::get_property $param $ip]
    if {[llength $value] != 0} {
        return $value
    }
    set value [common::get_property CONFIG.$param $ip]
    if {[llength $value] != 0} {
        return $value
    }
}

#
# It will return board name
#
proc ::hsi::utils::get_board_name { } {
    global board_name
    set board_name [common::get_property BOARD [::hsi::current_hw_design] ]
     if { [llength $board_name] == 0 } {
        set board_name "."
    }
    return $board_name
}

proc ::hsi::utils::get_trimmed_param_name { param } {
    set param_name $param
    regsub -nocase ^CONFIG. $param_name "" param_name
    regsub -nocase ^C_ $param_name "" param_name
    return $param_name
}
#
# It returns the ip subtype. First its check for special type of EDK_SPECIAL parameter
#
proc ::hsi::utils::get_ip_sub_type { ip_inst_object} {
    if { [string compare -nocase cell [common::get_property CLASS $ip_inst_object]] != 0 } {
        error "get_mem_type API expect only mem_range type object whereas $class type object is passed"
    }

    set ip_type [common::get_property CONFIG.EDK_SPECIAL $ip_inst_object]
    if { [llength $ip_type] != 0 } {
        return $ip_type
    }

    set ip_name [common::get_property IP_NAME $ip_inst_object]
    if { [string compare -nocase "$ip_name"  "lmb_bram_if_cntlr"] == 0
        || [string compare -nocase "$ip_name" "isbram_if_cntlr"] == 0
        || [string compare -nocase "$ip_name" "axi_bram_ctrl"] == 0
        || [string compare -nocase "$ip_name" "dsbram_if_cntlr"] == 0
        || [string compare -nocase "$ip_name" "ps7_ram"] == 0 } {
            set ip_type "BRAM_CTRL"
    } elseif { [string match -nocase *ddr* "$ip_name" ] == 1 } {
         set ip_type "DDR_CTRL"
     } elseif { [string compare -nocase "$ip_name" "mpmc"] == 0 } {
         set ip_type "DRAM_CTRL"
     } elseif { [string compare -nocase "$ip_name" "axi_emc"] == 0 } {
         set ip_type "SRAM_FLASH_CTRL"
     } elseif { [string compare -nocase "$ip_name" "psu_ocm_ram_0"] == 0
                || [string compare -nocase "$ip_name" "psu_ocm_ram_1"] == 0
                || [string compare -nocase "$ip_name" "psv_ocm_ram_0"] == 0 } {
         set ip_type "OCM_CTRL"
     } else {
         set ip_type [common::get_property IP_TYPE $ip_inst_object]
     }
     return $ip_type
}

proc ::hsi::utils::generate_psinit { } {
    set obj [::hsi::get_cells -hier -filter {CONFIGURABLE == 1}]
    if { [llength $obj] == 0 } {
      set xmlpath [common::get_property PATH [::hsi::current_hw_design]]
      if { $xmlpath != "" } {
        set xmldir [file dirname $xmlpath]
        set file "$xmldir[file separator]ps7_init.c"
        if { [file exists $file] } {
          file copy -force $file .
        }

        set file "$xmldir[file separator]ps7_init.h"
        if { [file exists $file] } {
          file copy -force $file .
        }
      }
    } else {
      generate_target {psinit} $obj -dir .
    }
}

# This API returns the interrupt ID of a IP Pin
# Usecase: to get the ID of a top level interrupt port, provide empty string for ip_name
# Usecase: If port width port than 1 bit, then it will return multiple interrupts ID with ":" seperated
proc ::hsi::utils::get_interrupt_id { ip_name port_name } {
    set ret -1
    set periph ""
    set intr_pin ""
    if { [llength $port_name] == 0 } {
        return $ret
    }

    if { [llength $ip_name] != 0 } {
        #This is the case where IP pin is interrupting
        set periph [::hsi::get_cells -hier -filter "NAME==$ip_name"]
        if { [llength $periph] == 0 } {
            return $ret
        }
        set intr_pin [::hsi::get_pins -of_objects $periph -filter "NAME==$port_name"]
        if { [llength $intr_pin] == 0 } {
            return $ret
        }
        set pin_dir [common::get_property DIRECTION $intr_pin]
        if { [string match -nocase $pin_dir "I"] } {
          return $ret
        }
    } else {
        #This is the case where External interrupt port is interrupting
        set intr_pin [::hsi::get_ports $port_name]
        if { [llength $intr_pin] == 0 } {
            return $ret
        }
        set pin_dir [common::get_property DIRECTION $intr_pin]
        if { [string match -nocase $pin_dir "O"] } {
          return $ret
        }
    }

    set intc_periph [::hsi::utils::get_connected_intr_cntrl $ip_name $port_name]
    if { [llength $intc_periph]  ==  0 } {
        return $ret
    }

    set intc_type [common::get_property IP_NAME $intc_periph]
    set irqid [common::get_property IRQID $intr_pin]
    if { [llength $irqid] != 0 && [string match -nocase $intc_type "ps7_scugic"] } {
        set irqid [split $irqid ":"]
        return $irqid
    }

    # For zynq the intc_src_ports are in reverse order
    if { [string match -nocase "$intc_type" "ps7_scugic"]  } {
        set ip_param [common::get_property CONFIG.C_IRQ_F2P_MODE $intc_periph]
        set ip_intr_pin [::hsi::get_pins -of_objects $intc_periph "IRQ_F2P"]
        if { [string match -nocase "$ip_param" "REVERSE"] } {
            set intc_src_ports [lreverse [::hsi::utils::get_intr_src_pins $ip_intr_pin]]
        } else {
            set intc_src_ports [::hsi::utils::get_intr_src_pins $ip_intr_pin]
        }
        set total_intr_count -1
        foreach intc_src_port $intc_src_ports {
            set intr_periph [::hsi::get_cells -of_objects $intc_src_port]
            set intr_width [::hsi::utils::get_port_width $intc_src_port]
            if { [llength $intr_periph] } {
                #case where an a pin of IP is interrupt
                if {[common::get_property IS_PL $intr_periph] == 0} {
                    continue
                }
            }
            set total_intr_count [expr $total_intr_count + $intr_width]
        }
    } else  {
        set intc_src_ports [::hsi::utils::get_interrupt_sources $intc_periph]
    }

    #Special Handling for cascading case of axi_intc Interrupt controller
    set cascade_id 0
    if { [string match -nocase "$intc_type" "axi_intc"] } {
        set cascade_id [::hsi::__internal::get_intc_cascade_id_offset $intc_periph]
    }

    set i $cascade_id
    set found 0
    foreach intc_src_port $intc_src_ports {
        if { [llength $intc_src_port] == 0 } {
            incr i
            continue
        }
        set intr_width [::hsi::utils::get_port_width $intc_src_port]
        set intr_periph [::hsi::get_cells -of_objects $intc_src_port]
        if { [string match -nocase $intc_type "ps7_scugic"] && [llength $intr_periph]} {
            if {[common::get_property IS_PL $intr_periph] == 0 } {
                continue
            }
        }
        if { [string compare -nocase "$port_name"  "$intc_src_port" ] == 0 } {
            if { [string compare -nocase "$intr_periph" "$periph"] == 0 } {
                set ret $i
                set found 1
                break
            }
        }
        set i [expr $i + $intr_width]
    }

    # interrupt source not found, this could be case where IP interrupt is connected
    # to core0/core1 nFIQ nIRQ of scugic
    if { $found == 0 && [string match -nocase $intc_type "ps7_scugic"]} {
        set sink_pins [::hsi::utils::get_sink_pins $intr_pin]
        lappend intr_pin_name;
        foreach sink_pin $sink_pins {
            set connected_ip [::hsi::get_cells -of_objects $sink_pin]
            set ip_name [common::get_property NAME $connected_ip]
            if { [string match -nocase "$ip_name" "ps7_scugic"] == 0 } {
                set intr_pin_name $sink_pin
            }
        }
        if {[string match -nocase "Core1_nIRQ" $sink_pin] || [string match -nocase "Core0_nIRQ" $sink_pin] } {
            set ret 31
        } elseif {[string match -nocase "Core0_nFIQ" $sink_pin] || [string match -nocase "Core1_nFIQ" $sink_pin] } {
           set ret 28
        }
    }

    set port_width [::hsi::utils::get_port_width $intr_pin]
    set tempret $ret
    set lastadded 0
    set ps7_scugic_flow 0
    set i 1
    for {set i 1 } { $i <= $port_width } { incr i } {
      if { [string match -nocase $intc_type "ps7_scugic"] && $found == 1  } {
        set ps7_scugic_flow 1
        set ip_param [common::get_property CONFIG.C_IRQ_F2P_MODE $intc_periph]
        if { [string compare -nocase "$ip_param" "DIRECT"]} {
            # if (total_intr_count - id) is < 16 then it needs to be subtracted from 76
            # and if (total_intr_count - id) < 8 it needs to be subtracted from 91
            if { $lastadded == 0} {
              set ret {}
              set tempret [expr $total_intr_count -$tempret + $lastadded]
            } else {
              set tempret [expr -$tempret + $lastadded]
            }
            if { $tempret < 8 } {
                set tempret [expr 91 - $tempret]
                set lastadded 91
            } elseif { $tempret < 16} {
                set tempret [expr 68 - ${tempret} + 8 ]
                set lastadded [expr 68 + 8]
            }
        } else {
            # if id is < 8 then it needs to be added to 61
            # and if id < 16 it needs to be added to 76
            if { $lastadded == 0} {
              set ret {}
            }
            set limit [expr $tempret - $lastadded]
            if { $limit < 8 } {
                set tempret [expr $limit + 61]
                set lastadded 61
            } elseif { $limit < 16} {
                set tempret [expr $limit + 84 - 8]
                set lastadded [expr 84 - 8]
            }
        }
      }
      if { $lastadded != 0} {
        lappend ret $tempret
        set tempret [expr $tempret + 1]
      }
      if { $ps7_scugic_flow == 0 && $i < $port_width} {
       lappend ret [expr $tempret + 1]
       incr tempret
      }
    }
    return $ret
}


# Get the memory range of IP for current processor
#
proc ::hsi::utils::get_ip_mem_ranges {periph} {
    set sw_proc_handle [::hsi::get_sw_processor]
    set hw_proc_handle [::hsi::get_cells -hier [common::get_property hw_instance $sw_proc_handle]]
        if { [llength $periph] != 0 } {
    set mem_ranges [::hsi::get_mem_ranges -of_objects $hw_proc_handle -filter "INSTANCE==$periph"]
        }
    return $mem_ranges
}
