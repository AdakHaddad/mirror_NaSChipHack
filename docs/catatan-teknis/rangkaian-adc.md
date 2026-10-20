# Rangkaian ADC Eksternal

Panduan merakit ADC eksternal untuk demo SeBatt, dari daftar belanja sampai uji di board. ADC berada di luar FPGA karena KV260 tidak menyediakan masukan analog di konektornya. Satu-satunya jalur sinyal ke logika FPGA adalah header Pmod J2.

## Pilihan ADC

Demo memakai **modul ADS1115** (16 bit, 4 kanal, I2C). Pilihan ini diambil 19 Oktober karena modul ADC SPI tidak tersedia, dan RTL pembacanya (i2c_master dan ads1115_ctrl) sudah lolos simulasi.

| Parameter | Nilai |
|---|---|
| Antarmuka | I2C, 2 kabel (SCL, SDA), 100 kHz |
| Alamat | 0x48 (pin ADDR ke GND) |
| Kanal | AIN0 terhadap GND |
| Rentang | ±4,096 V, 1 LSB = 0,125 mV |
| Catu | 3,3 V dari Pmod. Tegangan masuk tidak boleh melebihi VDD + 0,3 V |

## Daftar Belanja

| Barang | Jumlah | Catatan |
|---|---|---|
| Modul ADS1115 | 2 | Satu cadangan |
| Potensiometer 10 kΩ linear dengan kenop besar | 2 | Satu cadangan. Kenop besar agar mudah diputar juri |
| Kapasitor keramik 100 nF | 2 | Filter masukan AIN0 |
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

## Pin Modul ADS1115

| Pin modul | Sambungan |
|---|---|
| VDD | 3,3 V Pmod |
| GND | GND Pmod |
| SCL | Pmod pin 1 |
| SDA | Pmod pin 2 |
| ADDR | GND (alamat 0x48) |
| ALRT | Tidak dipakai |
| A0 | Keluaran saklar LIVE/DEMO |
| A1–A3 | Ke GND |

Modul umumnya sudah membawa resistor pull-up 10 kΩ di SCL dan SDA ke VDD, serta kapasitor decoupling. Karena pull-up mengikuti VDD, modul **wajib diberi 3,3 V, bukan 5 V**, agar pin FPGA tidak menerima 5 V.

## Rangkaian di Dalam Casing (Baterai 12 V)

Casing dari [folder casing](../../casing/README.md) ditempel ke baterai 12 V. Saklar LIVE/DEMO di tutup memilih sumber tegangan yang masuk ke A0:

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
             ├── saklar SPDT ──┬── ADS1115 A0
titik DEMO ──┘                 ├── 100 nF ke GND
                               └── dioda Schottky ke 3,3 V (pelindung)
