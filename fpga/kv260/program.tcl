# Program the KV260 PL with the Flow B bitstream over JTAG.
# Usage: vivado -mode batch -source program.tcl
#
# The PS must already be booted (Kria Ubuntu). This only loads the PL; it does
# not configure pl_clk0. Check RUNBOOK.md §5 first.

set here [file normalize [file dirname [info script]]]
set bit  [file join $here build kv260_top.bit]

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
