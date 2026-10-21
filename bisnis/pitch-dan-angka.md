# Pitch Bisnis, Framework, dan Asumsi Angka

Status: bahan Demo Day 23 Oktober 2026. Setiap angka punya label **[Sumber]**
(dengan tautan) atau **[Asumsi]** yang selalu disertai **Dasar** (perhitungan
atau sumber acuan) dan **cara verifikasi**. Jangan memakai angka **[Asumsi]**
tanpa menyebut dasarnya di sesi tanya jawab.

Dokumen pendukung: [lean-canvas.md](lean-canvas.md) (kanvas),
[business_model.md](business_model.md) (model bisnis lengkap),
[../pitch/pitch_deck.md](../pitch/pitch_deck.md) (naskah 5 menit), dan
[../pitch/catatan-pembanding.md](../pitch/catatan-pembanding.md) (pembanding
produk). Bila angka berbeda antar dokumen, dokumen ini yang dipakai karena
setiap angka punya status, dasar, dan sumber.

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
4. Setiap asumsi wajib punya **Dasar** dan rencana verifikasi.

Kurs yang dipakai: **USD 1 = Rp 16.000 [Asumsi]** — perbarui angka kurs saat
menyusun slide final.

## 3. Ukuran pasar (bottom-up)

### 3.1 Populasi dan jaringan (bersumber)

