# Naskah & Slide Pitch Deck Demo Day: SeBatt

**Waktu**: 5 Menit Presentasi + 3 Menit Tanya Jawab  
**Penyaji**: Tim NaS (Universitas Gadjah Mada)

---

## Slide 1: Judul & Hook (0:00 - 0:30)

- **Judul**: SeBatt — Secure Battery Identity Chip
- **Tagline**: Perancangan IP Keamanan Berbasis PUF dan HMAC-SHA-256 untuk Autentikasi Baterai Kendaraan Listrik
- **Poin Presenter**:
  > "Baterai adalah 40% dari biaya motor listrik. Di stasiun penukaran baterai (*battery swap*), bagaimana stasiun tahu bahwa baterai yang dimasukkan benar-benar baterai asli operator, dan bukan baterai tiruan atau baterai yang data voltasenya dimanipulasi oleh firmware BMS yang sudah di-hack?"
  > "Kami menghadirkan **SeBatt**: *silicon root of trust* yang menandatangani identitas dan voltase baterai langsung di titik sensor, tanpa menyimpan kunci permanen di memori."

---

## Slide 2: Masalah Nyata di Lapangan (0:30 - 1:15)

- **Problem 1: Kloning Identitas**: QR code & serial number software sangat mudah dipalsukan.
- **Problem 2: Manipulasi Telemetri**: BMS firmware adalah perangkat lunak yang bisa di-flash ulang untuk memalsukan data State of Charge (SoC) dan voltase demi mendapat klaim garansi atau menutupi sel baterai yang sudah rusak/berbahaya.
- **Problem 3: Ancaman Keselamatan & Finansial**: Baterai tidak layak pakai berisiko meledak/terbakar (*thermal runaway*) saat di-charge cepat di swap station.

---

## Slide 3: Solusi Kami: SeBatt IP Core (1:15 - 2:00)

- **Arsitektur**:
  1. **RO-PUF (Physical Unclonable Function)**: Sidik jari mikroskopis dari variasi pabrikasi silikon. Kunci kriptografis tidak disimpan di flash/NVM, melainkan direkonstruksi secara *on-the-fly*.
  2. **In-situ Signing**: ADC membaca voltase analog paket baterai, langsung dialirkan ke core HMAC-SHA-256 di silikon yang sama.
  3. **Zero-Trust Handshake**: Stasiun mengirimkan *nonce* unik setiap swap. Respons HMAC memvalidasi `nonce || Battery_ID || Voltage`.

---

## Slide 4: Demo Langsung (Live Demo) (2:00 - 3:15)

*Beralih ke layar monitor emulator stasiun Python + board FPGA Nexys A7-100T.*

- **Skenario 1: Autentikasi Sah (Valid)**
  - Stasiun kirim Nonce acak 256-bit.
  - Chip FPGA menghitung HMAC dalam 113 siklus clock.
  - Output: `VALID` (Voltase terverifikasi 3700 mV). Latensi total < 10 ms via UART.
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

| Parameter Target | Target Proposal | Hasil Capaian Tim | Status |
|---|---|---|---|
| **Latensi Core HMAC** | $\le 300$ siklus clock | **113 siklus** / blok | **Terlampaui (2.6x lebih cepat)** |
| **Latensi Ujung-ke-Ujung** | $< 20$ ms (UART 115200) | **~9.5 ms** | **Lolos target** |
| **Akurasi Deteksi Fraud** | 100% penolakan spoofing | **100% (40/40 test suite lolos)** | **Sempurna** |
| **Kepatuhan Kripto** | FIPS 180-4 & RFC 4231 | **100% Vektor Uji Lolos** | **Terverifikasi** |
| **Sumber Daya FPGA** | $< 5.000$ LUT | **~1.850 LUT** (Artix-7) | **Efisien (<37% budget)** |
| **Perkiraan Die ASIC** | Laporan sel SKY130 | Synthesizable RTL, target Open-PDK | **Siap MPW tapeout** |

---

## Slide 6: Model Bisnis & Pasar (4:00 - 4:30)

- **Pasar Sasaran**: Operator swap (Swap Energy, Oyika, Electrum, Pertamina) & produsen BMS nasional (IBC).
- **Model Monetisasi**:
  - Lisensi IP RTL Core ($50k–100k upfront) + Royalti ($0.25–0.50/chip)
  - Penyediaan modul secure element terprogram untuk retrofit armada
- **Dampak Ekonomi**: Mencegah kerugian fraud baterai senilai Rp 8–10 juta per paket baterai.

---

## Slide 7: Tim & Penutup (4:30 - 5:00)

- **Tim NaS (Universitas Gadjah Mada)**:
  - **Guntur Sulistyo** (Ketua / Hardware-in-the-Loop & Power Electronics)
  - **Dimas Eryan Ahnaf Fahrezi** (Sensing & Embedded ADC Interface)
  - **Muhammad Muqtada Alhaddad** (Digital IC Design & AXI Hardware Accelerator)
- **Closing Statement**:
  > "SeBatt memberikan kepastian mutlak pada integritas baterai EV Indonesia — dari level atom silikon hingga stasiun penukaran. Terima kasih."
