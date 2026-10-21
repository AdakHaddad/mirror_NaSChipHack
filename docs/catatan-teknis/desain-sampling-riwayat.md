# Catatan brainstorm — sampling, riwayat, hash chain, dan ECDSA

Status: **dasar Opsi A; keputusan utamanya sudah diimplementasikan.** Kontrak
final ada di [spesifikasi.md](spesifikasi.md).

Tanggal: 21 Oktober 2026  
Konteks: Flow B pure RTL, Cmod S7 untuk latihan dan KV260 untuk demo.

## 1. Status kode saat ini

Sudah ada (per 21 Oktober, setelah implementasi Flow B):

- `rtl/auth_ctrl.v`: sampling ADS1115 periodik (`SAMPLE_INTERVAL_MS = 1000`
  default demo; 100 ms tersedia sebagai uji beban), `seq` 32 bit, ring buffer
  64 record dengan tag HMAC per sampel.
- Pesan bertanda tangan berprefiks: 0x41 AUTH, 0x53 RECORD, 0x48 SUMMARY.
- `READ_HIST_REQ` / `READ_HIST_RESP` (N, rentang seq, tag per catatan, tag
  ringkasan ber-nonce), plus `RESULT`, `LOCK`, `UNLOCK`, `STATUS`, dan
  `CHIP_LOCKED`; lock setelah 3 RESULT gagal.
- Model Python di `model/protocol.py` memverifikasi riwayat dan anchor
  (HISTORY_GAP / HISTORY_ROLLBACK / HISTORY_TRUNCATED).
- `SAMPLE_CYCLES` dapat di-override; testbench memakai 12 000 siklus (1 ms)
  dan BAUD 1 Mbaud hanya untuk mempercepat simulasi.
- Regresi cocotb: 26/26 PASS (5 sha256, 4 hmac, 4 ads1115, 13 auth); model
  Python 57/57, termasuk verifikasi riwayat di `model/protocol.py` dan
  `model/station.py`.
- Bitstream Cmod S7 dibangun ulang 21 Okt dengan timing bersih.

Belum ada:

- `seq` di dalam `AUTH_RESP` (tetap di READ_HIST_RESP);
- penyimpanan `seq`/checkpoint di NVM aman;
- ECDSA;
- uji fisik board T6/T7/T9/T10.

Spesifikasi final ada di [spesifikasi.md](spesifikasi.md); catatan ini
menjelaskan alasan desainnya.

---

## 2. Apakah sampling 100 ms bagus?

**Untuk demo: cukup, tetapi terlalu cepat untuk histori produksi.**

Dengan buffer 64 record:

| Interval | Cakupan 64 record | Cakupan 10 record | Catatan |
|---|---:|---:|---|
| 100 ms | 6,4 detik | 1 detik | bench/test, bukan histori |
| 1 detik | 64 detik | 10 detik | cocok untuk demo urutan |
| 10 detik | 10,7 menit | 100 detik | perjalanan pendek |
| 1 menit | 64 menit | 10 menit | sesi charging |
| 10 menit | 10,7 jam | 100 menit | harian |
| 1 jam | 64 jam (2,7 hari) | 10 jam | jangka panjang |

Implikasi:

- 100 ms bukan masalah memori kalau hanya menyimpan sampel terakhir.
- 100 ms menjadi masalah kalau semua sampel disimpan: 10 sampel/detik =
  864.000 sampel/hari. Dengan record 38 B, itu sekitar 32,8 MB/hari.
- Untuk ring buffer 64 record, 100 ms hanya menyimpan 6,4 detik terakhir.
  Ini tidak cukup untuk cerita “riwayat beberapa hari”.
- 10 sampel selama beberapa hari terlalu jarang. Jika 10 sampel dibagi
  rata selama 3 hari, jaraknya sekitar 7,2 jam; event singkat seperti
  over-discharge bisa terlewat.

Rekomendasi:

- **Demo:** 1 sampel/detik, 64 record = 64 detik. Ini cukup untuk menunjukkan
  urutan, gap, dan verifikasi. 100 ms tetap bisa dipakai sebagai mode stress
  test, bukan default cerita.
