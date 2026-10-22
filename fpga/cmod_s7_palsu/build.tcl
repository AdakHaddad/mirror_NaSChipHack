# Non-project build for the Cmod S7-25 counterfeit battery.
# Usage: vivado -mode batch -source build.tcl
#
# The key is not a parameter of auth_ctrl.v, so this script copies the file
# into build/ and changes the key there. rtl/ is never modified.

set here   [file normalize [file dirname [info script]]]
set root   [file normalize [file join $here ../..]]
set rtl    [file join $root rtl]
set outdir [file join $here build]
file mkdir $outdir

# --- auth_ctrl.v with a different key -------------------------------------
# Genuine key: bytes 00 01 02 ... 1F. The patch XORs each 4-byte group base
# with 0xA5, so this board signs with a key the station does not know.
set orig  [file join $rtl auth_ctrl.v]
set fh    [open $orig r]
set src   [read $fh]
close $fh

set needle {base = {idx, 2'b00};}
set first  [string first $needle $src]
if {$first < 0 || $first != [string last $needle $src]} {
    error "Expected exactly one key line '$needle' in $orig. auth_ctrl.v changed; update build.tcl."
}
set patched [string map [list $needle {base = {idx, 2'b00} ^ 8'hA5;   // COUNTERFEIT KEY}] $src]

set fake [file join $outdir auth_ctrl_palsu.v]
set fh   [open $fake w]
puts -nonewline $fh $patched
close $fh
puts "Patched key written to $fake"

# --- build -----------------------------------------------------------------
read_verilog [list \
    [file join $rtl uart_if.v] \
    [file join $rtl axil_master.v] \
    [file join $rtl sha256_core.v] \
    [file join $rtl hmac_sha256.v] \
    $fake \
    [file join $rtl i2c_master.v] \
    [file join $rtl ads1115_ctrl.v] \
    [file join $rtl sebatt_top.v] \
    [file join $here rtl cmod_s7_palsu_top.v] \
]
read_xdc [file join $here cmod_s7_palsu.xdc]

synth_design -top cmod_s7_palsu_top -part xc7s25csga225-1
opt_design
place_design
route_design

report_utilization    -file [file join $outdir utilization.rpt]
report_timing_summary -file [file join $outdir timing.rpt]
write_bitstream -force [file join $outdir cmod_s7_palsu.bit]

puts "BITSTREAM: [file join $outdir cmod_s7_palsu.bit]"
