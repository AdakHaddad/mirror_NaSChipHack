# Cmod S7-25 Rev. B — counterfeit battery constraints
# Pin names are from Digilent Cmod-S7-25-Master.xdc.

## 12 MHz system clock
set_property -dict { PACKAGE_PIN M9 IOSTANDARD LVCMOS33 } [get_ports { clk }]
create_clock -add -name sys_clk_pin -period 83.33 -waveform {0 41.66 } [get_ports { clk }]

## Push button (active-high; wrapper uses it as reset)
set_property -dict { PACKAGE_PIN D2 IOSTANDARD LVCMOS33 } [get_ports { btn0 }]

## 4 LEDs (active-high). led[2] = last command accepted, led[3] = rejected or locked
set_property -dict { PACKAGE_PIN E2 IOSTANDARD LVCMOS33 } [get_ports { led[0] }]
set_property -dict { PACKAGE_PIN K1 IOSTANDARD LVCMOS33 } [get_ports { led[1] }]
set_property -dict { PACKAGE_PIN J1 IOSTANDARD LVCMOS33 } [get_ports { led[2] }]
set_property -dict { PACKAGE_PIN E1 IOSTANDARD LVCMOS33 } [get_ports { led[3] }]

## UART on Pmod JA, same positions as KV260 Pmod J2 (7 = TX, 8 = RX, 11 = GND)
set_property -dict { PACKAGE_PIN H3 IOSTANDARD LVCMOS33 } [get_ports { uart_tx }]
set_property -dict { PACKAGE_PIN H1 IOSTANDARD LVCMOS33 PULLUP true } [get_ports { uart_rx }]

## I2C pins unused (no ADC). Pulled up so the open-drain lines idle high.
set_property -dict { PACKAGE_PIN J2 IOSTANDARD LVCMOS33 PULLUP true } [get_ports { scl }]
set_property -dict { PACKAGE_PIN H2 IOSTANDARD LVCMOS33 PULLUP true } [get_ports { sda }]

## Configuration
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
