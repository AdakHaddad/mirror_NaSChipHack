# Lean Canvas SeBatt

Draf untuk sesi business model dan slide pitch. Bagian bertanda **[Isi]** membutuhkan data atau hitungan yang belum ada. Bagian bertanda **[Putuskan]** perlu disepakati tim. Angka harga dan pasar di dokumen ini berstatus hipotesis sampai ada sumber atau hasil wawancara.

## Kanvas

### 1. Problem

- Riwayat pemakaian baterai (tegangan, siklus, kejadian terkuras dalam) dilaporkan oleh firmware BMS dan dapat diubah atau di-reset. Stasiun hanya dapat mengukur tegangan sesaat ketika baterai ditukar.
- Nilai sisa baterai, klaim garansi, dan keputusan menerima baterai bergantung pada riwayat yang tidak dapat diverifikasi.
- Gauge yang ada sudah merekam riwayat di dalam chip, tetapi riwayat tersebut hanya dilindungi kata sandi dan tidak ditandatangani saat dibaca.

**Existing alternatives.** Kode QR dan nomor seri. Secure element autentikasi (DS28E38, OPTIGA Authenticate) yang membuktikan identitas saja. Gauge dengan lifetime data (TI BQ40Z50) yang tidak ditandatangani. Rincian ada di [catatan pembanding](../pitch/catatan-pembanding.md).

### 2. Customer Segments

Pihak yang dirugikan oleh riwayat palsu:

- Penyedia sewa atau pembiayaan baterai (*battery-as-a-service*, leasing), karena nilai sisa baterai menentukan risiko.
- Operator stasiun penukaran yang menerima baterai dari banyak pengguna.
- Produsen baterai dan BMS, untuk klaim garansi.
- Pembeli baterai bekas dan *second-life*.

**Early adopters [Putuskan].** Pilih satu sebagai pembeli utama di pitch. Usulan: operator yang menyewakan baterai sekaligus menjalankan stasiun penukaran, karena mereka menanggung nilai baterai dan sudah memiliki infrastruktur stasiun.

### 3. Unique Value Proposition

> Gauge baterai sudah merekam riwayat pemakaian. SeBatt membuat riwayat itu dapat dibuktikan: setiap sampel ditandatangani dengan nomor urut, sehingga riwayat yang diubah, dihapus, atau diputar balik ditolak stasiun.

**High-level concept.** Odometer baterai yang tidak dapat diputar balik.

### 4. Solution

- IP RTL yang menandatangani setiap sampel tegangan (HMAC-SHA-256) bersama nomor urut monoton, langsung setelah ADC dan tanpa perangkat lunak di tengah.
- Protokol stasiun yang memverifikasi identitas, kesegaran (*nonce*), dan kelengkapan riwayat.
- PoC berjalan di FPGA (AMD Kria KV260) dengan ADC eksternal dan emulator stasiun.

### 5. Channels

- Lisensi IP melalui pembuat gauge atau chip BMS. IP diintegrasikan ke chip yang sudah ada, tidak dijual sebagai chip terpisah.
- Pilot bersama operator lokal atau armada kampus.
- Ekosistem chip nasional (ICDeC ITB dan program semikonduktor pemerintah) untuk jalur prototipe silikon.

### 6. Revenue Streams

Hipotesis yang perlu divalidasi:

- Lisensi IP per desain chip ditambah royalti per unit. **[Isi]** Besaran dari pembanding lisensi IP sejenis.
- Modul tambahan untuk baterai yang sudah beredar (*retrofit*) selama IP belum terintegrasi di chip gauge. **[Isi]** Harga modul.
- Layanan verifikasi riwayat per penukaran atau per baterai per tahun bagi operator dan penyedia pembiayaan. **[Isi]** Tarif.

### 7. Cost Structure

- Pengembangan dan verifikasi RTL, termasuk sertifikasi keamanan bila diminta pelanggan.
- Prototipe silikon melalui MPW. **[Isi]** Biaya shuttle yang tersedia saat ini.
- Integrasi dengan mitra (dukungan teknis ke pembuat gauge atau BMS).
- Infrastruktur basis data verifikasi untuk layanan.

### 8. Key Metrics

| Tahap | Metrik |
|---|---|
| PoC | Latensi HMAC (siklus clock), latensi ujung ke ujung, LUT, Fmax, uji fungsi semua skenario serangan |
| Pilot | Jumlah baterai terpasang, persentase penukaran dengan riwayat terverifikasi, kasus riwayat tidak cocok yang terdeteksi |
| Bisnis | Jumlah lisensi IP, unit terpasang, pendapatan layanan per baterai |

### 9. Unfair Advantage

- RTL terbuka yang dapat diaudit dan disesuaikan oleh pembuat chip lokal. Produk pembanding bersifat tertutup.
- Tim menggabungkan elektronika daya (sensing tegangan baterai), desain IC digital, dan estimasi kondisi baterai berbasis data.
- Kedekatan dengan ekosistem chip nasional melalui ICDeC.

Catatan jujur: keunggulan teknisnya dapat ditiru oleh pembuat gauge besar. Keunggulan yang lebih tahan lama adalah kemitraan pilot dan kecepatan integrasi dengan pembuat BMS lokal.

## Mitra Kunci

Kotak ini tidak ada di Lean Canvas, tetapi penting untuk strategi implementasi.

| Mitra | Peran |
|---|---|
| Pembuat gauge atau chip BMS | Tempat IP diintegrasikan |
| Operator penukaran atau penyewaan baterai | Pilot dan pembeli layanan verifikasi |
| ICDeC dan program MPW | Prototipe silikon |
| Penyedia pembiayaan baterai | Pengguna data riwayat terverifikasi |

## Hitungan Dampak [Isi]

Hitungan bottom-up untuk satu segmen utama, sebagai pengganti angka TAM tanpa sumber:

| Komponen | Nilai | Sumber |
|---|---|---|
| Jumlah baterai di segmen utama | [Isi] | |
| Persentase baterai dengan riwayat bermasalah | [Isi] | |
| Kerugian per kasus (selisih nilai sisa, klaim garansi) | [Isi] | |
| Total kerugian per tahun | [Isi] | |
| Biaya SeBatt per baterai | [Isi] | |

Diisi Budi. Setiap angka disertai sumber atau dinyatakan sebagai asumsi.

## Versi Satu Slide

| Problem | UVP | Revenue |
|---|---|---|
| Riwayat baterai dari firmware BMS dapat diubah atau di-reset, padahal menentukan nilai sisa dan garansi | Setiap sampel ditandatangani dengan nomor urut. Riwayat yang diubah, dihapus, atau diputar balik ditolak | Lisensi IP ke pembuat gauge/BMS, modul retrofit, layanan verifikasi riwayat |
