# Rencana Tes Basys 3 — Sesi Hardware Satu-satunya

> **Revisi 19 Okt:** board sesi ini adalah **Cmod S7**, bukan Basys 3 (Basys 3
> tidak tersedia; tidak ada Basys/Nexys di hari-H). Langkah Flow A/Basys 3 di
> bawah disimpan sebagai referensi artefak dan pin; untuk Cmod S7 ganti target
> (cek part di Vivado; umumnya `xc7s25csga225-1`), XDC, dan input sampel ke
> **ADS1115 (I2C)**.

Sesi ini satu-satunya kesempatan menyentuh hardware sebelum hari-H. Tiga hasil wajib sebelum pulang:

1. **Flow A jalan** (halt fix hw_server 2024.1 bekerja) + **video fallback terekam** (asuransi hari-H).
2. **Rantai RTL minimal VALID** dari stasiun Python — tanpa prosesor lunak. Ini replika KV260.
3. **Kontrak frame riwayat dibekukan** (membebaskan RTL Muqtada + dashboard Budi).

Dibaca bersama [cara-jalan-board.md](cara-jalan-board.md). Semua langkah di bawah diketik manual satu per satu — tidak ada skrip yang perlu dijalankan; tiap perintah disertai hasil yang diharapkan.

## 0. Pre-flight Terverifikasi (dicek dari laptop, tanpa board)

| Cek | Hasil |
|---|---|
| Station offline `python3 -m model.station --offline --demo` | **PASS** — 4 skenario + benchmark 224 auth/dtk |
| `.venv`: pyserial + cocotb 2.1.0 | OK — sim RTL pakai `source .venv/bin/activate` |
| Artefak Flow A (`sebatt_bd_wrapperbasys3.bit`, `app_component.elf`, `.xsa`) | OK, lengkap |
| hw_server 2024.1 (`~/Xilinx/HWSRVR/2024.1/bin/hw_server`) | OK |
| python3 sistem: pyserial | OK (cocotb TIDAK di sistem — hanya di `.venv`) |
| Board tercolok | Belum (dicek saat sesi mulai) |

## 1. Fase 0 — Meja (10 menit, semua manual)

Colok Basys 3 dulu: kabel micro-USB ke port **PROG** di board, ujung satunya ke laptop. Lalu kerjakan berurutan:

**1.1 Cek board terbaca USB**
```bash
lsusb | grep -i ftdi
```
Harus muncul baris: `Future Technology Devices International, Ltd FT2232H ...` (chip USB-UART board). Kalau kosong: ganti kabel/port USB, tunggu 5 detik, ulang perintah.

**1.2 Cek port serial**
```bash
ls /dev/ttyUSB*
```
FT2232 punya dua kanal, jadi harus muncul dua port: `/dev/ttyUSB0` dan `/dev/ttyUSB1`. **UART = `/dev/ttyUSB1`** (kanal JTAG = ttyUSB0). Kalau hanya satu yang muncul: cabut-colok kabel, ulang.

**1.3 Cek izin akses**
```bash
id -nG | grep dialout
```
Harus muncul kata `dialout`. Kalau kosong: `sudo usermod -aG dialout $USER`, lalu logout + login lagi, ulang.

**1.4 Cek artefak Flow A**
```bash
ls -lh fpga/ws/app_component/_ide/bitstream/sebatt_bd_wrapperbasys3.bit
ls -lh fpga/ws/app_component/build/app_component.elf
ls -lh fpga/ws/platform_basys3/hw/sebatt_bd_wrapperbasys3.xsa
```
Ketiganya harus ada (ukuran tidak nol).

**1.5 Cek hw_server 2024.1**
```bash
ls -lh ~/Xilinx/HWSRVR/2024.1/bin/hw_server
```
File harus ada dan bisa dieksekusi.

**1.6 Siapkan lingkungan Python**
```bash
source .venv/bin/activate
python -c "import serial, cocotb; print('pyserial + cocotb OK')"
```
Harus mencetak `pyserial + cocotb OK`. (python3 sistem punya pyserial tapi TIDAK punya cocotb — sim RTL wajib lewat `.venv`.)

**1.7 Sanity station tanpa board**
```bash
python3 -m model.station --offline --demo
```
Harus berakhir dengan `Demo completed successfully. All security scenarios verified.`

**1.8 Jalankan hw_server** — terminal A, biarkan hidup sampai sesi selesai:
```bash
pkill -x hw_server        # jangan `pkill -f`: pola bisa cocok dengan shell sendiri
~/Xilinx/HWSRVR/2024.1/bin/hw_server 2>&1 | tee /tmp/hw_server.log
```
Tunggu log mencetak pesan listening / port 3121. Jangan pakai hw_server 2024.2 (bug `Cannot halt hart`, AR000037627).

Terminal B tetap dipakai untuk perintah station di fase berikutnya.

