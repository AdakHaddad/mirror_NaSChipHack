# KV260 — Flow B port

Status: **internal 100 MHz timing/fit check passes (20 Oct 2026)**. Carrier pin
map, PS clock setup, and `.bit.bin` boot are still TODO.

## What was checked

- Part: `xck26-sfvc784-2LV-c` (Kria KV260)
- Top: `sebatt_top`, `CLK_HZ=100_000_000`, `BAUD=115200`
- Constraint: `timing_only.xdc` (10 ns `pl_clk`; no board pins yet)

Result:

| Metric | Value |
|---|---|
| WNS | **+2.626 ns** |
| TNS / failing endpoints | 0 / 0 |
| CLB LUTs | 4 476 (3.82 %) |
| CLB registers | 5 256 (2.24 %) |
| BRAM / DSP | 0 / 0 |

The critical path is the SHA-256 `w` expansion (`cnt_reg[0] -> w_reg[*]`), the
same path that limits the Cmod S7 run. At 100 MHz on the KV260 it has 2.6 ns of
margin, so **do not raise `pl_clk0` above 100 MHz** without re-timing.

## Run the check

```bash
cd fpga/kv260
vivado -mode batch -source build_synth.tcl
```

Outputs in `build/`: `timing.rpt`, `utilization.rpt`,
`sebatt_kv260_routed.dcp`.

No bitstream is written because the carrier pin assignments are not defined.
`place_design`/`route_design` still place internal logic and report meaningful
internal timing; unconstrained I/O is ignored.

## Remaining work

1. Get the KV260 carrier pin map (PMOD for `scl`/`sda`, UART, reset, LEDs) and
   write the real XDC.
2. Decide how `clk` is driven: PS `pl_clk0` at 100 MHz, or a slower clock.
   `sebatt_top` must get the matching `CLK_HZ`.
3. Build the bitstream and verify T6/T7/T9 on the KV260.
4. Convert `.bit` to `.bit.bin` and prepare the boot flow (`bootgen`/overlay).
5. Re-check timing after pin/clock constraints are real.

## Why 100 MHz matters

At 12 MHz on the Spartan-7 the same design has >55 ns of setup margin. On the
KV260 the fabric is faster, but the SHA-256 expansion is still the limiter; the
100 MHz check is the useful data point. If the final carrier clock is 150 MHz,
pipeline the `w` expansion or use a slower PL clock.
