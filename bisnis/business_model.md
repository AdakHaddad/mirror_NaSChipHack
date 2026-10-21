# Model Bisnis & Analisis Pasar: SeBatt

> **Catatan (21 Okt 2026):** sebagian angka di dokumen ini belum bersumber
> (termasuk TAM dan royalti USD 0,25–0,50/chip). Angka pitch final yang
> berlabel **[Sumber]**/[Asumsi] dengan dasar dan tautan ada di
> [pitch-dan-angka.md](pitch-dan-angka.md) — pakai dokumen itu untuk
> presentasi.

## 1. Ringkasan Eksekutif

SeBatt (*Secure Battery Identity Chip*) menyediakan solusi akar kepercayaan perangkat keras (*hardware root of trust*) untuk ekosistem baterai kendaraan listrik (EV), khususnya jaringan stasiun penukaran baterai (*battery swap station*). Menggabungkan *Ring-Oscillator Physical Unclonable Function* (RO-PUF) dan penandatanganan kriptografis HMAC-SHA-256 langsung pada titik pengukuran tegangan ADC.

---

## 2. Masalah Pasar & Validasi Kebutuhan

### 2.1 Masalah Utama
1. **Pemalsuan Identitas Baterai**: Kode QR dan nomor seri mudah digandakan. Baterai non-standar/rusak dimasukkan ke stasiun swap menggunakan identitas baterai legal.
2. **Manipulasi Data Telemetri BMS**: Firmware BMS dapat diretas untuk memanipulasi *State of Charge* (SoC), tegangan, dan riwayat siklus baterai sebelum dikirim ke stasiun.
3. **Pencurian & Pasar Gelap**: Baterai EV bernilai 40–50% dari harga kendaraan (Rp 6–10 juta per paket). Tanpa penguncian kriptografis terikat silikon, baterai curian dapat dipakai di motor lain.

### 2.2 Bukti Lapangan
- Proyeksi RUPTL PLN 2025–2034: ~168.000 EV roda dua di Indonesia per akhir 2024, tumbuh eksponensial.
- Kerugian operator swap dari degradasi dini baterai palsu dan baterai hilang mencapai miliaran rupiah per tahun.
- Regulasi Baterai Global (EU Battery Passport 2023/1542) mewajibkan ketertelusuran siklus hidup dan integritas data baterai.

---

## 3. Solusi & Keunggulan Kompetitif (Unfair Advantage)

| Parameter | Solusi Konvensional (QR / MCU Software) | Secure Element Biasa (e.g. DS28E38) | SeBatt IP Core |
|---|---|---|---|
| **Ketahanan Kloning** | Tidak ada (dapat disalin) | Tinggi (PUF) | Tinggi (RO-PUF) |
| **Titik Penandatanganan Data** | Software MCU (rentan modifikasi) | Data eksternal dari MCU | Langsung di titik ADC sensor |
| **Integritas Sensor** | Terbuka serangan firmware | Rentan spoofing ADC | Terikat dalam satu silicon die |
| **Model Integrasi** | Chip terpisah | Chip terpisah (BOM tambah) | Lisensi IP core ke dalam chip BMS ASIC |
| **Perkiraan Biaya BOM** | Rendah (tidak aman) | $2.00–$3.50/unit | < $0.80/unit (integrasi SoC) |

---

## 4. Analisis Pasar (TAM / SAM / SOM)

- **Total Addressable Market (TAM)**:
  Pasar Global Battery Swapping & BMS Security: USD 1.8 Miliar (2026), CAGR 24.5%.
- **Serviceable Available Market (SAM)**:
  Pasar EV roda dua & armada swap Asia Tenggara (Indonesia, Vietnam, Thailand): ~2.5 juta unit baterai swap per tahun (~USD 75 Juta).
- **Serviceable Obtainable Market (SOM)**:
  Operator swapping & produsen BMS lokal di Indonesia (Swap Energy, Oyika, Electrum, IBC): 100.000 baterai dalam 2 tahun pertama (~USD 2.5 Juta).

---

## 5. Model Pendapatan (Revenue Streams)

1. **IP Core Licensing & Royalty**:
   - Lisensi upfront ke produsen chip fabless / BMS ASIC: USD 50,000–100,000 per implementasi.
   - Royalti per unit chip terproduksi: USD 0.25–0.50 per die.
2. **Turnkey Module / Pre-packaged IC**:
   - Penjualan modul add-on untuk produsen baterai eksisting (FPGA/ASIC packaging): USD 3.50/unit (margin kotor ~55%).
3. **Identity Verification & Fleet Analytics API (SaaS)**:
   - Biaya verifikasi cloud & audit trail per transaksi swap: Rp 50–100 per swap atau Rp 15.000/baterai/tahun untuk pemeliharaan identity database.

---

## 6. Struktur Biaya (Cost Structure)

- **R&D & Engineering**: Sintesis RTL, MPW (*Multi-Project Wafer*) tape-out via SkyWater SKY130 (open PDK / Efabless), pengujian reliabilitas silikon.
- **Operasional & Lisensi Tool**: EDA tool support, pengujian laboratorium suhu/tegangan PUF.
- **Sales & Integrasi**: Biaya FAE (*Field Application Engineer*) untuk integrasi ke arsitektur BMS mitra.

---

## 7. Rencana Traksi & Go-to-Market (GTM)

- **Tahap 1 (Hackathon - Q4 2026)**: Validasi PoC FPGA di Nexys A7 + emulator stasiun. Bukti verifikasi HMAC < 20 ms.
- **Tahap 2 (Q1–Q2 2027)**: Integrasi modul hardware ke paket baterai nyata mitra lokal (pilot test dengan armada kampus UGM / armada logistik).
- **Tahap 3 (Q3–Q4 2027)**: MPW shuttle tape-out (SkyWater SKY130) untuk silikon uji pertama.
- **Tahap 4 (2028)**: Komersialisasi IP lisensi ke produsen sel/BMS konsorsium baterai nasional.
