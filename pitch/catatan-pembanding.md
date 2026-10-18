# Catatan Pembanding Produk

Hasil penelusuran 18 Oktober 2026 untuk slide pembanding dan sesi tanya jawab.

## Temuan

- **Autentikasi baterai sudah umum.** Chip seperti DS28E38, Infineon OPTIGA Authenticate, dan TI bq26100 membuktikan keaslian baterai melalui challenge-response dengan harga di bawah US$1. Klaim "chip anti baterai palsu" tidak dapat dijual sebagai kebaruan.
- **TI BQ40Z50 mengukur sekaligus mengautentikasi, tetapi hanya identitas.** Autentikasinya berupa HMAC-SHA-1 atas pesan acak 160 bit dari host dengan kunci 128 bit. Data ukur tidak ikut di-hash. Gauge ini merekam Lifetime Data dan Black Box Recorder, tetapi riwayat tersebut hanya dilindungi mode akses SEALED/UNSEALED dan dapat di-reset melalui Lifetime Data Reset.
- **ADI wireless BMS mengamankan jaringan internal paket.** Chip node ADRF8800 memiliki AES, ECC-256, SHA-256, dan secure boot. Belum ditemukan dokumentasi yang menjelaskan autentikasi data tegangan per paket. Tujuannya juga berbeda, yaitu jalur node ke controller di dalam baterai, bukan pembuktian riwayat ke stasiun.
- **Paten swap fokus pada identitas.** Paten Gogoro dan paten autentikasi dua arah untuk stasiun swap membuktikan keaslian baterai, bukan keaslian riwayat pemakaian.
- **Riwayat baterai iPhone dapat diubah dengan alat yang dijual bebas.** iPhone menampilkan jumlah siklus dan kapasitas maksimum di menu Battery Health. Di pasar servis beredar programmer baterai seperti JCID V1S/V1SE dan Qianli Copy Power yang diiklankan dapat menulis ulang jumlah siklus dan persentase kesehatan baterai. Sumbernya halaman penjual, sehingga keandalan alat belum terverifikasi. Keberadaan produk tersebut menunjukkan bahwa pemalsuan riwayat baterai sudah menjadi praktik komersial, dan proteksi keaslian komponen tidak mencegah riwayat diubah.
- **Tidak ditemukan produk komersial yang menandatangani riwayat pengukuran per sampel.** Temuan ini belum berupa penelusuran paten menyeluruh.

## Posisi SeBatt

| Kemampuan | DS28E38 | BQ40Z50 | ADI wBMS | SeBatt |
|---|---|---|---|---|
| Membuktikan baterai asli | Ya (ECC, PUF) | Ya (HMAC-SHA-1) | Tidak jelas | Ya (HMAC-SHA-256) |
| Mengukur tegangan di chip yang sama | Tidak | Ya | Ya, melalui cell monitor | Ya, target ASIC |
| Merekam riwayat di dalam chip | Tidak | Ya | Tidak jelas | Ya |
| Riwayat ditandatangani, penghapusan dan rollback terdeteksi | Tidak | Tidak, hanya kata sandi | Tidak terdokumentasi | Ya |
| Diverifikasi pihak di luar baterai | Identitas | Identitas | Tidak, internal paket | Identitas dan riwayat |

## Kalimat untuk Pitch

> Gauge baterai di pasar sudah merekam riwayat pemakaian, tetapi riwayat itu hanya dilindungi kata sandi dan dapat di-reset. SeBatt menandatangani setiap sampel dengan nomor urut, sehingga stasiun dapat membuktikan riwayat tidak diubah, dihapus, atau diputar balik.

Pembuka untuk juri awam:

> Di iPhone, jumlah siklus baterai dapat di-reset dengan alat yang dijual bebas. Untuk baterai motor listrik yang harganya jutaan rupiah, SeBatt membuat riwayat seperti ini tidak dapat di-reset tanpa ketahuan.

- Sebut BQ40Z50 lebih dulu sebagai pembanding, sebelum juri yang menyebutnya.
- Gunakan "belum kami temukan di produk komersial", bukan "belum ada yang melakukan ini".
- Nomor urut dan riwayat bertanda tangan merupakan satu-satunya pembeda dari BQ40Z50, sehingga fitur ini harus terlihat di demo.

## Sumber

- [TI BQ40Z50-R5 Technical Reference Manual (SLUUCN4B), bagian 13.3–13.5](https://www.ti.com/lit/ug/sluucn4b/sluucn4b.pdf)
- [TI SLUAAQ0, pemrograman kunci SHA/ECC untuk BQ40Z50](https://www.ti.com/document-viewer/lit/html/SLUAAQ0)
- [ADI ADRF8800/ADRF8850 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/adrf8800-8850.pdf)
- [ADI Analog Dialogue, keamanan wBMS](https://www.analog.com/en/resources/analog-dialogue/articles/in-the-new-era-of-wireless-battery-management-systems-wbms-security-takes-the-spotlight.html)
- [Paten Gogoro US 12,229,243 B2](https://patents.justia.com/patent/12229243)
- [US 11,362,521, autentikasi dua arah untuk battery swapping](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11362521)
- [Infineon OPTIGA Authenticate](https://www.infineon.com/cms/de/product/security-smart-card-solutions/optiga-embedded-security-solutions/optiga-authenticate/optiga-authenticate-on/)
- [JCID V1S/V1SE Battery Detection Board (halaman penjual)](https://4phones.eu/products/jcid-v1s-v1se-battery-detection-board-for-iphone-6-14-series)
- [V1S Pro battery detect module (halaman penjual)](https://www.5g-m.com/en/jc-programmer/36533-v1s-pro-battery-detect-module-iphone-6-14-pro-max.html)
- [Qianli Copy Power Battery Data Corrector (halaman penjual)](https://4phones.eu/products/qianli-copy-power-battery-data-corrector)
