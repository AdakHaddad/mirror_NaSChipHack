# KV260 — Flow B demo

Status: **bitstream built and timing clean; Pmod pin map, PS clock design and
`.bit.bin` are in place (21 Oct 2026)**. Physical T6/T7/T9/T10 on the KV260 are
still pending.

- Part: `xck26-sfvc784-2LV-c`
- Top: `kv260_top` → `sebatt_top` + `design_1` PS block design
- Clock: PS `pl_clk0`, 100 MHz requested (actual 99.999001 MHz)
- UART: 115200 8N1 on Pmod J2 pins 7/8 via CP2102
- Sampling: 1 s (`SAMPLE_INTERVAL_MS=1000`)
- Pin map: `kv260.xdc`
- Artifacts: `build/kv260_top.bit`, `build/kv260_top.bit.bin`,
  `build/timing.rpt`, `build/utilization.rpt`
- Runbook: `RUNBOOK.md`

## Architecture

The PS is used only as the clock/reset source. `design_1` instantiates
`zynq_ultra_ps_e` with all AXI, interrupt and PL1–PL3 ports disabled; `pl_clk0`
comes from the IOPLL at 100 MHz and `pl_resetn0` is exported. No PL oscillator
is available on the KV260, so the PS is mandatory. The processor never touches
the sample path; ADC, HMAC, history and UART stay in the PL.

`kv260_top` synchronises the active-low reset button and instantiates
`sebatt_top` with `CLK_HZ` set to the actual PS clock and 1 s sampling.

## Pin map (Pmod J2, Digilent Type 1A numbering)

| Pmod | Package | Signal | Notes |
|---|---|---|---|
| 1 | H12 | `scl` | ADS1115 SCL, pull-up (module + internal) |
| 2 | E10 | `sda` | ADS1115 SDA, pull-up (module + internal) |
| 3 | D10 | `src_sel` | 0 = ADS1115, 1 = fixed 3000 mV; internal pulldown |
| 4 | C11 | `btn` | reset to GND, internal pull-up |
| 5, 11 | — | GND | ADS1115/CP2102/LED/button ground |
| 6, 12 | — | 3V3 | ADS1115 VDD and pot top |
| 7 | B10 | `uart_tx` | to CP2102 RXD |
| 8 | E12 | `uart_rx` | from CP2102 TXD |
| 9 | D11 | `led_green` | auth OK (`led[2] & ~led[3]`) |
| 10 | B11 | `led_red` | locked/error (`led[3]`) |

Package pins match the Kria K26 SOM pinout / KV260 master constraints
(`kv260_ispMipiRx` `pin.xdc`, Kria-PYNQ `base.xdc`), bank 45 at 3.3 V.

## Build

```bash
cd fpga/kv260
vivado -mode batch -source build.tcl
```

Full build takes roughly 20–25 minutes: PS block design + wrapper, synthesis,
place/route, bitstream, `.bin`, XSA. Outputs are copied to `build/`. The script
stops if WNS is negative or the implementation fails.

For a quick pre-pin timing/fit check only:

```bash
vivado -mode batch -source build_synth.tcl
```

That older flow uses `timing_only.xdc`, writes no bitstream, and overwrites
`build/timing.rpt` / `build/utilization.rpt`; rerun `build.tcl` for the final
reports.

## Result (21 Oct 2026, full build)

| Metric | Value |
|---|---|
| WNS | **+0.687 ns** |
| WHS | **+0.012 ns** |
| TNS / failing endpoints | 0 / 0 |
| CLB LUTs | 5 611 (4.79 %) |
| CLB registers | 6 130 (2.62 %) |
| BRAM / DSP | 0 / 0 |
| Clock | `clk_pl_0`, 10.000 ns, 100.000 MHz |

This build includes the fix for the multi-driven `sg_req*` nets: the
sample-to-signer request is now generated once in the command/signer block,
gated by `sample_busy && adc_valid`, instead of being driven from both the
sampling and signer blocks. The resulting bitstream has no tied-off signer
request.

The critical path is still the SHA-256 `w` expansion. **Do not raise `pl_clk0`
above 100 MHz** without pipelining it and re-running timing.

## Program

Primary: boot Kria Ubuntu, check the PL clock, then

```bash
sudo fpgautil -b kv260_top.bit.bin
```

JTAG fallback (PS already booted):

```bash
vivado -mode batch -source program.tcl
```

The full wiring, clock check (`pl0_ref`), demo commands and troubleshooting are
in `RUNBOOK.md`.

## Remaining work

1. Physical T6/T7/T9/T10 on the KV260 (same host commands as Cmod S7).
2. Confirm `pl0_ref` is enabled at 99.999 MHz by the stock Kria boot firmware.
   If it runs at the RPLL default (96.97 MHz) or is gated, fix the PS clock
   before testing (see RUNBOOK §5); the UART baud assumes 100 MHz.
3. If a higher PL clock is ever needed, pipeline the `w` expansion first.
