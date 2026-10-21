# Runbook Cmod S7 — jalankan dan demo

Panduan operasional Flow B di **Digilent Cmod S7-25**. Semua perintah dijalankan
dari root repo (`/home/muqtada/Documents/sebatt`) kecuali disebut lain.

Status 21 Okt 2026: sampling periodik 1 detik, riwayat 64 record bertanda
tangan, `READ_HIST`, dan lock sudah ada di RTL; regresi cocotb 20/20 dan
bitstream dibangun ulang dengan timing bersih. Yang belum dilakukan adalah uji
fisik T6/T7/T9.

- Bitstream: `fpga/cmod_s7/build/cmod_s7_top.bit`
- Part: `xc7s25csga225-1`
- Clock: 12 MHz, UART 115 200 8N1
- Sampling ADS1115: periodik 1 detik (`SAMPLE_INTERVAL_MS=1000`), independen dari UART
- Pin map: `fpga/cmod_s7/cmod_s7.xdc`
- Rujukan pin resmi: `Cmod-S7-25-Master.xdc` dari Digilent

---

## 1. Yang perlu disiapkan

| Barang | Catatan |
|---|---|
| Cmod S7-25 | USB micro-B data, bukan kabel charge-only |
| Modul ADS1115 | Modul I2C umum, alamat `0x48` |
| Potensiometer | 10 kΩ, ujung ke 3V3 dan GND, wiper ke AIN0 |
| Kabel jumper | 4 buah: VDD, GND, SCL, SDA |
| Laptop | Vivado 2024.2, Python + `.venv` repo ini |

Jangan memberi VDD ADS1115 5 V. Pakai **3V3** dari Cmod S7 agar SCL/SDA tetap
dalam rentang I/O Spartan-7.

---

## 2. Wiring

```
Cmod S7 3V3  ──────────────  ADS1115 VDD
Cmod S7 GND  ──────────────  ADS1115 GND
Pmod JA pin 1 (J2) ────────  ADS1115 SCL
Pmod JA pin 2 (H2) ────────  ADS1115 SDA
ADS1115 ADDR ──────────────  GND          (alamat 0x48)
ADS1115 AIN0 ──────────────  pot wiper
Pot ujung A  ──────────────  3V3
Pot ujung B  ──────────────  GND
```

Modul ADS1115 ungu biasanya sudah punya pull-up 10 kΩ ke VDD. Kalau modul tidak
punya pull-up, tambahkan 4,7–10 kΩ dari SCL ke 3V3 dan SDA ke 3V3.

---

## 3. Build bitstream (kalau file belum ada)

```bash
cd fpga/cmod_s7
vivado -mode batch -source build.tcl
```

Output:

- `build/cmod_s7_top.bit`
- `build/timing.rpt`
- `build/utilization.rpt`

Hasil 21 Okt: WNS **+55,788 ns**, 5 235 LUT, 6 024 FF, 0 BRAM/DSP, semua constraint met.
Build ulang hanya perlu kalau RTL berubah.

---

## 4. Program board

```bash
cd fpga/cmod_s7
vivado -mode batch -source program.tcl
```

Atau buka Vivado Hardware Manager dan program `build/cmod_s7_top.bit` secara
manual.

Setelah selesai:

- LED1 (E2) berkedip ~0,7 Hz sebagai heartbeat.
- Kalau tidak berkedip, tekan **BTN0** sekali (reset manual; BTN0 active-high).
- LED2 (K1) menyala sebentar saat transaksi auth.
- LED3 (J1) menyala setelah respons auth terkirim.
- LED4 (E1) menyala kalau ada error frame/CRC, ADC, atau AXI.

---

## 5. Cek port UART

Cmod S7 memakai FT2232: kanal A untuk JTAG, kanal B untuk UART.

```bash
ls -l /dev/ttyUSB*
python -m serial.tools.list_ports -v
```

Biasanya UART ada di **`/dev/ttyUSB1`**. Kalau hanya ada satu port, coba yang
tersedia; kalau ragu, lepas-sambung kabel USB dan lihat port mana yang muncul.

Kalau muncul `Permission denied`:

```bash
sudo usermod -aG dialout $USER
# logout lalu login lagi
```

atau untuk sesi ini saja:

```bash
sudo chmod 666 /dev/ttyUSB1
```

---

## 6. Smoke test satu autentikasi

```bash
source .venv/bin/activate
python -m model.station --port /dev/ttyUSB1
```

Contoh output yang benar:

```
Battery: 42415401
Voltage: 1234 mV
Result:  VALID
```

`42415401` adalah `BAT\x01`. Tegangan mengikuti posisi pot (0–3300 mV).
FPGA mengambil sampel baru setiap **1 detik**; setelah memutar pot, tunggu
sedikit (≥1 detik) sebelum `auth` agar nilai terbaru sudah masuk.

**Penting:** `Result: VALID` dengan `Voltage: 0 mV` berarti HMAC benar tetapi
ADS1115 tidak terbaca. Periksa wiring I2C dan LED4; itu bukan auth yang sehat.

---

## 7. Demo suite (8 autentikasi)

```bash
python -m model.station --port /dev/ttyUSB1 --demo
```

Urutan yang diharapkan:

```
[1] Valid authentication...                       -> VALID
[2] Multiple valid authentications (5x)...        -> VALID x5
[3] Read signed history...                        -> VALID / HISTORY_TRUNCATED
[4] Lock battery, attempt authentication...       -> BATTERY_LOCKED
[5] Unlock battery, re-authenticate...            -> VALID
Demo complete. 8 station transactions logged.
```

