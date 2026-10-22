# Layout ASIC SeBatt dengan Cadence (Genus + Innovus, SKY130)

Panduan langkah demi langkah mengubah RTL `rtl/` menjadi GDSII yang bisa
dikirim ke shuttle chipIgnite (Caravel, SKY130A). Ditulis 22 Oktober 2026.

> **Ini panduan, bukan hasil eksekusi.** Laptop demo tidak punya lisensi
> Cadence, PDK SKY130, atau Magic/KLayout. Semua angka area dan clock di
> bawah adalah perkiraan sampai diganti laporan Genus/Innovus. Jalankan
> perintah `ls` pada path PDK sebelum memakai nama file di panduan ini.

## 0. Keputusan di depan

| Pertanyaan | Jawaban |
|---|---|
| Alur mana yang dipakai? | Genus (sintesis) + Innovus (P&R). Signoff DRC/LVS memakai KLayout + Magic/netgen karena deck Pegasus/PVS untuk SKY130 tidak publik. |
| Apakah Cadence diterima shuttle? | Ya. ChipFoundry menyatakan mendukung "industry-standard commercial tools"; yang dikirim hanya **GDSII area user**, bukan seluruh chip. OpenLane tetap alur referensi mereka, jadi GDS Cadence harus lolos precheck yang sama. |
| Berapa area user? | Caravel: 2.920 × 3.520 µm (± 10,3 mm²), 38 GPIO. Contoh config MPW memakai `DIE_AREA 0 0 2920 3520`. |
| Berapa area desain kita? | Perkiraan kasar 0,5–1 mm² (6.207 FF + SRAM 16 Kb + kombinasional). Ganti dengan `report_area` Genus. Masih < 10% area user. |
| Clock? | `wb_clk_i` (clock harness, puluhan MHz) atau `user_clock2` (contoh MPW: periode 10 ns = 100 MHz). Mulai 50 MHz (20 ns), baru naik ke 100 MHz. Angka WNS FPGA tidak otomatis pindah ke ASIC. |
| SRAM? | `tag_mem` 512 × 32 bit (16 Kb) = **satu SRAM dual-port (1 baca + 1 tulis)**, bukan flip-flop. `buf_mem` 64 × 48 bit boleh flip-flop. |
| Lisensi? | `CDS_LIC_FILE`/`LM_LICENSE_FILE` ke server kampus. Tanpa lisensi, pakai LibreLane/OpenLane 2 (lihat §7). |

Cadence juga punya SKY130 PDK dalam *VLSI Fundamentals Education Kit*
(kerja sama SkyWater–Cadence, 2023). Untuk submission tetap pakai
`sky130A` dari open_pdks/ciel, karena itu PDK yang dipakai Caravel.
Kalau memakai PDK kit kampus, konfirmasi dulu ke ChipFoundry.

## 1. Menyiapkan PDK dan tool

Pasang PDK dengan ciel (pengelola PDK, penerus volare):

```bash
python3 -m pip install --user --upgrade ciel
ciel ls-remote --pdk-family sky130     # pilih hash open_pdks terbaru
ciel enable --pdk-family sky130 <hash>
export PDK_ROOT=$HOME/.ciel
export PDK=sky130A
```

Alternatif: bangun sendiri dengan open_pdks
(`./configure --enable-sky130-pdk && make && sudo make install`).
Cek lisensi dan binary:

```bash
echo $CDS_LIC_FILE
which genus innovus
```

Path penting (struktur open_pdks; nama file bisa berbeda sedikit antar build):

| Isi | Path |
|---|---|
| Liberty typical | `$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib` |
| Liberty lambat (setup) | `.../lib/sky130_fd_sc_hd__ss_100C_1v60.lib` (cek `ls`) |
| Liberty cepat (hold) | `.../lib/sky130_fd_sc_hd__ff_n40C_1v95.lib` (cek `ls`) |
| LEF sel | `.../lef/sky130_fd_sc_hd.lef` |
| Tech LEF | `.../techlef/sky130_fd_sc_hd__nom.tlef` |
| GDS sel | `.../gds/sky130_fd_sc_hd.gds` |
| Model Verilog sel | `.../verilog/sky130_fd_sc_hd.v` |
| Deck DRC KLayout | `$PDK_ROOT/sky130A/libs.tech/klayout/drc/sky130A.lydrc` |
| Tech KLayout (lyt/map) | `$PDK_ROOT/sky130A/libs.tech/klayout/tech/` |
| RC Magic | `$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc` |
| Setup netgen | `$PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl` |