```

**Pembagi tegangan 47 kΩ dan 10 kΩ** memberi rasio 10/57 = 0,175. Hasilnya untuk beberapa kondisi:

| Tegangan baterai | Masuk A0 | Keterangan |
|---|---|---|
| 14,4 V | 2,53 V | Tertinggi saat diisi (aki timbal-asam) |
| 12,6 V | 2,21 V | Penuh |
| 10,5 V | 1,84 V | Sekitar batas terkuras dalam untuk aki 12 V |

RTL mengirim tegangan A0 dalam milivolt. Stasiun mengalikannya dengan 5,7 untuk mendapatkan tegangan baterai. Satu LSB setara sekitar 0,7 mV tegangan baterai, sehingga ketelitian ADC jauh melebihi kebutuhan demo.

**Potensiometer dengan resistor seri 3,3 kΩ** menghasilkan 0–2,48 V, setara 0–14,1 V baterai setelah dikali 5,7. Dengan demikian, kedua posisi saklar memakai faktor yang sama, dan stasiun tidak perlu tahu posisi saklar.

Uji di meja tanpa casing boleh memakai potensiometer yang langsung terhubung antara 3,3 V dan GND, dengan wiper ke A0. Pada susunan ini faktor di stasiun adalah 1, bukan 5,7.

**Pengaman:**
- Sekring 0,5 A dipasang sedekat mungkin dengan kutub (+) baterai, karena baterai 12 V dapat mengalirkan arus sangat besar bila kabel terhubung singkat.
- Dioda Schottky (misalnya BAT43) dari A0 ke 3,3 V menahan tegangan berlebih apabila pembagi terlepas.
- GND baterai disatukan dengan GND Pmod. Hanya kutub (−) yang terhubung langsung, sedangkan kutub (+) selalu melalui pembagi.

**Batas terkuras dalam** bergantung pada jenis baterai. Untuk aki timbal-asam 12 V sekitar 10,5 V. Untuk paket Li-ion 3S sekitar 9 V (3,0 V per sel). Batas ini disesuaikan di dashboard dengan jenis baterai yang dipakai.

## Sambungan ke Pmod

Header Pmod J2 KV260 berisi 2 baris × 6 pin. Pin 5 dan 11 adalah GND, pin 6 dan 12 adalah 3,3 V. Delapan pin sisanya adalah sinyal ke logika FPGA.

| Pin Pmod | Sinyal | Tujuan |
|---|---|---|
| 1 | I2C SCL | ADS1115 SCL |
| 2 | I2C SDA | ADS1115 SDA |
| 3 | Tombol atau pemilih sumber | Cadangan |
| 4 | – | Bebas |
| 5 | GND | GND breadboard |
| 6 | 3,3 V | VDD ADS1115 dan rangkaian potensiometer |
| 7 | UART TX (dari FPGA) | RX adaptor CP2102 |
| 8 | UART RX (ke FPGA) | TX adaptor CP2102 |
| 9 | LED hijau | Resistor 330 Ω, lalu LED, lalu GND |
| 10 | LED merah | Resistor 330 Ω, lalu LED, lalu GND |
| 11 | GND | GND adaptor CP2102 |
| 12 | 3,3 V | Tidak dipakai |

Di Cmod S7, SCL dan SDA juga berada di pin 1 dan 2 Pmod JA (J2 dan H2), sedangkan UART memakai USB-UART bawaan board. Nama pin paket KV260 untuk file XDC diambil dari master XDC KV260, bukan dari tabel ini.

Hal yang perlu dijaga:
- Pin 5V pada adaptor CP2102 tidak disambungkan. Adaptor mendapat daya dari USB laptop.
- Semua GND disatukan: Pmod, ADS1115, potensiometer, dan adaptor CP2102.
- Catu 3,3 V Pmod dibatasi 100 mA. ADS1115 dan potensiometer hanya menarik kurang dari 1 mA.
- SCL dan SDA ditulis open-drain di RTL. FPGA hanya menarik ke 0, sedangkan logika 1 berasal dari pull-up modul.
- Belum dipastikan apakah jalur Pmod KV260 melewati penggeser level yang mengganggu sinyal open-drain. Cek di skematik carrier card atau tanyakan ke mentor.

## Cara Membaca ADS1115

ads1115_ctrl memakai mode single-shot. Setiap ada pulsa start:

1. Tulis konfigurasi 0xC383 ke register 0x01. Artinya: mulai konversi, AIN0 terhadap GND, rentang ±4,096 V, single-shot, 128 sampel per detik, komparator mati.
2. Tunggu 10 ms. Satu konversi pada 128 sampel per detik memerlukan 7,8 ms.
3. Baca 2 byte dari register 0x00.
4. Hitung mV = raw >> 3. Nilai negatif dijadikan 0.

Konversi nilai:

$$V_{A0} = \frac{raw}{8}\ \text{mV}$$

Contoh: kenop di tengah memberi sekitar 1,24 V pada rangkaian casing, sehingga mV sekitar 1240 dan tegangan baterai di stasiun sekitar 7,1 V.

## Antarmuka Modul ads1115_ctrl

| Port | Arah | Fungsi |
|---|---|---|
| clk, resetn | Masuk | Clock sistem dan reset aktif rendah |
| start | Masuk | Pulsa satu clock untuk mengambil satu sampel |
| busy | Keluar | 1 selama pembacaan berlangsung |
| valid | Keluar | Pulsa satu clock ketika data siap |
| error | Keluar | 1 apabila ADS1115 tidak membalas ACK, bertahan sampai start berikutnya |
| raw[15:0] | Keluar | Hasil mentah ADS1115 |
| mv[15:0] | Keluar | Tegangan A0 dalam milivolt |
| scl, sda | Dua arah | Ke Pmod pin 1 dan 2 |

`auth_ctrl` memicu `ads1115_ctrl` dari pewaktu sampel setiap 1 detik (default demo); `AUTH_REQ` dan `READ_HIST_REQ` memakai sampel terbaru tanpa memulai konversi baru.

## Urutan Pengujian

1. **Tanpa FPGA.** Rakit di breadboard, beri 3,3 V dari power supply, lalu ukur A0 dengan multimeter sambil memutar kenop. Tegangan harus bergerak sesuai tabel di atas.
2. **Uji I2C dengan mikrokontroler (opsional, paling cepat).** Baca ADS1115 dengan STM32 atau Arduino untuk memastikan modul hidup di alamat 0x48.
3. **Simulasi.** Jalankan uji cocotb ads1115 di folder sim. Uji ini lolos 2/2 (dijalankan ulang 20 Okt).
4. **Cmod S7 (T9).** Sambungkan modul ke Pmod JA, kirim AUTH_REQ dari stasiun sambil memutar kenop, lalu bandingkan nilai V dengan multimeter. Tidak boleh ada NACK. Prosedur lengkap ada di [RUNBOOK Cmod S7](../../fpga/cmod_s7/RUNBOOK.md).
5. **KV260.** Pindahkan sambungan ke Pmod J2 dengan urutan pin yang sama dan ganti file constraint ke pin KV260.

## Batasan

- Tegangan dapat dipalsukan sebelum masuk ADS1115 atau di jalur I2C. Pada produk, ADC berada di dalam chip yang sama dengan IP SeBatt.
- Demo memakai baterai 12 V. Paket motor listrik bertegangan 48 V ke atas membutuhkan isolasi dan proteksi masukan yang lebih ketat.
- Mode DEMO memakai potensiometer, sehingga adegan baterai terkuras tidak berasal dari baterai yang benar-benar terkuras. Hal ini disebutkan saat pitch.
