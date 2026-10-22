# Virtuoso Layout lewat RDP — panduan untuk `tutorial/hack01`

Panduan praktis mengerjakan layout di Cadence Virtuoso pada RDP
`10.251.7.7` (user `hack01`). Ditulis 22 Oktober 2026.

> **Password tidak disimpan di file ini.** Ketik saat Remmina meminta.
> Jangan pernah commit password ke repo.

Panduan ini sengaja generik karena isi `tutorial/hack01` belum diperiksa.
**Baca README/PDF di folder tutorial lebih dulu** — kalau ada instruksi
yang berbeda, ikuti tutorialnya. Bagian yang tidak cocok dengan PDK atau
versi Virtuoso di RDP tinggal disesuaikan.

## 0. Yang perlu disiapkan

- Remmina di laptop (`which remmina`).
- Host: `10.251.7.7`, user: `hack01`.
- Password: yang diberikan terpisah.
- Folder tutorial di mesin RDP: `tutorial/hack01` (bisa di `~` atau di
  path lain; cari dulu).

## 1. Masuk ke RDP

### Lewat GUI Remmina

1. Buka Remmina.
2. Klik **+** untuk profil baru.
3. Isi:
   - Protocol: **RDP**
   - Server: `10.251.7.7`
   - Username: `hack01`
   - Domain: kosongkan (atau `10.251.7.7` kalau diminta)
   - Password: kosongkan; isi saat prompt muncul
   - Resolution: **Use client resolution**
   - Color depth: **32 bpp**
4. **Connect**, lalu ketik password.

### Lewat terminal

```bash
remmina -c rdp://hack01@10.251.7.7
```

Kalau `xfreerdp` tersedia:

```bash
xfreerdp /v:10.251.7.7 /u:hack01 /dynamic-resolution /clipboard
```

Jangan menulis `/p:password` di command line — password akan tersimpan
di shell history. Biarkan `xfreerdp` yang meminta.

## 2. Sepuluh menit pertama di RDP

Buka terminal di desktop RDP, lalu:

```bash
hostname; whoami; pwd
```

Cari folder tutorial:

```bash
ls ~/tutorial/hack01
find ~ -maxdepth 4 -iname '*hack01*' -print 2>/dev/null
# kalau tidak ketemu:
find / -maxdepth 4 -type d -name hack01 2>/dev/null
```

Baca instruksinya dulu:

```bash
ls -la ~/tutorial/hack01
cat ~/tutorial/hack01/README* 2>/dev/null
# PDF:
evince ~/tutorial/hack01/*.pdf &
```

Buat salinan kerja supaya file tutorial tidak rusak (kalau tutorial
tidak melarang):

```bash
mkdir -p ~/work
cp -r ~/tutorial/hack01 ~/work/
cd ~/work/hack01
```

Cek PDK dan lisensi:

```bash
echo "PDK_ROOT=$PDK_ROOT"
echo "CDS_LIC_FILE=$CDS_LIC_FILE"
ls -la
cat cds.lib 2>/dev/null
```

Yang dicari: nama technology library (misalnya `gpdk180`, `tsmc18`,
`sky130A`) dan file setup Cadence.

## 3. Menjalankan Virtuoso

Dari folder tutorial/kerja:

```bash
ls -la          # cari setup.sh, setup.csh, .cshrc, cds.lib
source ./setup.sh          # kalau bash
# atau
source ./setup.csh         # kalau tcsh/csh
virtuoso &
```

Kalau `virtuoso: command not found`:

```bash
which virtuoso
module avail 2>/dev/null | grep -i cadence
ls /opt /tools /cadence 2>/dev/null
```

Berarti environment Cadence belum di-source. Cari file setup di folder
tutorial atau tanya admin lab; jangan menebak path.

## 4. Library dan cellview layout

### Kalau tutorial sudah punya library

Jangan membuat library baru. Buka **Library Manager**
(**Tools > Library Manager**), lalu **File > Open** dan pilih
library/cell yang disebut di tutorial.

### Kalau harus membuat dari nol

