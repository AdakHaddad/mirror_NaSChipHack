# Catatan Teknis 18 Oktober 2026

Ringkasan diskusi Guntur tentang arah teknis dan demo menjelang onsite. Dibaca semua anggota sebelum rapat.

## Kenapa Arah Perlu Disesuaikan

Proposal yang lolos menjanjikan dua hal yang akan dicek juri:

1. Setiap sampel tegangan dari ADC diberi **nomor urut** dan **ditandatangani HMAC** di dalam chip, lalu disimpan sebagai **riwayat**. Stasiun menolak riwayat yang diubah atau dihapus.
2. Semua itu dikerjakan **rangkaian RTL tanpa prosesor lunak**.

Poin 1 adalah satu-satunya pembeda SeBatt dari chip komersial. Contohnya TI BQ40Z50, yang sudah mengukur tegangan dan mengautentikasi baterai tetapi tidak menandatangani riwayatnya.

Kondisi repo saat ini:

- Core SHA-256 dan HMAC sudah lolos 9/9 vektor uji. Ini fondasi yang tetap dipakai.
- Desain FPGA memakai MicroBlaze dan firmware C di Nexys A7/Basys 3. Saat onsite kita wajib memakai **AMD Kria KV260** dari panitia, dan proposal menulis tanpa prosesor lunak.
- ADC, nomor urut, buffer riwayat, dan lock di chip belum ada. Tegangan masih angka tetap 3700 mV.

## Keputusan yang Diusulkan

- Jalur MicroBlaze **dibekukan** dan disimpan sebagai cadangan, tidak dihapus.
- Tenaga RTL dialihkan ke rangkaian ini, semuanya di logika FPGA:

```
ADC → spi_adc → auth_ctrl (nomor urut, buffer riwayat, lock) → hmac_sha256 → uart_if → laptop stasiun
```

- Gambaran alurnya ada di [gambar alur teknis](../gambar/alur-teknis.png). Format pesan UART, perintah riwayat, dan kode status disepakati di rapat sebagai kontrak antara Muqtada (RTL) dan Budi (Python).

## Catatan KV260

- **Clock** logika FPGA berasal dari prosesor ARM di board, jadi blok Zynq UltraScale+ MPSoC tetap dipasang di block design sebagai sumber clock.
- **Cara menjalankan.** Boot image Ubuntu KV260 dari SD card, lalu muat bitstream dengan `xmutil` atau `fpgautil`. Bagian ini cocok dipegang Muqtada karena terbiasa dengan Linux.
- **UART** bawaan board terhubung ke prosesor, bukan ke logika FPGA. UART dari rangkaian kita keluar lewat **PMOD** dan adaptor USB-UART (misalnya CP2102).
- **Hanya ada satu PMOD** (8 pin). Pin itu cukup untuk SPI ADC (4 pin) dan UART (2 pin).
- Board baru kita pegang 21 Oktober, jadi seluruh rangkaian **diuji dulu di Cmod S7**.
- Cek apakah instalasi Vivado sudah mendukung device **xck26**.

## Rancangan Demo

Cerita: baterai dipakai sekitar seminggu, sekali dikuras sampai habis, lalu catatan kejadian itu dihapus.

1. **Pemakaian normal.** Hasilnya diterima.
2. **Juri memutar kenop** sampai baterai terkuras, lalu catatannya dihapus. Layar menampilkan "Catatan jam 14–17 hilang, DITOLAK".
3. **Angka diubah** dari 2,0 V menjadi 3,6 V. Hasilnya "DITOLAK".

Ketentuan pendukung:

- Tulisan di layar memakai bahasa awam, tanpa kode status. Hurufnya besar.
- Satu slide pembanding: "BMS biasa: DITERIMA", "SeBatt: DITOLAK".
- Peran BMS curang dijalankan di **laptop kedua**, di antara board dan laptop stasiun.
- Board diberi label "CHIP SeBatt", dan LED besar di breadboard menyala hijau atau merah.
- Buffer berisi 64 sampel. Satu titik mewakili 3 jam, jadi totalnya sekitar 8 hari.
- Apabila board tidak merespons dalam 10 detik, video cadangan diputar.
- Replay dan lock tidak ditampilkan di demo. Keduanya disiapkan untuk tanya jawab.

## Pembagian Tugas

| Orang | Tugas |
|---|---|
| Muqtada | auth_ctrl (nomor urut, buffer, lock). Boot KV260 dan memuat bitstream |
| Guntur | spi_adc, uart_if, membeli dan merangkai ADC, uji di Cmod S7, constraint PMOD KV260, pitch deck |
| Budi | Dashboard stasiun, program BMS curang, testbench cocotb, dataset cadangan dari data baterai, angka bisnis bersumber |

## Jadwal

| Waktu | Target |
|---|---|
| Senin 19 Okt | Sepakat soal MicroBlaze dan protokol. Beli ADC, adaptor USB-UART, potensiometer |
| Selasa 20 Okt | Rangkaian lengkap jalan di Cmod S7. Video cadangan direkam |
| Rabu 21 Okt | Boot dan port ke KV260 |
| Kamis 22 Okt, 22.00 | Kirim slide, repositori, dan README 2 halaman |
| Jumat 23 Okt, 08.00 | Batas pengumpulan panitia |

README 2 halaman wajib memuat diagram blok, cara menjalankan, hasil uji, dan poin penggunaan AI.

## Jawaban untuk Pertanyaan Juri

| Pertanyaan | Jawaban |
|---|---|
| Kalau daya dicabut? | Nomor urut kembali ke nol, dan stasiun mendeteksinya sebagai rollback. Produk akhir butuh penghitung permanen (NVM) |
| Apakah kunci bisa dibaca? | Di produk tidak. key_vault dibuat sekali tulis tanpa port baca, dan setiap chip punya kunci berbeda |
| Apakah data ADC bisa dipalsukan? | Bisa, sebelum masuk chip. Pada chip akhir, ADC berada di dalam chip yang sama |
| Kalau basis data bocor? | Kunci ikut bocor. Ini batasan skema kunci simetris |
| Apa bedanya dengan BQ40Z50? | BQ40Z50 merekam riwayat tetapi tidak menandatanganinya, dan riwayat itu dapat di-reset |

## Kerapian Repositori

- File hasil generate Vivado (.dcp, .xci, cache) dikeluarkan dari repo. Proyek dibangun ulang dari skrip TCL.
- Tambahkan .gitattributes agar perbedaan line ending Windows dan Linux tidak membuat diff palsu.
- Atur email git sesuai akun GitHub masing-masing:

```
git config --global user.email "email@contoh.com"
```
