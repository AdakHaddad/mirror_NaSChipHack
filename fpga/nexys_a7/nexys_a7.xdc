## ============================================================================
##  nexys_a7.xdc — Constraints for Nexys A7-100T (xc7a100tcsg324-1)
##  SeBatt project — Hackathon Deeptech 2026
##
##  Only pins used in PoC: clock, reset, UART, status LEDs.
##  Reference: Digilent Nexys A7 Reference Manual
## ============================================================================

## --- Clock: 100 MHz oscillator ---
set_property -dict {PACKAGE_PIN E3 IOSTANDARD LVCMOS33} [get_ports sys_clk]
create_clock -period 10.000 -name sys_clk_pin -waveform {0.000 5.000} [get_ports sys_clk]

## --- Reset: active-low CPU_RESETN button ---
set_property -dict {PACKAGE_PIN C12 IOSTANDARD LVCMOS33} [get_ports sys_resetn]

## --- UART: USB-UART bridge (directly on board) ---
## RXD = data FROM PC TO FPGA (active input)
## TXD = data FROM FPGA TO PC (active output)
set_property -dict {PACKAGE_PIN C4 IOSTANDARD LVCMOS33} [get_ports uart_rxd]
set_property -dict {PACKAGE_PIN D4 IOSTANDARD LVCMOS33} [get_ports uart_txd]

## --- Status LEDs (active-high) ---
## LD0 = heartbeat (optional, for firmware blink)
## LD1 = HMAC busy
## LD2 = auth valid
## LD3 = auth invalid
# set_property -dict {PACKAGE_PIN H17 IOSTANDARD LVCMOS33} [get_ports {led[0]}]
# set_property -dict {PACKAGE_PIN K15 IOSTANDARD LVCMOS33} [get_ports {led[1]}]
# set_property -dict {PACKAGE_PIN J13 IOSTANDARD LVCMOS33} [get_ports {led[2]}]
# set_property -dict {PACKAGE_PIN N14 IOSTANDARD LVCMOS33} [get_ports {led[3]}]

## --- Configuration ---
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]
set_property CONFIG_MODE SPIx4 [current_design]
