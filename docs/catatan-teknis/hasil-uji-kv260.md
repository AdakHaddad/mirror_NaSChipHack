# Hasil Uji SeBatt di Kria KV260

Pengujian pertama rangkaian SeBatt di board Kria KV260 panitia, 21 Oktober 2026 (hari pertama onsite). Semua angka di dokumen ini diukur di board kecuali yang diberi label lain.

## Susunan Uji

| Bagian | Isi |
|---|---|
| Board | AMD Kria KV260, Kria Ubuntu dari kartu SD (dipakai hanya untuk menyalakan clock PL) |
| Bitstream | kv260_top.bit, Vivado 2024.2, xck26-sfvc784-2LV-c, dibangun 21 Okt 11.46 dari commit f36d639. Build ulang pukul 15.16 menghasilkan isi konfigurasi yang identik (hash isi 46c245355c6874eb) |
| Pemrograman | JTAG lewat Vivado 2026.1 Hardware Manager (Auto Connect, Program Device pada xck26), tanpa login ke Ubuntu |
| Komunikasi | CP2102 di Pmod J2 pin 7/8, 115200 8N1, laptop Windows (COM8) |
| Stasiun | model/station.py mode interaktif, dijalankan dengan Python 3.14 |
| Sumber tegangan | Tahap A: sumber tetap 3000 mV (Pmod 3 ke 3V3). Tahap B: ADS1115 dan potensiometer 10 kΩ di A0 (Pmod 3 ke GND) |

## Sambungan Pin

Penomoran mengikuti Pmod Digilent 12 pin. Pin 1–6 berada di satu baris dengan pin 5 (GND) dan pin 6 (3V3) di ujung daya. Pin 7–12 di baris seberang, pin 7 tepat di seberang pin 1.

```
[ujung daya]                         [ujung jauh]
 6(3V3)  5(GND)  4(HB)  3(SRC)  2(SDA)  1(SCL)
12(3V3) 11(GND) 10(MRH)  9(HJU)  8(RX)   7(TX)
```

| Pmod J2 | Pin FPGA | Sinyal | Sambung ke | Catatan |
|---|---|---|---|---|
| 1 | H12 | SCL | ADS1115 SCL | Terbaca 3,3 V saat diam (pull-up) |
| 2 | E10 | SDA | ADS1115 SDA | Terbaca 3,3 V saat diam. Jangan tersentuh GND |
| 3 | D10 | src_sel | GND untuk ADS1115, 3V3 untuk sumber tetap 3000 mV | Jangan dibiarkan terbuka, karena terbaca 1 |
| 4 | C11 | led_hb | Resistor 330 Ω, LED, GND | Berkedip sekitar 6 Hz bila PL hidup |
| 5, 11 | – | GND | GND ADS1115, potensiometer, CP2102, katoda LED | Semua GND disatukan |
| 6, 12 | – | 3V3 | VDD ADS1115, ujung atas potensiometer | Jangan memakai 5 V |
| 7 | B10 | uart_tx | RXD CP2102 | Terbaca 3,3 V saat diam |
| 8 | E12 | uart_rx | TXD CP2102 | Pull-up internal |
| 9 | D11 | led_green | Resistor 330 Ω, LED hijau, GND | Menyala setelah perintah diterima |
| 10 | B11 | led_red | Resistor 330 Ω, LED merah, GND | Menyala saat terkunci atau ADS1115 gagal dibaca |

| Modul | Pin | Sambung ke |
|---|---|---|
| ADS1115 | VDD | Pmod 6 (3V3) |
| | GND | Pmod 5 |
| | SCL | Pmod 1 |
| | SDA | Pmod 2 |
| | ADDR | GND (alamat 0x48) |
| | A0 | Kaki tengah potensiometer |
| | A1–A3, ALRT | Tidak dipakai |
| Potensiometer 10 kΩ | Kaki luar | 3V3 dan GND |
| | Kaki tengah | ADS1115 A0 |
| CP2102 | RXD, TXD, GND | Pmod 7, Pmod 8, Pmod 5 |
| | VCC/5V | Tidak disambung. Jumper logika di 3,3 V |

Kabel micro-USB KV260 memberi dua port COM dari chip FTDI. Pada laptop uji, COM15 adalah konsol Ubuntu dan COM14 tidak dipakai. JTAG untuk Vivado berada di kanal yang sama dan tidak muncul sebagai COM.

## Hasil

### 1. Bring-up

