# RTL

Kode Verilog IP SeBatt untuk Flow B, tanpa prosesor lunak. Belum ada kode pihak ketiga. Kalau nanti ada, kode itu disimpan di folder third_party beserta lisensinya.

| File | Isi | Status |
|---|---|---|
| sha256_core.v | Mesin kompresi SHA-256, 113 siklus per blok | Dipakai |
| hmac_sha256.v | HMAC-SHA-256 dengan slave AXI4-Lite, pesan maksimal 55 byte | Dipakai |
| axil_master.v | Master AXI4-Lite sederhana untuk register HMAC | Dipakai |
| uart_if.v | UART 8N1, sampling tengah bit | Dipakai |
| i2c_master.v | Master I2C 100 kHz, tulis dan baca 16 bit | Dipakai |
| ads1115_ctrl.v | Pembacaan single-shot ADS1115 (config 0xC383, AIN0), keluaran mV | Dipakai |
| auth_ctrl.v | Sampling periodik 1 detik, buffer 64 catatan bertanda tangan (prefiks 0x53), AUTH (0x41), READ_HIST dengan tanda tangan ringkasan (0x48), RESULT, LOCK, UNLOCK, STATUS, kunci setelah 3 kali gagal | Dipakai |
| sebatt_top.v | Top level Flow B: UART, I2C, auth_ctrl, LED, pemilih sumber (sw, src_sel) | Dipakai |
| key_vault.v | Penyimpan kunci tetap tahap 1. Kunci saat ini masih ditulis auth_ctrl | Belum dipasang |
| ro_puf.v | RO-PUF tahap 2 | Belum dipasang |

Top level per board ada di [fpga/kv260](../fpga/kv260/) dan [fpga/cmod_s7](../fpga/cmod_s7/). Testbench ada di [sim](../sim/).

## Catatan

- Mengubah file .v di folder ini, termasuk komentarnya saja, membuat preflight KV260 menganggap bitstream usang. Kumpulkan perubahan lalu bangun ulang sekali.
- Apabila ADS1115 gagal dibaca, AUTH tetap menandatangani tegangan valid terakhir dan LED merah menyala. Catatan riwayat baru tidak disimpan selama pembacaan gagal.
