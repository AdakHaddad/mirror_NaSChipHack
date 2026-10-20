# Rangkaian ADC Eksternal

Panduan merakit ADC eksternal untuk demo SeBatt, dari daftar belanja sampai uji di board. ADC berada di luar FPGA karena KV260 tidak menyediakan masukan analog di konektornya. Satu-satunya jalur sinyal ke logika FPGA adalah header Pmod J2.

## Pilihan ADC

| Pilihan | Keterangan | Rekomendasi |
|---|---|---|
| **MCP3202** | 12 bit, 2 kanal, SPI, kemasan DIP-8, catu 2,7–5,5 V | Utama |
| MCP3008 | 10 bit, 8 kanal, SPI, DIP-16 | Cadangan apabila MCP3202 tidak tersedia. Format pesannya mirip, hanya resolusi lebih rendah |
| Digilent Pmod AD1 | Modul Pmod siap colok, 12 bit, 2 kanal | Paling praktis, tetapi lebih mahal dan jarang tersedia di toko lokal |
| ADS1115 / ADS1015 | Antarmuka I2C | Tidak dipakai, karena rancangan memakai SPI |

## Daftar Belanja

| Barang | Jumlah | Catatan |
|---|---|---|
| MCP3202 DIP-8 | 2 | Satu cadangan |
| Potensiometer 10 kΩ linear dengan kenop besar | 2 | Satu cadangan. Kenop besar agar mudah diputar juri |
| Kapasitor keramik 100 nF | 4 | Decoupling catu dan filter masukan |
| Kapasitor elektrolit 10 µF | 2 | Decoupling catu |
| Resistor 330 Ω | 4 | Pembatas arus LED |
| LED 10 mm hijau dan merah | 2 + 2 | Penanda status di breadboard |
| Resistor 1% 47 kΩ, 10 kΩ, dan 3,3 kΩ | Masing-masing 2 | Pembagi tegangan 12 V dan resistor seri potensiometer |
| Saklar toggle mini SPDT (lubang 6 mm) | 1 | Saklar LIVE/DEMO |
| Dioda Schottky BAT43 | 2 | Pelindung masukan ADC |
| Sekring 0,5 A dengan dudukan inline | 1 | Di kabel (+) baterai |
| Kabel dan terminal untuk aki 12 V | 1 set | Dari kutub baterai ke casing |
| Adaptor USB-UART CP2102 (logika 3,3 V) | 3 | Board ke laptop, laptop ke laptop, satu cadangan |
| Breadboard kecil | 1 | |
| Kabel jumper male-female dan male-male | Masing-masing 20 | Header Pmod berupa pin, sehingga perlu ujung female |
| Casing cetak 3D dan strap velcro 25 mm | 1 + 2 | Lihat folder casing |

## Pin MCP3202

```
         ┌───U───┐
 CS/SHDN │1     8│ VDD/VREF   (3,3 V, juga menjadi tegangan referensi)
     CH0 │2     7│ CLK
     CH1 │3     6│ DOUT
     VSS │4     5│ DIN
         └───────┘
```

VDD sekaligus menjadi tegangan referensi. Dengan VDD 3,3 V, rentang masuk ADC adalah 0–3,3 V. Tegangan di atas VDD tidak boleh masuk ke CH0 atau CH1.

## Rangkaian di Dalam Casing (Baterai 12 V)

Casing dari [folder casing](../../casing/README.md) ditempel ke baterai 12 V. Saklar LIVE/DEMO di tutup memilih sumber tegangan yang masuk ke CH0:

- **LIVE:** tegangan baterai 12 V yang sebenarnya, melalui pembagi tegangan.
- **DEMO:** kenop potensiometer, untuk memperagakan baterai yang terkuras tanpa benar-benar menguras baterai.

