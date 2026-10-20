# Dashboard web SeBatt

Dashboard browser untuk demo stasiun penukaran baterai SeBatt. Semua data
berasal dari simulasi di `web/demo.py`; tidak memerlukan Flask, FastAPI, atau
koneksi internet.

## Menjalankan

```bash
python3 web/server.py
```

Buka <http://127.0.0.1:8000>. Opsi yang tersedia:

```bash
python3 web/server.py --host 0.0.0.0 --port 8080 --open
```

- `/` — dashboard stasiun
- `/diagram` — diagram use case
- `/use-case.png` dan `/use-case.pdf` — berkas diagram ukuran penuh

State demo disimpan di memori proses. Menghentikan server atau menekan
**Reset demo** mengembalikan 16 catatan awal.

## Alur demo

1. Tekan **Tukar baterai** untuk verifikasi awal: hasil `DITERIMA`, kartu
   kesehatan baterai terisi.
2. Geser tegangan ke `2,0 V`, tekan **Catat sampel**, lalu **Hapus catatan**.
   Tukar lagi untuk memicu `HISTORY_GAP`.
3. Tekan **Pulihkan catatan**, lalu tukar lagi untuk kembali `DITERIMA`.
4. Catat sampel baru, tekan **Ubah angka**, lalu tukar untuk memicu
   `INVALID_HMAC`. Tiga penolakan berturut-turut mengunci chip.
5. **Cabut daya chip** lalu tukar untuk memicu `ROLLBACK`.
6. Gunakan **Buka kunci chip** atau **Reset demo** untuk mengulang.

Tombol serangan hanya aktif setelah ada verifikasi awal dan catatan baru yang
belum masuk ke `last_seq` server.

## Pengujian

```bash
python3 -m unittest web.test_demo -v
```

Tes mencakup verifikasi awal, deteksi catatan hilang dan berubah, pemulihan,
buffer 64 catatan, rollback setelah daya dicabut, dan penguncian setelah tiga
penolakan.
