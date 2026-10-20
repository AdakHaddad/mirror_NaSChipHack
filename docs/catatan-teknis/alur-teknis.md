# Alur Teknis SeBatt

![Alur teknis SeBatt: rantai perangkat (A) dan urutan protokol saat penukaran (B)](../gambar/alur-teknis.png)

Gambar di atas adalah arsitektur target yang dijanjikan di proposal. Dokumen ini menjelaskannya sebagai satu alur berurutan, dari baterai dibuat sampai stasiun memutuskan menerima atau menolak. Contoh angka dipakai di setiap langkah. Tegangan ditulis dalam volt agar mudah dibaca, padahal yang tersimpan di chip berupa angka mentah dari ADC.

## Dua Istilah yang Perlu Dipahami Dulu

**Nomor urut (seq).** Angka yang menempel pada setiap catatan tegangan, mirip nomor halaman buku. Angka ini hanya dapat bertambah satu: 121, 122, 123, dan seterusnya. Apabila ada catatan yang dibuang, urutannya akan bolong, misalnya 149 langsung ke 153.

**Tanda tangan (tag HMAC).** Kode 32 byte yang dihitung dari isi catatan dan kunci rahasia K. Sifatnya:
- isi catatan berubah sedikit saja, kodenya berubah total,
- tanpa K, kode yang benar tidak dapat dibuat,
- siapa pun yang memegang K dapat menghitung ulang kode tersebut untuk memeriksa.

K hanya dimiliki chip dan basis data operator.

## Kenapa Riwayat Tegangan Penting

Tegangan yang turun saat baterai dipakai adalah hal normal. Yang dicari SeBatt adalah kejadian ketika tegangan keluar dari batas aman, karena kejadian itu merusak sel secara permanen.

Contoh untuk satu sel Li-ion NMC (angka berbeda untuk jenis sel lain, cek datasheet sel yang dipakai):

| Kondisi | Tegangan per sel | Arti |
|---|---|---|
| Penuh | sekitar 4,2 V | Normal |
| Pemakaian biasa | 4,2 V turun ke sekitar 3,3 V | Normal |
| Batas bawah aman | sekitar 2,5–3,0 V | BMS seharusnya memutus arus |
| Terkuras dalam | di bawah batas aman, misalnya 2,0 V | Kapasitas turun permanen dan sel berisiko saat diisi lagi |
| Kelebihan isi | di atas sekitar 4,2 V | Merusak dan berisiko panas |

Zona merusak biasanya tersentuh karena baterai dibiarkan kosong berminggu-minggu, BMS di-bypass, atau pengisian memakai charger yang tidak sesuai. Pemiliknya memiliki alasan untuk menyembunyikan kejadian ini saat menjual baterai bekas, mengajukan klaim garansi, atau menukar baterai sewaan.

Stasiun hanya melihat tegangan saat ini. Baterai yang minggu lalu terkuras sampai 2,0 V lalu diisi penuh lagi terlihat normal di 4,2 V. Hanya riwayat yang menunjukkan kejadian tersebut, dan SeBatt memastikan riwayat itu tidak dapat dihapus atau diubah tanpa ketahuan.

Batasannya, tegangan paket dapat menutupi satu sel yang rusak. Produk yang lebih lengkap mencatat tegangan per sel, arus, dan suhu.

Masalah serupa sudah terjadi di HP. iPhone menampilkan jumlah siklus dan kesehatan baterai, tetapi di pasar servis beredar alat yang diiklankan dapat menulis ulang kedua data tersebut. SeBatt membawa persoalan yang sama ke baterai kendaraan listrik, yang harganya jauh lebih tinggi.

## Langkah 0. Saat Baterai Dibuat

1. Chip SeBatt dipasang di dalam paket baterai, bersama ADC dan pembagi tegangan.
2. Chip diberi ID, misalnya BAT-0001, dan kunci rahasia K.
3. Basis data operator mencatat: ID = BAT-0001, kunci = K, seq terakhir = 0.

## Langkah 1. Selama Baterai Dipakai (Berulang Terus)