## 2. Menyiapkan RTL (bagian yang paling sering menggagalkan tapeout)

### 2.1 Dua tahap, bukan satu

Caravel mengharapkan `user_project_wrapper` sebagai top. Alur yang dipakai
proyek-proyek MPW:

1. **Harden core** `sebatt_core` (RTL kita + SRAM) menjadi makro:
   GDS + LEF + Liberty/Verilog + DEF.
2. **Harden wrapper** `user_project_wrapper` (makro tadi + pin Caravel)
   pada area 2.920 × 3.520 µm, lalu kirim GDS wrapper.

Satu tahap (flat, seluruh desain langsung di area 2.920 × 3.520 µm) juga
sah dan lebih cepat, tetapi utilisasi sangat rendah dan kabel panjang.
Untuk tapeout pertama, dua tahap lebih mudah di-debug.

### 2.2 Port wrapper

Wrapper Caravel punya (lihat `user_project_wrapper.v`):

- `wb_clk_i`, `wb_rst_i` (reset **aktif tinggi**), bus Wishbone
  `wbs_*`, `la_data_in/out`, `la_oenb`;
- `io_in[37:0]`, `io_out[37:0]`, `io_oeb[37:0]`;
- `user_clock2`, `user_irq[2:0]`;
- `vccd1`, `vssd1` (1,8 V) dan `vdda1/2`, `vssa1/2` (3,3 V, tidak dipakai).

Pemetaan yang diusulkan:

| Sinyal SeBatt | Caravel |
|---|---|
| `uart_rx` / `uart_tx` | `io_in[n]` / `io_out[n]`, `io_oeb[n]=0` |
| `scl`, `sda` | `io_in[n]`, `io_out[n]`, `io_oeb[n]` (open-drain: `oeb=1` saat lepas) |
| `src_sel` | `io_in[n]` |
| `led_green`, `led_red` | `io_out[n]`, `io_oeb[n]=0` |
| `wb_*` | `wbs_ack_o = 0`, `wbs_dat_o = 0` (atau slave register kecil, opsional) |
| `user_irq` | `3'b000` |

`resetn = ~wb_rst_i`, dan sebaiknya tambahkan sinkronisasi deassert reset.

### 2.3 Hal-hal yang harus diubah sebelum sintesis

- **Tri-state di dalam core tidak bisa di-routing Innovus.** `i2c_master`
  dan `ads1115_ctrl` memakai `inout scl/sda`. Pecah di batas core menjadi
  `scl_i, scl_o, scl_oe` (idem SDA), lalu di wrapper:
  `assign io_out[n] = 1'b0; assign io_oeb[n] = ~oe;`.
- **Parameter clock harus clock ASIC.** `CLK_HZ` di `sebatt_top`/`auth_ctrl`
  menentukan UART dan interval sampling. Untuk chip 50 MHz, elaborasi
  dengan `CLK_HZ=50_000_000`, bukan 100 MHz punya KV260.
- **SRAM.** `tag_mem` 512 × 32, satu port tulis (signer) dan satu port baca
  (READ_HIST). Buat makro SRAM dual-port 512×32 dengan OpenRAM (mendukung
  SKY130, menghasilkan `.lib/.lef/.gds`), lalu instansiasi sebagai makro.
  Jangan biarkan 16 Kb menjadi flip-flop. Isi awal tidak perlu di-reset:
  `hist_n` membatasi pembacaan ke catatan yang sudah ditulis.
- **Buang yang khusus board.** `sw[7:0]`, `led_hb`, dan pin Pmod tidak
  masuk wrapper; parameter `BATTERY_ID` tetap.
- **Lint dan simulasi gate-level.** Jalankan iverilog dengan model
  `sky130_fd_sc_hd.v` setelah sintesis; jangan menunggu sampai GDS.
