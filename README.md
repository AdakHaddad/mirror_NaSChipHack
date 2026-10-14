# Hackathon Deeptech 2026

Proyek untuk Hackathon Deeptech 2026: Designing Chips for Real-World Impact, ICDeC ITB Innovation Park, 21–23 Oktober 2026.

## Ringkasan

SeBatt adalah chip keamanan untuk memverifikasi keaslian baterai kendaraan listrik di stasiun penukaran. Chip memakai Ring-Oscillator PUF dan HMAC-SHA-256 untuk menjawab nonce dari basis data identitas tanpa menyimpan kunci permanen. Tema Internet of Things.

Prototipe dijalankan di FPGA Nexys A7-100T (Artix-7). IP keamanan terhubung ke MicroBlaze melalui AXI4-Lite, dan PC menjalankan emulator stasiun serta basis data dalam Python.

## Struktur Repositori

| Folder | Isi |
|---|---|
| [proposal/](proposal/) | Mini proposal dan surat pernyataan orisinalitas |
| [model/](model/) | Model referensi Python, uji unit, dan generator vektor uji |
| [sim/](sim/) | Testbench dan vektor uji |
| [rtl/](rtl/) | Kode Verilog/SystemVerilog |
| [fpga/](fpga/) | Proyek Vivado/Quartus dan constraint per board |
| [bisnis/](bisnis/) | Business model, analisis pasar, dan proyeksi dampak |
| [pitch/](pitch/) | Slide dan naskah pitch Demo Day |
| [docs/](docs/) | Milestone, gambar, dan referensi |

## Tim

| Nama | Peran |
|---|---|
| Guntur Sulistyo (ketua) | |
| Dimas Eryan Ahnaf Fahrezi | |
| Muhammad Muqtada Alhaddad | |

Tim NaS, Universitas Gadjah Mada.

## Dokumentasi Terkait

- [Milestone dan pembagian tugas](docs/MILESTONES.md)
