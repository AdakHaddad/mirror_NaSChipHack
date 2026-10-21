# Dashboard web SeBatt

Dashboard browser untuk demo stasiun penukaran baterai SeBatt. Dua mode
tersedia:

- **Simulasi** (default) — data dari `web/demo.py`, tanpa board.
- **FPGA** — data autentikasi, riwayat, dan kesehatan berasal dari KV260
  melalui UART; serangan “BMS curang” dilakukan di sisi host dengan mengubah
  salinan dump sebelum verifikasi.

Tidak memerlukan Flask, FastAPI, atau koneksi internet.

## Menjalankan simulasi

```bash
python3 web/server.py
```

Buka <http://127.0.0.1:8000>. Opsi:

```bash
python3 web/server.py --host 0.0.0.0 --port 8080 --open
```

- `/` — dashboard stasiun
- `/diagram` — diagram use case
- `/use-case.png` dan `/use-case.pdf` — berkas diagram ukuran penuh

## Menjalankan dengan FPGA

Pastikan bitstream sudah termuat dan UART board tersambung ke laptop
(`fpga/kv260/demo/load.sh`, lalu `run_station.sh` untuk uji terminal).

```bash
# auto-deteksi USB-UART
python3 web/server.py --fpga

# port eksplisit
python3 web/server.py --fpga /dev/ttyUSB0 --baud 115200

# Windows
py -3.14 -m web.server --fpga COM8 --open
```

Chip menandatangani tegangan di pin ADC. Dashboard mengubahnya ke tegangan baterai dengan profil yang sama dengan station CLI (`--profil`, bawaan `sel`): kenop 0–3,3 V di A0 dibaca sebagai satu sel Li-ion 0–4,2 V, terkuras dalam di bawah 2,5 V, dan satu siklus berarti turun di bawah 3,0 V lalu naik di atas 4,0 V. Verifikasi tanda tangan tetap memakai nilai pin yang asli. Grafik dashboard dibuat untuk skala sel, sedangkan profil `aki12v` dipakai lewat station CLI.

Persyaratan: `pyserial` terpasang dan pengguna masuk grup `dialout` (atau punya
akses ke port). Auto-deteksi memprioritaskan CP2102/CH340; port KV260 “ML
Carrier Card” biasanya console PS, bukan UART Pmod. Jika hanya port itu yang
terlihat, sambungkan adapter CP2102 atau beri `--fpga /dev/ttyUSBx` secara
eksplisit. Cek dulu dengan `python3 -m model.station --port /dev/ttyUSBx`.

### Perbedaan mode FPGA

- Slider tegangan, “Catat sampel”, dan rekam otomatis disembunyikan. FPGA
  mengambil sampel ADS1115 sendiri sekitar satu detik sekali.
- Tombol **Muat riwayat** mengambil dump bertanda tangan tanpa verifikasi,
  sehingga grafik dapat bergerak sebelum tombol **Tukar baterai** ditekan.
- **Tukar baterai** menjalankan autentikasi dan verifikasi riwayat yang
  sesungguhnya di board. Jangkar (`seq_anchor`) hanya maju setelah verifikasi
  berhasil.
- **Hapus catatan** / **Ubah angka** mengubah salinan dump di laptop stasiun,
  lalu verifikasi memakai nonce dan tag asli dari FPGA. Hasilnya
  `HISTORY_GAP` atau `INVALID_HMAC`.
- **Cabut daya chip** dinonaktifkan; lakukan di board. **Reset demo** hanya
  membersihkan tampilan, bukan riwayat FPGA.
- Setelah memuat ulang bitstream, `seq` chip kembali ke 0. Restart server
  dashboard agar jangkar basis data ikut kembali ke 0; kalau tidak, verifikasi
  pertama akan melaporkan `HISTORY_ROLLBACK`.

Wiring board dan urutan pemuatan ada di `fpga/kv260/RUNBOOK.md`. Pin UART:
B10 `uart_tx` → RX adapter, E12 `uart_rx` ← TX adapter, GND bersama.

## Alur demo

### Simulasi

1. **Tukar baterai** untuk verifikasi awal: `DITERIMA`, kartu kesehatan terisi.
2. Geser ke `2,0 V`, **Catat sampel**, lalu **Hapus catatan**; tukar untuk
   memicu `HISTORY_GAP`.
3. **Pulihkan catatan**, tukar lagi untuk `DITERIMA`.
4. Catat sampel baru, **Ubah angka**, tukar untuk `INVALID_HMAC`. Tiga
   penolakan berturut-turut mengunci chip.
5. **Cabut daya chip** lalu tukar untuk `ROLLBACK`.
6. **Buka kunci chip** atau **Reset demo** untuk mengulang.

### FPGA

1. Nyalakan board, muat bitstream, sambungkan UART, jalankan server `--fpga`.
2. Putar potensiometer; tekan **Muat riwayat** untuk melihat sampel baru.
3. **Tukar baterai** → `DITERIMA` dan kesehatan terverifikasi.
4. Putar ke bawah, tunggu satu sampel, **Muat riwayat**, lalu **Hapus catatan**
   atau **Ubah angka**; **Tukar baterai** → `DITOLAK`.
5. **Pulihkan catatan**, tukar lagi → `DITERIMA`. Tiga penolakan mengunci chip;
   **Buka kunci chip** mengembalikannya.

## Pengujian

```bash
python3 -m unittest web.test_demo web.test_hardware -v
```

Tes hardware memakai `FakeStation` berbasis model chip di memori, jadi tidak
memerlukan board. Tes mencakup refresh tanpa verifikasi, verifikasi riwayat
bertanda tangan asli, deteksi hapus/ubah, pemulihan, buffer 64 catatan, dan
penguncian setelah tiga penolakan.