- **Produksi:** sampling adaptif:
  - idle: 1 sampel / 5–15 menit;
  - charging/discharging: 1 sampel / 1–10 detik;
  - event trigger: sampel langsung saat tegangan/arus/suhu melewati batas,
    ditambah beberapa sampel sebelum/sesudah.
- Pisahkan **sampling rate** dari **logging rate**. Sampling cepat berguna
  untuk proteksi, tetapi yang ditandatangani/disimpan sebaiknya record
  periodik yang lebih jarang ditambah event snapshot.

---

## 3. Apakah cukup menyimpan hash terakhir?

Secara kriptografis, hash chain adalah **commitment**:

```text
H_i = HMAC(K, H_{i-1} || ID || seq_i || V_i)
```

`H_n` mengikat seluruh urutan sebelumnya. Kalau satu record diubah, `H_n`
tidak cocok. Tetapi:

- `H_n` tidak bisa di-inverse menjadi `V_1..V_n`.
- Verifikasi membutuhkan data asli record dan anchor awal.
- Hash tanpa kunci bisa diforgery; harus HMAC atau signature.
- Chain head tidak membuktikan kelengkapan data. Verifier harus tahu berapa
  record yang seharusnya ada, atau memiliki anchor dari kunjungan sebelumnya.
- `H_n` bukan pengganti penyimpanan data; itu bukti integritas, bukan
  kompresi histori.

### Skenario “kirim data asli saat charging, chip hanya simpan hash terakhir”

Ini bisa menjadi desain **checkpoint + station archive**:

1. Chip menyimpan record asli sampai kunjungan berikutnya.
2. Saat charging, chip mengirim record `seq, V` dan `H_n`.
3. Station menghitung ulang chain dari anchor terakhir.
4. Setelah station menyimpan data dan mengirim ACK, chip boleh menghapus
   record lama dan menyimpan `seq_n, H_n` di NVM aman.
5. Kunjungan berikutnya, station melanjutkan verifikasi dari checkpoint.

Syarat dan risikonya:

- Chip tetap harus menyimpan record asli sampai dump; kalau hanya `H_n`,
  tidak ada data yang bisa dikirim.
- Station menjadi pemilik histori. Kalau data station hilang, histori hilang.
- Battery yang charging di station lain tidak punya anchor yang sama.
- `seq` harus monotonic dan tersimpan di NVM aman; counter volatile akan
  reset saat power loss.
- Perlu nonce/ACK agar dump lama tidak bisa di-replay.
- Jangan menghapus data sebelum station mengonfirmasi penyimpanan.

Untuk 64 record, penghematannya kecil: **64 × 38 B = 2,4 KB**. Menghapus data
untuk menghemat 2 KB justru menciptakan risiko kehilangan audit trail.

---

## 4. Konsep ring buffer

Ring buffer adalah array tetap dengan pointer tulis yang berputar:

```text
slot:    0    1    2   ...  63
seq:    121  122  123  ...  184
                          ^
                     write_ptr berikutnya
```

- Sampel baru ditulis di slot berikutnya.
- Saat penuh, sampel paling lama ditimpa.
- `head` = record tertua yang masih ada.
- `count` = jumlah record valid.
- Saat dump, station membaca dari `head` sampai record terbaru.

Yang diperiksa station:

- `seq` harus berurutan;
- HMAC/chain setiap record harus cocok;
- `seq` terbaru tidak boleh lebih kecil dari anchor station (rollback);
- gap di **awal** buffer = record lama sudah tertimpa (normal);
- gap di **tengah** = ada record hilang (curiga);
- `seq` mundur = rollback.

Contoh:

```text
Station anchor: last_seq = 120
Buffer berisi : 121, 122, 124, 125
```

Record 123 hilang di tengah → curiga. Bandingkan:

```text
Station anchor: last_seq = 120
Buffer berisi : 130, 131, 132
```

Record 121–129 sudah tertimpa karena kapasitas buffer → gap di awal, bukan
bukti fraud, tetapi station tidak bisa memverifikasi bagian yang sudah hilang.

