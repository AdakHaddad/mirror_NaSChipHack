# Naskah & Slide Pitch Deck Demo Day: SeBatt

**Waktu**: 5 Menit Presentasi + 3 Menit Tanya Jawab  
**Penyaji**: Tim NaS (Universitas Gadjah Mada)

---

## Slide 1: Judul & Hook (0:00 - 0:30)

- **Judul**: SeBatt — Secure Battery Identity Chip
- **Tagline**: Perancangan IP Keamanan Berbasis PUF dan HMAC-SHA-256 untuk Autentikasi Baterai Kendaraan Listrik
- **Poin Presenter**:
  > "Baterai adalah 40% dari biaya motor listrik. Di stasiun penukaran baterai (*battery swap*), bagaimana stasiun tahu bahwa baterai yang dimasukkan benar-benar baterai asli operator, dan bukan baterai tiruan atau baterai yang data voltasenya dimanipulasi oleh firmware BMS yang sudah di-hack?"
  > "Kami menghadirkan **SeBatt**: *silicon root of trust* yang menandatangani identitas dan voltase baterai langsung di titik sensor. Demo hari ini memakai kunci tetap (tahap 1). Tahap 2 menurunkan kunci dari RO-PUF sehingga kunci tidak perlu disimpan permanen."

---

## Slide 2: Masalah Nyata di Lapangan (0:30 - 1:15)

- **Problem 1: Kloning Identitas**: QR code & serial number software sangat mudah dipalsukan.
- **Problem 2: Manipulasi Telemetri**: BMS firmware adalah perangkat lunak yang bisa di-flash ulang untuk memalsukan data State of Charge (SoC) dan voltase demi mendapat klaim garansi atau menutupi sel baterai yang sudah rusak/berbahaya.
- **Problem 3: Ancaman Keselamatan & Finansial**: Baterai tidak layak pakai berisiko meledak/terbakar (*thermal runaway*) saat di-charge cepat di swap station.

---

## Slide 3: Solusi Kami: SeBatt IP Core (1:15 - 2:00)

- **Arsitektur**:
  1. **RO-PUF (Physical Unclonable Function), tahap 2**: Sidik jari mikroskopis dari variasi pabrikasi silikon. Kunci kriptografis tidak disimpan di flash/NVM, melainkan direkonstruksi secara *on-the-fly*. RTL dan model RO-PUF ada, tetapi belum terpasang di rangkaian demo. Demo memakai kunci tetap.
  2. **In-situ Signing**: ADC membaca voltase analog paket baterai, langsung dialirkan ke core HMAC-SHA-256 di silikon yang sama. Pada PoC, ADC berupa modul ADS1115 eksternal (I2C).
  3. **Zero-Trust Handshake**: Stasiun mengirimkan *nonce* unik setiap swap. Respons HMAC memvalidasi `nonce || Battery_ID || Voltage`.
- **Gambar slide**: rantai perangkat + urutan protokol ada di [gambar alur teknis](../docs/gambar/alur-teknis.png) (16:9, siap tempel di slide).

---

## Slide 4: Demo Langsung (Live Demo) (2:00 - 3:15)

*Beralih ke layar monitor emulator stasiun Python + board FPGA Kria KV260 (latihan di Cmod S7).*

- **Skenario 1: Autentikasi Sah (Valid)**
  - Stasiun kirim Nonce acak 256-bit.
  - Chip FPGA membaca ADS1115, lalu menghitung HMAC (4 blok SHA-256, masing-masing 113 siklus clock).
  - Output: `VALID` dengan tegangan dari ADS1115. Latensi ujung ke ujung diukur onsite (target < 20 ms).
- **Skenario 2: Serangan Replay (Replay Attack)**
  - Penyerang merekam respons sebelumnya dan mengirimkannya kembali.
  - Hasil: `REPLAY_DETECTED` (Stasiun menolak karena nonce sudah pernah dipakai).