1. **File > New > Library**
2. Name: misalnya `hack01_<inisial>`
3. Pilih **Attach to an existing technology library**
4. Pilih technology library PDK yang dipakai tutorial
   (nama persisnya ada di README; contoh `gpdk180`, `tsmc18`, `sky130A`)
5. **OK**

Langkah 3–4 penting. Tanpa attach technology library, layer, via, PCell,
dan runset DRC tidak akan muncul.

Buat cellview layout:

1. **File > New > Cell View**
2. Library: library di atas
3. Cell: nama cell dari tutorial (misalnya `inv`, `nand2`, atau
   `hack01`)
4. View: `layout`
5. Tool: **Virtuoso**
6. **OK**

## 5. Setting awal Layout Editor

- Panel **LSW** di kiri: pilih layer sebelum menggambar.
- Tekan `e` (Display Options): aktifkan grid, snap, pin names, dan
  marker.
- Set grid/snap sesuai tutorial. Nilai umum: grid `0.005 µm`, snap
  `0.005 µm` untuk 180 nm; cek angka yang diminta tutorial.
- `f` untuk fit view; `k` untuk ruler.

### Bindkey yang sering dipakai

| Tombol | Fungsi |
|---|---|
| `r` | Rectangle |
| `p` | Path |
| `w` | Wire (kalau ter-bind) |
| `i` | Instance |
| `m` | Move |
| `c` | Copy |
| `s` | Stretch |
| `q` | Properties |
| `k` | Ruler |
| `f` | Fit |
| `u` | Undo |
| `F2` | Save |
| `Esc` | Cancel |
| `Delete` | Delete |

Kalau satu bindkey tidak jalan, cek **Options > Bindkeys**; tiap instalasi
bisa berbeda.

### Membuat objek

- **Create > Rectangle** — diff/active, poly, metal.
- **Create > Path** — routing.
- **Create > Via** — pindah layer. Pilih via dari PDK (misalnya `V1`
  untuk metal1–metal2; di SKY130 `mcon` untuk li1–met1). Jangan menumpuk
  via manual kalau PDK sudah menyediakan.
- **Create > Instance** — transistor PCell atau sel dari library PDK.
  Setelah diletakkan, `q` untuk mengubah W/L, fingers, multiplier.
- **Create > Pin** — port. Nama harus **persis sama** dengan schematic
  (huruf besar/kecil berpengaruh), arah `input`/`output`/`inout`, dan
  letaknya di layer konduktor (biasanya metal1).
- **Create > Label** — teks; pin biasanya otomatis membuat label.
- **Create > Guard Ring** — kalau PDK menyediakan PCell guard ring.

## 6. Alur layout

Pilih salah satu. Kalau tutorial menyediakan schematic, pakai **Layout XL**.

### A. Dari schematic — Layout XL (disarankan)

1. Buka **schematic** cell yang akan di-layout.
2. **Launch > Layout XL** (atau **Tools > Layout XL**).
3. Buat/ pilih cellview `layout`.
4. Di Layout XL: **Connectivity > Generate > All From Source**
   (nama menu bisa sedikit berbeda). Ini membuat instance device dan pin
   dari schematic.
5. Tempatkan device; gunakan **Connectivity > Net Highlighting** dan
   tampilkan ratsnest untuk melihat koneksi yang belum tersambung.
6. Routing dengan `w`/`p` di metal layer yang benar; pasang via di
   perpindahan layer.
7. **Connectivity > Check Against Source**; perbaiki error sampai bersih.
8. **Verify > DRC**.

Kalau **Generate** abu-abu: cell tidak terhubung ke schematic, technology
library belum di-attach, atau PDK tidak punya PCell untuk device itu.

### B. Manual dari nol

1. Buat cellview `layout`.
2. Tempatkan device dengan `i` (kalau ada PCell), atau gambar dari nol
   mengikuti stick diagram/floorplan di tutorial.
3. Tambahkan pin dengan **Create > Pin**; nama harus sama dengan
   schematic.
4. Jalankan DRC lebih awal dan sering; jangan menunggu sampai selesai.