Dengan kapasitas 10, setelah 10 sampel baru, sampel ke-11 menimpa sampel
pertama. Jadi “10 data” berarti jendela 10 record terakhir, bukan seluruh
histori.

### Memori record

| Format | Ukuran/record | 64 record |
|---|---:|---:|
| `seq(4) + V(2) + HMAC(32)` | 38 B | 2.432 B |
| `seq(4) + V(2)` saja | 6 B | 384 B |
| `seq(4) + V(2) + chain head(32)` | 6 B + 32 B total | 416 B |
| `seq(4) + V(2) + ECDSA P-256(64)` | 70 B | 4.480 B |

Untuk FPGA/ASIC, 2,4 KB sangat kecil. Jangan mengorbankan audit trail hanya
untuk menghemat beberapa kilobyte.

---

## 5. ECDSA: membantu atau tidak?

### Yang diperbaiki ECDSA

Dengan HMAC, station harus menyimpan kunci simetris `K`. Kalau station
compromised, attacker bisa memalsukan histori. Dengan ECDSA:

- chip menyimpan private key;
- station hanya perlu public key;
- station yang compromised tidak bisa memalsukan signature;
- banyak station/pihak ketiga bisa memverifikasi;
- ada non-repudiation.

### Yang tidak diselesaikan ECDSA

- Data yang dihilangkan tetap tidak terlihat.
- Rollback tetap butuh `seq` monotonic dan anchor/NVM.
- Sampling yang terlalu jarang tetap terlalu jarang.
- Private key yang bisa diekstrak tetap bisa dipakai untuk forge.
- Kelengkapan data tetap butuh sequence continuity, trusted time, atau
  mekanisme checkpoint.

### Biaya ECDSA

| Aspek | HMAC-SHA256 | ECDSA P-256 |
|---|---|---|
| Kunci verifikasi | simetris, rahasia | public key |
| Ukuran tag | 32 B | 64 B |
| Beban FPGA | rendah | jauh lebih besar |
| Latency | ~452 siklus | milidetik–puluhan milidetik |
| Nonce | tidak perlu | wajib unik |
| 64 record | ~2,4 KB | ~4,5 KB |
| Multi-verifier | tidak | ya |
| PKI/enrollment | tidak | ya |

Catatan keamanan:

- Reuse nonce ECDSA dapat membocorkan private key. Gunakan RFC 6979 atau RNG
  hardware yang benar.
- Private key harus disimpan aman; PUF saat ini lebih cocok untuk kunci
  simetris. ECDSA membutuhkan provisioning dan proteksi side-channel/fault.
- Public key harus terikat ke identitas chip; kalau database public key bisa
  ditukar, attacker bisa mendaftarkan public key miliknya.

### Hybrid yang masuk akal

1. Per sampel: HMAC chain murah.
2. Per checkpoint (misalnya 64 record atau saat kunjungan):
   `signature = ECDSA(private_key_chip, ID || seq_n || H_n)`.
3. Station menyimpan record asli + checkpoint, lalu memverifikasi HMAC chain,
   ECDSA checkpoint, dan urutan `seq`.

Ini memberi non-repudiation pada checkpoint tanpa ECDSA per sampel. Tetapi
station tetap butuh `K` untuk memverifikasi HMAC chain. Kalau ingin verifikasi
tanpa `K` sama sekali, perlu ECDSA per record atau Merkle tree dengan root
ECDSA—jauh lebih kompleks.

### Rekomendasi ECDSA

- **Jangan implementasikan ECDSA sekarang.** Untuk hackathon, HMAC sudah cukup.
- Fokus ke `seq`, ring buffer, `READ_HIST`, dan verifikasi station.
- ECDSA dipertimbangkan setelah ada kebutuhan multi-operator/audit pihak ketiga.
- Kalau nanti dipakai, gunakan **ECDSA per checkpoint**, bukan per sampel
  100 ms.
- Alternatif yang perlu dievaluasi: Ed25519 (deterministik, lebih mudah
  menghindari nonce reuse), tetapi membutuhkan SHA-512 dan core berbeda.

---

## 6. Rekomendasi desain

### Untuk demo

