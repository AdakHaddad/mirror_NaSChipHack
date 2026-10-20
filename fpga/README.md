# FPGA Build & Run Guide (Flow A — MicroBlaze fallback)

> The main demo path is **Flow B**: pure RTL on the Cmod S7, then KV260. See
> [`cmod_s7/README.md`](cmod_s7/README.md) for the built bitstream, pin map, and
> programming steps. The KV260 100 MHz timing/fit check is in
> [`kv260/README.md`](kv260/README.md). This document describes the older Flow A
> MicroBlaze fallback.

## Prerequisites

- Vivado 2023.2+ (or 2024.x) with Artix-7 support
- Nexys A7-100T board + USB cable
- Python 3.10+ with `pyserial`

## Step 1: Package HMAC IP

```bash
cd fpga/
vivado -mode batch -source package_ip.tcl
```

This creates `fpga/ip_repo/hmac_sha256_1.0/` with the packaged IP core.

## Step 2: Create Block Design

```bash
cd fpga/nexys_a7/
vivado -mode batch -source ../../fpga/create_bd.tcl
```

Or in Vivado GUI:
1. Open Vivado → Create Project → select `xc7a100tcsg324-1`
2. Settings → IP → Repository → Add `fpga/ip_repo/`
3. Source TCL: `source ../../fpga/create_bd.tcl`

## Step 3: Synthesize & Generate Bitstream

In Vivado:
```tcl
launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
```

## Step 4: Export Hardware

```tcl
write_hw_platform -fixed -include_bit -file sebatt_bd_wrapper.xsa
```

## Step 5: Build Firmware (Vitis)

1. Open Vitis → Create Platform Project from `.xsa`
2. Create Application Project → Empty C Application
3. Add `fpga/fw/sebatt_fw.c`
4. Build → Program FPGA → Run

## Step 6: Run Station Emulator

```bash
# Install pyserial
pip install pyserial

# Auto-detect port and authenticate
python -m model.station

# Explicit port
python -m model.station --port /dev/ttyUSB1

# Run demo sequence
python -m model.station --demo

# Throughput benchmark
python -m model.station --benchmark --count 1000

# Interactive mode
python -m model.station --interactive

# Offline test (no hardware needed)
python -m model.station --offline
```

## Address Map

| Peripheral | Base Address | Size |
|---|---|---|
| BRAM (code+data) | 0x00000000 | 128 KB |
| AXI UART Lite | 0x40600000 | 64 KB |
| HMAC-SHA-256 IP | 0x44A00000 | 4 KB |

## HMAC IP Registers

| Offset | Name | R/W | Description |
|---|---|---|---|
| 0x00 | CTRL | R/W | [0]=start(auto-clear) [1]=init(auto-clear) |
| 0x04 | STATUS | RO | [0]=done [1]=busy |
| 0x08 | MSG_LEN | R/W | Message length in bytes (default 38) |
| 0x10–0x2C | KEY[0..7] | R/W | 256-bit key (big-endian words) |
| 0x30–0x6C | MSG[0..15] | R/W | Message block (up to 64 bytes) |
| 0x70–0x8C | HASH[0..7] | RO | 256-bit HMAC result |

## Porting to Different Board

1. Change part number in `create_bd.tcl` (`-part` argument)
2. Create new `.xdc` with correct pin assignments for:
   - 100 MHz clock input
   - Active-low reset button
   - UART RX/TX pins
3. Rebuild
