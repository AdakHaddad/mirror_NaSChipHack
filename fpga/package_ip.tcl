# ===========================================================================
#  package_ip.tcl — Package hmac_sha256 as AXI4-Lite IP for Vivado
#  SeBatt project
#
#  Usage (run in Vivado):
#    cd <repo_root>/fpga
#    source package_ip.tcl
#
#  Creates ip_repo/hmac_sha256_1.0/ with component.xml
#  Then add ip_repo/ to block design IP catalog.
# ===========================================================================

set ip_name    "hmac_sha256"
set ip_version "1.0"
set ip_vendor  "sebatt"
set ip_library "ip"
set rtl_dir    [file normalize "../rtl"]
set ip_dir     [file normalize "./ip_repo/${ip_name}_${ip_version}"]

# Create a temporary project for packaging
set tmp_proj [file normalize "./tmp_ip_pkg"]
create_project -force tmp_ip_pkg $tmp_proj -part xc7a100tcsg324-1

# Add RTL sources
add_files -norecurse [list \
    $rtl_dir/sha256_core.v \
    $rtl_dir/hmac_sha256.v \
]
set_property top hmac_sha256 [current_fileset]
update_compile_order -fileset sources_1

# Package IP
ipx::package_project -root_dir $ip_dir -vendor $ip_vendor -library $ip_library \
    -taxonomy /UserIP -import_files -force

# Set identification
set_property vendor        $ip_vendor  [ipx::current_core]
set_property library       $ip_library [ipx::current_core]
set_property name          $ip_name    [ipx::current_core]
set_property version       $ip_version [ipx::current_core]
set_property display_name  "SeBatt HMAC-SHA-256" [ipx::current_core]
set_property description   "HMAC-SHA-256 engine with AXI4-Lite slave interface" [ipx::current_core]
set_property company_url   "https://github.com" [ipx::current_core]

# Identify AXI4-Lite slave interface
# Vivado should auto-detect from port naming convention (s_axi_*)
ipx::infer_bus_interfaces xilinx.com:interface:aximm_rtl:1.0 [ipx::current_core]

# Set address space parameters
set axi_intf [ipx::get_bus_interfaces S_AXI -of_objects [ipx::current_core]]
if {$axi_intf ne ""} {
    # Memory map
    set mem_map [ipx::add_memory_map S_AXI [ipx::current_core]]
    set addr_block [ipx::add_address_block Reg $mem_map]
    set_property range 256 $addr_block
    set_property width 32 $addr_block

    # Associate memory map with interface
    set_property slave_memory_map_ref S_AXI $axi_intf
}

# Clock and reset associations
ipx::associate_bus_interfaces -busif S_AXI -clock s_axi_aclk [ipx::current_core]

# Validate and save
ipx::check_integrity [ipx::current_core]
ipx::save_core [ipx::current_core]

# Cleanup temp project
close_project
file delete -force $tmp_proj

puts "============================================"
puts "IP packaged to: $ip_dir"
puts "Add to Vivado: Settings → IP → Repository → Add $ip_dir/.."
puts "============================================"
