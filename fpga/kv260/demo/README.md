# KV260 demo bundle

Paket singkat untuk demo SeBatt di Kria KV260. Detail lengkap ada di
`../RUNBOOK.md`.

## Isi

| File | Dipakai di | Fungsi |
|---|---|---|
| `../build/kv260_top.bit.bin` | board | bitstream untuk `fpgautil` |
| `load.sh` | board | cek `pl0_ref`, unload app bawaan, load bitstream, cek `dmesg` |
| `run_station.sh` | laptop | jalankan `model.station` dengan venv repo |
| `preflight.sh` | laptop | cek artefak, timing, pin XDC, tes model, deteksi USB-serial |

## 1. Preflight di laptop

```bash
fpga/kv260/demo/preflight.sh          # cepat
fpga/kv260/demo/preflight.sh --full   # + cocotb 26/26
```

Harus berakhir `GO`. Kalau `NO-GO`, jangan lanjut ke board.

## 2. Wiring Pmod J2 (Digilent 12-pin)

| Pmod | Package | Signal | Sambung ke |
|---|---|---|---|
| 1 | H12 | `scl` | ADS1115 SCL |
| 2 | E10 | `sda` | ADS1115 SDA |
| 3 | D10 | `src_sel` | GND = ADS1115, 3V3 = tetap 3000 mV. Jangan dibiarkan terbuka (terbaca 1) |
| 4 | C11 | `led_hb` | LED heartbeat + 330 Ω ke GND (berkedip = PL hidup) |
| 5, 11 | — | GND | GND ADS1115, CP2102, katoda LED |
| 6, 12 | — | 3V3 | VDD ADS1115, pot |
| 7 | B10 | `uart_tx` | CP2102 RXD |
| 8 | E12 | `uart_rx` | CP2102 TXD |
| 9 | D11 | `led_green` | LED hijau + 330 Ω ke GND |
| 10 | B11 | `led_red` | LED merah + 330 Ω ke GND |

Jangan beri ADS1115 5 V; pakai 3V3. CP2102 harus 3,3 V dan GND-nya ikut
disambung ke Pmod GND.

## 3. Load di KV260

Dari laptop:

```bash
scp fpga/kv260/build/kv260_top.bit.bin \
    fpga/kv260/demo/load.sh kria@<ip-kv260>:~/
```

Di board:

```bash
chmod +x load.sh
sudo ./load.sh ./kv260_top.bit.bin
```

`load.sh` akan berhenti kalau `fpgautil` tidak ada. Cek yang penting:

- `pl0_ref` ≈ `99999001` Hz dan `enable_count > 0`
- `dmesg` tidak menunjukkan error FPGA manager

Kalau clock gated, ikuti `../RUNBOOK.md` §5 (`clk_ignore_unused`). Kalau rate
96,97 MHz, jangan lanjut demo UART; lihat §5 untuk fallback BOOT.BIN/build
ulang.

Tidak ada tombol reset. Memuat ulang bitstream mengembalikan `seq` chip ke 0;
kalau memakai `--history` setelah reload, jalankan
`run_station.sh --interactive` lalu `reset-anchor` agar stasiun tidak
melaporkan `HISTORY_ROLLBACK`.

## 4. Jalankan demo di laptop

```bash
fpga/kv260/demo/run_station.sh --check         # cek cepat board (STATUS/AUTH/READ_HIST)
fpga/kv260/demo/run_station.sh                 # satu autentikasi
fpga/kv260/demo/run_station.sh --demo          # suite 8 transaksi
fpga/kv260/demo/run_station.sh --interactive   # demo manual untuk juri
fpga/kv260/demo/run_station.sh --history       # cek riwayat
```

Kalau ada lebih dari satu `/dev/ttyUSB*`, pilih port CP2102:

```bash
fpga/kv260/demo/run_station.sh --port /dev/ttyUSB1 --demo
```

Untuk dashboard web (grafik, kartu kesehatan, tombol serangan), jalankan tanpa
opsi: server mencari adapter USB-UART sendiri dan langsung memakai mode FPGA.

```bash
.venv/bin/python web/server.py                    # auto-deteksi
.venv/bin/python web/server.py --fpga /dev/ttyUSB1 # pilih port
.venv/bin/python web/server.py --sim               # latihan tanpa board
.venv/bin/python -m model.station --check          # cek board sebelum demo
```

Buka <http://127.0.0.1:8000>. Tombol **Muat riwayat** mengambil sampel baru
tanpa verifikasi; **Tukar baterai** menjalankan autentikasi dan verifikasi
riwayat asli dari board. Detail ada di `web/README.md`.

Contoh output auth yang benar:

```text
Battery: 42415401
Voltage: 1500 mV
Result:  VALID
```

`VALID` dengan `Voltage: 0 mV` berarti HMAC benar tetapi ADS1115 tidak
terbaca; periksa wiring I2C. LED merah menyala saat lock/error.

## 5. Fallback

- **`fpgautil` gagal**: program lewat JTAG dari laptop,
  `vivado -mode batch -source ../program.tcl` (PS harus sudah boot).
- **Board/clock bermasalah**: jalankan `run_station.sh --offline --demo` untuk
  demo simulasi, atau pakai Cmod S7.
- **UART port salah**: lepas CP2102, lihat `ls -l /dev/ttyUSB*`, sambung lagi.
