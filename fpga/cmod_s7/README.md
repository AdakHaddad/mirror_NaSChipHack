# Flow B — Cmod S7-25 demo

Status: **periodic sampling, signed history, READ_HIST, and lock implemented;
bitstream rebuilt and timing-clean on 21 Oct 2026**. Hardware execution (T7/T9)
still pending.

**Step-by-step run and demo guide: [RUNBOOK.md](RUNBOOK.md).**

## Pin map

| Signal | FPGA pin | Board location | Notes |
|---|---|---|---|
| `clk` | `M9` | 12 MHz oscillator | `create_clock` 83.33 ns |
| `btn0` | `D2` | BTN0 | active-high; manual reset |
| `led[0]` | `E2` | LED1 | heartbeat |
| `led[1]` | `K1` | LED2 | auth busy |
| `led[2]` | `J1` | LED3 | auth OK |
| `led[3]` | `E1` | LED4 | error (frame/ADC/AXI) |
| `uart_tx` | `L12` | USB-UART (FT2232 B) | FPGA output |
| `uart_rx` | `K15` | USB-UART (FT2232 B) | FPGA input |
| `scl` | `J2` | Pmod JA pin 1 | ADS1115 SCL |
| `sda` | `H2` | Pmod JA pin 2 | ADS1115 SDA |

Pin data comes from Digilent's official
[`Cmod-S7-25-Master.xdc`](https://github.com/Digilent/digilent-xdc/blob/master/Cmod-S7-25-Master.xdc).
The part is `xc7s25csga225-1`.

## Wiring (ADS1115 module)

```
ADS1115 VDD  -> 3V3 (Cmod S7 3V3 pin)
ADS1115 GND  -> GND
ADS1115 SCL  -> JA1 (J2)
ADS1115 SDA  -> JA2 (H2)
ADS1115 ADDR -> GND        (address 0x48)
ADS1115 AIN0 -> pot wiper
Pot ends      -> 3V3 and GND
ADS1115 AIN1 -> GND        (not used)
```
The common purple ADS1115 modules already have 10 k pull-ups to VDD. Power the
module from 3.3 V, not 5 V, so the I2C lines stay within the Spartan-7 I/O
range.

## Build

```bash
cd fpga/cmod_s7
vivado -mode batch -source build.tcl
```

Outputs:

- `build/cmod_s7_top.bit`
- `build/timing.rpt`
- `build/utilization.rpt`

Verified on 21 Oct 2026: WNS **+55.646 ns** (all constraints met), 5 358 LUTs
(36.7 %), 6 022 FFs (20.6 %), 1 BUFG, 0 DSP, 0 Block RAM. The 64-record
buffer and tag memory infer as distributed RAM/registers.

## Program

```bash
cd fpga/cmod_s7
vivado -mode batch -source program.tcl
```

Or open Hardware Manager and program `build/cmod_s7_top.bit` manually. Press
BTN0 after configuration if the design does not start (the wrapper also has a
~5.5 ms power-on reset).

## Run the station side

The UART is the FT2232 channel B port; on Linux it is normally
`/dev/ttyUSB1` (channel A is JTAG). At 115 200 8N1:

```bash
source .venv/bin/activate
pip install pyserial          # once, if missing
python -m model.station --port /dev/ttyUSB1 --demo
```

The FPGA samples AIN0 every **1 s** (default `SAMPLE_INTERVAL_MS`), independently
of UART traffic. The station sends `AUTH_REQ` with a 32-byte nonce; the FPGA signs
the latest sample with `HMAC-SHA256(key, 0x41 || nonce || battery_id || voltage)`
and returns `AUTH_RESP` (battery id, voltage, HMAC). `READ_HIST_REQ` returns the
last 64 signed records plus a nonce-bound summary tag. Expected LEDs:

- LED1 (E2): ~0.7 Hz heartbeat
- LED2 (K1): on while an auth transaction is in progress
- LED3 (J1): on after a valid response
- LED4 (E1): on frame/CRC, ADC, or AXI error

The fixed demo key is `bytes(range(32))` and the battery id is `BAT\x01`, so the
station's default identity matches the FPGA.

## If the demo does not respond

1. Confirm the UART device: `ls /dev/ttyUSB*`; channel B is usually the second.
2. Check that the ADS1115 answers: run an I2C scan on the FPGA (T9) or verify
   SCL/SDA with a scope; address must be `0x48`.
3. Confirm the module is powered at 3.3 V and AIN0 is between 0 and 4.096 V.
4. Re-read the LEDs: no heartbeat means clock/reset/programming, not UART.
5. The first sample is taken after ~1 s. An auth request that arrives before
   that waits for the first sample; the station timeout is 2 s.
