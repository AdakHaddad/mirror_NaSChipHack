#!/usr/bin/env bash
# Load the SeBatt bitstream on a running Kria KV260 (run on the board).
# Usage:
#   scp fpga/kv260/build/kv260_top.bit.bin fpga/kv260/demo/load.sh kria@<ip>:~/
#   ssh kria@<ip>
#   chmod +x load.sh
#   sudo ./load.sh ./kv260_top.bit.bin
set -euo pipefail

BITBIN="${1:-$(cd "$(dirname "$0")" && pwd)/../build/kv260_top.bit.bin}"
BITBIN="$(readlink -f "$BITBIN")"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: run as root (sudo ./load.sh <bit.bin>)" >&2
    exit 1
fi
if [[ ! -f "$BITBIN" ]]; then
    echo "ERROR: bitstream not found: $BITBIN" >&2
    exit 1
fi

mount -t debugfs none /sys/kernel/debug 2>/dev/null || true

clock_state() {
    local base=/sys/kernel/debug/clk/pl0_ref
    if [[ -r "$base/clk_rate" && -r "$base/clk_enable_count" ]]; then
        printf 'pl0_ref: rate=%s enable_count=%s\n' \
            "$(cat "$base/clk_rate")" "$(cat "$base/clk_enable_count")"
    else
        echo "pl0_ref: not exposed by this kernel (check clk_summary manually)"
    fi
}

echo "== before =="
clock_state

if command -v xmutil >/dev/null 2>&1; then
    xmutil unloadapp >/dev/null 2>&1 || true
fi

if ! command -v fpgautil >/dev/null 2>&1; then
    echo "ERROR: fpgautil not found. Install dfx-mgr, or use JTAG (program.tcl)." >&2
    exit 1
fi

echo "== loading $BITBIN =="
fpgautil -b "$BITBIN"
sleep 1

echo "== after =="
clock_state
echo "== dmesg (tail) =="
dmesg | tail -n 20

rate="$(cat /sys/kernel/debug/clk/pl0_ref/clk_rate 2>/dev/null || true)"
count="$(cat /sys/kernel/debug/clk/pl0_ref/clk_enable_count 2>/dev/null || true)"
if [[ -n "$rate" && "$rate" != "99999001" && "$rate" != "100000000" ]]; then
    echo
    echo "WARNING: pl0_ref is $rate Hz, not ~100 MHz. UART/I2C will be wrong."
    echo "         See RUNBOOK.md section 5 (clock / BOOT.BIN fallback)."
fi
if [[ "$count" == "0" ]]; then
    echo
    echo "WARNING: pl0_ref is gated (enable_count=0)."
    echo "         Add clk_ignore_unused to the kernel cmdline and reboot,"
    echo "         then load the bitstream again (RUNBOOK.md section 5)."
fi

echo
echo "Next: on the host, from the repo root:"
echo "  source .venv/bin/activate"
echo "  python -m model.station --port /dev/ttyUSB0"
echo "or run fpga/kv260/demo/run_station.sh --demo"
