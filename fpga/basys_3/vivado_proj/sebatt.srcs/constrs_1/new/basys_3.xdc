## ============================================================================
## basys3.xdc - Constraints for Digilent Basys 3 (xc7a35tcpg236-1)
## SeBatt project - Hackathon Deeptech 2026
##
## Used in PoC: clock, reset, UART, status LEDs.
## ============================================================================

## --- Clock: 100 MHz oscillator ---
set_property -dict {PACKAGE_PIN W5 IOSTANDARD LVCMOS33} [get_ports sys_clk]
create_clock -period 10.000 -name sys_clk_pin -waveform {0.000 5.000} [get_ports sys_clk]

## --- Reset: active-low CPU_RESETN button ---
set_property -dict {PACKAGE_PIN U18 IOSTANDARD LVCMOS33} [get_ports sys_resetn]

## --- UART: USB-UART bridge ---
## RXD = data FROM PC TO FPGA
## TXD = data FROM FPGA TO PC
set_property -dict {PACKAGE_PIN B18 IOSTANDARD LVCMOS33} [get_ports uart_rxd]
set_property -dict {PACKAGE_PIN A18 IOSTANDARD LVCMOS33} [get_ports uart_txd]


## --- Status LEDs (active-high) ---
## LD0 = heartbeat
## LD1 = HMAC busy
## LD2 = auth valid
## LD3 = auth invalid
# set_property -dict {PACKAGE_PIN U16 IOSTANDARD LVCMOS33} [get_ports {led[0]}]
# set_property -dict {PACKAGE_PIN E19 IOSTANDARD LVCMOS33} [get_ports {led[1]}]
# set_property -dict {PACKAGE_PIN U19 IOSTANDARD LVCMOS33} [get_ports {led[2]}]
# set_property -dict {PACKAGE_PIN V19 IOSTANDARD LVCMOS33} [get_ports {led[3]}]

## --- Configuration ---
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]
set_property CONFIG_MODE SPIx1 [current_design]