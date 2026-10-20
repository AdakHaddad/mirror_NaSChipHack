# Milestone Proyek

> **Revisi 18–20 Okt:** jalur demo utama sekarang **Flow B** — RTL murni + UART,
> Cmod S7 lalu KV260. Flow A (MicroBlaze + AXI) hanya fallback. Lihat
> [`context.md` §7.3](../context.md). Tabel dan arsitektur di bawah tetap
> disimpan sebagai catatan rencana awal.

Rencana kerja dari seleksi sampai Demo Day. Centang `[x]` setiap tugas yang selesai dan isi kolom PIC (penanggung jawab).

| # | Milestone | Tenggat | Hasil akhir |
|---|---|---|---|
| M0 | Pendaftaran dan mini proposal | 9 Okt | Tim terdaftar, mini proposal terkirim |
| M1 | Pengumuman peserta lolos | 15 Okt | Keputusan lanjut |
| M2 | Fondasi teknis dan pembekalan online | 19 Okt | Model referensi Python dan RTL inti lolos simulasi |
| M3 | Siap onsite | 20 Okt | Demo minimal jalan di board sendiri, kerangka business model dan pitch deck |
| M4 | Onsite hari 1–2 | 21–22 Okt | Demo di board panitia, metrik kinerja terukur, business model final |
| M5 | Demo Day | 23 Okt | Pitch, demo live, video cadangan |

Prinsip urutan kerja: jalur kritis dulu. Satu demo minimal harus jalan sebelum fitur tambahan dikerjakan.

Arsitektur PoC: **MicroBlaze + AXI4-Lite** pada Nexys A7-100T. IP kustom (`ro_puf`, `hmac_sha256`) sebagai AXI4-Lite peripheral. Logika `auth_ctrl` di firmware C. UART via AXI UART Lite IP bawaan Xilinx.

```
PC (Python station emulator)
   │ UART 115200
   ▼
MicroBlaze ──AXI4-Lite──┬── hmac_sha256 (IP kustom)
                         ├── ro_puf (IP kustom, tahap 2)
                         └── AXI UART Lite (Xilinx IP)
```

Jalur kritis: `Python model → vektor uji → RTL → simulasi → Vivado block design → board demo`

---

## M0 — Pendaftaran dan mini proposal (9 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Tim lengkap, minimal 3 anggota rumpun Teknik Elektro | Semua | [x] |
| Pilih sub-tema dan ide | Semua | [x] |
| Mini proposal sesuai template panitia | Muqtada | [x] |
| Surat pernyataan orisinalitas ditandatangani semua anggota | Semua | [x] |
| KTP seluruh anggota (NIK disensor) dalam satu file | Semua | [x] |

## M1 — Pengumuman (15 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Cek pengumuman di kanal resmi | Semua | [x] |
| Ajukan bantuan transport ke Admin ICDeC bila dari luar Bandung | | [ ] |
| Tanyakan board FPGA dan tools EDA yang disediakan | | [ ] |

## M2 — Fondasi teknis (16–19 Okt)

### Hari 1 — Sabtu 17 Okt: Model referensi Python

| Tugas | PIC | Selesai |
|---|---|---|
| `model/sha256.py` — SHA-256 dari nol, lolos FIPS 180-4 | Muqtada | [x] |
| `model/hmac.py` — HMAC-SHA-256, lolos RFC 4231 | Muqtada | [x] |
| `model/ro_puf.py` — model behavioral RO-PUF + KeyVault | Muqtada | [x] |
| `model/protocol.py` — simulasi challenge-response | Muqtada | [x] |
| `model/gen_vectors.py` — generator vektor uji untuk RTL | Muqtada | [x] |
| `model/test_model.py` + `model/test_history.py` — unit test semua komponen (52/52 lolos) | Muqtada | [x] |
| Ikuti pembekalan online | Semua | [x] |

### Hari 2 — Minggu 18 Okt: RTL + simulasi

| Tugas | PIC | Selesai |
|---|---|---|
| `rtl/sha256_core.v` — SHA-256 compression core | Muqtada | [x] |
| `rtl/hmac_sha256.v` — HMAC wrapper + AXI4-Lite register interface | Muqtada | [x] |
| `rtl/key_vault.v` — fixed key store (tahap 1) | Muqtada | [x] |
| `rtl/ro_puf.v` — RO-PUF (behavioral sim / structural FPGA) (tahap 2) | Guntur | [x] |
| `sim/` — cocotb testbench, verifikasi terhadap vektor uji Python | Muqtada | [x] |
| Semua RTL lolos simulasi terhadap vektor FIPS + RFC (9/9 lolos) | Muqtada | [x] |

### Hari 3 — Senin 19 Okt: FPGA integrasi

| Tugas | PIC | Selesai |
|---|---|---|
| Vivado block design: MicroBlaze + AXI UART Lite + HMAC IP (`create_bd.tcl` valid di Vivado 2024.2) | Muqtada | [x] |
| Pin constraints Nexys A7-100T (`fpga/nexys_a7/nexys_a7.xdc`) | Guntur | [x] |
| Firmware C: baca nonce dari UART → tulis ke HMAC IP → baca respons → kirim balik (`fpga/fw/sebatt_fw.c`) | Muqtada | [x] |
| `model/station.py` — emulator stasiun Python (kirim nonce, verifikasi respons via UART) | Muqtada | [x] |
| Tes end-to-end: stasiun → UART → board → UART → stasiun → VALID/INVALID (offline simulasi lolos) | Semua | [x] |

## M3 — Siap onsite (20 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Demo minimal jalan di board milik sendiri (skrip BD & firmware teruji) | Semua | [x] |
| Perbaiki edge case, uji skenario: replay, data diubah, baterai lock (52/52 uji lolos) | Semua | [x] |
| Kerangka business model (pengguna, pasar, nilai tambah) (`bisnis/business_model.md`) | Dimas | [x] |
| Kerangka pitch deck (`pitch/pitch_deck.md`) | Dimas | [x] |
| Video demo cadangan | Guntur | [ ] |
| Bawa board, kabel, bitstream cadangan di USB | Semua | [ ] |

## M4 — Onsite hari 1–2 (21–22 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Porting ke board panitia (ganti constraint, rebuild) | Muqtada | [ ] |
| Ukur metrik kinerja (akurasi, latensi, throughput, resource) | Guntur | [ ] |
| Evaluasi RO-PUF di board (Hamming intra < 10%, inter 40–60%) | Guntur | [ ] |
| Sintesis Yosys → SKY130 (perkiraan ASIC) | Muqtada | [ ] |
| Business model final | Dimas | [ ] |
| Latihan pitch | Semua | [ ] |

## M5 — Demo Day (23 Okt)

| Tugas | PIC | Selesai |
|---|---|---|
| Pitch dan demo live | Semua | [ ] |
| Demo: autentikasi valid | Semua | [ ] |
| Demo: tolak replay attack | Semua | [ ] |
| Demo: tolak data tegangan yang diubah | Semua | [ ] |
| Demo: tolak baterai berstatus lock | Semua | [ ] |
