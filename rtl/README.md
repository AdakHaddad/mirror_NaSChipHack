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
| `auth_ctrl.v` | Parser frame + CRC-8, alur AUTH_REQ -> ADC -> HMAC -> AUTH_RESP |
| `sebatt_top.v` | Top-level Flow B: UART, I2C/ADS1115, auth_ctrl, LED |
