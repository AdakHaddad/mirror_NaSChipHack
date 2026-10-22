# Program the Cmod S7-25 with the counterfeit-battery bitstream.
# Usage: vivado -mode batch -source program.tcl
# Only the Cmod S7 should be on the JTAG chain (unplug the KV260 JTAG cable).

set here [file normalize [file dirname [info script]]]
set bit  [file join $here build cmod_s7_palsu.bit]

if {![file exists $bit]} {
    error "Bitstream not found: $bit (run build.tcl first)"
}

open_hw_manager
connect_hw_server
open_hw_target

set dev [lindex [get_hw_devices] 0]
current_hw_device $dev
refresh_hw_device -update_hw_probes false $dev
set_property PROGRAM.FILE $bit $dev
program_hw_devices $dev
refresh_hw_device $dev

puts "Programmed $dev with $bit"
close_hw_manager
