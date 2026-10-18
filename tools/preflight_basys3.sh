#!/usr/bin/env bash
# Pre-flight sesi hardware Basys 3 — jalankan sebelum duduk di meja.
# Usage: bash tools/preflight_basys3.sh
set -u
cd "$(dirname "$0")/.."

pass=0; warn=0; fail=0
ok()    { echo "  [OK]   $1"; pass=$((pass+1)); }
warnp() { echo "  [WARN] $1"; warn=$((warn+1)); }
failp() { echo "  [FAIL] $1"; fail=$((fail+1)); }

echo "== Board =="
if lsusb 2>/dev/null | grep -qiE "ftdi|digilent"; then
  ok "FTDI/Digilent terdeteksi di lsusb"
else
  warnp "Board belum terdeteksi — colok kabel micro-USB ke port PROG, tunggu 5 detik"
fi
if compgen -G "/dev/ttyUSB*" >/dev/null; then
  ok "Port serial: $(ls /dev/ttyUSB* | tr '\n' ' ')(UART FT2232 biasanya ttyUSB1)"
else
  warnp "Belum ada /dev/ttyUSB*"
fi
if id -nG 2>/dev/null | grep -qw dialout; then
  ok "User ada di grup dialout"
else
  warnp "User TIDAK di grup dialout (sudo usermod -aG dialout \$USER, lalu login ulang)"
fi

echo "== Artefak Flow A =="
while IFS='|' read -r p d; do
  if [ -f "$p" ]; then ok "$d: $p"; else failp "$d HILANG: $p"; fi
done <<'EOF'
fpga/ws/app_component/_ide/bitstream/sebatt_bd_wrapperbasys3.bit|bitstream
fpga/ws/app_component/build/app_component.elf|ELF firmware
fpga/ws/platform_basys3/hw/sebatt_bd_wrapperbasys3.xsa|XSA platform
EOF

echo "== Alat =="
if [ -x "$HOME/Xilinx/HWSRVR/2024.1/bin/hw_server" ]; then
  ok "hw_server 2024.1 (fix halt): $HOME/Xilinx/HWSRVR/2024.1/bin/hw_server"
else
  failp "hw_server 2024.1 tidak ditemukan"
fi
if command -v vivado >/dev/null; then ok "vivado: $(command -v vivado)"; else warnp "vivado tidak di PATH"; fi
if [ -x .venv/bin/python ]; then
  if .venv/bin/python -c "import serial, cocotb" 2>/dev/null; then
    ok ".venv: pyserial + cocotb siap (pakai: source .venv/bin/activate)"
  else
    warnp ".venv ada tapi pyserial/cocotb belum lengkap"
  fi
else
  warnp ".venv tidak ada"
fi
if python3 -c "import serial" 2>/dev/null; then ok "python3 sistem: pyserial"; else warnp "python3 sistem tanpa pyserial — pakai .venv"; fi
if command -v iverilog >/dev/null; then ok "iverilog (sim RTL)"; else warnp "iverilog tidak ada"; fi

echo
echo "Ringkasan: $pass OK, $warn WARN, $fail FAIL"
[ "$fail" -eq 0 ] || exit 1