- **DFT/scan tidak wajib** untuk 100 unit; uji fungsional lewat UART cukup.
  Catat ini sebagai batasan, bukan lupa.

Perkiraan: 6.207 FF + 16 Kb SRAM + kombinasional; pada 45% utilisasi
core sekitar 1,0–1,5 mm². Angka final dari `report_area`.

## 3. Sintesis dengan Genus

Contoh `syn/genus.tcl` (jalankan `genus -files syn/genus.tcl`; kalau server
hanya menyediakan mode legacy, ganti `set_db` dengan `set_attribute`):

```tcl
set PDK_ROOT $::env(PDK_ROOT)
set LIB_TT   $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
set SRAM_LIB syn/sram_512x32_tt.lib

read_libs $LIB_TT $SRAM_LIB
read_hdl -language v2001 [list \
  rtl/sha256_core.v rtl/hmac_sha256.v rtl/axil_master.v \
  rtl/uart_if.v rtl/i2c_master.v rtl/ads1115_ctrl.v \
  rtl/auth_ctrl.v rtl/sebatt_top.v syn/sebatt_core_wrapper.v ]
elaborate sebatt_core
read_sdc syn/sebatt_core.sdc

check_design -unresolved
set_db syn_generic_effort high
set_db syn_map_effort high
syn_generic
syn_map
syn_opt

report_area   > reports/genus_area.rpt
report_timing > reports/genus_timing.rpt
report_power  > reports/genus_power.rpt
write_hdl -mapped > out/sebatt_core.v
write_sdc          > out/sebatt_core.sdc
```

`syn/sebatt_core.sdc` minimal:

```tcl
create_clock -name clk -period 20.0 [get_ports clk]   ;# 50 MHz; 10.0 = 100 MHz
set_clock_uncertainty 0.5 [get_clocks clk]
set_input_delay  2.0 -clock clk [remove_from_collection [all_inputs] [get_ports clk]]
set_output_delay 2.0 -clock clk [all_outputs]
set_load 0.05 [all_outputs]
set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 -pin Y \
  [remove_from_collection [all_inputs] [get_ports clk]]
```

Yang diperiksa sebelum lanjut:

- `check_design` bersih: tidak ada black box selain SRAM, tidak ada latch.
- Semua sel terpetakan ke `sky130_fd_sc_hd`; SRAM tetap `dont_touch`.
- WNS ≥ 0 pada 20 ns (50 MHz). Naikkan ke 10 ns hanya setelah bersih.
- `report_area` masuk akal (ratusan ribu µm², bukan jutaan).

## 4. Place and route dengan Innovus

### 4.1 MMMC

`pnr/mmmc.tcl`:

```tcl
set PDK_ROOT $::env(PDK_ROOT)
set LIBDIR $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib

create_library_set -name tt -timing [list \
  $LIBDIR/sky130_fd_sc_hd__tt_025C_1v80.lib pnr/sram_512x32_tt.lib]
create_library_set -name ss -timing [list \
  $LIBDIR/sky130_fd_sc_hd__ss_100C_1v60.lib pnr/sram_512x32_ss.lib]
create_library_set -name ff -timing [list \
  $LIBDIR/sky130_fd_sc_hd__ff_n40C_1v95.lib pnr/sram_512x32_ff.lib]

create_constraint_mode -name func -sdc_files out/sebatt_core.sdc
create_delay_corner  -name slow -library_set ss
create_delay_corner  -name fast -library_set ff

create_analysis_view -name setup -constraint_mode func -delay_corner slow
create_analysis_view -name hold  -constraint_mode func -delay_corner fast
set_analysis_view -setup {setup} -hold {hold}
```

Cek nama corner dengan `ls $LIBDIR`; tidak semua build punya corner yang
sama. Kalau hanya ada `tt`, pakai tt untuk setup dan hold dan sebutkan
keterbatasannya.

### 4.2 Inisialisasi dan floorplan