Langkah ini berjalan sendiri di dalam chip setiap selang waktu tertentu (100 ms pada demo, yang mewakili 3 jam pemakaian). Tidak ada perangkat lunak yang ikut campur.

1. **Ukur.** ads1115_ctrl meminta modul ADS1115 (lewat I2C) membaca tegangan paket. Contohnya, hasilnya 3,7 V.
2. **Beri nomor.** auth_ctrl menaikkan penghitung, misalnya dari 120 menjadi 121.
3. **Simpan.** auth_ctrl menulis pasangan (121, 3,7 V) ke buffer riwayat di dalam chip.

Setelah beberapa hari, isi buffer kira-kira seperti ini:

| seq | Tegangan |
|---|---|
| 121 | 3,7 V |
| 122 | 3,6 V |
| … | … |
| 150 | 2,0 V (baterai terkuras dalam) |
| … | … |
| 184 | 3,8 V |

Buffer menampung 64 catatan terakhir. Saat penuh, catatan paling lama ditimpa.

Pada langkah ini catatan **belum ditandatangani**. Catatan cukup disimpan, karena buffer berada di dalam chip dan tidak dapat diubah oleh BMS atau program apa pun.

## Langkah 2. Baterai Masuk Stasiun

1. Stasiun membuat angka acak baru (nonce), misalnya 7f3a…, lalu mengirimnya ke chip. Nonce yang selalu baru mencegah jawaban lama dipakai ulang.
2. Chip membalas dengan ID, seq terakhir (184), tegangan saat ini (3,8 V), dan tanda tangan atas semua data tersebut beserta nonce.
3. Stasiun bertanya ke basis data: seq terakhir yang diketahui untuk BAT-0001 adalah 120. Karena itu stasiun meminta catatan mulai dari seq 121.

## Langkah 3. Chip Mengirim Riwayat dan Menandatanganinya

Untuk setiap catatan di buffer, dimulai dari seq 121, chip melakukan:

1. Mengambil catatan, misalnya (121, 3,7 V).
2. Menghitung tanda tangan dari ID + seq + tegangan dengan kunci K. Hasilnya misalnya a91f….
3. Mengirim (121, 3,7 V, a91f…) ke stasiun.

Langkah ini diulang sampai seq 184, lalu chip mengirim pesan selesai berisi jumlah catatan (64).

Inilah saat catatan ditandatangani. Tanda tangan dibuat di dalam chip, tepat sebelum catatan keluar. Setelah keluar, catatan dan tanda tangannya melewati jalur yang dapat disadap BMS, tetapi perubahan apa pun akan terlihat di langkah berikutnya.

## Langkah 4. Basis Data Memeriksa

Untuk setiap catatan yang diterima, basis data melakukan:

1. **Hitung ulang tanda tangan** dari ID + seq + tegangan dengan K miliknya, lalu bandingkan dengan tanda tangan dari chip. Hasilnya harus sama.
2. **Periksa urutan.** seq harus 121, 122, 123, dan seterusnya tanpa lompatan sampai 184.

Selain itu, tanda tangan jawaban pada langkah 2 juga diperiksa dengan nonce yang tadi dikirim.

## Langkah 5. Keputusan

- Semua cocok: baterai **diterima**. Basis data menyimpan seq terakhir = 184 untuk penukaran berikutnya.
- Ada yang tidak cocok: baterai **ditolak**, dengan alasan yang ditampilkan di layar.
- Stasiun memberi tahu chip hasilnya. Setelah tiga kali ditolak berturut-turut, chip mengunci diri dan tidak mau menjawab lagi.

## Kartu Kesehatan Baterai

Setelah riwayat dinyatakan valid, stasiun merangkumnya menjadi kartu yang mirip menu Battery Health di iPhone:

```
┌ Kesehatan Baterai BAT-0001 ───────────┐
│ Siklus pengisian    : 12              │
│ Terkuras dalam      : 1 kali          │
│ Tegangan terendah   : 2,0 V           │
│ Riwayat             : TERVERIFIKASI ✓ │
└───────────────────────────────────────┘
```

