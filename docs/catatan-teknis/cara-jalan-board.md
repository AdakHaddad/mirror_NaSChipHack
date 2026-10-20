# Cara Menjalankan Demo per Board

Satu arsitektur untuk semua board: **RTL murni + UART + laptop stasiun Python**. Board latihan sekarang **Cmod S7** (tim); Basys 3 / Nexys A7 tidak diandalkan lagi (dan tidak dibawa ke hackathon); KV260 dari panitia adalah panggung hari-H. Karena sesi hardware hanya hari ini, semua risiko yang bisa diuji tanpa KV260 harus habis di Cmod S7. **ADC pindah dari MCP3202 (SPI) ke ADS1115 (I2C) per 19 Okt** karena tidak ada modul SPI ADC. Dibaca bersama [alur-demo.md](alur-demo.md) dan [council-18-okt.md](council-18-okt.md). **Rencana tes siap-jalan: [rencana-tes-basys3.md](rencana-tes-basys3.md)** (semua cek manual, ditulis langkah per langkah; bagian Basys 3 tetap dipakai sebagai referensi pin).

## 1. Arsitektur yang Sama di Semua Board

```
sumber tegangan → FPGA CHIP SeBatt → adaptor serial → laptop BMS curang → laptop stasiun
(ADS1115 I2C,     ├ sumber sampel      (CP2102 di        (laptop kedua)
 switch/XADC/     ├ auth_ctrl          KV260; FTDI
 script di RTL)   │  (nomor urut,       onboard di
                  │   buffer riwayat,   Cmod S7/Basys)
                  │   lock)
                  ├ hmac_sha256
                  ├ LED status (opsional)
                  └ uart_if (pengganti CAN)
```

- FPGA = chip SeBatt. Laptop stasiun = emulator Python (verifikasi HMAC, urutan, nonce).
- Laptop kedua = BMS curang, duduk di antara board dan stasiun.
- Tidak ada prosesor lunak, tidak ada PYNQ, tidak ada IP vendor.

## 2. Flow A vs Flow B — Dua Level Demo

| | Flow A: autentikasi (Ada sekarang) | Flow B: riwayat (Target hari-H) |
|---|---|---|
| Perangkat | MicroBlaze V + firmware C di `fpga/ws` | RTL murni di KV260 |
| Isi | `AUTH_REQ` (nonce) → HMAC(nonce‖ID‖3700 mV tetap) → `AUTH_RESP`, lock/unlock, replay | Chip sampel tegangan berkala → seq++ → HMAC per catatan → buffer 64 → stasiun minta riwayat + nonce → verifikasi semua |
| Adegan | Valid, lock, replay | Valid, **catatan dihapus → DITOLAK**, **angka diubah → DITOLAK** |
| Alat | Vitis 2024.2 + hw_server 2024.1 (fix halt) | Vivado + Python |

Yang belum ada untuk Flow B (gap list):

- RTL: seq counter + buffer riwayat 64 + lock di dalam `auth_ctrl`. Sumber sampel ADS1115/I2C, `i2c_master` + `ads1115_ctrl`, `uart_if`, `auth_ctrl`, dan `sebatt_top` sudah ada (20 Okt).
- Protokol: command riwayat (`READ_HIST` + layout record seq/V/HMAC) — **belum ada di `model/protocol.py`**; ini kontrak Budi–Muqtada yang harus dibekukan lebih dulu.
- Stasiun: verifikasi riwayat + dashboard (kartu kesehatan, grafik).
- Video cadangan Flow A/B direkam di sesi latihan (wajib, karena tidak ada board kedua di hari-H).

Flow A tidak akan diporting ke KV260 (proposal: tanpa prosesor lunak). Nilainya: validasi hardware (HMAC IP, UART, protokol) + bahan video fallback.

## 3. Aturan Jalur Data

> Software boleh mengubah data **setelah** ditandatangani — itu justru adegan BMS curang. **Sebelum** ditandatangani, tidak boleh ada software.

