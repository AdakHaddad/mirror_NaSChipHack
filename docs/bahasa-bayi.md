# SeBatt — Ringkasan untuk Semua Orang

Dokumen ini menjelaskan SeBatt tanpa istilah teknis. Cocok untuk latihan pitch,
menjelaskan proyek ke teman atau keluarga, dan menjawab pertanyaan juri yang
bukan dari bidang chip.

## Versi 15 detik

> SeBatt adalah buku catatan anti-curang untuk baterai motor listrik. Setiap
> catatan tegangan diberi nomor halaman dan stempel rahasia. Kalau ada halaman
> yang dihapus atau angkanya diubah, stasiun penukaran bisa tahu dan menolak
> baterainya.

## Versi 60 detik

> Saat menukar baterai, stasiun hanya melihat tegangan saat itu. Stasiun tidak
> tahu apakah baterai itu minggu lalu dikuras sampai rusak, karena riwayatnya
> dilaporkan oleh software yang bisa diubah.
>
> SeBatt menaruh chip kecil di dalam baterai. Setiap beberapa jam chip itu
> mencatat tegangan, memberi nomor urut, dan menandatanganinya dengan kunci
> rahasia yang tidak pernah keluar dari chip. Saat baterai masuk stasiun,
> stasiun memeriksa nomor dan tanda tangannya.
>
> Kalau ada catatan yang dihapus, nomornya bolong. Kalau angkanya diubah, tanda
> tangannya tidak cocok. Dua-duanya membuat stasiun menolak baterai.
>
> Di demo: baterai normal diterima. Baterai yang dikuras sampai 2,0 V lalu
> catatannya dihapus ditolak. Catatan yang sama diubah dari 2,0 V menjadi 3,6 V
> juga ditolak.

## Analogi meja makan

> Bayangkan paspor baterai. Setiap halaman punya nomor urut dan segel lilin
> yang hanya bisa dibuat oleh baterai itu. Seseorang boleh merobek halaman, tapi
> nomor yang hilang akan ketahuan. Orang itu juga tidak bisa memalsukan segelnya.
>
> Atau: ini seperti odometer mobil yang tidak bisa diputar mundur.

## Masalahnya, tanpa istilah teknis

Baterai yang pernah rusak bisa terlihat normal lagi setelah diisi ulang.
Kerusakannya permanen, tetapi buktinya hilang. Yang mencatat riwayat adalah
software BMS, dan software bisa diubah atau diganti.

Akibatnya:

- baterai berbahaya bisa masuk lagi ke jaringan penukaran,
- pemilik bisa menyembunyikan kerusakan saat menjual atau mengklaim garansi,
- baterai curian sulit dibedakan dari baterai resmi,
- nilai baterai bekas menjadi sulit dipercaya.

## Cara kerjanya dalam lima langkah

1. **Ukur.** Chip membaca tegangan baterai secara berkala.
2. **Beri nomor.** Setiap catatan mendapat nomor urut yang hanya bisa naik.
3. **Beri stempel.** Chip menghitung tanda tangan rahasia dari isi catatan.
4. **Simpan.** Chip menyimpan 64 catatan terakhir.
5. **Periksa.** Saat penukaran, stasiun meminta catatan, menghitung ulang tanda
   tangan, dan memeriksa nomor urutnya.

Kalau semua cocok, baterai **DITERIMA**. Kalau ada yang tidak cocok, baterai
**DITOLAK** dan alasannya ditampilkan.

## Yang sudah ada dan yang belum

| Sudah ada | Belum ada |
|---|---|
| Rumus pengaman (SHA-256 dan HMAC) di Python dan di chip | Jalur riwayat lengkap di chip |
| Program stasiun untuk uji terima, tolak, dan hitung kecepatan | Tampilan dashboard dan kartu kesehatan baterai |
| Prototipe di board lama sebagai cadangan | Port ke board KV260 milik panitia |
| Rencana tes dan alur demo | Video cadangan |

Kalimat jujur yang bisa dipakai:

