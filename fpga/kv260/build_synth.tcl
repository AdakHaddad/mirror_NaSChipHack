# KV260 timing/fit check for the PL-only core (no PS/BD, no bitstream).
# For the demo bitstream use build.tcl.
# Usage: vivado -mode batch -source build_synth.tcl

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
]
read_xdc [file join $here timing_only.xdc]

synth_design -top sebatt_top -part xck26-sfvc784-2LV-c \
    -generic CLK_HZ=100000000 -generic BAUD=115200
opt_design
place_design
route_design

report_timing_summary -file [file join $outdir timing.rpt]
report_utilization    -file [file join $outdir utilization.rpt]
write_checkpoint  -force [file join $outdir sebatt_kv260_routed.dcp]