- **Skenario 3: Manipulasi Data Sensor (Data Tampering)**
  - Firmware perantara mengubah data voltase dari 3700 mV menjadi 4200 mV.
  - Hasil: `INVALID_HMAC` (Penolakan seketika karena tanda tangan kriptografis tidak cocok).
- **Skenario 4: Baterai Dilaporkan Hilang/Rusak (Locked)**
  - Operator menandai baterai curian di database.
  - Hasil: `BATTERY_LOCKED` (Stasiun mengunci slot dan menolak transaksi).

---

## Slide 5: Metrik Kinerja & Hasil Pengujian (3:15 - 4:00)

Kondisi per 20 Oktober. Setiap angka diberi sumbernya. Kolom ini diisi ulang setelah pengukuran di KV260.

| Metrik | Target proposal | Kondisi sekarang | Sumber |
|---|---|---|---|
| Latensi HMAC | ≤ 300 siklus clock | SHA-256 113 siklus per blok. HMAC memakai 4 blok, sekitar 452 siklus ditambah overhead, di atas target | Simulasi cocotb (dijalankan ulang 20 Okt), perhitungan |
| Latensi ujung ke ujung | < 20 ms (UART 115200) | Belum diukur di board | – |
| *Throughput* | ≥ 50 autentikasi per detik | Belum diukur di board | – |
| Uji fungsi | 100% serangan ditolak, 1.000 percobaan per skenario | Uji 1.000 percobaan belum dijalankan. Model Python lolos 40 uji unit | Uji unit Python (dijalankan ulang 20 Okt) |
| Kepatuhan kripto | FIPS 180-4 dan RFC 4231 | RTL lolos vektor FIPS 180-4 dan RFC 4231 | Simulasi cocotb (dijalankan ulang 20 Okt) |
| Sumber daya FPGA | < 5.000 LUT, Fmax ≥ 50 MHz | Cmod S7 sekitar 4.400 LUT. KV260 lolos *timing* 100 MHz (WNS +2,7 ns, tanpa pin) | Sintesis Vivado (dilaporkan Muqtada) |
| Perkiraan ASIC | Jumlah sel, luas, daya SKY130 | Belum dijalankan | – |

---

## Slide 6: Model Bisnis & Pasar (4:00 - 4:30)

- **Pasar Sasaran**: Operator swap (SWAP Energi, Electrum, V-Green/VinFast, Volta/Oyika) & produsen BMS/gauge nasional.
- **Model Monetisasi** (dasar & sumber lengkap di [../bisnis/pitch-dan-angka.md](../bisnis/pitch-dan-angka.md)):
  - Lisensi IP RTL Core: $50k–100k upfront + royalti 1–2% harga chip (benchmark ARM; ilustrasi $0,02–0,10/chip)
  - Modul retrofit armada: $3,50/unit, margin kotor ±55%
  - Layanan verifikasi: Rp 5.000–10.000/baterai/tahun (0,3–1% pendapatan langganan operator)
- **Dampak Ekonomi**: Kerugian per kasus Rp 2–4 juta; harga baterai Rp 4,55 juta (VinFast) dan ≈ setengah harga motor (Polytron)
- **Angka pasar & asumsi lengkap**: [../bisnis/pitch-dan-angka.md](../bisnis/pitch-dan-angka.md) — jangan sebut TAM tanpa sumber.

---

## Slide 7: Tim & Penutup (4:30 - 5:00)

- **Tim NaS (Universitas Gadjah Mada)**:
  - **Guntur Sulistyo** (Ketua / Hardware-in-the-Loop & Power Electronics)
  - **Muhammad Muqtada Alhaddad** (Digital IC Design & AXI Hardware Accelerator)
  - **Muhammad Budi Setiawan** (Program Stasiun, Dashboard & Data Baterai)
- **Closing Statement**:
  > "SeBatt membuat riwayat baterai EV dapat diperiksa, dari titik ukur di dalam paket sampai stasiun penukaran. Terima kasih."
