# Cara Demo dengan Board dan Dashboard

Langkah operasional demo SeBatt di KV260 dengan dashboard stasiun Python. Alur ini sudah dicoba di board pada 22 Oktober 2026 dengan kenop langsung di A0 dan berjalan sesuai urutan di bawah. Rangkaian LiPo 3S dan profil lipo3s belum dicoba di board. Demo baterai palsu dengan Cmod S7 ada di [README baterai palsu](../../fpga/cmod_s7_palsu/README.md). Cerita dan peran tiap orang ada di [alur-demo.md](alur-demo.md), rangkaian ADC di [rangkaian-adc.md](rangkaian-adc.md).

## Prasyarat

- KV260 dengan kartu SD Ubuntu dan adaptor 12 V.
- Laptop stasiun dengan Vivado Hardware Manager, Python 3.14, dan pyserial.
- Adaptor CP2102, modul ADS1115, kenop, LED hijau, merah, dan heartbeat.
- Bitstream yang sudah diuji di board.

## Sambungan Pmod J2

| Pin | Sinyal | Tujuan |
|---|---|---|
| 1 | SCL | ADS1115 SCL |
| 2 | SDA | ADS1115 SDA |
| 3 | src_sel | GND (membaca ADS1115). Jangan dibiarkan terbuka |
| 4 | led_hb | 330 Ω, LED heartbeat, GND |
| 5, 11 | GND | GND bersama: ADS1115, CP2102, (−) LiPo |
| 6 | 3,3 V | VDD ADS1115 |
| 7 | uart_tx | RXD CP2102 |
| 8 | uart_rx | TXD CP2102 |
| 9 | LED hijau | 330 Ω, LED, GND |
| 10 | LED merah | 330 Ω, LED, GND |

Pin 5V pada CP2102 tidak disambung.

## Persiapan Sebelum Tampil

1. Nyalakan KV260 dan tunggu Ubuntu selesai boot. Clock 100 MHz untuk rancangan baru tersedia setelah PS menyala.
2. Muat bitstream melalui Vivado: Hardware Manager, Open Target, Auto Connect, pilih xck26, lalu Program Device. LED heartbeat di Pmod 4 harus berkedip.
3. Cek nomor port CP2102 di Device Manager. Contoh di bawah memakai COM8.
4. Jalankan self-check. Ketiga baris harus [OK].

   ```powershell
   py -3.14 -m model.station --check --port COM8
   ```

   Self-check dan dashboard tidak dapat membuka port yang sama secara bersamaan. Jalankan self-check lebih dulu, baru dashboard.

5. Jalankan dashboard sesuai rangkaian yang dipakai.

   ```powershell
   # Rangkaian LiPo 3S (pembagi 120k, kenop 10k, 15k)
   py -3.14 -m web.server --fpga COM8 --profil lipo3s --open

   # Kenop langsung 0-3,3 V di A0, tanpa LiPo
   py -3.14 -m web.server --fpga COM8 --open
   ```

   Penanda di kanan atas dashboard harus hijau dengan tulisan "FPGA · COM8".

6. Uji satu kali dengan menekan Tukar baterai. Hasilnya harus DITERIMA dan LED hijau menyala.
7. Tampilkan dashboard layar penuh di proyektor dan siapkan video cadangan.

## Urutan Demo

Dua aturan menentukan urutan tombol.

- Tombol Hapus catatan dan Ubah angka selalu menyerang catatan terbaru yang belum diverifikasi. FPGA menambah satu catatan setiap detik, sehingga tombol serangan harus ditekan selagi kenop masih di bawah agar yang diserang memang catatan terkuras.
- Serangan tetap aktif setelah DITOLAK sampai tombol Pulihkan ditekan.

