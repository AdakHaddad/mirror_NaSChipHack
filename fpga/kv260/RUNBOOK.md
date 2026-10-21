# Runbook KV260 — jalankan dan demo

Panduan operasional Flow B di **Kria KV260**. Semua perintah dijalankan dari
root repo (`/home/muqtada/Documents/sebatt`) di laptop, kecuali bagian yang
dijalankan di board.

Status 21 Okt 2026: bitstream penuh sudah dibangun ulang setelah perbaikan
multi-driver `sg_req*`, dump race, CRC, parser resync, adc-free source, LED,
dan bus I2C (WNS +0,749 ns, 5 607 LUT, 6 207 FF), peta pin Pmod dan block design clock PS
sudah ada. **Uji fisik T6/T7/T9/T10 di KV260 belum dilakukan.** Uji RTL cocotb
26/26 dan uji board Cmod S7 tetap menjadi bukti fungsional sampai KV260 diuji.

- Bitstream: `fpga/kv260/build/kv260_top.bit`
- Boot image: `fpga/kv260/build/kv260_top.bit.bin`
- Part: `xck26-sfvc784-2LV-c`
- Clock: PS `pl_clk0`, 100 MHz (aktual 99,999001 MHz)
- UART: 115200 8N1, Pmod J2 pin 7/8 lewat CP2102
- Sampling ADS1115: periodik 1 detik (`SAMPLE_INTERVAL_MS=1000`)
- Pin map: `fpga/kv260/kv260.xdc`
- Rujukan pin: master XDC KV260 / Kria K26 SOM (`kv260_ispMipiRx` `pin.xdc`,
  Kria-PYNQ `base.xdc`)
- Paket demo: `fpga/kv260/demo/` — `preflight.sh`, `load.sh`,
  `run_station.sh`, dan panduan singkat `README.md`

---

## 1. Yang perlu disiapkan

| Barang | Catatan |
|---|---|
| Kria KV260 + PSU 12 V | Kartu SD berisi Kria Ubuntu yang sudah bisa boot |
| Kabel micro-USB | Untuk konsol serial PS (bukan jalur aplikasi) |
| CP2102 / CH340 / FT232 3,3 V | **Wajib** untuk UART PL; siapkan satu cadangan |
| Modul ADS1115 | Alamat `0x48` (ADDR ke GND) |
| Potensiometer 10 kΩ | Ujung ke 3V3/GND, wiper ke AIN0 |
| LED ketiga + resistor 330 Ω | Heartbeat di Pmod 4 (berkedip = logika PL hidup) |
| LED hijau + merah + resistor 220–330 Ω | Indikator auth/lock |
| Kabel jumper | Pmod J2 ke ADS1115, CP2102, LED |
| Laptop | Vivado 2024.2, Python + `.venv` repo ini |

Jangan memberi VDD ADS1115 5 V. Pakai **3V3** dari Pmod (pin 6/12). Jangan
memberi daya board dari pin 3V3 Pmod.

---

## 2. Wiring

Pmod J2 pada KV260 memakai urutan Digilent Type 1A: pin data 1–4 dan 7–10,
GND/3V3 di 5/6 dan 11/12.

```
KV260 Pmod J2                         Perangkat
1  (H12) SCL   ─────────────────────  ADS1115 SCL
2  (E10) SDA   ─────────────────────  ADS1115 SDA
3  (D10) src_sel  ── GND             (GND = ADS1115, 3V3 = sumber tetap 3000 mV)
4  (C11) hb    ─── 330 Ω ── LED ────  GND        (berkedip = PL hidup)
5  (GND)       ─────────────────────  ADS1115 GND, CP2102 GND, katoda LED
6  (3V3)       ─────────────────────  ADS1115 VDD, ujung atas pot
7  (B10) TX    ─────────────────────  CP2102 RXD
8  (E12) RX    ─────────────────────  CP2102 TXD
9  (D11) green ─── 330 Ω ── LED ────  GND
10 (B11) red   ─── 330 Ω ── LED ────  GND
11 (GND)       ─────────────────────  GND
12 (3V3)       ─────────────────────  3V3
```

Catatan:

