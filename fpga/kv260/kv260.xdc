# KV260 carrier Pmod J2 — Flow B demo
# Package pins are from the Kria K26 SOM pinout (SOM240 nets HDA11..HDA18)
# and match the KV260 master constraints / kv260_ispMipiRx pin.xdc.
#
# Pmod pin numbering is the Digilent Type 1A order on the physical connector:
#   data 1-4, 7-10; GND/3V3 on 5/6 and 11/12.

## Pmod 1: I2C SCL to ADS1115 (open-drain, external/module pull-ups)
set_property -dict { PACKAGE_PIN H12 IOSTANDARD LVCMOS33 } [get_ports { scl }]
set_property PULLUP true [get_ports { scl }]

## Pmod 2: I2C SDA to ADS1115
set_property -dict { PACKAGE_PIN E10 IOSTANDARD LVCMOS33 } [get_ports { sda }]
set_property PULLUP true [get_ports { sda }]

## Pmod 3: source select (0 = ADS1115, 1 = fixed 3000 mV). Leave open.
set_property -dict { PACKAGE_PIN D10 IOSTANDARD LVCMOS33 } [get_ports { src_sel }]
set_property PULLDOWN true [get_ports { src_sel }]

## Pmod 4: reset button, active low (press to GND)
set_property -dict { PACKAGE_PIN C11 IOSTANDARD LVCMOS33 } [get_ports { btn }]
set_property PULLUP true [get_ports { btn }]

## Pmod 7/8: UART to CP2102 (TX -> CP2102 RXD, RX <- CP2102 TXD)
set_property -dict { PACKAGE_PIN B10 IOSTANDARD LVCMOS33 } [get_ports { uart_tx }]
set_property -dict { PACKAGE_PIN E12 IOSTANDARD LVCMOS33 } [get_ports { uart_rx }]

## Pmod 9/10: green (auth OK) and red (locked/error) LEDs
set_property -dict { PACKAGE_PIN D11 IOSTANDARD LVCMOS33 } [get_ports { led_green }]
set_property -dict { PACKAGE_PIN B11 IOSTANDARD LVCMOS33 } [get_ports { led_red }]

## Configuration
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.OVERTEMPSHUTDOWN ENABLE [current_design]
