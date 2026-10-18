# ===========================================================================
#  create_bd.tcl — Vivado block design: MicroBlaze + HMAC IP + UART
#  SeBatt project — Hackathon Deeptech 2026
#
#  Usage:
#    cd fpga/nexys_a7/
#    vivado -mode batch -source ../../fpga/create_bd.tcl
#
#  Target: Nexys A7-100T (xc7a100tcsg324-1)
# ===========================================================================

set proj_name "sebatt"
set proj_dir  [file normalize [pwd]]
set rtl_dir   [file normalize "../../rtl"]
set xdc_dir   [file normalize "."]

# --- Create project ---
create_project $proj_name $proj_dir/vivado_proj -part xc7a100tcsg324-1 -force

# --- Add RTL sources ---
add_files -norecurse [list \
    $rtl_dir/sha256_core.v \
    $rtl_dir/hmac_sha256.v \
    $rtl_dir/key_vault.v \
]
update_compile_order -fileset sources_1

# --- Create block design ---
create_bd_design "sebatt_bd"

# ===================================================================
# Step 1: MicroBlaze Subsystem
# ===================================================================
create_bd_cell -type ip -vlnv xilinx.com:ip:microblaze microblaze_0

apply_bd_automation -rule xilinx.com:bd_rule:microblaze \
    -config {
        axi_periph {Enabled}
        axi_intc {0}
        cache {None}
        clk {New Clocking Wizard}
        debug_module {Debug Only}
        ecc {None}
        local_mem {128KB}
        preset {None}
    } [get_bd_cells microblaze_0]

# Configure clk_wiz_1 for single-ended 100MHz oscillator pin (E3 on Nexys A7)
set_property -dict [list \
    CONFIG.PRIM_SOURCE {Single_ended_clock_capable_pin} \
    CONFIG.PRIM_IN_FREQ {100.000} \
    CONFIG.CLKOUT1_REQUESTED_OUT_FREQ {100.000} \
    CONFIG.RESET_TYPE {ACTIVE_LOW} \
    CONFIG.RESET_PORT {resetn} \
] [get_bd_cells clk_wiz_1]

# External clock and reset ports
create_bd_port -dir I -type clk -freq_hz 100000000 sys_clk
connect_bd_net [get_bd_ports sys_clk] [get_bd_pins clk_wiz_1/clk_in1]

create_bd_port -dir I -type rst sys_resetn
set_property CONFIG.POLARITY ACTIVE_LOW [get_bd_ports sys_resetn]
connect_bd_net [get_bd_ports sys_resetn] [get_bd_pins clk_wiz_1/resetn]
connect_bd_net [get_bd_ports sys_resetn] [get_bd_pins rst_clk_wiz_1_100M/ext_reset_in]

# ===================================================================
# Step 2: AXI UART Lite (115200 baud)
# ===================================================================
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_uartlite axi_uartlite_0
set_property -dict [list \
    CONFIG.C_BAUDRATE {115200} \
    CONFIG.C_DATA_BITS {8} \
] [get_bd_cells axi_uartlite_0]

apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
    Master {/microblaze_0 (Periph)}
    Clk_master {Auto}
    Clk_slave {Auto}
    Clk_xbar {Auto}
} [get_bd_intf_pins axi_uartlite_0/S_AXI]

# External UART pins (C4, D4 on Nexys A7)
create_bd_port -dir I uart_rxd
create_bd_port -dir O uart_txd
connect_bd_net [get_bd_ports uart_rxd] [get_bd_pins axi_uartlite_0/rx]
connect_bd_net [get_bd_pins axi_uartlite_0/tx] [get_bd_ports uart_txd]

# ===================================================================
# Step 3: SeBatt HMAC-SHA-256 IP (Custom RTL Module Reference)
# ===================================================================
create_bd_cell -type module -reference hmac_sha256 hmac_sha256_0

apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {
    Master {/microblaze_0 (Periph)}
    Clk_master {Auto}
    Clk_slave {Auto}
    Clk_xbar {Auto}
} [get_bd_intf_pins hmac_sha256_0/s_axi]

# Fixed base address for HMAC IP (matches sebatt_fw.c: 0x44A00000)
set_property offset 0x44A00000 [get_bd_addr_segs /microblaze_0/Data/SEG_hmac_sha256_0_reg0]

# ===================================================================
# Step 4: Validate, Layout, Save
# ===================================================================
regenerate_bd_layout
validate_bd_design
save_bd_design

# ===================================================================
# Step 5: Generate HDL Wrapper & Add Constraints
# ===================================================================
make_wrapper -files [get_files sebatt_bd.bd] -top
set wrapper_files [glob -nocomplain $proj_dir/vivado_proj/${proj_name}.gen/sources_1/bd/sebatt_bd/hdl/*_wrapper.v]
if {$wrapper_files eq ""} {
    set wrapper_files [glob -nocomplain $proj_dir/vivado_proj/${proj_name}.srcs/sources_1/bd/sebatt_bd/hdl/*_wrapper.v]
}
add_files -norecurse $wrapper_files
# The RTL for hmac_sha256 is also a source because it is instantiated by the
# module-reference IP in the block design.  Do not let Vivado infer that RTL
# module as the design top: its AXI-Lite pins are internal to the BD, not FPGA
# package I/O.  The wrapper exposes only sys_clk, sys_resetn, uart_rxd, and
# uart_txd.
set_property top sebatt_bd_wrapper [current_fileset]
update_compile_order -fileset sources_1

# Add Nexys A7 XDC
if {[file exists $xdc_dir/nexys_a7.xdc]} {
    add_files -fileset constrs_1 -norecurse $xdc_dir/nexys_a7.xdc
}

puts ""
puts "============================================================"
puts "  SeBatt Block Design Built Successfully!"
puts "============================================================"
puts "  Address Map:"
foreach seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces /microblaze_0/Data]] {
    set offset [get_property OFFSET $seg]
    set range  [get_property RANGE $seg]
    puts [format "    %-45s : offset=%s range=%s" $seg $offset $range]
}
puts "============================================================"
puts "  Next commands:"
puts "    launch_runs synth_1 -jobs 4"
puts "    wait_on_run synth_1"
puts "    launch_runs impl_1 -to_step write_bitstream -jobs 4"
puts "    wait_on_run impl_1"
puts "    write_hw_platform -fixed -include_bit -file sebatt.xsa"
puts "============================================================"