```tcl
set init_lef_file [list \
  $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef \
  $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef \
  pnr/sram_512x32.lef ]
set init_verilog out/sebatt_core.v
set init_top_cell sebatt_core
set init_mmmc_file pnr/mmmc.tcl
init_design

setDesignMode -process 130
floorPlan -site unithd -d 900 800 10 10 10 10 -su 0.45
```

Sesuaikan ukuran dengan SRAM dan `report_area`; 900 × 800 µm hanya titik
awal. Tempatkan SRAM lebih dulu (`placeInstance`), snap ke grid, lalu
kunci (`setPlaceMode -place_global_place_io_pins true`).

Power (nama net makro Caravel adalah `vccd1`/`vssd1`; pin sel tetap
`VPWR`/`VGND`/`VPB`/`VNB`):

```tcl
globalNetConnect vccd1 -type pgpin -pin VPWR -inst *
globalNetConnect vccd1 -type pgpin -pin VPB  -inst *
globalNetConnect vssd1 -type pgpin -pin VGND -inst *
globalNetConnect vssd1 -type pgpin -pin VNB  -inst *

addRing -nets {vccd1 vssd1} -type core_rings \
  -layer {top met5 bottom met5 left met4 right met4} \
  -width 2.0 -spacing 1.0 -offset 1.0
sroute -connect {corePin blockPin} -layerChangeRange {met1 met5}
```

Pastikan pin `vccd1`/`vssd1` di top dikenali sebagai power/ground (bukan
sinyal biasa); `checkDesign -all` akan mengeluh kalau tidak. Ikat semua
input yang tidak dipakai, jangan dibiarkan floating.

Untuk tahap wrapper, salin urutan pin dan PDN dari
`caravel_user_project/openlane/user_project_wrapper` (`fixed_wrapper_cfgs.tcl`,
`pdn_cfg.tcl`); jangan mengarang urutan pin sendiri. DIE_AREA wrapper tetap
`0 0 2920 3520`.

### 4.3 Place, CTS, route

```tcl
placeDesign
optDesign -preCTS
checkPlace

create_ccopt_clock_tree_spec -file pnr/ccopt.spec
source pnr/ccopt.spec
ccopt_design

setNanoRouteMode -routeWithTimingDriven true
routeDesign
optDesign -postRoute
optDesign -postRoute -hold
```

Pemeriksaan wajib:

```tcl
verifyConnectivity -type all
check_antenna -detailed
checkDesign -all
report_timing -max_paths 20 > reports/pnr_timing.rpt
report_area   > reports/pnr_area.rpt
report_power  > reports/pnr_power.rpt
```

Kalau ada pelanggaran antena, sisipkan diode dari library
(`sky130_fd_sc_hd__diode_2`) pada net yang ditunjuk, lalu route ulang.
Jangan matikan cek antena.

### 4.4 Ekspor GDS

Paling aman: Innovus menulis DEF, lalu Magic/KLayout yang menulis GDS dengan
tech SKY130 (map layer bawaan PDK, tidak perlu map buatan sendiri).

```tcl
defOut out/sebatt_core.def
saveDesign out/sebatt_core.enc
saveNetlist out/sebatt_core.v
```

```tcl
# magic -d XR -rcfile $PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc
lef read $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef
lef read $PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
lef read pnr/sram_512x32.lef
def read out/sebatt_core.def
gds write out/sebatt_core.gds
```

`streamOut` langsung dari Innovus juga bisa, tetapi `sky130A.map` di PDK
adalah map gaya Magic/KLayout; map untuk `streamOut` harus dibuat dan
diperiksa manual. Untuk tapeout pertama, DEF → Magic/KLayout lebih sedikit
risikonya.

## 5. Signoff (open source)

DRC KLayout:

```bash
klayout -b -r $PDK_ROOT/sky130A/libs.tech/klayout/drc/sky130A.lydrc \
  -rd input=out/sebatt_core.gds \
  -rd report=out/sebatt_core.lyrdb \
  -rd topcell=sebatt_core
```

Magic DRC + ekstrak untuk LVS:

```tcl
# magic -d XR -rcfile $PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc
gds read out/sebatt_core.gds
load sebatt_core
select top cell
drc check
drc count
extract do local
extract all
ext2spice lvs
ext2spice -o out/sebatt_core.spice
```

