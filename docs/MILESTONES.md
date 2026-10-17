# Milestone Proyek

Rencana kerja dari pengumuman sampai Demo Day. Centang [x] setiap tugas yang selesai. Pembagian PIC (penanggung jawab) di bawah adalah usulan awal dan dapat diubah tim.

| # | Milestone | Tenggat | Hasil akhir |
|---|---|---|---|
| M0 | Pendaftaran dan mini proposal | 14 Okt | Mini proposal dan surat pernyataan terkirim |
| M1 | Pengumuman | 15 Okt | Lolos seleksi |
| M2 | Fondasi teknis | 17 Okt | RTL SHA-256 dan HMAC lolos vektor uji FIPS 180-4 dan RFC 4231 |
| M3 | Integrasi di board sendiri | 20 Okt | Riwayat tegangan bertanda tangan tampil VALID/INVALID di emulator, dengan kunci tetap |
| M4 | Onsite hari 1–2 | 21–22 Okt | Berjalan di board panitia, metrik Tabel 1 terukur |
| M5 | Demo Day | 23 Okt | Pitch, demo live, video cadangan |

Urutan kerja mengikuti jalur kritis. Demo dengan kunci tetap harus berjalan sebelum PUF dikerjakan.

---

## M0–M1 — Pendaftaran dan pengumuman

| Tugas | PIC | Selesai |
|---|---|---|
| Mini proposal sesuai template panitia | Semua | [x] |
| Surat pernyataan orisinalitas ditandatangani semua anggota | Semua | [x] |
| Pengumuman peserta lolos | Semua | [x] |

## M2 — Fondasi teknis (17 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| RTL SHA-256 dan HMAC lolos vektor uji di Verilator | Muqtada | [ ] |
| Guntur ikut verifikasi agar RTL tidak bergantung pada satu orang | Guntur | [ ] |
| Pilih dan beli modul ADC SPI, plus cadangan | Dimas | [ ] |

## M3 — Integrasi di board sendiri (18–20 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| spi_adc diuji di Cmod S7 atau Artix-7 | Dimas | [ ] |
| Penghitung nomor urut dan penyimpanan riwayat sampel di auth_ctrl | Muqtada | [ ] |
| uart_if dan emulator stasiun Python dengan 1.000 percobaan per skenario | Guntur | [ ] |
| Sintesis Yosys ke SKY130 (jumlah sel, luas, daya) | Muqtada | [ ] |
| Pengukuran RO-PUF di dua board, keputusan pakai atau tidak (19 Okt) | Guntur | [ ] |
| Business model satu slide: harga, pembeli, kerugian per kasus dalam rupiah | Dimas | [ ] |
| Kerangka pitch deck | Semua | [ ] |
| Video demo cadangan | Guntur | [ ] |
| Uji kelulusan: VALID/INVALID dengan tegangan asli dari ADC | Semua | [ ] |

## Pertanyaan untuk pembekalan online (16–19 Okt)

| Pertanyaan | Jawaban |
|---|---|
| Board FPGA dan tools EDA yang disediakan | |
| Pin header untuk SPI dan UART | |
| Boleh membawa RTL yang disiapkan sebelum 21 Okt | |

## M4 — Onsite hari 1–2 (21–22 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Porting ke board panitia | Muqtada, Guntur | [ ] |
| Ukur metrik Tabel 1 | Guntur | [ ] |
| Business model final | Dimas | [ ] |
| Latihan pitch | Semua | [ ] |

## M5 — Demo Day (23 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Pitch dan demo live | Semua | [ ] |