```
(+) baterai ── sekring 0,5 A ── 47 kΩ ──┬── titik LIVE
                                         │
                                       10 kΩ
                                         │
(−) baterai ─────────────────────────────┴── GND

3,3 V ── 3,3 kΩ ── [potensiometer 10 kΩ] ── GND
                          │
                       wiper = titik DEMO

titik LIVE ──┐
             ├── saklar SPDT ──┬── MCP3202 pin 2 (CH0)
titik DEMO ──┘                 ├── 100 nF ke GND
                               └── dioda Schottky ke 3,3 V (pelindung)
```

**Pembagi tegangan 47 kΩ dan 10 kΩ** memberi rasio 10/57 = 0,175. Hasilnya untuk beberapa kondisi:

| Tegangan baterai | Masuk ADC | Keterangan |
|---|---|---|
| 14,4 V | 2,53 V | Tertinggi saat diisi (aki timbal-asam) |
| 12,6 V | 2,21 V | Penuh |
| 10,5 V | 1,84 V | Sekitar batas terkuras dalam untuk aki 12 V |

Satu kode ADC setara sekitar 4,6 mV tegangan baterai. Stasiun mengalikan nilai masuk ADC dengan 5,7 untuk mendapatkan tegangan baterai.

**Potensiometer dengan resistor seri 3,3 kΩ** menghasilkan 0–2,48 V, setara 0–14,1 V baterai setelah dikali 5,7. Dengan demikian, kedua posisi saklar memakai faktor yang sama, dan stasiun tidak perlu tahu posisi saklar.

**Pengaman:**
- Sekring 0,5 A dipasang sedekat mungkin dengan kutub (+) baterai, karena baterai 12 V dapat mengalirkan arus sangat besar bila kabel terhubung singkat.
- Dioda Schottky (misalnya BAT43) dari CH0 ke 3,3 V menahan tegangan berlebih apabila pembagi terlepas.
- GND baterai disatukan dengan GND Pmod. Hanya kutub (−) yang terhubung langsung, sedangkan kutub (+) selalu melalui pembagi.

**Batas terkuras dalam** bergantung pada jenis baterai. Untuk aki timbal-asam 12 V sekitar 10,5 V. Untuk paket Li-ion 3S sekitar 9 V (3,0 V per sel). Batas ini disesuaikan di dashboard dengan jenis baterai yang dipakai.

Kapasitor 100 nF dan 10 µF tetap dipasang dekat pin 8 MCP3202. CH1 dihubungkan ke GND.

## Sambungan ke Pmod

Header Pmod J2 berisi 2 baris × 6 pin. Pin 5 dan 11 adalah GND, pin 6 dan 12 adalah 3,3 V. Delapan pin sisanya adalah sinyal ke logika FPGA.

| Pin Pmod | Sinyal | Tujuan |
|---|---|---|
| 1 | SPI CS | MCP3202 pin 1 |
| 2 | SPI MOSI | MCP3202 pin 5 (DIN) |
| 3 | SPI MISO | MCP3202 pin 6 (DOUT) |
| 4 | SPI SCK | MCP3202 pin 7 (CLK) |
| 5 | GND | GND breadboard |
| 6 | 3,3 V | VDD MCP3202 dan rangkaian potensiometer |
| 7 | UART TX (dari FPGA) | RX adaptor CP2102 |
| 8 | UART RX (ke FPGA) | TX adaptor CP2102 |
| 9 | LED hijau | Resistor 330 Ω, lalu LED, lalu GND |
| 10 | LED merah | Resistor 330 Ω, lalu LED, lalu GND |
| 11 | GND | GND adaptor CP2102 |
| 12 | 3,3 V | Tidak dipakai |

Urutan pin 1–4 mengikuti konvensi Pmod SPI dari Digilent. Nama pin paket FPGA (untuk file XDC) diambil dari board file KV260 di Vivado, bukan dari tabel ini.

Hal yang perlu dijaga:
- Pin 5V pada adaptor CP2102 tidak disambungkan. Adaptor mendapat daya dari USB laptop.
- Semua GND disatukan: Pmod, MCP3202, potensiometer, dan adaptor CP2102.
- Catu 3,3 V Pmod dibatasi 100 mA. MCP3202 dan potensiometer hanya menarik beberapa miliampere.

