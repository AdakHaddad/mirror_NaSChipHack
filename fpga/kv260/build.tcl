# Full KV260 build: PS clock block design + PL bitstream + .bit.bin
# Usage:
#   vivado -mode batch -source build.tcl
#   vivado -mode batch -source build.tcl -tclargs 125   ;# other pl_clk0 (MHz)
#   vivado -mode batch -source build.tcl -tclargs 100 96968727
#       ;# keep the PS at 100 MHz in the BD but build the RTL for the clock the
#       ;# stock Kria firmware actually provides (see RUNBOOK §5)
#
# The PS is used only as the clock source (pl_clk0 @ 100 MHz by default) and
# for pl_resetn0. All sample/auth logic stays in the PL.

set here    [file normalize [file dirname [info script]]]
set root    [file normalize [file join $here ../..]]
set rtl     [file join $root rtl]
set outdir  [file join $here build]
set projdir [file join $outdir project]

set PL_CLK_MHZ 100
if {$argc >= 1} {
    set PL_CLK_MHZ [lindex $argv 0]
}
set CLK_HZ [expr {$PL_CLK_MHZ * 1000000}]
set RTL_CLK_HZ 0
if {$argc >= 2} {
    set RTL_CLK_HZ [lindex $argv 1]
}

file mkdir $outdir
create_project -force kv260 $projdir -part xck26-sfvc784-2LV-c
set_property target_language Verilog [current_project]

add_files [list \
    [file join $rtl uart_if.v] \
    [file join $rtl axil_master.v] \
    [file join $rtl sha256_core.v] \
    [file join $rtl hmac_sha256.v] \
    [file join $rtl auth_ctrl.v] \
    [file join $rtl i2c_master.v] \
    [file join $rtl ads1115_ctrl.v] \
    [file join $rtl sebatt_top.v] \
    [file join $here kv260_top.v] \
]
add_files -fileset constrs_1 [file join $here kv260.xdc]

# ---------------------------------------------------------------------------
# PS block design: clock only. 100 MHz on pl_clk0 from the IOPLL; the Kria
# SOM feeds PS_REF_CLK (33.33 MHz) internally, so there is no fabric port.
# ---------------------------------------------------------------------------
create_bd_design design_1
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e ps]

set ps_cfg [list \
    CONFIG.PSU__USE__M_AXI_GP0 {0} \
    CONFIG.PSU__USE__M_AXI_GP1 {0} \
    CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__USE__S_AXI_GP0 {0} \
    CONFIG.PSU__USE__S_AXI_GP1 {0} \
    CONFIG.PSU__USE__S_AXI_GP2 {0} \
    CONFIG.PSU__USE__S_AXI_GP3 {0} \
    CONFIG.PSU__USE__S_AXI_ACP {0} \
    CONFIG.PSU__USE__S_AXI_ACE {0} \
    CONFIG.PSU__USE__IRQ0 {0} \
    CONFIG.PSU__USE__IRQ1 {0} \
    CONFIG.PSU__USE__EVENT_RPU {0} \
    CONFIG.PSU__USE__CLK0 {0} \
    CONFIG.PSU__USE__CLK1 {0} \
    CONFIG.PSU__USE__CLK2 {0} \
    CONFIG.PSU__USE__CLK3 {0} \
    CONFIG.PSU__USE__RST0 {0} \
    CONFIG.PSU__USE__RST1 {0} \
    CONFIG.PSU__USE__RST2 {0} \
    CONFIG.PSU__USE__RST3 {0} \
    CONFIG.PSU__USE__FABRIC__RST {1} \
    CONFIG.PSU__USE__DDR_INTF_REQUESTED {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} \
    CONFIG.PSU__FPGA_PL1_ENABLE {0} \
    CONFIG.PSU__FPGA_PL2_ENABLE {0} \
    CONFIG.PSU__FPGA_PL3_ENABLE {0} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__SRCSEL {IOPLL} \
    CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ $PL_CLK_MHZ \
]
set_property -dict $ps_cfg $ps

set clk_port [create_bd_port -dir O -type clk pl_clk0]
set CLK_HZ [get_property CONFIG.FREQ_HZ [get_bd_pins $ps/pl_clk0]]
if {$RTL_CLK_HZ <= 0} {
    set RTL_CLK_HZ $CLK_HZ
}
set_property CONFIG.FREQ_HZ $CLK_HZ $clk_port
connect_bd_net [get_bd_pins $ps/pl_clk0] $clk_port

set rst_port [create_bd_port -dir O -type rst resetn]
set_property CONFIG.POLARITY ACTIVE_LOW $rst_port
connect_bd_net [get_bd_pins $ps/pl_resetn0] $rst_port

save_bd_design
validate_bd_design

set wrapper [make_wrapper -files [get_files design_1.bd] -top]
add_files -norecurse $wrapper

set_property top kv260_top [current_fileset]
set_property generic "CLK_HZ=$RTL_CLK_HZ" [current_fileset]
update_compile_order -fileset sources_1

# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------
set_property STEPS.WRITE_BITSTREAM.ARGS.BIN_FILE true [get_runs impl_1]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "synth_1 failed: [get_property STATUS [get_runs synth_1]]"
}

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "impl_1 failed: [get_property STATUS [get_runs impl_1]]"
}

open_run impl_1
report_timing_summary -file [file join $outdir timing.rpt]
report_utilization    -file [file join $outdir utilization.rpt]

set wns [get_property SLACK [get_timing_paths -delay_type max]]
puts "WNS = $wns ns"
if {$wns < 0} {
    error "Timing not met: WNS $wns ns"
}

if {[catch {
    write_hw_platform -fixed -include_bit -force \
        -file [file join $outdir kv260_top.xsa]
} msg]} {
    puts "WARNING: XSA not written: $msg"
} else {
    puts "XSA      : [file join $outdir kv260_top.xsa]"
}

set run_dir [file join $projdir kv260.runs impl_1]
set bit_src [file join $run_dir kv260_top.bit]
if {[file exists $bit_src]} {
    file copy -force $bit_src [file join $outdir kv260_top.bit]
} else {
    puts "WARNING: missing build product $bit_src"
}

set bin_src ""
foreach cand {kv260_top.bin kv260_top.bit.bin} {
    set path [file join $run_dir $cand]
    if {[file exists $path]} {
        set bin_src $path
        break
    }
}
if {$bin_src ne ""} {
    file copy -force $bin_src [file join $outdir kv260_top.bit.bin]
} else {
    puts "WARNING: no boot image (.bin) produced by write_bitstream"
}

puts "BITSTREAM: [file join $outdir kv260_top.bit]"
puts "BITBIN   : [file join $outdir kv260_top.bit.bin]"
puts "CLOCK    : pl_clk0 = $PL_CLK_MHZ MHz requested, BD=$CLK_HZ, RTL=$RTL_CLK_HZ"