**Opsi A — ring buffer dengan HMAC per record**

- Kapasitas 64 record.
- Record: `seq(4) || V(2) || HMAC(32)` = 38 B.
- Total 2,4 KB.
- Setiap record ditandatangani saat sampling.
- Station memverifikasi tiap record, urutan, dan anchor.
- Interval default demo: **1 detik** (64 detik), bukan 100 ms.
- 100 ms tetap tersedia sebagai parameter stress test.

Keuntungan: sederhana, setiap record bisa diverifikasi mandiri, tidak perlu
menghapus data, dan mudah dijelaskan ke juri.

### Untuk produksi

- Sampling adaptif dan event-triggered.
- Ring buffer lebih besar (256–1024 record) atau checkpoint + station archive.
- `seq` dan checkpoint di NVM aman.
- Station menyimpan arsip dan anchor; chip hanya menghapus setelah ACK.
- ECDSA checkpoint opsional untuk multi-operator/audit.

### Jangan

- Jangan hanya menyimpan hash terakhir tanpa data asli di tempat lain.
- Jangan mengandalkan `seq` volatile untuk rollback detection.
- Jangan memakai ECDSA per sampel 100 ms.
- Jangan mengklaim chain head membuktikan kelengkapan data tanpa anchor,
  sequence, dan asumsi trusted time.

---

## 7. Batasan keamanan yang perlu disebut

- Tanpa **trusted time**, chip tidak bisa membuktikan bahwa sampling benar-benar
  dilakukan setiap interval. `seq` hanya membuktikan urutan record yang
  dikirim, bukan bahwa tidak ada sampling yang dilewati.
- Kalau chip sendiri dimanipulasi, ia bisa memilih sampel mana yang dicatat.
  Kriptografi tidak bisa membuktikan sampling terjadi tanpa hardware/clock
  yang dipercaya.
- Anchor station mendeteksi rollback hanya jika station pernah melihat `seq`
  yang lebih tinggi.
- Ring buffer yang sudah menimpa record lama tidak bisa mengembalikan data
  tersebut; station harus mengarsipkan lebih awal.
- Kunci fixed `bytes(range(32))` hanya untuk demo; produksi membutuhkan
  per-chip key/PUF dan provisioning yang aman.

---

## 8. Keputusan

Sudah diputuskan dan diimplementasikan:

1. Interval demo: **1 detik**; 100 ms sebagai mode uji beban.
2. Kapasitas buffer: **64 record**.
3. Format record: **HMAC per record**, bukan chain head.
4. ECDSA: **tidak** untuk hackathon; HMAC tetap dipakai.

Masih terbuka:

1. Apakah chip boleh menghapus record setelah ACK station?
2. Apakah perlu field tambahan: flags, suhu, arus, atau min/max per interval?
3. Bagaimana menyimpan `seq`/checkpoint di NVM aman pada FPGA demo?

---

## 9. Status langkah implementasi

1. Kontrak record dan `READ_HIST_REQ/RESP`: **selesai**.
2. `seq` counter dan ring buffer di `auth_ctrl`: **selesai**.
3. `seq` masuk ke HMAC record: **selesai**.
4. Dump riwayat dengan nonce: **selesai**.
5. Verifikasi station untuk urutan, HMAC, gap, rollback, replay: **selesai**
   di `model/protocol.py` dan `model/station.py`.
6. Interval demo default 1 detik: **selesai**; 100 ms tetap tersedia.
7. Tes delete, edit, reorder, rollback, replay: **selesai** di
   `sim/test_auth_ctrl.py` dan `model/test_history.py`.
8. ECDSA checkpoint: **ditunda** sampai alur HMAC stabil dan ada kebutuhan
   multi-operator.

## 10. Referensi

- `rtl/auth_ctrl.v` — sampler periodik dan auth FSM saat ini.
- `context.md` §3.3–3.6 — layout pesan, target history record, domain separation.
- `docs/catatan-teknis/alur-teknis.md` — narasi langkah sampling dan riwayat.
- `docs/catatan-teknis/rencana-tes-basys3.md` — Fase 3 kontrak riwayat.