Contoh kalau tutorialnya inverter (hanya ilustrasi — nama layer ikut
PDK): nwell untuk PMOS, active/diff di dalam nwell dan pwell, poly
sebagai gate, contact, metal1, via, metal2; pin `A`, `Y`, `VDD`, `VSS`.
Jangan mengarang nama layer: pilih dari LSW.

## 7. DRC dan LVS

### DRC

1. **Verify > DRC**
2. Pilih runset/rule file dari tutorial atau PDK
   (misalnya `*.rul`, `*.runset`, Calibre/Assura/PVS runset).
3. **Run**; tunggu sampai selesai.
4. Klik marker; **Verify > Markers > Explain** untuk membaca pelanggaran.
5. Perbaiki, jalankan ulang, ulangi sampai **0 pelanggaran**.

### LVS

1. **Verify > LVS**
2. Pilih runset dari tutorial/PDK.
3. Bandingkan schematic vs layout (lewat extracted view).
4. Penyebab umum gagal:
   - nama atau arah pin salah;
   - label pin tidak berada di layer yang benar;
   - `VDD`/`VSS` belum tersambung;
   - W/L, fingers, atau multiplier device berbeda dari schematic;
   - ada net yang belum di-routing.

Kalau tutorial memakai Assura/Calibre/PVS, nama menu dan runset berbeda;
ikuti file Makefile/script di folder tutorial.

## 8. Simpan dan export GDS

Simpan:

```text
F2   atau   Design > Save
```

Export GDS dari GUI:

1. **File > Export > Stream...**
2. Library/cell/view: pilih cellview `layout`.
3. Output file: misalnya `~/work/hack01/<cell>.gds`.
4. Layer map: ambil dari PDK/tutorial (jangan mengarang).
5. Tech file: technology file PDK.
6. **OK**, lalu baca log — pastikan tidak ada error.

Alternatif command line (kalau tersedia):

```bash
strmout -library <lib> -strmFile <cell>.gds -topCell <cell> \
  -view layout -layerMap <layermap> -techFile <techfile>
```

Cek hasilnya:

```bash
ls -lh ~/work/hack01/*.gds
```

## 9. Checklist sebelum menutup sesi

- [ ] Layout sudah di-save (`F2`).
- [ ] DRC 0 pelanggaran.
- [ ] LVS bersih (kalau diminta).
- [ ] Semua pin bernama persis seperti schematic.
- [ ] GDS sudah diexport dan ukurannya masuk akal (bukan 0 byte).
- [ ] File hasil ada di home RDP, bukan hanya di memori.
- [ ] Logout dari RDP; jangan shutdown mesin.

## 10. Troubleshooting

| Gejala | Penyebab umum | Solusi |
|---|---|---|
| `virtuoso: command not found` | Environment belum di-source | `source setup.sh`/`setup.csh`; cek `module avail`; tanya admin |
| License error | `CDS_LIC_FILE` salah / server lisensi mati | `echo $CDS_LIC_FILE`; coba `lmstat`; hubungi admin |
| Layer tidak muncul di LSW | Library tidak di-attach ke tech library | Buat ulang library dengan **Attach to existing technology library** |
| Cellview read-only | File tutorial milik user lain | Copy ke `~/work`, atau minta akses tulis |
| DRC runset tidak ketemu | Path runset salah | Cari `*.rul`/`*.runset` di folder tutorial/PDK |
| LVS pin mismatch | Nama/arah pin atau label salah | Samakan nama dengan schematic; pastikan pin di metal |
| Snap tidak jalan | Grid/snap off | `e` > Display/Grid; aktifkan snap |
| GDS kosong | Cell/view/top cell salah | Cek pilihan di Stream Out dan baca log |
| RDP putus | Jaringan | Reconnect; pekerjaan tersimpan di home RDP, bukan di laptop |

## 11. Kalau macet

Kirim ke saya:

1. Screenshot jendela **CIW** (log Cadence) — terutama baris error merah.
2. Screenshot/teks **DRC** atau **LVS** log (20 baris terakhir).
3. Output `ls -la` folder `tutorial/hack01`.
4. Nama technology library/PDK yang dipakai.
5. Langkah persis yang sedang dikerjakan.

Tanpa tiga hal pertama, error-nya sering tidak bisa ditebak dari jauh.