- **CP2102**: sambungkan GND dan TX/RX saja. Kalau adaptor diberi daya dari USB
  laptop, jangan sambungkan VCC-nya ke 3V3 Pmod. Set jumper logika ke **3,3 V**;
  TXD CP2102 harus 3,3 V karena bank Pmod 3,3 V.
- **ADS1115**: modul ungu biasanya sudah punya pull-up 10 kΩ. Kalau tidak,
  tambahkan 4,7–10 kΩ dari SCL dan SDA ke 3V3. ADDR ke GND.
- **LED**: anoda ke pin Pmod lewat resistor, katoda ke GND. Pin aktif tinggi.
- **Heartbeat (Pmod 4)**: LED berkedip sekitar 6 Hz begitu bitstream termuat dan
  pl_clk0 jalan. Tidak berkedip berarti masalah clock/bitstream, bukan UART.
- **Tidak ada tombol reset.** Reset membuat seq kembali ke 0, sehingga stasiun
  melaporkan HISTORY_ROLLBACK sampai seq melewati anchor. Untuk mulai ulang,
  muat ulang bitstream dan kosongkan anchor di stasiun.
- **Pmod 3**: pemilih sumber. **Sambungkan ke GND** untuk ADS1115, ke 3V3 untuk
  sumber tetap 3000 mV (tanpa ADC). **Jangan dibiarkan terbuka**: pada uji 21 Okt
  pin terbuka terbaca 1 walaupun ada pull-down internal, sehingga chip memakai
  sumber tetap 3000 mV. Pin dibaca terus, jadi boleh dipindah tanpa memuat ulang.
- Konsol serial PS KV260 memakai micro-USB tersendiri; itu **bukan** UART
  aplikasi. UART aplikasi hanya lewat CP2102 di Pmod 7/8.

---

## 3. Build bitstream

Kalau `build/kv260_top.bit` belum ada atau RTL/constraint berubah:

```bash
cd fpga/kv260
vivado -mode batch -source build.tcl
```

Waktu build penuh sekitar 20–25 menit (block design, sintesis, place/route,
bitstream, `.bin`, XSA). Output:

- `build/kv260_top.bit`
- `build/kv260_top.bit.bin` (untuk `fpgautil`)
- `build/timing.rpt`, `build/utilization.rpt`
- `build/kv260_top.xsa` (kalau langkah XSA berhasil)

Hasil 21 Okt: build board 11.46 WNS **+1,466 ns**, 5 633 LUT, 6 201 FF;
build ulang 21.26 WNS **+0,749 ns**, WHS +0,015 ns, 0 endpoint gagal,
5 607 LUT, 6 207 FF, 0 BRAM, 0 DSP. Build 21.26 sudah memakai perbaikan
multi-driver `sg_req*`, dump race, CRC, parser resync, adc-free source, LED,
dan bus I2C; belum diuji ulang di board. Jalur kritis
SHA-256 `w` expansion; **jangan naikkan `pl_clk0` di atas 100 MHz** tanpa
pipeline dan re-timing.

Cek cepat tanpa bitstream (opsional):

```bash
vivado -mode batch -source build_synth.tcl
```

Skrip itu memakai `timing_only.xdc`, tidak menulis bitstream, dan menimpa
`build/timing.rpt`/`utilization.rpt`; jalankan `build.tcl` lagi untuk laporan
final.

---

## 4. Boot KV260 dan siapkan board

1. Boot Kria Ubuntu dari SD card. Konsol PS lewat micro-USB carrier:
   `sudo picocom -b 115200 /dev/ttyUSB1` (nomor port bisa berbeda).
2. Pastikan board dapat alamat IP dan bisa di-`ssh`.
3. Lepas aplikasi bawaan Kria supaya PL bebas:

   ```bash
   sudo xmutil unloadapp
   sudo xmutil listapps
   ```

   Kalau `unloadapp` error karena tidak ada app, abaikan.
4. Salin boot image ke board:

   ```bash
   scp fpga/kv260/build/kv260_top.bit.bin \
       fpga/kv260/demo/load.sh <user>@<ip-kv260>:~/
   ```

---

## 5. Cek clock PL (wajib sebelum percaya UART)

Desain memakai `pl_clk0` dari PS, bukan osilator PL. Clock ini harus aktif di
**99,999001 MHz** (atau 100 MHz); kalau tidak, UART/I2C ikut salah dan frame
akan rusak.

Di board:

```bash
sudo mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
sudo cat /sys/kernel/debug/clk/pl0_ref/clk_rate
sudo cat /sys/kernel/debug/clk/pl0_ref/clk_enable_count
```

Atau:

```bash
sudo grep -i pl0 /sys/kernel/debug/clk/clk_summary
```

Yang diharapkan:

- `clk_rate` ≈ `99999001` (atau `100000000`)
- `clk_enable_count` > 0

Kalau `pl0_ref` **disabled** (enable count 0), kernel mematikan clock yang tidak
dipakai. Tambahkan `clk_ignore_unused` ke cmdline kernel dan reboot:

```bash
sudo sed -i '$ s/$/ clk_ignore_unused/' /boot/firmware/cmdline.txt
sudo reboot
```

(Path Kria Ubuntu 22.04: `/boot/firmware/cmdline.txt`; kalau tidak ada, cek
`/boot/cmdline.txt`. File harus tetap satu baris.) Kalau setelah reboot
`clk_enable_count` masih 0, firmware boot belum mengaktifkan PL0; lanjut ke
pilihan BOOT.BIN di bawah.

Kalau `clk_rate` justru **96,97 MHz**, firmware boot stock memakai RPLL, bukan
IOPLL 100 MHz. Bitstream ini dibangun untuk 100 MHz, jadi jangan lanjut.
Pilihan:

1. **Perbaikan benar:** buat BOOT.BIN dari `build/kv260_top.xsa` mengikuti alur
   boot firmware Kria, supaya `psu_init` memasang PL0 dari IOPLL 100 MHz.
2. **Sementara:** build ulang RTL untuk clock aktual, misalnya
   `vivado -mode batch -source build.tcl -tclargs 100 96968727`, lalu ulangi
   cek. UART akan benar di 96,97 MHz, tetapi clock tidak sesuai target demo.

Jangan mengandalkan `pl_clk0` tanpa cek ini; LED/UART yang diam sering berasal
dari clock yang belum aktif, bukan dari RTL.

---

## 6. Program PL

### 6a. `fpgautil` (utama)

Cara tercepat, sekaligus mengecek clock sebelum/sesudah load:

```bash
chmod +x load.sh
sudo ./load.sh ./kv260_top.bit.bin
```

Atau manual:

```bash
sudo fpgautil -b ~/kv260_top.bit.bin
sudo dmesg | tail -n 20
```

`fpgautil` biasanya sudah ada di `/usr/sbin/fpgautil` pada Kria Ubuntu. Kalau
tidak ada, pasang paket FPGA manager/dfx-mgr sesuai panduan Kria, atau pakai
JTAG. `.bit.bin` di sini dibuat oleh Vivado (`write_bitstream -bin_file`);
FPGA Manager sejak 2018.3 menerima format Vivado maupun bootgen, jadi
konversi bootgen tidak diperlukan.

### 6b. JTAG (cadangan)

Dari laptop, dengan KV260 tersambung JTAG dan PS sudah boot:

```bash
cd fpga/kv260
vivado -mode batch -source program.tcl
```

JTAG hanya memuat PL; clock PS tetap harus sudah benar (bagian 5). Kalau muncul
`Cannot halt hart`, itu bug hw_server 2024.2; pakai `fpgautil` atau hw_server
2024.1.

### 6c. Cek hidup

LED heartbeat di Pmod 4 berkedip sekitar 6 Hz saat `pl_clk0` dan logika PL
hidup. Tanda aplikasi siap adalah respons UART terhadap satu `AUTH_REQ`
(bagian 8). LED hijau menyala setelah auth valid; LED merah menyala saat
lock/error (termasuk ADS1115 tidak terbaca).

---

## 7. Cek port UART aplikasi

CP2102 biasanya muncul sebagai `/dev/ttyUSB0`; konsol PS KV260 bisa menempati
port lain dan juga terdeteksi sebagai USB serial. `model.station` sekarang
memprioritaskan CP210x/CH340, tetapi tetap sebutkan `--port` kalau ada lebih
dari satu adapter. Kalau ragu, lepas-sambung CP2102 dan lihat port mana yang
muncul.

```bash
ls -l /dev/ttyUSB*
python -m serial.tools.list_ports -v
```

Kalau `Permission denied`:

```bash
sudo usermod -aG dialout $USER
# logout lalu login lagi
```

atau untuk sesi ini:

```bash
sudo chmod 666 /dev/ttyUSB0
```

---

## 7b. Self-check sebelum demo

Satu perintah untuk memastikan board benar-benar siap: STATUS, AUTH, lalu satu
pembacaan riwayat bertanda tangan. Tidak ada RESULT yang dikirim, jadi hitungan
gagal dan lock chip tidak berubah; jangkar stasiun ikut menyesuaikan ke `seq`
terakhir yang valid.

```bash
source .venv/bin/activate
python -m model.station --check              # auto-deteksi CP2102
python -m model.station --check --port /dev/ttyUSB1
```

Contoh output siap demo:

```
[OK] STATUS: locked=False, fail_cnt=0
[OK] AUTH: VALID, 3700 mV, 42415401
[OK] READ_HIST: VALID, 12 catatan
```

Dashboard menjalankan self-check yang sama saat start dan mencetak baris
`[OK]`/`[FAIL]`:

```bash
python3 web/server.py            # auto-deteksi; pakai --sim untuk latihan
```

Urutan yang benar: muat bitstream dulu (bagian 6), baru jalankan self-check dan
dashboard. Setelah bitstream dimuat ulang, `seq` chip kembali ke 0 — restart
server dashboard supaya jangkar ikut kembali ke 0; kalau tidak, pertukaran
pertama akan melaporkan `HISTORY_ROLLBACK`.

`READ_HIST: HISTORY_TRUNCATED` tetap dianggap OK (jangkar stasiun baru dan
buffer sudah berputar). `FAIL` pada salah satu baris berarti jangan mulai demo:
lihat bagian 12.

---

## 8. Smoke test satu autentikasi

```bash
source .venv/bin/activate
python -m model.station --port /dev/ttyUSB0
```

Contoh output yang benar:

```
Battery: 42415401
Voltage: 1234 mV
Result:  VALID
```

`42415401` adalah `BAT\x01`. Tegangan mengikuti posisi pot (0–3300 mV). FPGA
mengambil sampel baru setiap **1 detik**; setelah memutar pot, tunggu ≥1 detik
sebelum `auth`.

**Penting:** `Result: VALID` dengan `Voltage: 0 mV` berarti HMAC benar tetapi
ADS1115 tidak terbaca. Periksa wiring I2C; LED merah akan menyala. Itu bukan
auth yang sehat.

---

## 9. Demo suite (8 autentikasi)

