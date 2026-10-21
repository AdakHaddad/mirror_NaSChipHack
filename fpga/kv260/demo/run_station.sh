#!/usr/bin/env bash
# Run the SeBatt station emulator against the KV260 UART (run on the laptop).
# Usage:
#   fpga/kv260/demo/run_station.sh                 # single auth
#   fpga/kv260/demo/run_station.sh --demo          # 8-transaction demo
#   fpga/kv260/demo/run_station.sh --interactive   # manual demo
#   fpga/kv260/demo/run_station.sh --port /dev/ttyUSB1 --history
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT" || exit 1

if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    echo "ERROR: python3 not found" >&2
    exit 1
fi

exec "$PY" -m model.station "$@"
