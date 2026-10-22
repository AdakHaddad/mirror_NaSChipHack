# Baterai Palsu (Cmod S7)

Cmod S7 berperan sebagai baterai tiruan untuk demo keaslian. Rancangannya sama dengan chip SeBatt di KV260 dan memakai identitas baterai yang sama (BAT-0001), tetapi dibangun dengan kunci yang berbeda. Stasiun memeriksa autentikasi dengan kunci asli, sehingga baterai ini ditolak dengan status INVALID_HMAC.

Status: bitstream dibangun 22 Oktober 2026 pukul 09.37 dengan Vivado 2026.1 (0 error, 0 critical warning, WNS +55,272 ns pada clock 12 MHz). Berhasil diuji di board pada hari yang sama: Cmod S7 ditolak saat penukaran, lalu KV260 diterima kembali setelah kabel dipindah.

## Isi Folder

| Berkas | Isi |
|---|---|
| rtl/cmod_s7_palsu_top.v | Wrapper Cmod S7. UART di Pmod JA, sumber sampel tetap 3000 mV, tanpa ADC |
| cmod_s7_palsu.xdc | Constraint pin Cmod S7 |
| build.tcl | Menyalin auth_ctrl.v ke build/, mengganti kunci pada salinan, lalu membangun bitstream |
| program.tcl | Memuat bitstream ke Cmod S7 melalui JTAG |

Folder rtl/ milik tim tidak diubah. Kunci palsu hanya ada di build/auth_ctrl_palsu.v hasil build.tcl. Apabila baris kunci di auth_ctrl.v berubah, build.tcl berhenti dengan pesan galat agar skrip ini diperbarui.

## Perbedaan dengan Chip Asli

| | KV260 (asli) | Cmod S7 (palsu) |
|---|---|---|
| Identitas baterai | 0x42415401 | 0x42415401, disalin |
| Kunci | 00 01 02 … 1F | Basis tiap 4 byte di-XOR 0xA5 |
| Sumber sampel | ADS1115 | Nilai tetap 3000 mV |
| UART | Pmod J2 pin 7 dan 8 | Pmod JA pin 7 dan 8 |
| Clock | 100 MHz dari PS | 12 MHz osilator board |

## Sambungan

Posisi pin UART dan GND sama dengan Pmod J2 KV260, sehingga kabel dari CP2102 cukup dipindah dari satu board ke board lain pada posisi yang sama.

| Pin Pmod JA | Pin paket | Sinyal | Ke CP2102 |
|---|---|---|---|
| 7 | H3 | uart_tx | RXD |
| 8 | H1 | uart_rx | TXD |
| 11 | – | GND | GND |

Cmod S7 mendapat daya dari kabel micro-USB-nya sendiri. Kabel yang sama dipakai untuk memuat bitstream.

## Membangun dan Memuat

```powershell
cd fpga/cmod_s7_palsu
vivado -mode batch -source build.tcl
vivado -mode batch -source program.tcl
```

Bitstream tersimpan di build/cmod_s7_palsu.bit. Saat memuat, hanya Cmod S7 yang tersambung ke JTAG.

## Uji Sebelum Demo

1. Sambungkan CP2102 ke Pmod JA Cmod S7, lalu jalankan self-check.

   ```powershell
   py -3.14 -m model.station --check --port COM8
   ```

   Hasil yang diharapkan: STATUS [OK], AUTH [FAIL] dengan INVALID_HMAC, dan READ_HIST [FAIL] dengan INVALID_HMAC karena tag ringkasan juga dibuat dengan kunci palsu. Self-check tidak mengirim RESULT, sehingga LED Cmod S7 belum berubah. Kegagalan kedua baris ini adalah tanda baterai palsu bekerja.

2. Pindahkan kabel kembali ke KV260 dan jalankan self-check yang sama. Ketiga baris harus [OK].

## Pemakaian Saat Demo

1. Dashboard berjalan dengan --fpga COM8 dan kabel CP2102 di KV260. Tukar baterai menghasilkan DITERIMA.
2. Cabut kabel 3 pin dari Pmod J2 KV260 dan colokkan ke Pmod JA Cmod S7 pada posisi yang sama.
3. Tekan Tukar baterai. Hasil yang diharapkan: DITOLAK, INVALID_HMAC pada tahap autentikasi. LED led[3] di Cmod S7 menyala.
4. Kembalikan kabel ke KV260 dan tekan Tukar baterai. Hasilnya kembali DITERIMA, karena riwayat dan hitungan gagal di KV260 tidak tersentuh.

Selama kabel di Cmod S7, jangan tekan Muat riwayat, karena grafik akan menampilkan riwayat baterai palsu. Angka gagal berturut-turut di dashboard sempat menunjukkan milik Cmod S7 sampai penukaran berikutnya ke KV260.

## Batasan

- Baterai palsu ini menjalankan rancangan SeBatt yang sama dengan kunci lain. Tiruan yang tidak memiliki chip SeBatt sama sekali tidak menjawab, dan stasiun melaporkan kesalahan komunikasi.
- Pada purwarupa, kunci asli tersimpan di bitstream. Tiruan yang berhasil membaca bitstream asli dapat menyalin kuncinya. Tahap 2 memakai RO-PUF agar kunci tidak tersimpan.