```bash
python -m model.station --port /dev/ttyUSB0 --demo
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

LOCK/UNLOCK/STATUS/READ_HIST sudah ada di RTL. Setelah LOCK, chip membalas
AUTH_REQ dan READ_HIST_REQ dengan CHIP_LOCKED.

---

## 10. Demo 60–90 detik untuk juri

Persiapan:

1. Board menyala, bitstream termuat, clock PL sudah dicek.
2. Pot di posisi jelas (misalnya 1,5 V) dan sudah lewat ≥1 detik.
3. Terminal di root repo dan venv aktif.
4. Mode interaktif:

```bash
python -m model.station --port /dev/ttyUSB0 --interactive
```

Alur:

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

Kalimat inti:

- Tegangan dibaca ADS1115 lewat I2C setiap 1 detik dan masuk langsung ke RTL;
  tidak ada software di jalur sampel.
- RTL menghitung HMAC-SHA-256 atas `0x41 || nonce || battery_id || voltage`.
- Station hanya percaya nilai di dalam frame yang ditandatangani.
- `READ_HIST_REQ` mengembalikan 64 record `seq || V || HMAC` plus tag ringkasan
  ber-nonce; station memeriksa urutan dan setiap tag.
- LOCK mengunci chip; tiga RESULT gagal juga mengunci chip.

Serangan tanpa hardware:

```bash
python -m model.station --offline
```

---

## 11. T6/T7/T9/T10 checklist

| Tes | Perintah | Lulus kalau |
|---|---|---|
| T0 Self-check | `python -m model.station --check` | STATUS/AUTH/READ_HIST semua `[OK]` (tanpa RESULT, lock tidak berubah) |
| T6 Program | `sudo fpgautil -b ~/kv260_top.bit.bin` | load sukses, `dmesg` bersih, `pl0_ref` aktif |
| T7 Auth | `python -m model.station --port /dev/ttyUSB0` | `VALID`, voltage wajar |
| T7 Variasi | putar pot, tunggu ≥1 detik, auth lagi | voltage berubah, tetap `VALID` |
| T9 ADS1115 | putar pot, tunggu ≥1 detik, auth | voltage mengikuti pot, LED merah padam |
| T10 Riwayat | `python -m model.station --port /dev/ttyUSB0 --history` | `VALID`/`HISTORY_TRUNCATED`, jumlah record dan rentang seq wajar |
| T8 LED | lihat LED saat auth/lock | hijau = auth OK, merah = lock/error |

Tidak ada perintah I2C scan di RTL. Pembacaan ADS1115 diverifikasi lewat nilai
tegangan pada respons auth; kalau belum ada sampel sukses, voltage 0. Kalau I2C
gagal setelah sampel baik, sampel terakhir dipertahankan dan LED merah menyala.

---

## 12. Troubleshooting

| Gejala | Kemungkinan | Tindakan |
|---|---|---|
| LED mati, UART tidak merespons | clock PL tidak aktif / bitstream belum termuat | cek `pl0_ref`, `dmesg`, ulangi `fpgautil` |
| UART garbage / `CRC mismatch` | clock PL bukan 100 MHz, baud/port salah, ground tidak common | cek `pl0_ref`; pastikan 115200 dan GND CP2102 ke Pmod |
| `fpgautil: command not found` | paket FPGA manager belum ada | cek `/usr/sbin/fpgautil`, pasang paket Kria, atau pakai JTAG |
| `fpgautil` gagal / permission | bukan root, app bawaan masih termuat | `sudo`, `sudo xmutil unloadapp` |
| `VALID` tapi voltage 0 | ADS1115 tidak terdeteksi | cek VDD 3V3, SCL/SDA, ADDR ke GND, pull-up; LED merah |
| Voltage tidak berubah | wiper pot tidak ke AIN0 / belum 1 detik | pindahkan wiper, tunggu ≥1 detik |
| Selalu `INVALID_HMAC` | key/ID tidak cocok | pakai repo ini; key demo `bytes(range(32))`, ID `BAT\x01` |
| Selalu `BATTERY_LOCKED` | 3 RESULT gagal / lock manual | `unlock` atau power cycle |
| `JTAG ... Cannot halt hart` | bug hw_server 2024.2 | pakai `fpgautil` atau hw_server 2024.1 |
| Build berhenti di `validate_bd_design` FREQ_HZ | port BD tidak cocok dengan pin PS | jalankan `build.tcl` versi ini (membaca frekuensi aktual dari pin PS) |
| `Permission denied` port serial | user tidak di grup `dialout` | `sudo usermod -aG dialout $USER`, login ulang |
| Dashboard jatuh ke mode simulasi padahal CP2102 tersambung | auto-deteksi melewati port “ML Carrier Card” atau salah pilih adapter | cek `/dev/ttyUSB*`, paksa `--fpga /dev/ttyUSBx` |
| Self-check `[FAIL]` | board tidak menjawab, bitstream belum termuat, atau voltage 0 | muat bitstream (bagian 6), cek wiring I2C/LED, ulangi `--check` |

---

## 13. Batasan demo (jangan diklaim lebih)

- Kunci masih fixed `bytes(range(32))`; PUF belum di jalur demo.
- UNLOCK belum diautentikasi; siapa pun yang bisa mengirim frame bisa membuka.
- Seq, riwayat, dan lock volatil; daya putus menghapus semuanya.
- Dump riwayat maksimal ~215 ms pada 115200 baud; station memakai timeout 2 detik.
- ADS1115 masih modul terpisah; tegangan bisa dipalsukan sebelum FPGA.
- Bitstream khusus `xck26-sfvc784-2LV-c`; jangan pakai di varian SOM lain.
- `pl_clk0` milik PS/firmware boot. Kalau firmware stock tidak memasang 100 MHz,
  bitstream ini tidak akan berjalan benar; lihat bagian 5.
- Heartbeat di Pmod 4 hanya menandakan clock PL; liveness aplikasi tetap dicek lewat UART.
- Uji fisik KV260 belum dilakukan per 21 Okt 2026.