> Opsional: langkah 1.1–1.7 punya versi skripnya di `tools/preflight_basys3.sh` (`bash tools/preflight_basys3.sh`). Sesi ini tetap ikuti manual dulu supaya paham tiap cek; skrip tinggal dipakai kalau buru-buru.

## 2. Fase 1 — Flow A: halt fix + demo + video (90 menit)

| # | Tes | Perintah | Ekspektasi |
|---|---|---|---|
| T1 | Program bitstream | Vivado Hardware Manager → Open Target → `localhost:3121` → Program `fpga/ws/app_component/_ide/bitstream/sebatt_bd_wrapperbasys3.bit` | Target terbuka, program sukses |
| T2 | Firmware Vitis | Buka workspace `fpga/ws` → `app_component` → Run (atau Debug) | Pesan timeout boleh muncul **sekali**; hart berhenti; firmware jalan. Kalau gagal → xsct: `connect; targets; rst -processor; dow <elf>; con` |
| T3 | Demo station | `python3 -m model.station --port /dev/ttyUSB1 --demo` | Skenario 1 VALID, 2 REPLAY_DETECTED, 3 INVALID_HMAC, 4 BATTERY_LOCKED |
| T4 | **Rekam video fallback** | HP statis / screen record | 60–90 dtk: 1) VALID → 2) replay DITOLAK → 3) angka diubah DITOLAK → 4) lock DITOLAK. **Backup 2 tempat sebelum tidur** |

Kalau T2 gagal total: cek `/tmp/hw_server.log`, ulang dari T1; jangan habiskan >30 menit di sini — lanjut Fase 2, rekam video dari RTL kalau RTL jadi.

## 3. Fase 2 — Rantai RTL Minimal (target utama, replika KV260)

Blok Fase 2 (status per 20 Okt):

| File | Isi |
|---|---|
| `rtl/uart_if.v` | **Sudah ada (20 Okt).** UART 8N1, sampling tengah bit, `BIT_CYCLES = CLK_HZ/BAUD` |
| `rtl/auth_ctrl.v` | **Sudah ada (21 Okt).** Sampling ADS1115 periodik 1 detik; parse frame `[CMD][LEN:2][PAYLOAD][CRC8]`; `AUTH_REQ` memakai sampel terakhir → HMAC → `AUTH_RESP`; ring buffer 64 record, `READ_HIST`, `RESULT`/`LOCK`/`UNLOCK`/`STATUS`, lock setelah 3 kegagalan |
| `rtl/axil_master.v` | **Sudah ada (20 Okt).** Master AXI4-Lite untuk KEY/MSG/CTRL ke `hmac_sha256` |
| `rtl/i2c_master.v` + `rtl/ads1115_ctrl.v` | **Sudah ada (20 Okt).** ADS1115 I2C: tulis config `0xC383`, baca AIN0 single-ended, `V_mV = code / 8`; sim `make ads1115` PASS 2/2 |
| `rtl/sebatt_top.v` | **Sudah ada (20 Okt).** clk/reset/uart + ADS1115 + `auth_ctrl` + LED heartbeat |
| `fpga/cmod_s7/` | **Sudah ada (20 Okt).** `cmod_s7_top.v`, `cmod_s7.xdc`, `build.tcl`, `program.tcl`; bitstream WNS +55,193 ns |

**Aturan pagi: SIM DULU, board belakangan.**
- Regresi lama: `source .venv/bin/activate && cd sim && make hmac` (cocotb 2.1.0 di `.venv`; python3 sistem tidak punya).
- ADS1115: `make ads1115` → 2/2 PASS (config `0xC383`, 26400→3300 mV, 16000→2000 mV, 0x8000→0 mV).
- Auth chain: `make auth` → 5/5 PASS (`sim/test_auth_ctrl.py`); responsive, nonce kedua, CRC salah diabaikan, command tak dikenal diabaikan, dan interval sampling periodik. Bandingkan byte `AUTH_RESP` dengan `model.hmac`/`model.protocol` (Python = referensi emas). **Merah = jangan ke board.**
- Regresi total: `make all` → 5 sha256 + 4 hmac + 2 ads1115 + 5 auth = 16/16 PASS.

**Mapping tegangan (beku untuk tes ini):** switch `V_mV = 3000 + sw[7:0] * 5` → 3000–4275 mV (fallback). ADS1115 `V_mV = code / 8` (LSB 0,125 mV), AIN0 0–3,3 V dari potensiometer. RTL membaca pin switch/I2C langsung; station hanya mempercayai nilai dari dalam frame.

Tabel pin (verified dari Digilent Basys-3-Master.xdc; W5/U18/B18/A18 sudah ada di `basys_3.xdc`):

| Sinyal | Pin |
|---|---|
| SW[0..7] | V17, V16, W16, W17, W15, V15, W14, W13 |
| LED[0..3] | U16, E19, U19, V19 |

