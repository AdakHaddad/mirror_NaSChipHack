# RTL

Kode Verilog/SystemVerilog IP SeBatt. Kode pihak ketiga disimpan di rtl/third_party/ beserta lisensinya.

| File | Isi |
|---|---|
| `sha256_core.v` | Mesin kompresi SHA-256 |
| `hmac_sha256.v` | HMAC-SHA-256 + slave AXI4-Lite |
| `key_vault.v` | Penyimpan kunci tetap (tahap 1) |
| `ro_puf.v` | RO-PUF (tahap 2) |
| `i2c_master.v` | Master I2C 100 kHz untuk ADS1115 (tulis 16-bit / baca 16-bit) |
| `ads1115_ctrl.v` | FSM single-shot ADS1115: config 0xC383, AIN0, keluaran mV |
| `uart_if.v` | UART 8N1, sampling tengah bit, `BIT_CYCLES = CLK_HZ/BAUD` |
| `axil_master.v` | Master AXI4-Lite sederhana untuk akses register HMAC |
| `auth_ctrl.v` | Sampling ADS1115 periodik (`SAMPLE_INTERVAL_MS`, default 1000 ms); parser frame + CRC-8; ring buffer 64 catatan `seq(4)+V(2)+tag(32)` dengan tag HMAC per sampel; AUTH_REQ/RESULT/LOCK/UNLOCK/STATUS/READ_HIST_REQ; lock setelah 3 RESULT gagal; pesan berprefiks 0x41/0x53/0x48 |
| `sebatt_top.v` | Top-level Flow B: UART, I2C/ADS1115, auth_ctrl, LED (hijau=OK, merah=locked/error), `sw`/`src_sel` untuk pemilih sumber. Wrapper Cmod mengikat `src_sel=0` dan tidak membawa LED hijau/merah |