| Uji | Hasil |
|---|---|
| LED heartbeat di Pmod 4 | Berkedip, sehingga bitstream termuat dan clock PL dari PS menyala |
| STATUS | Dijawab dalam 9,9–16,2 ms, unlocked, fail_cnt = 0 |
| AUTH (sumber tetap) | VALID, 3000 mV, tanda tangan HMAC dari FPGA cocok dengan perhitungan stasiun |
| READ_HIST | VALID atau HISTORY_TRUNCATED, 64 catatan dengan seq berurutan dan tanda tangan ringkasan cocok |

### 2. Riwayat bertanda tangan terhadap serangan

Setiap serangan dijalankan pada dump asli yang baru diambil dari chip, lalu diubah oleh program BMS curang (perintah attack di station.py) sebelum diverifikasi.

| Serangan | Contoh | Hasil stasiun |
|---|---|---|
| Ubah tegangan satu catatan | seq 128: 3000 menjadi 3600 mV | Ditolak, INVALID_HMAC |
| Ubah tegangan dari ADS1115 | seq 1240: 1985 menjadi 3600 mV | Ditolak, INVALID_HMAC |
| Sembunyikan kejadian tegangan rendah | seq 1647: 502 menjadi 3600 mV | Ditolak, INVALID_HMAC |
| Hapus catatan di tengah | seq 128–130 dibuang | Ditolak, HISTORY_GAP |
| Potong catatan terbaru dan palsukan rentang | 5 catatan terbaru dibuang | Ditolak, INVALID_HMAC karena tanda tangan ringkasan tidak cocok |
| Putar ulang jawaban lama | dump untuk nonce lama | Ditolak, INVALID_HMAC |
| Dump asli tanpa perubahan (kontrol) | 64 catatan | VALID |

Semua serangan ditolak dan semua dump asli diterima.

### 3. Penguncian chip

| Uji | Hasil |
|---|---|
| LOCK, lalu AUTH | Chip membalas CHIP_LOCKED, stasiun menampilkan BATTERY_LOCKED. Diulang empat kali, tetap terkunci |
| UNLOCK, lalu AUTH | VALID kembali |
| STATUS setelah serangan | fail_cnt kembali 0 setelah RESULT VALID berikutnya |

Penguncian otomatis setelah tiga RESULT gagal berturut-turut sudah lolos simulasi, tetapi belum diperagakan di board.

### 4. ADS1115

| Uji | Hasil |
|---|---|
| Kenop di tengah | 1651 mV, sesuai setengah dari 3,3 V |
| Kenop diputar | 1985–1990 mV, lalu 501–502 mV |
| Catatan baru | Bertambah satu per detik dari ADS1115 |
| Pembacaan dibandingkan multimeter | Belum dilakukan |

### 5. Kinerja

| Metrik | Target proposal | Hasil | Keterangan |
|---|---|---|---|
| Latensi autentikasi ujung ke ujung | < 20 ms | 13,7 ms rata-rata (50 percobaan), 14,2–14,7 ms per percobaan tunggal | Diukur di laptop, termasuk latensi USB Windows dan pengiriman RESULT |
| *Throughput* autentikasi | ≥ 50 per detik | 73,1 per detik, 50/50 VALID | Satu RESULT ikut terkirim per autentikasi |
| READ_HIST 64 catatan | – | 292,5 ms | Termasuk verifikasi 65 tag di stasiun |
| Latensi HMAC di FPGA | ≤ 300 siklus | Sekitar 452 siklus ditambah overhead | Perhitungan dari simulasi, belum diukur di board |
| WNS di 100 MHz | Fmax ≥ 50 MHz | +1,466 ns | Laporan sintesis Vivado, dilaporkan Muqtada |

## Temuan Selama Uji