| # | Tes | Perintah | Ekspektasi |
|---|---|---|---|
| T5 | Build bitstream RTL | Cmod S7: `cd fpga/cmod_s7 && vivado -mode batch -source build.tcl`; part `xc7s25csga225-1`, top `cmod_s7_top` | **PASS 21 Okt:** bitstream dibangun ulang, WNS +55,788 ns (semua constraint met), 5 235 LUT / 6 024 FF |
| T6 | Program | `cd fpga/cmod_s7 && vivado -mode batch -source program.tcl` (atau Hardware Manager) | LED heartbeat berkedip |
| T7 | Auth RTL | `python3 -m model.station --port /dev/ttyUSB1 --interactive` → AUTH | VALID; putar pot ADS1115, tunggu ≥1 detik → AUTH → VALID dengan V baru |
| T8 | LED status (opsional) | – | LED valid/reject saat T7 |
| T9 | ADS1115 I2C | Scan `0x48`, baca AIN0 sambil pot diputar | `V_mV` berubah mengikuti pot; tidak ada NACK |

**T7 PASS = target hari ini tercapai.** Ini yang akan dijalankan di KV260.

## 4. Fase 3 — Bekukan Kontrak Frame Riwayat (30 menit, bisa paralel)

Usulan untuk diratifikasi Muqtada + Budi hari ini, lalu ditulis:

- `READ_HIST_REQ = 0x07`, payload: `nonce(32)` — tantangan segar per dump.
- `READ_HIST_RESP = 0x08`, payload: `count(1) + N × record(38B)` dengan `record = seq(4 BE) ‖ voltage(2 BE) ‖ tag(32)`.
- `tag_i = HMAC(K, ID‖seq_i‖V_i)`; iterasi 2 (kalau waktu): rantai `tag_i = HMAC(K, ID‖seq_i‖V_i‖tag_{i-1})`.
- Station anchor per baterai: `{last_seq, last_seen_time}`; seq gap / seq mundur ⇒ ditolak; nonce di REQ mencegah precompute.
- Ukuran: 64 record = 1 + 64×38 = 2433 B ≈ 211 ms @ 115200 — aman.
- Output: `Command` enum + encoder/decoder di `model/protocol.py`, catat di `alur-teknis.md`.

## 5. Fase 4 — Tanpa Board (sore / sambil menunggu)

- [x] Build penuh `xck26` (port KV260): **21 Okt** part `xck26-sfvc784-2LV-c`, 100 MHz, WNS +0,687 ns, 5 611 LUT / 6 130 FF; multi-driver `sg_req*` fixed; bitstream + `.bit.bin` + runbook di `fpga/kv260/`; uji board belum
- [ ] SD image Ubuntu untuk KV260 + kenalan update BOOT.BIN
- [ ] Loopback CP2102: jumper TX–RX, kirim/terima via pyserial
- [ ] `fpga/kv260/`: constraint PMOD asli (nama pin dari carrier KV260), `shell.json`, `.bif` + `bootgen` untuk `.bit → .bit.bin`; timing-only check sudah ada

## 6. Aturan Stop (keras)

- **15:00:** kalau T7 belum VALID → STOP RTL. Sisa waktu untuk video T4 + kontrak Fase 3 + Fase 4. RTL lanjut besok di meja, jangan bakar sesi board satu-satunya.
- **T4 wajib sebelum pulang** — tanpa video, hari-H tanpa jaring pengaman.

## 7. Lembar Log (isi selama sesi)

| Jam | Tes | Hasil | Catatan |
|---|---|---|---|
| | T1 | | |
| | T2 | | |
| | T3 | | |
| | T4 | | |
| 21 Okt | T5 | PASS | `cmod_s7_top.bit` dibangun ulang; WNS +55,788 ns; 5 235 LUT / 6 024 FF |
| | T6 | | |
| | T7 | | |
| | T8 | | |
| | T9 | | |
| | Fase 3 | | |
| | Fase 4 | | |

## 8. Perintah Referensi

Semua cek persiapan manual ada tertulis di bagian 1 (Fase 0) — tidak ada skrip.

```bash
# hw_server fix (terminal A, biarkan hidup)
pkill -x hw_server        # jangan `pkill -f`: pola bisa cocok dengan shell sendiri
~/Xilinx/HWSRVR/2024.1/bin/hw_server 2>&1 | tee /tmp/hw_server.log

# Station (terminal B)
python3 -m model.station --offline --demo          # sanity tanpa board
python3 -m model.station --port /dev/ttyUSB1 --demo
python3 -m model.station --port /dev/ttyUSB1 --interactive

# Sim RTL (cocotb ada di .venv)
source .venv/bin/activate && cd sim && make hmac

# Dump frame mentah (kalau framing dicurigai bug)
python3 - <<'EOF'
from model.protocol import WireProtocol, AuthRequest
import serial, os
s = serial.Serial("/dev/ttyUSB1", 115200, timeout=1)
s.write(WireProtocol.encode_auth_req(AuthRequest(os.urandom(32))))
print(s.read(64).hex())
EOF
```