> "Kami sudah membuktikan bagian pengamannya. Sekarang kami memindahkannya dari
> prototipe berbasis prosesor ke rangkaian chip murni di KV260."

## Demo dalam tiga adegan

| Adegan | Yang dilakukan | Hasil |
|---|---|---|
| 1. Pemakaian normal | Kenop diputar di zona aman, lalu "Tukar baterai" | **DITERIMA**, riwayat terverifikasi |
| 2. Dikuras lalu catatan dihapus | Kenop diputar sampai 2,0 V, catatan dihapus, lalu "Tukar baterai" | **DITOLAK**, catatan hilang |
| 3. Angka diubah | 2,0 V diganti menjadi 3,6 V, lalu "Tukar baterai" | **DITOLAK**, data diubah |

## Kenapa ini penting

- **Keamanan:** baterai rusak tidak kembali beredar dan berisiko terbakar.
- **Uang:** operator terlindungi dari klaim garansi palsu, penjualan baterai
  rusak, dan baterai curian.
- **Kepercayaan:** baterai bekas bisa dinilai dari riwayat yang bisa dipercaya,
  bukan dari cerita penjual.

## Jawaban untuk orang awam

| Pertanyaan | Jawaban |
|---|---|
| Ini baterai? | Bukan. Ini chip kecil yang ditanam di dalam paket baterai. |
| Menggantikan BMS? | Tidak. BMS tetap mengatur pengisian; SeBatt mengamankan data yang dilaporkan BMS. |
| Pemilik bisa mengakalinya? | Bisa mengubah data setelah keluar dari chip, tetapi stasiun mendeteksinya. Pemilik tidak bisa membuat stempel palsu. |
| Kalau dayanya dicabut? | Nomor urut kembali ke nol. Stasiun melihat nomor yang mundur dan menolak. Produk akhir butuh memori permanen. |
| Kenapa tidak pakai software saja? | Software bisa di-flash ulang. Kunci dan proses stempel harus berada di hardware. |
| Cepat? | Ya. Perhitungan di chip memakan ratusan siklus clock; lewat kabel serial hanya milidetik. |
| Mahal? | Model bisnisnya lisensi IP. Target biaya di bawah 1 dolar per chip; FPGA hanya prototipe. |
| Apa bedanya dengan chip baterai biasa? | Chip biasa mengamankan **identitas** baterai. SeBatt mengamankan **isi riwayatnya**. |
| Datanya bisa dipalsukan? | Pada demo, sensor masih terpisah. Pada chip akhir, sensor berada di chip yang sama. |

## Kalimat yang boleh dan jangan dipakai

| Boleh | Jangan |
|---|---|
| "Kami sudah membuktikan pengaman dan protokolnya." | "Semua fitur sudah selesai." |
| "PUF adalah rencana tahap dua." | "PUF sudah jalan di demo." |
| "Demo memakai ADC terpisah." | "ADC sudah menyatu di chip." |
| "Riwayat 64 catatan adalah target demo." | "Riwayat 64 catatan sudah jalan." |
| "Counter masih hilang saat daya putus." | "Rollback sudah teratasi sepenuhnya." |

## Glosarium untuk orang awam

| Istilah | Arti sederhana |
|---|---|
| ADC | Alat yang mengubah tegangan listrik menjadi angka. |
| BMS | Otak baterai yang mengatur pengisian dan melindungi sel. |
| HMAC | Stempel rahasia yang dibuat dari isi catatan dan kunci. |
| Kunci | Rahasia yang hanya dimiliki chip; dipakai untuk membuat stempel. |
| Nonce | Angka acak baru untuk setiap penukaran, supaya jawaban lama tidak bisa dipakai ulang. |
| Nomor urut (seq) | Nomor halaman catatan; hanya bisa naik, tidak bisa mundur. |
| PUF | Sidik jari unik dari silikon chip. |
| Ring buffer | Buku catatan 64 halaman; halaman paling lama ditimpa saat penuh. |
| FPGA | Chip yang bisa diprogram ulang; dipakai sebagai prototipe. |
| KV260 | Board FPGA dari panitia yang dipakai saat demo. |
