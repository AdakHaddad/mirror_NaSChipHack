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
| Resistor 1% 120 kΩ dan 15 kΩ | Masing-masing 2 | Pembagi tegangan LiPo. Pengganti: 100 kΩ + 22 kΩ seri dan 10 kΩ + 4,7 kΩ seri |
| Konektor JST-XH 4 pin betina | 1 | Pasangan konektor balance LiPo 3S |
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
| A0 | Wiper kenop pada pembagi LiPo |
| A1–A3 | Ke GND |

Modul umumnya sudah membawa resistor pull-up 10 kΩ di SCL dan SDA ke VDD, serta kapasitor decoupling. Karena pull-up mengikuti VDD, modul **wajib diberi 3,3 V, bukan 5 V**, agar pin FPGA tidak menerima 5 V.

## Rangkaian Baterai LiPo 3S

Skematik lengkap ada di [rangkaian-adc.png](../gambar/rangkaian-adc.png), dibuat oleh skrip rangkaian-adc.py di folder yang sama. Baterai demo adalah LiPo 3S (12,6 V penuh, 11,1 V nominal). Tegangannya diambil dari dua pin paling luar konektor balance JST-XH, sehingga kabel arus besar XT60 tidak disentuh. LiPo hanya diukur. KV260 tetap memakai adaptor 12 V sendiri.

Kenop potensiometer menjadi bagian dari pembagi tegangan, sehingga satu rangkaian melayani pembacaan asli sekaligus simulasi baterai terkuras.

```
(+) LiPo ── R1 120 kΩ ──┬── [kenop 10 kΩ] ──┬── R2 15 kΩ ── (−) LiPo = GND
                        atas    wiper       bawah
                                  │
                                  ├── 100 nF ke GND
                                  └── ADS1115 A0
```

**Kenop di ujung atas** memberi rasio 25/145, atau tegangan LiPo dibagi 5,8. Inilah tegangan LiPo yang sebenarnya, dan nilainya dapat dicocokkan dengan multimeter.

| Tegangan LiPo | Per sel | Masuk A0 |
|---|---|---|
| 12,6 V | 4,20 V (penuh) | 2,17 V |
| 11,1 V | 3,70 V (nominal) | 1,91 V |
| 9,0 V | 3,00 V (batas terkuras dalam) | 1,55 V |

**Kenop diputar turun** menurunkan rasio sampai 15/145 di ujung bawah. LiPo 12,4 V lalu terbaca 7,4 V, seolah baterai terkuras, tanpa benar-benar menguras sel. Tegangan A0 selalu berada di antara 1,3 V dan 2,17 V pada posisi kenop mana pun, jauh di bawah batas 3,3 V.

RTL mengirim tegangan A0 dalam milivolt. Stasiun mengalikannya dengan faktor di profil lipo3s (model/station.py). Satu LSB ADS1115 setara sekitar 0,7 mV tegangan LiPo.

**Kalibrasi.** Toleransi resistor 1% dan impedansi masukan ADS1115 dapat menggeser faktor sampai sekitar 2%. Putar kenop ke ujung atas, ukur LiPo dengan multimeter, lalu jalankan AUTH di station yang mencetak "pin N mV". Faktor baru adalah tegangan multimeter dibagi N. Isi nilai itu ke kolom scale profil lipo3s.

**Profil lipo3s** menilai riwayat dengan batas berikut:

| Kejadian | Batas |
|---|---|
| Terkuras dalam | di bawah 9,0 V (3,0 V per sel) |
| Satu siklus pengisian | turun di bawah 10,5 V, lalu naik di atas 12,3 V |
| Pita aman di grafik | 9,0–12,6 V |

Siklus pengisian hanya terhitung apabila pembacaan dengan kenop di ujung atas melewati 12,3 V. Untuk memperagakannya, LiPo perlu diisi penuh sebelum demo.

**Pengaman:**
- R1 disolder menempel di konektor J1. Setelah R1, kabel yang terhubung singkat hanya mengalirkan sekitar 0,1 mA, sehingga seluruh kabel ke breadboard aman tanpa sekring.
- Arus ke A0 dibatasi R1, sehingga dioda ESD internal ADS1115 sudah cukup sebagai pelindung.
- Kutub (−) LiPo disatukan dengan GND Pmod. Kutub (+) hanya terhubung melalui R1.
- Pembagi menarik sekitar 0,09 mA dari LiPo. Cabut konektor balance setelah demo.

Uji di meja tanpa LiPo memakai potensiometer yang langsung terhubung antara 3,3 V dan GND, dengan wiper ke A0. Susunan ini memakai profil sel, yang membaca 0–3,3 V di A0 sebagai satu sel Li-ion 0–4,2 V.

## Sambungan ke Pmod

Header Pmod J2 KV260 berisi 2 baris × 6 pin. Pin 5 dan 11 adalah GND, pin 6 dan 12 adalah 3,3 V. Delapan pin sisanya adalah sinyal ke logika FPGA.

| Pin Pmod | Sinyal | Tujuan |
|---|---|---|
| 1 | I2C SCL | ADS1115 SCL |
| 2 | I2C SDA | ADS1115 SDA |
| 3 | src_sel | GND = baca ADS1115, 3,3 V = sumber tetap 3000 mV. Jangan dibiarkan terbuka |
| 4 | led_hb | Resistor 330 Ω, lalu LED heartbeat, lalu GND |
| 5 | GND | GND breadboard dan (−) LiPo |
| 6 | 3,3 V | VDD ADS1115 |
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

Contoh: LiPo 12,4 V dengan kenop di ujung atas memberi sekitar 2,14 V di A0, sehingga mV sekitar 2138 dan tegangan baterai di stasiun 2138 × 5,8 ≈ 12,4 V.

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

1. **Tanpa FPGA.** Rakit pembagi, sambungkan LiPo, lalu ukur wiper terhadap GND dengan multimeter sambil memutar kenop. Tegangan harus bergerak di antara sekitar 1,3 V dan 2,17 V, dan tidak pernah melebihi 3,3 V. Baru setelah itu wiper disambung ke A0.
2. **Uji I2C dengan mikrokontroler (opsional, paling cepat).** Baca ADS1115 dengan STM32 atau Arduino untuk memastikan modul hidup di alamat 0x48.
3. **Simulasi.** Jalankan uji cocotb ads1115 di folder sim. Uji ini lolos 2/2 (dijalankan ulang 20 Okt).
4. **Cmod S7 (T9).** Sambungkan modul ke Pmod JA, kirim AUTH_REQ dari stasiun sambil memutar kenop, lalu bandingkan nilai V dengan multimeter. Tidak boleh ada NACK. Prosedur lengkap ada di [RUNBOOK Cmod S7](../../fpga/cmod_s7/RUNBOOK.md).
5. **KV260.** Pindahkan sambungan ke Pmod J2 dengan urutan pin yang sama dan ganti file constraint ke pin KV260.

## Batasan

- Tegangan dapat dipalsukan sebelum masuk ADS1115 atau di jalur I2C. Pada produk, ADC berada di dalam chip yang sama dengan IP SeBatt.
- Demo memakai LiPo 3S 12,6 V. Paket motor listrik bertegangan 48 V ke atas membutuhkan isolasi dan proteksi masukan yang lebih ketat.
- Adegan baterai terkuras dibuat dengan memutar kenop pada pembagi, bukan dengan menguras LiPo, karena LiPo rusak bila dikuras di bawah 3,0 V per sel. Hal ini disebutkan saat pitch. Kenop di ujung atas tetap membaca tegangan LiPo yang sebenarnya.
