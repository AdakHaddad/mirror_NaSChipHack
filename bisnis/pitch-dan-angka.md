# Pitch Bisnis, Framework, dan Asumsi Angka

Status: bahan Demo Day 23 Oktober 2026. Setiap angka diberi label **[Sumber]**
(dengan tautan) atau **[Asumsi]** (dengan dasar dan cara memverifikasi). Jangan
memakai angka **[Asumsi]** di panggung tanpa menyebut asumsinya; sesi tanya
jawab akan mengetes dasarnya.

Dokumen pendukung: [lean-canvas.md](lean-canvas.md) (kanvas),
[business_model.md](business_model.md) (model bisnis lengkap),
[../pitch/pitch_deck.md](../pitch/pitch_deck.md) (naskah 5 menit), dan
[../pitch/catatan-pembanding.md](../pitch/catatan-pembanding.md) (pembanding
produk). Bila angka berbeda antar dokumen, dokumen ini yang dipakai karena
setiap angka punya status dan sumber.

## 1. Kalimat inti pitch

> Gauge baterai di pasar sudah merekam riwayat pemakaian, tetapi riwayat itu
> hanya dilindungi kata sandi dan dapat di-reset. SeBatt menandatangani setiap
> sampel dengan nomor urut di dalam silikon, sehingga stasiun dapat
> membuktikan riwayat tidak diubah, dihapus, atau diputar balik. Bagi operator
> swap dan penyedia pembiayaan baterai, nilai sisa baterai menjadi dapat
> dipertanggungjawabkan.

Tiga hal yang harus muncul di slide: masalah (riwayat tidak dapat dibuktikan),
solusi (tanda tangan per sampel di silikon, tanpa perangkat lunak di tengah),
model (lisensi IP + modul retrofit + layanan verifikasi).

## 2. Framework yang dipakai

1. **Lean Canvas** — kotak di [lean-canvas.md](lean-canvas.md); semua bagian
   **[Isi]** dijawab di dokumen ini.
2. **Perhitungan bottom-up**, bukan TAM atas-bawah. Angka TAM "USD 1,8 Miliar"
   dan "CAGR 24,5%" di business_model.md belum bersumber; **jangan dipakai di
   pitch**. Hitungan dimulai dari jumlah baterai nyata di jaringan swap
   Indonesia, kali kerugian per kasus, lalu pangsa yang wajar.
3. **Unit economics per aliran pendapatan** (lisensi, modul, layanan) dengan
   margin dan biaya infrastruktur cloud (basisnya di
   [alur-teknis.md](../docs/catatan-teknis/alur-teknis.md) §"Isi Basis Data").
4. Setiap tabel angka punya kolom status: **[Sumber]** + tautan, atau
   **[Asumsi]** + dasar.

Kurs yang dipakai di dokumen ini: **USD 1 = Rp 16.000 [Asumsi]**.

## 3. Ukuran pasar (bottom-up)

### 3.1 Populasi dan jaringan (bersumber)

