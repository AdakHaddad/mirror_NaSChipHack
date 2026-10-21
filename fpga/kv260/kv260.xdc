# KV260 carrier Pmod J2 — Flow B demo
# Package pins are from the Kria K26 SOM pinout (SOM240 nets HDA11..HDA18)
# and match the KV260 master constraints / kv260_ispMipiRx pin.xdc.
#
# Wiring uses the Digilent 12-pin numbering:
#   signals 1-4 and 7-10, GND on 5/11, 3V3 on 6/12.
#   Pmod 1 H12 scl         Pmod 7  B10 uart_tx
#   Pmod 2 E10 sda         Pmod 8  E12 uart_rx
#   Pmod 3 D10 src_sel     Pmod 9  D11 led_green
#   Pmod 4 C11 led_hb      Pmod 10 B11 led_red
# (The KV260 schematic labels the raw header positions 1,3,5,7 / 2,4,6,8;
#  those are not the Digilent pin numbers.)

## Pmod 1: I2C SCL to ADS1115 (open-drain, external/module pull-ups)
set_property -dict { PACKAGE_PIN H12 IOSTANDARD LVCMOS33 } [get_ports { scl }]
set_property PULLUP true [get_ports { scl }]

## Pmod 2: I2C SDA to ADS1115
set_property -dict { PACKAGE_PIN E10 IOSTANDARD LVCMOS33 } [get_ports { sda }]
set_property PULLUP true [get_ports { sda }]

## Pmod 3: source select (0 = ADS1115, 1 = fixed 3000 mV). Leave open.
set_property -dict { PACKAGE_PIN D10 IOSTANDARD LVCMOS33 } [get_ports { src_sel }]
set_property PULLDOWN true [get_ports { src_sel }]

## Pmod 4: heartbeat LED (blinks while the PL clock runs)
set_property -dict { PACKAGE_PIN C11 IOSTANDARD LVCMOS33 } [get_ports { led_hb }]

## Pmod 7/8: UART to CP2102 (TX -> CP2102 RXD, RX <- CP2102 TXD)
set_property -dict { PACKAGE_PIN B10 IOSTANDARD LVCMOS33 } [get_ports { uart_tx }]
set_property -dict { PACKAGE_PIN E12 IOSTANDARD LVCMOS33 } [get_ports { uart_rx }]
# Idle-high when the CP2102 is unplugged, so noise does not reach the parser.
set_property PULLUP true [get_ports { uart_rx }]

## Pmod 9/10: green (auth OK) and red (locked/error) LEDs
set_property -dict { PACKAGE_PIN D11 IOSTANDARD LVCMOS33 } [get_ports { led_green }]
set_property -dict { PACKAGE_PIN B11 IOSTANDARD LVCMOS33 } [get_ports { led_red }]

## Configuration
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.OVERTEMPSHUTDOWN ENABLE [current_design]