LVS:

```bash
netgen -batch lvs \
  "out/sebatt_core.spice sebatt_core" \
  "out/sebatt_core.v sebatt_core" \
  $PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl \
  out/sebatt_core_lvs.rpt
```

Terakhir, precheck resmi shuttle (`mpw_precheck` dari ChipFoundry) pada GDS
wrapper. Precheck inilah gerbang sebenarnya, bukan DRC lokal.

## 6. Yang dikirim ke shuttle

- GDSII area user (`user_project_wrapper.gds`) — syarat utama ChipFoundry.
- LEF makro/wrapper (kalau diminta untuk integrasi; hasilkan dengan Cadence
  Abstract atau KLayout dari GDS).
- Netlist Verilog hasil sintesis + SDC, untuk review.
- Laporan: timing setup/hold, area, DRC, LVS, antena, precheck.
- Catatan batasan: tanpa scan/DFT, ADC eksternal, PUF belum aktif.

Checklist sebelum kirim:

- [ ] `check_design` Genus bersih; tidak ada black box selain SRAM.
- [ ] Timing setup dan hold ≥ 0 pada corner yang dipakai.
- [ ] DRC KLayout 0 pelanggaran; density metal terpenuhi.
- [ ] LVS match (termasuk SRAM dan pin power).
- [ ] Antena bersih.
- [ ] DIE_AREA wrapper 0 0 2920 3520; urutan pin sesuai Caravel.
- [ ] `vccd1`/`vssd1` tersambung ke seluruh sel dan SRAM.
- [ ] UART/I2C keluar lewat `io_*` dengan `io_oeb` benar.
- [ ] `CLK_HZ` sama dengan clock wrapper; reset polaritas benar.
- [ ] Precheck ChipFoundry lolos.

## 7. Kalau tidak punya lisensi Cadence

Gunakan LibreLane/OpenLane 2 dengan PDK dan constraint yang sama; konsepnya
satu-satu:

| Cadence | Open source |
|---|---|
| Genus | Yosys (+ ABC) |
| Innovus | OpenROAD (`floorplan`, `place`, `cts`, `route`) |
| Pegasus/PVS | KLayout + Magic + netgen |
| Abstract | KLayout / Magic `lef write` |

Hasil OpenLane bisa langsung dibandingkan dengan hasil Cadence pada
`report_area`, WNS, dan DRC; jangan membandingkan angka FPGA dengan ASIC.

## 8. Perkiraan waktu dan risiko

- Lingkungan + PDK: 2–4 jam (unduhan PDK besar).
- Perbaikan RTL (tri-state, wrapper, parameter, SRAM): 1 hari.
- Sintesis + P&R core 1–2 hari untuk yang sudah pernah; 3–5 hari untuk
  yang baru pertama kali.
- Wrapper + pin order + PDN: 1 hari.
- Signoff + precheck: 1 hari, sering jadi tempat munculnya kejutan.

Risiko terbesar, berurutan: SRAM macro tidak cocok, tri-state di dalam core,
urutan pin wrapper, antena/density, dan lisensi Cadence yang tidak tersedia
saat dibutuhkan.

## 9. Rujukan

- ChipFoundry, *chipIgnite FAQ* (harga, GDS-only, dukungan tool komersial):
  <https://chipfoundry.io/faqs>
- Caravel `user_project_wrapper.v` (daftar port dan power):
  <https://github.com/efabless/caravel_user_project>
- open_pdks dan ciel:
  <https://github.com/fossi-foundation/open-pdks>, <https://pypi.org/project/ciel/>
- Tech KLayout SKY130 (lyt/lydrc/map):
  <https://github.com/fossi-foundation/sky130_klayout_pdk>
- SkyWater–Cadence SKY130 Education Kit (latar belakang):
  <https://www.skywatertechnology.com/skywater-announces-availability-of-cadence-open-source-pdk-and-reference-design-for-skywaters-130-nm-process/>
- Tutorial Innovus umum (UI, MMMC, floorplan):
  <https://limsk.ece.gatech.edu/course/ece6133/lab/innovus.pdf>