LOCK/UNLOCK/STATUS/READ_HIST sudah diimplementasikan di RTL. Setelah LOCK,
chip membalas AUTH_REQ dan READ_HIST_REQ dengan CHIP_LOCKED.

---

## 8. Demo 60–90 detik untuk juri

Persiapan sebelum naik panggung:

1. Board sudah diprogram, LED1 berkedip.
2. Pot berada di posisi jelas (misalnya 1,5 V).
3. Terminal sudah di folder repo dan venv aktif.
4. Jalankan mode interaktif:

```bash
python -m model.station --port /dev/ttyUSB1 --interactive
```

Alur di panggung:

```text
station> auth
  Battery: 42415401  Voltage: 1500mV  -> VALID

# putar pot ke posisi lain, tunggu >=1 detik

station> auth
  Battery: 42415401  Voltage: 2750mV  -> VALID

station> lock
  Battery locked

station> auth
  Battery: 42415401  Voltage: 2750mV  -> BATTERY_LOCKED

station> unlock
  Battery unlocked

station> auth
  Battery: 42415401  Voltage: 2750mV  -> VALID
```

Kalimat inti yang perlu disampaikan:

- Tegangan dibaca ADS1115 lewat I2C setiap 1 detik dan masuk langsung ke RTL;
  tidak ada software di jalur sampel.
- RTL menghitung HMAC-SHA-256 atas `0x41 || nonce || battery_id || voltage`.
- Station hanya percaya nilai yang ada di dalam frame yang ditandatangani.
- Memutar pot mengubah nilai yang ditandatangani; station memverifikasi ulang.
- `READ_HIST_REQ` mengembalikan 64 record `seq || V || HMAC` dan satu tag
  ringkasan ber-nonce; station memeriksa urutan dan setiap tag.
- LOCK sekarang mengunci chip; setelah tiga RESULT gagal chip juga terkunci.

Kalau ditanya soal serangan:

```bash
python -m model.station --offline
```

Mode offline menampilkan replay, perubahan tegangan, dan battery lock tanpa
hardware. Gunakan sebagai jawaban kalau juri minta melihat penolakan.

---

## 9. T6/T7/T9 checklist

| Tes | Perintah | Lulus kalau |
|---|---|---|
| T6 Program | `vivado -mode batch -source program.tcl` | LED1 berkedip |
| T7 Auth | `python -m model.station --port /dev/ttyUSB1` | `VALID`, voltage wajar |
| T7 Variasi | putar pot, tunggu ≥1 detik, lalu auth lagi | voltage berubah, tetap `VALID` |
| T9 ADS1115 | putar pot, tunggu ≥1 detik, lalu auth | voltage mengikuti pot, LED4 padam |
| T10 Riwayat | `python -m model.station --port /dev/ttyUSB1 --history` | `VALID` atau `HISTORY_TRUNCATED`, jumlah record dan rentang seq wajar |
| T8 LED | lihat LED2/3/4 saat auth | busy/valid/error sesuai |

Tidak ada perintah "I2C scan" di RTL. Pembacaan ADS1115 diverifikasi lewat
nilai tegangan pada respons auth; kalau belum pernah ada sampel sukses, voltage 0;
kalau I2C gagal setelah sampel baik, sampel terakhir dipertahankan dan LED4 menyala.

---

## 10. Troubleshooting

| Gejala | Kemungkinan | Tindakan |
|---|---|---|
| LED1 tidak berkedip | belum diprogram, salah bitstream, board belum reset | program ulang, tekan BTN0, cek USB |
| `Permission denied` | user tidak di grup `dialout` | `sudo usermod -aG dialout $USER`, login ulang |
| Tidak ada respons UART | port salah (`ttyUSB0` = JTAG) | pakai `/dev/ttyUSB1` |
| `CRC mismatch` / frame rusak | baud/port salah, ground tidak common | pastikan 115200, GND ADS1115 ke GND board |
| `VALID` tapi voltage 0 | ADS1115 tidak terdeteksi | cek VDD 3V3, SCL/SDA, ADDR ke GND, LED4 |
| Voltage tidak berubah | wiper pot tidak ke AIN0 | pindahkan wiper ke AIN0, ujung pot ke 3V3/GND |
| Selalu `INVALID_HMAC` | key/ID tidak cocok | pastikan memakai repo ini; key demo `bytes(range(32))`, ID `BAT\x01` |
| Program gagal | kabel USB bukan data, hw_server | ganti kabel, jalankan `hw_server`, cek `lsusb` |
| `make` gagal | venv belum aktif | `source .venv/bin/activate` |

---

## 11. Batasan demo (jangan diklaim lebih)

- Kunci masih fixed `bytes(range(32))`; PUF belum di jalur demo.
- UNLOCK belum diautentikasi; siapa pun yang bisa mengirim frame dapat membuka lock.
- Seq counter, riwayat, dan lock bersifat volatil; daya putus menghapus semuanya.
- Dump riwayat maksimal ~215 ms pada 115200 baud; station memakai timeout 2 detik.
- ADS1115 masih modul terpisah; tegangan bisa dipalsukan sebelum FPGA. Ini
  batasan PoC yang sudah didokumentasikan.
- Bitstream khusus Cmod S7-25 (`xc7s25csga225-1`). Board varian lain perlu build
  ulang.