- **Siklus pengisian** dihitung setiap kali tegangan naik dari bawah ambang rendah ke atas ambang tinggi.
- **Terkuras dalam** dihitung setiap kali tegangan turun di bawah batas aman.
- Apabila riwayat ditolak, kartu menampilkan "Riwayat: TIDAK DAPAT DIPERCAYA ✗" tanpa angka.

Perhitungan ini dilakukan program stasiun dari riwayat yang sudah diverifikasi, sehingga tidak menambah rangkaian di chip. Jumlah siklus dari tegangan saja merupakan perkiraan. Gauge sungguhan menghitungnya dari arus masuk dan keluar (*coulomb counting*).

## Contoh Kecurangan dan Cara Ketahuan

BMS yang curang berada di antara chip dan stasiun. BMS dapat mengubah atau membuang catatan yang lewat, tetapi tidak memiliki K.

| Kecurangan | Yang terjadi | Hasil |
|---|---|---|
| Catatan seq 150–152 (saat terkuras) dibuang | Stasiun menerima 149 lalu 153 | Ditolak: catatan hilang |
| Tegangan seq 150 diubah dari 2,0 V menjadi 3,6 V | Tanda tangan seq 150 dihitung dari 2,0 V, hasil hitung ulang dari 3,6 V berbeda | Ditolak: data diubah |
| BMS membuat tanda tangan baru untuk 3,6 V | Tidak dapat, karena BMS tidak memegang K | Ditolak: data diubah |
| Jawaban penukaran minggu lalu dikirim ulang | Nonce lama tidak cocok dengan nonce baru | Ditolak: jawaban lama |
| Daya chip dicabut agar penghitung kembali ke 0 | seq terakhir lebih kecil dari 120 yang tercatat | Ditolak: penghitung diputar balik |

## Siapa Mengerjakan Apa di Dalam Chip

| Modul | Peran dalam alur |
|---|---|
| ads1115_ctrl + i2c_master | Langkah 1.1: membaca ADS1115 lewat I2C |
| auth_ctrl | Langkah 1.2–1.3: memberi nomor dan menyimpan. Langkah 2–3: melayani stasiun. Langkah 5: menghitung kegagalan dan mengunci |
| key_vault | Menyimpan K. Hanya terhubung ke hmac_sha256 |
| hmac_sha256 | Langkah 2.2 dan 3.2: menghitung tanda tangan |
| uart_if | Jalur pesan ke dan dari stasiun |

Byte awal pesan yang ditandatangani membedakan dua jenis tanda tangan: 0x53 untuk catatan (ID, seq, tegangan) dan 0x41 untuk jawaban nonce (nonce, ID, seq terakhir, tegangan). Dengan pembeda ini, tanda tangan catatan tidak dapat dipakai sebagai jawaban nonce.

## Memori di Chip

| Data | Ukuran |
|---|---|
| Buffer riwayat, 64 catatan × (seq 4 byte + tegangan 2 byte) | 384 byte |
| Penghitung nomor urut | 4 byte |
| Kunci K | 32 byte |
| ID | 4 byte |
| Total | sekitar 420 byte |

Ukuran ini kecil. Di FPGA hanya memakai sebagian kecil satu blok RAM.

**Daya putus.** Buffer dan penghitung disimpan di memori yang isinya hilang saat daya putus. Chip mendapat daya dari paket baterai, sehingga saat baterai terkuras sangat dalam, chip dapat ikut mati dan catatan kejadian itu hilang. Produk membutuhkan memori permanen (flash, EEPROM, atau FRAM) atau cadangan daya kecil untuk chip.

**Buffer penuh.** 64 catatan dengan satu catatan per 3 jam mencakup sekitar 8 hari. Apabila baterai tidak ditukar lebih lama, catatan paling lama tertimpa. Chip memberi tahu seq tertua yang masih tersimpan, sehingga stasiun dapat membedakan dua keadaan:
- bolong di awal riwayat berarti catatan lama tertimpa (riwayat terpotong, bukan kecurangan),
- bolong di tengah riwayat berarti ada catatan yang dibuang di jalan (kecurangan).