| Angka | Nilai | Waktu | Sumber |
|---|---:|---|---|
| Kendaraan listrik (KBLBB) di Indonesia | 207.478 unit | 2024 | [Kemenperin via CNN Indonesia](https://www.cnnindonesia.com/otomotif/20250425162635-603-1222670/populasi-kendaraan-listrik-loncat-78-persen-di-indonesia) |
| Kendaraan listrik (KBLBB) di Indonesia | 541.678 unit | Agustus 2026 | [Kemenperin via Okezone, 15 Okt 2026](https://digital.okezone.com/view/2026/10/15/4/106303/pengguna-kendaraan-listrik-di-indonesia-terus-bertambah) |
| Sepeda motor listrik (bagian dari KBLBB) | 196.051 unit | Juni 2025 | [Kemenhub via Bisnis.com](https://otomotif.bisnis.com/read/20251024/275/1923129/kemenhub-jumlah-kendaraan-listrik-207478-unit-sepeda-motor-paling-banyak) |
| Target pemerintah 2030 | 13 juta motor listrik | – | [Kemenperin via Tempo](https://www.tempo.co/ekonomi/outlook-2025-menanti-perkembangan-infrastruktur-kendaraan-listrik-1196867) |
| Stasiun swap SWAP Energi | 1.500+ stasiun | 2026 | [swap.id](https://www.swap.id/) |
| Stasiun swap Electrum | 400+ BSS, 16 juta penukaran total | 2025 | [electrum.id](https://electrum.id/id/about-us) |
| Stasiun swap Volta | 300+ lokasi | Sep 2025 | [TYCORUN, sekunder](https://www.tycorun.com/blogs/industry-insights/top-10-electric-two-wheller-with-swappable-batteries-in-indonesia) |
| Tarif tukar Honda Mobile Power Pack | ± Rp 8.000 per swap | 2026 | [chargeevcalculator, sekunder](https://chargeevcalculator.com/id/en/guide/tukar-baterai-motor-listrik) |

Sumber sekunder dipakai hanya sebagai pembanding kasar; utamakan daftar resmi
operator saat wawancara.

### 3.2 Baterai terpasang hari ini (bottom-up)

Operator tidak mempublikasikan jumlah baterai, jadi diperkirakan lewat rasio
baterai per stasiun.

| Komponen | Nilai | Status |
|---|---|---|
| Rasio baterai per stasiun | 8–12 unit | **[Asumsi]** — satu stasiun melayani puluhan pengguna harian; verifikasi dengan operator |
| Stasiun total 3 jaringan utama | ± 2.200 | [Sumber] — 1.500 (SWAP) + 400 (Electrum) + 300 (Volta) |
| **Baterai swap terpasang** | **± 22.000 unit (rentang 15.000–30.000)** | **[Asumsi]** dari perkalian di atas |

Ini adalah **SAM hari ini**. Jangan klaim "100.000 baterai dalam 2 tahun" dari
business_model.md sebagai target utama; simpan sebagai skenario optimis yang
membutuhkan 2–3 operator besar sekaligus.

### 3.3 Nilai yang diselamatkan (value pool)

| Komponen | Nilai | Status |
|---|---|---|
| Baterai per pilot (satu operator menengah) | 5.000–10.000 unit | **[Asumsi]** |
| Persentase riwayat bermasalah per tahun | 1–3% | **[Asumsi]** — tanya operator: pernah menemukan riwayat diubah/di-reset? |
| Kerugian per kasus | Rp 2–4 juta | **[Asumsi]** — nilai sisa pack Rp 6–10 juta, kerugian sebagian + downtime |

Contoh hitung untuk 5.000 baterai (nilai tengah):
`5.000 × 2% × Rp 3 juta = Rp 300 juta/tahun` per operator (rentang Rp 100–600
juta).

Harga layanan SeBatt **Rp 15.000/baterai/tahun [Asumsi]** = Rp 75 juta/tahun
untuk 5.000 baterai — sekitar **25% dari nilai tengah yang diselamatkan**
(Rp 300 juta) dan hanya **0,15–0,25% dari nilai pack**. Framing untuk pitch:
biaya verifikasi seperti premi asuransi kecil; pada skenario tengah operator
menghemat sekitar 4 kali biaya verifikasi.

### 3.4 Aliran pendapatan dan contoh hitung

| Aliran | Harga | Contoh hitung | Status harga |
|---|---|---|---|
| Lisensi IP ke pembuat gauge/BMS | USD 50–100k upfront + royalti USD 0,25–0,50/die | 1 desain + 100.000 chip: USD 75–150k (± Rp 1,2–2,4 M) | **[Asumsi]** — benchmark harga lisensi IP sebelum pitch bisnis |
| Modul retrofit | USD 3,50/unit, margin kotor ± 55% (BOM ± USD 1,60) | 10.000 unit: USD 35k penjualan, USD 19,25k laba kotor (± Rp 308 juta) | **[Asumsi]** |
| Layanan verifikasi | Rp 15.000/baterai/tahun atau Rp 50–100/swap | 10.000 baterai: Rp 150 juta/tahun | **[Asumsi]** |

Catatan: pendapatan lisensi adalah tujuan jangka panjang (butuh desain menang
di mitra); pendapatan modul dan layanan adalah jalur pendek yang bisa dimulai
dengan pilot.

### 3.5 Biaya dan modal pra-silikon

| Komponen | Perkiraan | Status |
|---|---|---|
| MPW / tape-out SKY130 | USD 10–50k per shuttle | **[Asumsi]** — cek harga terbaru program seperti chipIgnite/Tiny Tapeout saat menyusun anggaran |
| EDA alur ASIC | USD 10–50k/tahun (PoC sekarang Rp 0: Vivado + alur terbuka) | **[Asumsi]** |
| Cloud + KMS/HSM | Rp 10–30 juta/tahun untuk 10.000 baterai (data inti 4 MB per 10.000 baterai; lihat alur-teknis.md) | **[Asumsi]** |
| Sertifikasi keamanan | Baru relevan saat masuk produksi | – |

### 3.6 Titik impas kasar (bukan proyeksi)

Pilot 10.000 baterai: layanan Rp 150 juta/tahun + laba modul sekali bayar
± Rp 308 juta. Bila biaya tim paruh waktu dan cloud Rp 150–250 juta/tahun,
pilot sudah bisa jalan **tanpa investor**, asalkan operator mau bayar. Angka
**[Asumsi]**; fungsinya menunjukkan jalur non-dilutif (hibah, hadiah, pilot
berbayar), bukan janji keuntungan.

### 3.7 Sensitivitas dan jawaban siap pakai

| Pertanyaan juri | Jawaban |
|---|---|
| "Operator tidak mau bayar" | Pilot kecil dulu; kalau operator nol, pembeli tetap ada: produsen BMS/gauge (klaim garansi), perusahaan pembiayaan, pembeli baterai bekas. |
| "Pasarnya kecil" | Bottom-up hari ini puluhan ribu baterai; target nasional 13 juta motor listrik 2030; nilai per baterai naik saat baterai menjadi aset yang dibiayai. |
| "Kenapa tidak jual chip sendiri?" | Butuh volume ratusan ribu unit untuk menutup wafer + GTM chip; model IP core menghindari capex fabrika dan langsung masuk ke chip mitra. |
| "Apa bedanya dengan BQ40Z50?" | Jawab dengan kolom pembanding di [catatan-pembanding.md](../pitch/catatan-pembanding.md); klaim hanya "riwayat bertanda tangan belum kami temukan di produk komersial". |
| "Kalau firmware operator sendiri curang?" | Justru itu kasusnya: tanda tangan dibuat di silikon yang sama dengan ADC, bukan di firmware yang bisa di-flash ulang. |

## 4. Posisi: startup atau bukan?

**Untuk pitch: ya, bingkai sebagai startup deep-tech** — masalah → pelanggan
pertama → model monetisasi → traksi PoC. Juri menilai kejelasan itu, bukan
legalitas entitas.

**Untuk eksekusi: jangan mengklaim skala venture.** Siklus silikon panjang,
pembelinya korporat (operator/BMS/pabrikan), dan biaya besar (EDA, tape-out)
datang setelah pilot, bukan sebelum. Jalur bertahap yang masuk akal:

1. **Okt 2026** — Demo Day: hadiah/hibah non-dilutif + jaringan operator.
2. **Q1–Q2 2027** — pilot berbayar dengan 1 operator (metrik: baterai
   terpasang, kasus riwayat tidak cocok yang terdeteksi).
3. **2027–2028** — MPW SKY130 + kemitraan gauge/BMS lokal (jalur ICDeC).
4. **2028+** — spin-off atau lisensi; investor baru relevan bila pilot
   menunjukkan penyerapan dan harga diterima.

Kriteria keputusan (putuskan bersama tim setelah Demo Day):

| Pertanyaan | Ya | Tidak |
|---|---|---|
| Ada anggota yang mau full-time pasca lulus? | jalur startup | jalur riset + lisensi |
| Ada operator yang mau pilot berbayar? | jalur startup | pilot internal dulu |
| Ada akses pendanaan non-dilutif untuk MPW? | percepat tape-out | tunda silikon, fokus modul/layanan |

Kalau mayoritas "tidak", posisi paling jujur adalah **proyek riset kampus
dengan jalur lisensi** — tetap kuat di pitch teknis, tanpa overclaim
komersial.

**Yang tidak boleh diklaim** (pasti ditanya di Q&A):

- PUF sudah terpasang di demo — belum; demo memakai kunci tetap, PUF baru
  model (`model/ro_puf.py`).
- Angka TAM USD 1,8 Miliar dan CAGR 24,5% — tidak bersumber; jangan disebut.
- Sudah ada pilot/produksi chip — belum; yang ada PoC FPGA + rencana.
- "Menghilangkan semua penipuan" — SeBatt membuktikan riwayat, bukan
  menggantikan pengukuran arus/sensor lain.

## 5. Tugas validasi (sebelum pitch bisnis berikutnya)

1. Wawancara 2–3 operator (SWAP, Electrum, Volta/Oyika, atau armada kampus):
   pernah menemukan riwayat diubah/di-reset? berapa kerugian per kasus? berapa
   harga wajar per baterai per tahun?
2. Wawancara 1–2 produsen BMS/gauge: bersedia integrasi IP? syaratnya?
3. Benchmark harga lisensi IP sejenis dan royalti per chip.
4. Cek biaya MPW dan EDA terbaru untuk anggaran tape-out.
5. Ganti semua label **[Asumsi]** di dokumen ini dengan angka wawancara; update
   [lean-canvas.md](lean-canvas.md) bagian **[Isi]**.

## 6. Sumber

- Kemenperin: populasi KBLBB 207.478 (2024), 274.802 (Juni 2025) —
  [Bisnis.com](https://otomotif.bisnis.com/read/20250828/275/1906541/pemerintah-sebut-populasi-kendaraan-listrik-terus-meningkat-berkat-insentif),
  [CNN Indonesia](https://www.cnnindonesia.com/otomotif/20250425162635-603-1222670/populasi-kendaraan-listrik-loncat-78-persen-di-indonesia)
- Kemenperin: 541.678 unit KBLBB hingga Agustus 2026 —
  [Okezone, 15 Okt 2026](https://digital.okezone.com/view/2026/10/15/4/106303/pengguna-kendaraan-listrik-di-indonesia-terus-bertambah)
- Kemenhub: 196.051 sepeda motor listrik per Juni 2025 —
  [Bisnis.com](https://otomotif.bisnis.com/read/20251024/275/1923129/kemenhub-jumlah-kendaraan-listrik-207478-unit-sepeda-motor-paling-banyak)
- Target 13 juta motor listrik 2030 —
  [Tempo](https://www.tempo.co/ekonomi/outlook-2025-menanti-perkembangan-infrastruktur-kendaraan-listrik-1196867)
- SWAP Energi 1.500+ stasiun — [swap.id](https://www.swap.id/)
- Electrum 400+ BSS, 16 juta penukaran —
  [electrum.id](https://electrum.id/id/about-us)
- Volta 300+ lokasi (sekunder) dan tarif swap Honda (sekunder) —
  [TYCORUN](https://www.tycorun.com/blogs/industry-insights/top-10-electric-two-wheller-with-swappable-batteries-in-indonesia),
  [chargeevcalculator](https://chargeevcalculator.com/id/en/guide/tukar-baterai-motor-listrik)
