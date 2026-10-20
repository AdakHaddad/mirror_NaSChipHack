# Timing-only constraint for the KV260 port.
# The real carrier pin map (PMOD, UART, reset) is still TODO; this file lets
# Vivado check the internal 100 MHz timing before the board is available.
create_clock -period 10.000 -name pl_clk [get_ports { clk }]