- **Pmod 3 yang dibiarkan terbuka terbaca 1.** Pull-down internal FPGA kalah, sehingga chip memakai sumber tetap 3000 mV. Pmod 3 harus disambung ke GND untuk ADS1115 dan ke 3V3 untuk sumber tetap. Aturan ini sudah dicatat di RUNBOOK dan spesifikasi.
- **AUTH menandatangani tegangan valid terakhir saat ADS1115 gagal dibaca.** Tanda kegagalan adalah berhentinya catatan riwayat baru dan LED merah, bukan isi AUTH_RESP. Ini dicatat sebagai batasan.
- **LED merah tidak pernah padam setelah satu penolakan.** Flag error di auth_ctrl hanya dibersihkan saat reset, dan LED hijau menyala setiap chip selesai membalas, bukan saat stasiun menerima. Sudah diperbaiki di RTL: LED kini mengikuti putusan RESULT terakhir, dan merah padam setelah RESULT VALID atau UNLOCK. Uji cocotb baru (24/24) lolos. Perbaikan ini menunggu build ulang bitstream dan belum diuji di board.
- **Pmod 2 (SDA) yang tersambung ke GND membuat pembacaan I2C bernilai 0 mV.** Kabel SDA harus terpisah dari GND.
- **HISTORY_TRUNCATED muncul pada dump pertama setelah stasiun dijalankan ulang.** Jangkar stasiun kembali ke 0 sementara catatan lama di chip sudah tertimpa. Status ini diterima dengan peringatan, dan dump berikutnya VALID.
- **Ubuntu Kria tidak perlu login untuk memprogram lewat JTAG**, karena clock PL sudah menyala setelah boot. Login tetap diperlukan untuk mengecek atau memperbaiki clock pl0_ref. Kata sandi board diminta ke panitia.

## Belum Diuji

- Perbandingan pembacaan ADS1115 dengan multimeter.
- Penguncian otomatis setelah tiga RESULT gagal di board.
- Rollback setelah daya chip diputus.
- Uji fungsi 1.000 percobaan per skenario.
- Frekuensi pl0_ref yang sebenarnya (perlu login).
- Pembagi tegangan 12 V di casing.
- Daya FPGA dan perkiraan ASIC SKY130.

## Cara Mengulang

1. Rakit kabel sesuai tabel Sambungan Pin dengan board dalam keadaan mati.
2. Nyalakan KV260 dengan kartu SD Kria Ubuntu, tunggu sekitar 2 menit.
3. Vivado → Open Hardware Manager → Open Target → Auto Connect → klik kanan xck26 → Program Device → kv260_top.bit.
4. Pastikan LED di Pmod 4 berkedip. Board yang dimatikan atau di-reboot perlu diprogram ulang.

### Perintah PowerShell

Mencari port COM CP2102 dan KV260:

```powershell
Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'COM\d+' } | Select-Object Name, Manufacturer
```

CP2102 muncul sebagai "Silicon Labs CP210x USB to UART Bridge". Port FTDI adalah milik KV260. Semua perintah di bawah dijalankan dari folder repo, dan tidak ada program lain (misalnya PuTTY) yang sedang membuka port CP2102.

```powershell
cd C:\Users\GunturS\HKITB

# Mode interaktif (dipakai untuk demo)
py -3.14 -m model.station --port COM8 --interactive

# Satu kali autentikasi
py -3.14 -m model.station --port COM8

# Satu kali pembacaan riwayat
py -3.14 -m model.station --port COM8 --history

# Throughput dan latensi, 100 autentikasi
py -3.14 -m model.station --port COM8 --benchmark --count 100

# Uji tanpa board (model Python)
py -3.14 -m model.station --offline --demo
```

Ganti COM8 dengan nomor port CP2102 di laptop yang dipakai.

### Perintah di mode interaktif

| Perintah | Fungsi | Hasil yang diharapkan |
|---|---|---|
| status | Status kunci dan penghitung gagal di chip | Chip: unlocked, fail_cnt=0 |
| auth | Autentikasi dengan nonce baru | Voltage: ... mV → VALID |
| history | Membaca dan memverifikasi riwayat | 64 records ... → VALID (dump pertama setelah station dijalankan bisa HISTORY_TRUNCATED) |
| attack tamper [seq] [mV] | Mengubah satu catatan (bawaan 3600 mV) | INVALID_HMAC → DITOLAK |
| attack delete [n] | Membuang n catatan di tengah | HISTORY_GAP → DITOLAK |
| attack cut [n] | Membuang n catatan terbaru dan memalsukan rentang | INVALID_HMAC → DITOLAK |
| attack replay | Memakai dump untuk nonce lama | INVALID_HMAC → DITOLAK |
| lock / unlock | Mengunci atau membuka chip | auth → BATTERY_LOCKED saat terkunci |
| reset-anchor | Mengosongkan jangkar seq di stasiun | Dipakai setelah chip diprogram ulang |
| bench | 50 autentikasi beruntun | Rate dan Latency |
| quit | Keluar | |

Setiap hasil ditolak dilaporkan ke chip lewat RESULT. Tiga penolakan berturut-turut mengunci chip, sehingga sisipkan history yang VALID di antara serangan apabila chip tidak ingin terkunci. Gunakan unlock untuk membuka kembali.
