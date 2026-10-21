# Simulasi

Testbench cocotb untuk RTL. Vektor uji dibuat oleh model referensi dan disimpan di [model/vectors/](../model/vectors/).

```bash
source .venv/bin/activate
cd sim
make sha256     # SHA-256 core
make hmac       # HMAC-SHA-256
make ads1115    # i2c_master + ads1115_ctrl (model ADS1115)
make auth       # auth_ctrl + uart_if + axil_master + hmac (9 tes)
make all        # semua target: 5 sha256 + 4 hmac + 2 ads1115 + 13 auth
```

Tes auth juga memverifikasi sampling periodik (`adc_start` setiap `SAMPLE_CYCLES`),
isi READ_HIST_RESP terhadap HMAC Python (64 catatan + tag ringkasan), lock setelah
tiga RESULT gagal, serta LOCK/UNLOCK/STATUS/CHIP_LOCKED. TB memakai
`BAUD=1_000_000` dan `SAMPLE_CYCLES=12000` (1 ms) hanya untuk mempercepat
simulasi; hardware memakai 115200 baud dan default 1000 ms (1 detik).

Icarus memakai `sim_build/sim.vvp` yang sama untuk semua target, jadi `make all`
menjalankan `make clean` di antara target. Untuk target tunggal setelah target
lain, jalankan `make clean` lebih dulu.
