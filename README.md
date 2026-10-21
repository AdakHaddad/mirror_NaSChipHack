# SeBatt: Secure Battery Identity Chip

Chip yang ditanam pada paket baterai kendaraan listrik untuk membuktikan keaslian baterai dan keaslian riwayat tegangannya selama pemakaian.

Hackathon Deeptech 2026: Designing Chips for Real-World Impact · Tema Internet of Things · ICDeC ITB Innovation Park, 21–23 Oktober 2026

## Ringkasan

Stasiun penukaran baterai hanya dapat mengukur tegangan sesaat ketika baterai ditukar. Riwayat selama pemakaian dilaporkan oleh firmware BMS, sehingga dapat diubah sebelum sampai ke stasiun, termasuk pada baterai yang identitasnya asli.

SeBatt mengambil sampel tegangan paket secara berkala melalui ADC. Setiap sampel diberi nomor urut dari penghitung yang hanya dapat bertambah, lalu ditandatangani dengan HMAC-SHA-256 di dalam IP yang sama. Tahap pertama memakai kunci tetap, dan tahap kedua menurunkan kunci dari Ring-Oscillator PUF. Saat penukaran, basis data identitas menghitung ulang setiap tanda tangan, sehingga sampel yang diubah, dihapus, atau disisipkan akan ditolak.

## Arsitektur

Seluruh IP ditulis dalam Verilog/SystemVerilog standar tanpa IP vendor maupun prosesor lunak, agar dapat dipindahkan ke FPGA yang disediakan panitia. PC menjalankan emulator stasiun dan basis data dalam Python, terhubung melalui UART sebagai pengganti bus CAN.

| Modul | Tugas |
|---|---|
| ads1115_ctrl + i2c_master | Membaca sampel tegangan dari modul ADS1115 (I2C) |
| auth_ctrl | Sampling ADS1115 periodik (1 detik default demo) + FSM `AUTH_REQ -> HMAC -> AUTH_RESP`; seq 32 bit, ring buffer 64 catatan bertag HMAC per sampel, `READ_HIST`, dan penguncian setelah 3 kegagalan |
| hmac_sha256 | Menandatangani nonce, ID, dan sampel tegangan |
| key_vault | Penyimpan kunci tetap (tahap 1). Belum dipasang, kunci saat ini ditulis oleh auth_ctrl |
| ro_puf + fuzzy_ext | Kunci dari PUF (tahap 2) |
| uart_if | Komunikasi dengan emulator stasiun |

Diagram lengkap, target metrik, dan batas proof of concept ada di [mini proposal](docs/kirim/ChipHack26_NaS_InternetOfThings_MiniProposal.pdf).

## Status

| Tahap | Status |
|---|---|
| Mini proposal | Lolos seleksi |
| Persiapan pra-onsite | Berjalan, lihat [milestone](docs/MILESTONES.md) |
| RTL Flow B | Rantai autentikasi + riwayat bertanda tangan lolos 20/20 uji simulasi cocotb (5 sha256 + 4 hmac + 2 ads1115 + 9 auth; diperbarui 21 Okt). Bitstream Cmod S7 dibangun ulang 21 Okt (WNS +55,788 ns, 5.235 LUT, 6.024 FF); build penuh KV260 + `.bit.bin` (WNS +1,475 ns); uji board belum |
| Demo web (web/) | Model protokol Python, belum terhubung ke FPGA |
| Onsite dan Demo Day | 21–23 Oktober 2026 |

## Struktur Repositori

| Folder | Isi |
|---|---|
| [model/](model/) | Model referensi Python dan generator vektor uji |
| [sim/](sim/) | Testbench dan vektor uji |
| [rtl/](rtl/) | Kode Verilog/SystemVerilog |
| [fpga/](fpga/) | Proyek FPGA dan constraint per board |
| [bisnis/](bisnis/) | Business model dan analisis pasar |
| [pitch/](pitch/) | Slide dan naskah pitch Demo Day |
| [docs/](docs/) | Dokumen lomba: milestone, mini proposal, PDF kiriman, dan dokumen anggota |

## Tim

Tim NaS, Universitas Gadjah Mada.

| Nama | Program studi |
|---|---|
| Guntur Sulistyo (ketua) | Teknik Elektro |
| Muhammad Muqtada Alhaddad | Teknologi Informasi |
| Muhammad Budi Setiawan | Teknologi Informasi |
