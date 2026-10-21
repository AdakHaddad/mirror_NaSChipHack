#!/usr/bin/env bash
# Host-side preflight for the KV260 demo.
# Usage:
#   fpga/kv260/demo/preflight.sh          # artifacts, timing, pin map, Python tests
#   fpga/kv260/demo/preflight.sh --full   # also run the cocotb RTL suite (~2.5 min)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT" || exit 1

FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

fail=0
ok()  { printf '  OK   %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*"; fail=1; }
warn() { printf '  WARN %s\n' "$*"; }

echo "== KV260 demo preflight =="

echo "-- artifacts"
for f in \
    fpga/kv260/build/kv260_top.bit \
    fpga/kv260/build/kv260_top.bit.bin \
    fpga/kv260/build/timing.rpt \
    fpga/kv260/build/utilization.rpt \
    fpga/kv260/kv260.xdc \
    fpga/kv260/kv260_top.v
do
    if [[ -s "$f" ]]; then
        ok "$f ($(du -h "$f" | cut -f1))"
    else
        bad "missing or empty: $f"
    fi
done

echo "-- timing"
if grep -q "All user specified timing constraints are met" fpga/kv260/build/timing.rpt 2>/dev/null; then
    ok "timing constraints met"
else
    bad "timing.rpt does not report met constraints"
fi
wns="$(grep -A4 'WNS(ns)' fpga/kv260/build/timing.rpt 2>/dev/null | grep -E '^\s+-?[0-9]+\.[0-9]+' | head -1 | awk '{print $1}')"
if [[ -n "$wns" ]]; then
    if awk "BEGIN{exit !($wns >= 0)}"; then
        ok "WNS = $wns ns"
    else
        bad "WNS = $wns ns"
    fi
fi

echo "-- XDC package pins"
check_pin() {
    local pin="$1" port="$2"
    if grep -qE "PACKAGE_PIN[[:space:]]+${pin}[[:space:]]+IOSTANDARD[[:space:]]+LVCMOS33.*get_ports[[:space:]]*\{[[:space:]]*${port}[[:space:]]*\}" fpga/kv260/kv260.xdc; then
        ok "$port -> $pin"
    else
        bad "$port -> $pin not found in kv260.xdc"
    fi
}
check_pin H12 scl
check_pin E10 sda
check_pin D10 src_sel
check_pin C11 led_hb
check_pin B10 uart_tx
check_pin E12 uart_rx
check_pin D11 led_green
check_pin B11 led_red

echo "-- implemented I/O (routed design)"
io_rpt=fpga/kv260/build/project/kv260.runs/impl_1/kv260_top_io_placed.rpt
if [[ -f "$io_rpt" ]]; then
    for pair in "H12 scl" "E10 sda" "D10 src_sel" "C11 led_hb" \
                "B10 uart_tx" "E12 uart_rx" "D11 led_green" "B11 led_red"
    do
        read -r pin port <<< "$pair"
        if grep -qE "^\| ${pin} +\| ${port} +\|.*\| +45 \|" "$io_rpt"; then
            ok "$port on $pin, bank 45"
        else
            bad "$port on $pin not found in $io_rpt"
        fi
    done
else
    warn "routed I/O report not found (clean tree); rerun build.tcl for the pin check"
fi

echo "-- Python model"
if [[ -x .venv/bin/python ]]; then
    if .venv/bin/python -m pytest model/ -q >/tmp/sebatt_pytest.log 2>&1; then
        ok "$(tail -1 /tmp/sebatt_pytest.log)"
    else
        bad "model tests failed (see /tmp/sebatt_pytest.log)"
    fi
else
    warn ".venv/bin/python not found; skipping model tests"
fi

if [[ "$FULL" -eq 1 ]]; then
    echo "-- RTL cocotb suite"
    if PATH="$ROOT/.venv/bin:$PATH" make -C sim all >/tmp/sebatt_cocotb.log 2>&1; then
        ok "cocotb 23/23 (sha256 5, hmac 4, ads1115 2, auth 12)"
    else
        bad "cocotb suite failed (see /tmp/sebatt_cocotb.log)"
    fi
fi

echo "-- host USB-serial"
if [[ -x .venv/bin/python ]]; then
    .venv/bin/python - <<'PY'
try:
    from serial.tools import list_ports
except Exception as exc:
    print(f"  WARN pyserial unavailable: {exc}")
else:
    ports = [p for p in list_ports.comports() if not p.device.startswith("/dev/ttyS")]
    if not ports:
        print("  WARN no USB-serial adapter found (connect CP2102)")
    for p in ports:
        print(f"  OK   {p.device}: {p.description}")
PY
else
    warn "cannot enumerate serial ports without .venv"
fi

echo
if [[ "$fail" -eq 0 ]]; then
    echo "GO: host preflight passed."
    echo "Next: copy build/kv260_top.bit.bin and demo/load.sh to the KV260, run load.sh,"
    echo "      then run demo/run_station.sh --demo"
else
    echo "NO-GO: fix the failures above before demo day."
fi
exit "$fail"
