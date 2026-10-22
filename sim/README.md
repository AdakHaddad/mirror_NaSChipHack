# Simulasi

Testbench cocotb untuk RTL. Vektor uji dibuat oleh model referensi dan disimpan di [model/vectors/](../model/vectors/).

```bash
source .venv/bin/activate
cd sim
make sha256     # SHA-256 core
make hmac       # HMAC-SHA-256
make ads1115    # i2c_master + ads1115_ctrl (model ADS1115)
make auth       # auth_ctrl + uart_if + axil_master + hmac (9 tes)
make all        # semua target: 5 sha256 + 4 hmac + 4 ads1115 + 13 auth
```

Tes auth juga memverifikasi sampling periodik (`adc_start` setiap `SAMPLE_CYCLES`),
isi READ_HIST_RESP terhadap HMAC Python (64 catatan + tag ringkasan), lock setelah
tiga RESULT gagal, serta LOCK/UNLOCK/STATUS/CHIP_LOCKED. TB memakai
`BAUD=1_000_000` dan `SAMPLE_CYCLES=12000` (1 ms) hanya untuk mempercepat
simulasi; hardware memakai 115200 baud dan default 1000 ms (1 detik).

Icarus memakai `sim_build/sim.vvp` yang sama untuk semua target, jadi `make all`
menjalankan `make clean` di antara target. Untuk target tunggal setelah target
lain, jalankan `make clean` lebih dulu.

## Smoke test tanpa cocotb

`tb_smoke.v` mengirim satu frame STATUS lewat UART dan harus mencetak
`SMOKE PASS`. Tidak butuh Python:

```bash
cd sim
iverilog -g2012 -o /tmp/smoke.vvp -s tb_smoke \
  ../rtl/sha256_core.v ../rtl/hmac_sha256.v ../rtl/axil_master.v \
  ../rtl/uart_if.v ../rtl/i2c_master.v ../rtl/ads1115_ctrl.v \
  ../rtl/auth_ctrl.v ../rtl/sebatt_top.v tb_smoke.v
vvp /tmp/smoke.vvp
```
