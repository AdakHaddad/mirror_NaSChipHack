# Non-project build for the Cmod S7-25 Flow B demo.
# Usage: vivado -mode batch -source build.tcl

set here   [file normalize [file dirname [info script]]]
set root   [file normalize [file join $here ../..]]
set rtl    [file join $root rtl]
set outdir [file join $here build]
file mkdir $outdir

read_verilog [list \
    [file join $rtl uart_if.v] \
    [file join $rtl axil_master.v] \
    [file join $rtl sha256_core.v] \
    [file join $rtl hmac_sha256.v] \
    [file join $rtl auth_ctrl.v] \
    [file join $rtl i2c_master.v] \
    [file join $rtl ads1115_ctrl.v] \
    [file join $rtl sebatt_top.v] \
    [file join $here rtl cmod_s7_top.v] \
]
read_xdc [file join $here cmod_s7.xdc]

synth_design -top cmod_s7_top -part xc7s25csga225-1
opt_design
place_design
route_design

report_utilization    -file [file join $outdir utilization.rpt]
report_timing_summary -file [file join $outdir timing.rpt]
write_bitstream -force [file join $outdir cmod_s7_top.bit]
write_checkpoint  -force [file join $outdir cmod_s7_top_routed.dcp]

puts "BITSTREAM: [file join $outdir cmod_s7_top.bit]"
