# Simulasi

Testbench cocotb untuk RTL. Vektor uji dibuat oleh model referensi dan disimpan di [model/vectors/](../model/vectors/).

```bash
source .venv/bin/activate
cd sim
make sha256     # SHA-256 core
make hmac       # HMAC-SHA-256
make ads1115    # i2c_master + ads1115_ctrl (model ADS1115)
make auth       # auth_ctrl + uart_if + axil_master + hmac (4 tes)
make all        # semua target: 5 sha256 + 4 hmac + 2 ads1115 + 4 auth
```

Icarus memakai `sim_build/sim.vvp` yang sama untuk semua target, jadi `make all`
menjalankan `make clean` di antara target. Untuk target tunggal setelah target
lain, jalankan `make clean` lebih dulu.