- Sumber sampel harus dari pin/RTL (switch, XADC, script ramp, ADS1115 lewat I2C) — bukan dari PS (AXI/PYNQ) dan bukan dari jalur UART.
- Kalau PS/notebook yang menulis nilai tegangan ke IP, sampel melewati software sebelum ditandatangani — persis kelemahan DS28E38 yang diserang di proposal B4. Juri bisa mematahkan klaim utama.
- Konsekuensi: PYNQ tidak dipakai untuk sumber sampel; stasiun tetap Python di laptop.

## 4. Sumber Input Demo

| Alternatif | Board | Yang perlu dibawa | Catatan |
|---|---|---|---|
| **ADS1115 (I2C) + potensiometer** | **Cmod S7 / KV260 / semua** | modul ADS1115 + pot + kabel jumper | **Pilihan sekarang** (19 Okt). Kenop fisik untuk juri, I2C 2 pin. Modul umumnya sudah ada pull-up |
| Switch bank sebagai "ADC" | Basys 3 / Nexys A7 (16 switch) | LED + wire saja | Fallback murah; tidak tersedia di KV260 |
| XADC on-chip + potensiometer | **Nexys A7 saja** (konektor JXADC) | Pot + resistor divider (22k/10k, range XADC 0–1 V) + wire | ADC **di dalam FPGA** — paling nyambung ke klaim "ADC dalam chip"; tapi tidak ada di KV260/Cmod S7 |
| Scripted ramp di RTL + tombol | Semua, terutama KV260 | LED + wire saja | Tegangan auto-play "seminggu"; tombol = trigger drain event. Paling deterministik |

KV260 hari-H: pakai ADS1115 + pot kalau kenop fisik wajib, dengan scripted ramp + tombol sebagai cadangan. Adegan hapus/ubah catatan tidak tergantung sumber tegangan.

## 5. Keputusan Toolchain (PYNQ vs Vitis+C vs RTL)

| Opsi | Cmod S7 / Basys 3 / Nexys A7 | KV260 | Putusan |
|---|---|---|---|
| PYNQ + Jupyter | **Tidak bisa.** PYNQ butuh PS ARM (Zynq); Basys/Nexys hanya FPGA Artix-7, Cmod S7 Spartan-7 | Bisa (Kria-PYNQ) | **Jangan.** Stasiun sudah Python di laptop; PYNQ menambah overlay, packaging, dan risiko hari-H tanpa manfaat |
| Vitis + C (MicroBlaze V) | Bisa, proyek lama sudah ada | **Tidak boleh** — proposal: tanpa prosesor lunak | **Bekukan sebagai cadangan.** Tidak diporting, tidak jadi jalur demo |
| RTL + UART + Python | Bisa | Bisa | **Pakai ini di semua board** |

Kalau PYNQ tetap dipakai, bentuknya: image Kria-PYNQ → IP dibungkus AXI-Lite + overlay `.bit`/`.hwh` → `Overlay()` di notebook → baca/tulis register dari Python. Tapi: (1) bungkus AXI = kerjaan berhari-hari, (2) PS menulis sampel = melanggar Aturan Jalur Data, (3) tidak menambah apa pun di atas stasiun laptop. Tetap skip.

Alasan jalur RTL: sesuai proposal, port hanya ganti constraint + synthesa ulang, dan bebas dari bug `Cannot halt hart` (AR000037627, hw_server 2024.2) karena tidak ada hart yang perlu di-halt.

## 6. Urutan Uji di Cmod S7 / Basys/Nexys (Sesi Hardware)

Prosedur lengkap dengan test ID (T1–T9), perintah siap-salin, tabel pin switch/LED, dan lembar log ada di **[rencana-tes-basys3.md](rencana-tes-basys3.md)**. Untuk Cmod S7, runbook operasional + skrip demo ada di **[RUNBOOK.md](../../fpga/cmod_s7/RUNBOOK.md)**. Ringkasnya:

Pin penting:

| Sinyal | Cmod S7 (dari `Cmod-S7-25-Master.xdc`) | Basys 3 (dari basys_3.xdc) | Nexys A7 (dari master XDC Digilent) |
|---|---|---|---|
| Clock | M9 (12 MHz) | W5 (100 MHz) | E3 (100 MHz) |
| Reset | D2 (BTN0, active-high) | U18 (btnC) | internal reset / cek master XDC |
| UART RX (dari FTDI) | K15 | B18 | C4 (UART_TXD_IN) |
| UART TX (ke FTDI) | L12 | A18 | D4 (UART_RXD_OUT) |
| Input sampel | ADS1115 AIN0 (pot) | switch bank | switch bank / JXADC + pot |
| ADS1115 SCL / SDA | JA1 = J2 / JA2 = H2 | JA1 = J1 / JA2 = L2 | PMOD (ambil dari master XDC) |
| LED | E2, K1, J1, E1 | U16, E19, U19, V19 | cek master XDC |

Cmod S7 dan kedua board lama punya USB-UART FTDI bawaan — tidak perlu CP2102 untuk latihan. Cek port: `ls /dev/ttyUSB*` (FT2232 punya kanal JTAG + UART; UART biasanya `ttyUSB1`). Pin Cmod S7 sudah diekstrak ke `fpga/cmod_s7/cmod_s7.xdc`; bitstream 20 Okt: `cd fpga/cmod_s7 && vivado -mode batch -source build.tcl` (WNS +55,193 ns), program dengan `program.tcl`.

Prioritas uji (urut):

1. **Rantai RTL minimal** (nilai tertinggi — inilah yang jalan di KV260): UART ↔ stasiun Python, HMAC IP, seq counter, sampel dari ADS1115 (I2C) atau switch. Target: station verifikasi HMAC → VALID.
2. **Kalau T7/T9 di Cmod S7 gagal:** tes Flow A (MicroBlaze) dengan hw_server 2024.1 → validasi HMAC di hardware + UART + protokol stasiun → **rekam video fallback** dari sini.
3. **Freeze kontrak frame riwayat** (`READ_HIST` + layout record) — membebaskan Muqtada (RTL) dan Budi (dashboard) untuk kerja paralel.
4. **Tanpa board:** synthesa RTL untuk `xck26`, siapkan SD image Ubuntu, uji loopback CP2102 di laptop (TX-RX jumper), tulis draft constraint PMOD KV260.

Urutan uji fungsional: PING/loopback → vektor HMAC → alur demo penuh (valid, catatan dihapus, angka diubah).

## 7. Runbook KV260 (Hari-H)

1. Boot Ubuntu dari SD card (ikuti panduan Kria; firmware lama perlu update BOOT.BIN agar Ubuntu 22.04 mau boot).
2. Saat boot, app bawaan `k26-starter-kits` memuat bitstream bawaan. Lepas dulu:
   ```
   sudo xmutil unloadapp
   sudo xmutil listapps
   ```
3. Muat bitstream SeBatt, pilih salah satu:
   - Paket: taruh di `/lib/firmware/sebatt/` (`sebatt.bit.bin` + `shell.json`), lalu `sudo xmutil loadapp sebatt`.
   - Langsung: `sudo fpgautil -b sebatt.bit.bin`.
   - Konversi `.bit` → `.bit.bin` sesuai format Kria (cek saat bring-up).
4. Clock: PS Zynq UltraScale+ di block design sebagai sumber `pl_clk0` (keputusan 18 Okt). PL hanya berisi logika SeBatt + pin PMOD.
5. UART: PMOD + CP2102 ke laptop. **CP2102 wajib** — UART onboard KV260 milik PS, bukan PL; tidak ada jalur lain tanpa menulis bridge software di PS (yang merusak cerita demo). **Cek tegangan bank PMOD di skematik KV260 sebelum menyambung.**
6. ADS1115: VDD 3,3 V, GND, SCL/SDA ke 2 pin PMOD; ADDR→GND (`0x48`); AIN0 ke potensiometer. Pull-up modul biasanya cukup.
7. Constraint PMOD: ambil nama pin dari master XDC KV260 — jangan menebak.
8. Verifikasi berurutan: `xmutil listapps` → load sukses → PING di terminal serial → satu riwayat valid → satu modifikasi ditolak. Baru demo penuh.

PMOD 2×6 KV260: 8 pin data — cukup untuk UART (2) + LED (1) + ADS1115 I2C (2) + spare.

## 8. Checklist Port Basys/Nexys → KV260