| Angka | Nilai | Waktu | Sumber |
|---|---:|---|---|
| Kendaraan listrik (KBLBB) di Indonesia | 207.478 unit | 2024 | [Kemenperin via CNN Indonesia](https://www.cnnindonesia.com/otomotif/20250425162635-603-1222670/populasi-kendaraan-listrik-loncat-78-persen-di-indonesia) |
| Kendaraan listrik (KBLBB) di Indonesia | 541.678 unit | Agustus 2026 | [Kemenperin via Okezone, 15 Okt 2026](https://digital.okezone.com/view/2026/10/15/4/106303/pengguna-kendaraan-listrik-di-indonesia-terus-bertambah) |
| Sepeda motor listrik (bagian dari KBLBB) | 196.051 unit | Juni 2025 | [Kemenhub via Bisnis.com](https://otomotif.bisnis.com/read/20251024/275/1923129/kemenhub-jumlah-kendaraan-listrik-207478-unit-sepeda-motor-paling-banyak) |
| Target pemerintah 2030 | 13 juta motor listrik | – | [Kemenperin via Tempo](https://www.tempo.co/ekonomi/outlook-2025-menanti-perkembangan-infrastruktur-kendaraan-listrik-1196867) |
| Stasiun swap SWAP Energi | 1.500+ stasiun | 2026 | [swap.id](https://www.swap.id/) |
| Stasiun swap Electrum | 400+ BSS; 10.000+ pengguna; 16 juta penukaran | 2025 | [electrum.id](https://electrum.id/id/about-us) |
| Stasiun swap V-Green (VinFast) | 2.000+ titik | Jul 2026 | [detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast) |
| Stasiun swap Volta | 300+ lokasi | Sep 2025 | [TYCORUN, sekunder](https://www.tycorun.com/blogs/industry-insights/top-10-electric-two-wheller-with-swappable-batteries-in-indonesia) |
| Tarif sewa baterai (langganan) | Rp 84.000–250.000/bulan | 2026 | [VinFast via detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast), [Polytron](https://polytron.co.id/kategori-produk/polytron-ev/2-wheel/) |
| Tarif tukar | Rp 6.000 (VinFast), Rp 8.000 (Honda) per swap | 2026 | [detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast), [chargeevcalculator, sekunder](https://chargeevcalculator.com/id/en/guide/tukar-baterai-motor-listrik) |
| Harga jual satu baterai (VinFast) | Rp 4.550.000 | Jul 2026 | [detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast) |
| Harga baterai ≈ setengah harga motor | – | – | [Polytron](https://polytron.co.id/kategori-produk/polytron-ev/2-wheel/) |

Sumber sekunder dipakai hanya sebagai pembanding kasar; utamakan daftar resmi
operator saat wawancara.

### 3.2 Baterai terpasang hari ini (bottom-up)

Operator tidak mempublikasikan jumlah baterai, jadi diperkirakan dari
kapasitas rak swap.

| Komponen | Nilai | Status / Dasar |
|---|---|---|
| Slot baterai per rak stasiun | 8–10 slot | **[Sumber]** — spesifikasi GoStation Gogoro, [gogoro.com](https://www.gogoro.com/smartscooter/s1) (catatan kaki: "8 to 10 battery slots") |
| Jumlah rak per stasiun | 1 rak/stasiun | **[Asumsi]** — konservatif; lokasi besar bisa beberapa rak. Verifikasi: hitung slot saat kunjungan lapangan |
| Stasiun total 3 jaringan utama | ± 2.200 | **[Sumber]** — 1.500 (SWAP) + 400 (Electrum) + 300 (Volta) |
| **Baterai berpindah antar-rak** | **± 20.000 (rentang 15.000–30.000)** | **[Asumsi]** dengan dasar: 2.200 stasiun × 8–10 slot, ditambah stok cadangan di gudang/GH |

V-Green (2.000+ titik) tidak dihitung karena jumlah baterainya belum tersedia.
Ini adalah **SAM hari ini**: puluhan ribu baterai. Jangan klaim "100.000
baterai dalam 2 tahun" dari business_model.md sebagai target utama; simpan
sebagai skenario optimis yang membutuhkan banyak operator.

### 3.3 Nilai yang diselamatkan (value pool)

- **Baterai per pilot: 2.000–5.000 unit [Asumsi].** Dasar: Electrum punya
  10.000+ pengguna di 400+ BSS ≈ 25 pengguna/BSS
  ([electrum.id](https://electrum.id/id/about-us)); satu klaster 80–200 BSS
  ≈ 2.000–5.000 pengguna, dan tiap motor memakai 1–2 baterai (opsi baterai
  ganda VinFast, [detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast)).
  Verifikasi: tanya operator berapa baterai aktif di satu klaster.
- **Persentase riwayat bermasalah per tahun: 1–2% [Asumsi].** Dasar: belum
  ada sumber publik untuk prevalensi kecurangan riwayat; angka disandarkan
  pada tingkat penggantian baterai karena kegagalan yang jarang — 1,5%
  (MV 2011–2023) dan di bawah 1% (MV 2016–2023) menurut studi Recurrent
  ([DOE](https://www.energy.gov/cmei/vehicles/articles/fotw-1339-april-22-2024-plug-electric-vehicle-battery-replacements-due))
  dan degradasi rata-rata 2,3%/tahun yang memicu sengketa garansi
  ([Geotab 2026](https://www.globenewswire.com/news-release/2026/01/13/3218328/0/en/Updated-analysis-finds-average-battery-degradation-of-2-3-per-year-with-charging-behaviour-emerging-as-a-key-driver.html)).
  Verifikasi: tanya operator — pernah menemukan riwayat diubah/di-reset?
- **Kerugian per kasus: Rp 2–4 juta [Asumsi].** Dasar: harga jual satu
  baterai Rp 4,55 juta ([detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast));
  kerugian adalah sebagian nilai baterai (nilai sisa turun/diganti) ditambah
  downtime. Baterai ≈ setengah harga motor ([Polytron](https://polytron.co.id/kategori-produk/polytron-ev/2-wheel/)),
  sehingga insentif pencurian/kecurangan nyata.

Contoh hitung untuk 2.000 baterai (nilai tengah):
`2.000 × 1,5% × Rp 3 juta = Rp 90 juta/tahun` per operator (rentang Rp 40–160
juta untuk 1–2% dan Rp 2–4 juta).

### 3.4 Harga dan aliran pendapatan

Setiap harga disertai dasar; contoh hitung memakai pilot 2.000 baterai.

| Aliran | Harga | Dasar | Contoh hitung |
|---|---|---|---|
| Layanan verifikasi | Rp 5.000–10.000/baterai/tahun | **[Asumsi]** dengan dasar: 0,3–1% dari pendapatan langganan Rp 84.000–250.000/bulan = Rp 1–3 juta/tahun ([detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast), [Polytron](https://polytron.co.id/kategori-produk/polytron-ev/2-wheel/)); setara Rp 50–100 per swap pada kuota 20 swap/bulan; target 10–20% dari nilai tengah yang diselamatkan | 2.000 baterai: Rp 10–20 juta/tahun |
| Modul retrofit | USD 3,50/unit, margin kotor ± 55% (BOM ± USD 1,60) | **[Asumsi]** dengan dasar: harga chip autentikasi pasar < USD 1–3 (business_model.md) + MCU/PCB/packaging; belum ada kutipan vendor | 2.000 unit: USD 7.000 penjualan, ± USD 3.850 laba kotor (± Rp 62 juta) |
| Lisensi IP | USD 50–100k upfront | **[Asumsi]** dengan dasar: kisaran umum lisensi IP "ratusan ribu dolar" ([eeNews Europe](https://www.eenewseurope.com/en/the-ip-licensing-business-model-a-love-story)); ambil sisi bawah karena IP menengah | 1 desain menang: Rp 800 juta–1,6 M |
| Royalti per chip | 1–2% dari harga chip gauge | **[Sumber]** benchmark: ARM 1–2% dari harga jual chip, umumnya 0,5–3% ([comparables lisensi](https://www.nen.wfglobal.org/digest/semiconductor-patent-licensing-comparables-royalty-rates-580088)); royalti IP biasanya "beberapa sen sampai puluhan sen per chip" ([eeNews](https://www.eenewseurope.com/en/the-ip-licensing-business-model-a-love-story)). Ilustrasi chip USD 2–5 → USD 0,02–0,10/chip | 100.000 chip: USD 2.000–10.000 |
| | | **Koreksi penting:** angka royalti USD 0,25–0,50/chip di business_model.md dan pitch_deck.md melebihi benchmark (itu 5–25% harga chip); jangan dipakai tanpa pembenaran value-based | |

Catatan: pendapatan lisensi adalah tujuan jangka panjang; pendapatan modul dan
layanan adalah jalur pendek yang bisa dimulai dengan pilot berbayar.

### 3.5 Biaya dan modal pra-silikon

| Komponen | Perkiraan | Status / Dasar |
|---|---|---|
| MPW / tape-out SKY130 | **USD 14.950** per proyek (100 part QFN) | **[Sumber]** — chipIgnite via ChipFoundry, jadwal shuttle 2025–2026, [chipfoundry.io/faqs](https://chipfoundry.io/faqs). Catatan: Efabless tutup Maret 2025 ([HN](https://news.ycombinator.com/item?id=43222168)); jangan sebut "Efabless" sebagai mitra. Opsi lebih murah: Tiny Tapeout (ratusan USD, desain sangat kecil) |
| EDA alur ASIC | USD 10–50k/tahun | **[Asumsi]** — PoC sekarang Rp 0 (Vivado + alur terbuka); verifikasi dengan kutipan vendor EDA |
| Cloud + KMS/HSM | Rp 10–30 juta/tahun untuk puluhan ribu baterai | **[Asumsi]** — basis data inti 4 MB per 10.000 baterai dan KMS/HSM terkelola; hitungannya di [alur-teknis.md](../docs/catatan-teknis/alur-teknis.md) §"Isi Basis Data" |
| Sertifikasi keamanan | Baru relevan saat masuk produksi | – |

### 3.6 Titik impas kasar (bukan proyeksi)

Pilot 2.000 baterai tahun pertama: layanan Rp 10–20 juta + laba kotor modul
± Rp 62 juta sekali bayar. Angka ini **belum menutup biaya tim penuh**; artinya
pilot adalah pembelian bukti dan referensi, bukan sumber pendapatan utama.
Kesimpulan untuk pitch: jalur pendanaan yang masuk akal adalah hibah/hadiah
non-dilutif + pilot berbayar kecil, bukan investor di tahap ini. Skenario
skala (ilustrasi 2028): 50.000 baterai × Rp 7.500 = Rp 375 juta/tahun layanan,
ditambah satu design win lisensi (± Rp 1,2 M) dan royalti.

### 3.7 Sensitivitas dan jawaban siap pakai

| Pertanyaan juri | Jawaban |
|---|---|
| "Operator tidak mau bayar" | Pilot kecil dulu; kalau operator nol, pembeli tetap ada: produsen BMS/gauge (klaim garansi), perusahaan pembiayaan, pembeli baterai bekas. |
| "Pasarnya kecil" | Bottom-up hari ini puluhan ribu baterai (± 20.000 dari 2.200 stasiun × 8–10 slot); target nasional 13 juta motor listrik 2030; nilai per baterai naik saat baterai menjadi aset yang dibiayai. |
| "Angka Anda dari mana?" | Tunjuk dokumen ini: setiap angka berlabel **[Sumber]** dengan tautan atau **[Asumsi]** dengan dasar; sebutkan yang masih perlu wawancara. |
| "Kenapa tidak jual chip sendiri?" | Butuh volume ratusan ribu unit untuk menutup wafer + GTM chip; model IP core menghindari capex fabrikasi. |
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
3. **2027–2028** — MPW SKY130 via ChipFoundry (USD 14.950) + kemitraan
   gauge/BMS lokal (jalur ICDeC).
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
- Royalti USD 0,25–0,50/chip — melebihi benchmark 0,5–3%; pakai 1–2% harga
  chip atau jangan sebut angkanya.
- Sudah ada pilot/produksi chip — belum; yang ada PoC FPGA + rencana.
- "Menghilangkan semua penipuan" — SeBatt membuktikan riwayat, bukan
  menggantikan pengukuran arus/sensor lain.

## 5. Tugas validasi (sebelum pitch bisnis berikutnya)

1. Wawancara 2–3 operator (SWAP, Electrum, V-Green/Volta, armada kampus):
   pernah menemukan riwayat diubah/di-reset? berapa kerugian per kasus?
   berapa harga wajar per baterai per tahun? berapa baterai aktif per klaster?
2. Wawancara 1–2 produsen BMS/gauge: bersedia integrasi IP? syaratnya?
3. Benchmark harga lisensi IP sejenis dan royalti per chip (mulai dari
   tautan di §3.4; cari 2–3 contoh transaksi).
4. Minta kutipan resmi ChipFoundry untuk shuttle 2027 + estimasi biaya EDA.
5. Ganti semua label **[Asumsi]** di dokumen ini dengan angka wawancara;
   perbarui [lean-canvas.md](lean-canvas.md) bagian **[Isi]**.

## 6. Sumber

**Pasar dan operator**

- Populasi KBLBB 207.478 (2024) — [CNN Indonesia](https://www.cnnindonesia.com/otomotif/20250425162635-603-1222670/populasi-kendaraan-listrik-loncat-78-persen-di-indonesia)
- Populasi KBLBB 541.678 (Agustus 2026) — [Okezone, 15 Okt 2026](https://digital.okezone.com/view/2026/10/15/4/106303/pengguna-kendaraan-listrik-di-indonesia-terus-bertambah)
- 196.051 sepeda motor listrik (Juni 2025) — [Bisnis.com](https://otomotif.bisnis.com/read/20251024/275/1923129/kemenhub-jumlah-kendaraan-listrik-207478-unit-sepeda-motor-paling-banyak)
- Target 13 juta motor listrik 2030 — [Tempo](https://www.tempo.co/ekonomi/outlook-2025-menanti-perkembangan-infrastruktur-kendaraan-listrik-1196867)
- SWAP 1.500+ stasiun — [swap.id](https://www.swap.id/)
- Electrum 400+ BSS, 10.000+ pengguna, 16 juta penukaran — [electrum.id](https://electrum.id/id/about-us)
- V-Green 2.000+ titik, tarif sewa Rp 84.000–144.000/bulan, swap Rp 6.000, harga baterai Rp 4.550.000 — [detik.com](https://oto.detik.com/motor-listrik/d-8581711/begini-sistem-dan-biaya-sewa-baterai-motor-listrik-vinfast)
- Sewa baterai Polytron Rp 125.000–200.000/bulan; baterai ≈ setengah harga motor — [Polytron](https://polytron.co.id/kategori-produk/polytron-ev/2-wheel/)
- Tarif Honda Rp 8.000/swap (sekunder) — [chargeevcalculator](https://chargeevcalculator.com/id/en/guide/tukar-baterai-motor-listrik)
- Volta 300+ lokasi (sekunder) — [TYCORUN](https://www.tycorun.com/blogs/industry-insights/top-10-electric-two-wheller-with-swappable-batteries-in-indonesia)

**Teknis/acuan asumsi**

- Kapasitas rak GoStation 8–10 slot — [Gogoro](https://www.gogoro.com/smartscooter/s1) (catatan kaki spesifikasi)
- Penggantian baterai karena kegagalan 1,5% (MV 2011–2023), <1% (MV 2016–2023) — [DOE/Recurrent](https://www.energy.gov/cmei/vehicles/articles/fotw-1339-april-22-2024-plug-electric-vehicle-battery-replacements-due)
- Degradasi baterai EV rata-rata 2,3%/tahun; fast charging hingga 3,0% — [Geotab, Jan 2026](https://www.globenewswire.com/news-release/2026/01/13/3218328/0/en/Updated-analysis-finds-average-battery-degradation-of-2-3-per-year-with-charging-behaviour-emerging-as-a-key-driver.html)

**Lisensi IP dan silikon**

- Perilaku umum lisensi IP: royalti atas chip 3–5% jarang — [LES webinar (PDF)](https://cdn.ymaws.com/members.lesusacanada.org/resource/collection/4C61AEDD-DEA7-4BAD-AA71-82F7FB8005EF/Semiconductors_Licensing_-_All_You_Need_to_Know_webinar_January_26_2022.pdf)
- Komparasi royalti: 0,5–3% net sales; ARM 1–2% harga chip — [comparables](https://www.nen.wfglobal.org/digest/semiconductor-patent-licensing-comparables-royalty-rates-580088)
- Struktur lisensi: fee ratusan ribu–jutaan USD; royalti beberapa sen–puluhan sen — [eeNews Europe](https://www.eenewseurope.com/en/the-ip-licensing-business-model-a-love-story)
- chipIgnite via ChipFoundry USD 14.950, shuttle 2025–2026 — [chipfoundry.io/faqs](https://chipfoundry.io/faqs)
- Efabless berhenti operasi Maret 2025 — [Hacker News](https://news.ycombinator.com/item?id=43222168)