| Adegan | Kenop | Tombol | Hasil |
|---|---|---|---|
| 1. Pemakaian normal | Atas atau normal | Tukar baterai | DITERIMA, LED hijau, kartu kesehatan terisi |
| 2. Terkuras lalu dihapus | Juri memutar ke bawah dan menahannya | Tunggu 2–3 detik, Muat riwayat, Hapus catatan, Tukar baterai | DITOLAK (HISTORY_GAP), LED merah |
| 3. Angka diubah | Tetap di bawah | Pulihkan, tunggu 1–2 detik, Muat riwayat, Ubah angka, Tukar baterai | DITOLAK (INVALID_HMAC), titik merah dengan panah di grafik |
| 4. Penutup | Kembali ke atas | Pulihkan, Tukar baterai | DITERIMA, kartu kesehatan menunjukkan Terkuras dalam 1 berwarna merah |

Adegan 4 selalu dijalankan. Riwayat asli diterima dan kejadian terkuras tetap tercatat, sehingga cerita demo selesai dengan utuh. Hitungan gagal berturut-turut juga kembali ke 0. Tanpa adegan 4, hitungan berhenti di 2/3 dan satu kegagalan berikutnya akan mengunci chip.

## Pertanyaan Juri yang Dapat Diperagakan

| Pertanyaan | Yang dilakukan | Hasil |
|---|---|---|
| Bagaimana kalau dicoba terus? | Ubah angka lalu Tukar baterai tiga kali tanpa Pulihkan | Chip terkunci, LED merah menyala terus, tombol Buka kunci chip muncul |
| Bagaimana kalau dayanya dicabut? | Muat ulang bitstream, lalu Tukar baterai tanpa me-restart dashboard | DITOLAK (HISTORY_ROLLBACK). Akui bahwa produk membutuhkan penghitung di memori permanen |
| Bagaimana kalau jawaban lama dikirim ulang? | Tutup dashboard, jalankan station CLI, ketik attack replay | DITOLAK (INVALID_HMAC), karena tag ringkasan terikat pada nonce lama |

Perintah station CLI untuk pertanyaan ketiga:

```powershell
py -3.14 -m model.station --port COM8 --interactive --profil lipo3s
```

## Hal yang Perlu Diingat

- Setiap kali bitstream dimuat ulang atau daya board dicabut, seq chip kembali ke 0. Tutup dashboard dengan Ctrl+C lalu jalankan lagi sebelum demo berikutnya.
- Tombol Reset tampilan hanya membersihkan layar. Riwayat di FPGA tidak terhapus.
- Tombol Cabut daya chip dinonaktifkan di mode FPGA. Pencabutan daya dilakukan langsung di board.
- Setelah chip terkunci, tekan Buka kunci chip sebelum melanjutkan demo.

## Penanganan Masalah

| Gejala | Penyebab | Tindakan |
|---|---|---|
| Penanda di dashboard bertuliskan Model Python, bukan FPGA | Dashboard dijalankan tanpa --fpga | Jalankan ulang dengan --fpga COM8 |
| Dashboard gagal membuka port | Port dipakai program lain atau nomor COM salah | Tutup station CLI atau PuTTY, cek Device Manager |
| Tegangan tidak berubah saat kenop diputar, tetap 17,40 V (profil lipo3s) atau 3,82 V (profil sel) | Pmod 3 terbuka atau terhubung ke 3,3 V, sehingga chip mencatat nilai tetap 3000 mV | Sambungkan Pmod 3 ke GND |
| Grafik tidak bertambah | I2C ke ADS1115 terputus | Cek SCL, SDA, dan VDD ADS1115, lalu Muat riwayat |
| Penukaran pertama ditolak HISTORY_ROLLBACK | Bitstream dimuat ulang tetapi dashboard tidak di-restart | Restart dashboard |
| Tombol serangan menampilkan "Tidak ada catatan baru" | Belum ada sampel setelah verifikasi terakhir | Tunggu 1–2 detik, Muat riwayat, ulangi |
| Board tidak merespons | Bitstream tidak termuat atau UART terputus | Jalankan mode simulasi (`py -3.14 -m web.server --open`) atau putar video cadangan |