- [ ] Top RTL sama; hanya wrapper pin + constraint yang berubah
- [ ] Clock: W5/E3 → `pl_clk0` dari PS di BD
- [ ] UART: FTDI onboard → PMOD + CP2102 (nomor pin baru)
- [ ] Input: ADS1115 I2C / switch → scripted ramp + tombol
- [ ] ADS1115 terdeteksi di `0x48` (scan I2C) dan membaca AIN0
- [ ] Target device `xck26` terbaca di Vivado
- [ ] `bit` → `bit.bin`, muat via xmutil/fpgautil
- [ ] Video fallback sudah direkam sebelum berangkat
- [ ] PING + 1 riwayat valid + 1 modifikasi ditolak, sebelum demo penuh

## 9. Daftar Barang

**Wajib:**

| Barang | Fungsi | Perkiraan harga |
|---|---|---|
| CP2102 / CH340 / FT232 (USB-UART 3,3 V) ×2 | Satu-satunya jalur chip → stasiun di KV260; 1 backup | Rp 50–100k |
| Modul ADS1115 (I2C, 16-bit) ×2 | Sumber tegangan demo (AIN0, addr 0x48); 1 cadangan | Rp 30–60k |
| microSD 32 GB + reader | Boot Ubuntu KV260 (cek juga apakah panitia menyediakan + PSU 12 V) | Rp 60–80k |
| Jumper wire set (F-F, F-M) | PMOD KV260 ↔ CP2102/LED | Rp 15–30k |
| Kabel micro-USB + USB-C spare | Programming/power kedua board dan aksesori | punya, bawa cadangan |

**Opsional (wow / asuransi):**

| Barang | Efek | Harga |
|---|---|---|
| LED 10mm merah + hijau + resistor 220Ω | DITOLAK/VALID terlihat dari seluruh ruangan; LED digerakkan pin RTL, bukan layar | Rp 10k |
| Buzzer aktif | Bunyi saat DITOLAK | Rp 5k |
| Potensiometer 10k + knob | Kenop juri untuk AIN0 ADS1115 (0–3,3 V); resistor 22k/10k hanya untuk rute XADC Nexys | Rp 15k |
| Mock baterai kardus/akrilik + label + QR | Meja demo terasa "produk" | Rp 30k |
| Banner kecil "STASIUN PENUKARAN BATERAI" | Panggung stasiun | Rp 20k |

**Jangan beli:** Arduino/RPi, PMOD AD1/AD2 Digilent, modul ADC SPI (MCP3202 tidak dipakai — ADS1115 I2C sudah cukup).

## 10. Cadangan: MicroBlaze V + Vitis (Beku)

Jalur lama di `fpga/basys_3` dan `fpga/ws` disimpan, tidak dihapus, dan **tidak dipakai** untuk demo. Kalau RTL mandek total dan terpaksa:

```
pkill -x hw_server          # jangan `pkill -f`: pola bisa cocok dengan shell sendiri
/home/muqtada/Xilinx/HWSRVR/2024.1/bin/hw_server
```

lalu jalankan debug Vitis 2024.2 seperti biasa (mungkin tetap mencetak pesan timeout sekali; hart seharusnya berhenti). Ingat: jalur ini tidak bisa dipakai di KV260 (proposal melarang prosesor lunak), jadi hanya penyelamat latihan, bukan rencana utama.

## 11. Yang Tidak Dilakukan

- PYNQ di Basys 3 / Nexys A7 — mustahil (tanpa PS ARM).
- PYNQ di KV260 — bisa, tapi melanggar Aturan Jalur Data kalau dipakai untuk sumber sampel; stasiun tetap di laptop.
- Soft processor atau IP wizard (MIG, Block Memory Generator) di jalur demo.
- UART PS KV260 untuk demo — pakai PMOD supaya logika FPGA yang bicara.
- Menaruh sumber sampel di software (PS/AXI/PYNQ/UART) — merusak klaim utama.
- Mengandalkan Basys/Nexys/Cmod S7 di hari-H — yang dibawa ke panggung hanya KV260; posisi board lain digantikan video fallback.
- Modul ADC SPI (MCP3202) — dibatalkan 19 Okt; ADS1115 I2C menggantikannya.