## Cara Membaca MCP3202

Satu pembacaan memakai SPI mode 0 (clock diam di logika 0). MCP3202 membaca DIN pada tepi naik clock dan mengubah DOUT pada tepi turun, sehingga FPGA membaca DOUT pada tepi naik.

1. CS diturunkan ke 0.
2. FPGA mengirim 4 bit konfigurasi melalui DIN, satu bit per clock:

| Bit | Nilai | Arti |
|---|---|---|
| Start | 1 | Awal perintah |
| SGL/DIFF | 1 | Mode single-ended |
| ODD/SIGN | 0 | Kanal CH0 (1 untuk CH1) |
| MSBF | 1 | Data dikirim mulai dari bit paling penting |

3. Satu clock berikutnya MCP3202 mengirim null bit (0) melalui DOUT.
4. Dua belas clock berikutnya MCP3202 mengirim hasil 12 bit, dimulai dari bit 11.
5. CS dinaikkan kembali ke 1.

Total 17 clock per pembacaan. Pada catu 3,3 V, clock SPI dijaga di bawah 0,9 MHz. Contohnya, clock FPGA 100 MHz dibagi 200 menghasilkan 500 kHz.

Konversi nilai:

$$V_{masuk} = \frac{kode}{4096} \times 3.3\ \text{V}$$

Contoh: kenop di tengah memberi sekitar 1,65 V, sehingga kode sekitar 2048.

## Antarmuka Modul spi_adc

| Port | Arah | Fungsi |
|---|---|---|
| clk, rst_n | Masuk | Clock sistem dan reset |
| start | Masuk | Pulsa satu clock dari auth_ctrl untuk mengambil satu sampel |
| busy | Keluar | 1 selama pembacaan berlangsung |
| valid | Keluar | Pulsa satu clock ketika data siap |
| data[11:0] | Keluar | Hasil ADC |
| spi_cs_n, spi_sck, spi_mosi | Keluar | Ke Pmod pin 1, 4, 2 |
| spi_miso | Masuk | Dari Pmod pin 3 |

Pengatur waktu sampel (setiap 100 ms pada demo) berada di auth_ctrl, sehingga spi_adc cukup mengurus satu pembacaan setiap ada pulsa start.

## Urutan Pengujian

1. **Tanpa FPGA.** Rakit di breadboard, beri 3,3 V dari power supply, lalu ukur CH0 dengan multimeter sambil memutar kenop. Tegangan harus bergerak 0–3,3 V.
2. **Uji SPI dengan mikrokontroler (opsional, paling cepat).** Baca MCP3202 dengan STM32 atau Arduino yang sudah ada di lab untuk memastikan rangkaian dan perintah SPI benar sebelum RTL dikerjakan.
3. **Simulasi spi_adc.** Testbench cocotb dengan model MCP3202 sederhana yang membalas kode tetap, misalnya 0xA5C. Pastikan urutan 17 clock dan bit konfigurasi sesuai tabel di atas.
4. **Cmod S7.** Sambungkan rangkaian ke header Pmod Cmod S7, kirim hasil pembacaan ke laptop melalui UART, lalu bandingkan dengan multimeter. Selisih yang wajar beberapa kode.
5. **KV260.** Pindahkan sambungan ke Pmod J2 dan ganti file constraint ke pin KV260.

## Batasan

- Tegangan dapat dipalsukan sebelum masuk MCP3202 atau di jalur SPI. Pada produk, ADC berada di dalam chip yang sama dengan IP SeBatt.
- Demo memakai baterai 12 V. Paket motor listrik bertegangan 48 V ke atas membutuhkan isolasi dan proteksi masukan yang lebih ketat.
- Mode DEMO memakai potensiometer, sehingga adegan baterai terkuras tidak berasal dari baterai yang benar-benar terkuras. Hal ini disebutkan saat pitch.