**Arah produk.** Chip cukup menyimpan ringkasan peristiwa, misalnya jumlah siklus, tegangan terendah, jumlah kejadian di bawah batas aman, dan lama berada di zona merusak. Penghitung siklus yang akurat membutuhkan sensor arus. Ukurannya belasan byte, tidak pernah penuh, dan mudah disimpan di memori permanen. Demo tetap memakai buffer 64 catatan agar grafik riwayat terlihat.

## Isi Basis Data

Basis data berada di server operator, bukan di stasiun, karena berisi kunci K semua baterai. Stasiun hanya meneruskan data ke server.

| Data per baterai | Ukuran |
|---|---|
| ID | 4 byte |
| Kunci K | 32 byte |
| Nomor urut terakhir | 4 byte |
| Status (normal atau terkunci) | 1 byte |
| Total | sekitar 40 byte |

Untuk 100.000 baterai totalnya sekitar 4 MB. Tanda tangan tidak disimpan, karena cukup dihitung ulang saat penukaran lalu dibuang.

Riwayat juga tidak wajib disimpan utuh. Setelah dinyatakan valid, basis data dapat menyimpan ringkasannya saja, misalnya "tegangan terendah 2,0 V pada catatan ke-150". Apabila riwayat lengkap tetap disimpan (seq dan tegangan tanpa tanda tangan), kebutuhannya sekitar 400 byte per penukaran, atau sekitar 15 GB per tahun untuk 100.000 baterai yang ditukar sekali sehari.

**Konsekuensi.** Stasiun harus terhubung ke server setiap kali penukaran, karena hanya server yang memegang K. Solusi tahap produk adalah tanda tangan asimetris (misalnya ECDSA). Chip menyimpan kunci privat, stasiun cukup menyimpan kunci publik, sehingga verifikasi dapat dilakukan tanpa koneksi. Gantinya, rangkaian tanda tangan di chip jauh lebih besar daripada HMAC.

## Pada Demo

| Produk nyata | Pada demo |
|---|---|
| Sel baterai, pembagi tegangan, ADC | Potensiometer atau satu sel, pembagi tegangan, modul ADS1115 (I2C, 16 bit) |
| Chip SeBatt | FPGA Kria KV260 |
| Bus CAN di konektor | UART melalui PMOD dan adaptor USB-UART |
| Stasiun dan basis data | Program Python di laptop stasiun |
| BMS curang | Program perantara di laptop kedua |

## Batasan

- ADC masih modul terpisah (ADS1115 lewat I2C), sehingga tegangan dapat dipalsukan sebelum masuk chip. Pada chip akhir, ADC berada di dalam chip.
- Penghitung dan buffer riwayat hilang saat daya putus, termasuk saat baterai terkuras sangat dalam. Produk membutuhkan memori permanen atau cadangan daya.
- K juga tersimpan di basis data, sehingga basis data yang bocor berarti kunci bocor, dan stasiun harus terhubung ke server.
- Kunci uji di demo sama untuk semua chip. Pada produk, setiap chip memiliki kunci sendiri.

## Status Pengerjaan per 20 Oktober (revisi ADC: ADS1115/I2C)

| Bagian | Status |
|---|---|
| hmac_sha256 dan inti SHA-256 | Ada, lolos 9/9 vektor uji |
| key_vault | Ada, versi uji (kunci masih dapat dibaca dan ditulis ulang) |
| Emulator stasiun Python | Ada untuk autentikasi (nonce + HMAC); riwayat/seq belum |
| ads1115_ctrl + i2c_master | Ada, lolos 2/2 uji cocotb (20 Okt); lihat `sim/test_ads1115.py` |
| uart_if versi RTL | Ada, lolos 4/4 uji rantai auth (20 Okt) |
| auth_ctrl + axil_master + sebatt_top | Ada, lolos 4/4 uji `make auth` (20 Okt) |
| Bitstream Cmod S7 | Ada (20 Okt), timing WNS +52,746 ns; uji board T6/T7/T9 belum |
| Nomor urut, buffer riwayat, penguncian di chip | Belum |
| Permintaan riwayat dan pemeriksaan urutan di stasiun | Belum |
| Kartu kesehatan baterai di dashboard | Belum |
| Port ke KV260 | Timing 100 MHz PASS (WNS +2,749 ns); pin PMOD/bit.bin belum |
