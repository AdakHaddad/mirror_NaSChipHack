"""Skematik rangkaian ADC SeBatt: LiPo 3S, pembagi dengan kenop, ADS1115, Pmod J2 KV260.

Jalankan dari root repo:
    python docs/gambar/rangkaian-adc.py
Hasil: docs/gambar/rangkaian-adc.png dan rangkaian-adc.svg
"""
from pathlib import Path

import schemdraw
import schemdraw.elements as elm

OUT = Path(__file__).with_suffix("")
RED = "#b02a22"
GREEN = "#1e6e45"
NAVY = "#1f3a5f"
GREY = "#555555"


def text(d, xy, s, size=10, color="black", halign="left", valign="center"):
    d.add(elm.Label().at(xy).label(s, fontsize=size, color=color,
                                   halign=halign, valign=valign))


def box(d, x0, y0, x1, y1, title, size=11):
    """Rectangle from top-left (x0, y0) to bottom-right (x1, y1), title above."""
    d.add(elm.Line().at((x0, y0)).to((x1, y0)))
    d.add(elm.Line().at((x1, y0)).to((x1, y1)))
    d.add(elm.Line().at((x1, y1)).to((x0, y1)))
    d.add(elm.Line().at((x0, y1)).to((x0, y0)))
    text(d, ((x0 + x1) / 2, y0 + 0.45), title, size=size, halign="center")


def pin(d, edge_x, y, side, name, lead=1.0):
    """Pin lead leaving the box at edge_x; returns the outer end."""
    out = edge_x - lead if side == "left" else edge_x + lead
    d.add(elm.Line().at((edge_x, y)).to((out, y)))
    inner = edge_x + 0.2 if side == "left" else edge_x - 0.2
    text(d, (inner, y), name, size=10, halign="left" if side == "left" else "right")
    return (out, y)


def draw():
    schemdraw.config(fontsize=10, lw=1.3)
    d = schemdraw.Drawing()

    # ---------------- J1: konektor balance LiPo 3S ----------------
    box(d, 0, 0, 3.2, -4, "J1  balance LiPo 3S")
    bp = pin(d, 3.2, -1.0, "right", "+12,6 V", lead=0.5)
    bn = pin(d, 3.2, -3.0, "right", "GND", lead=0.5)
    text(d, (1.6, -4.5), "JST-XH: pin paling luar\n(kabel (−) dan kabel sel ke-3)",
         size=8.5, color=GREY, halign="center", valign="top")
    d.add(elm.Line().at(bn).to((4.4, -3.0)))
    d.add(elm.Ground())

    # ---------------- Pembagi R1 - kenop - R2: satu rangkaian ----------------
    # Kenop di ujung atas: A0 = V_LiPo x 25/145 (tegangan asli, faktor 5,8).
    # Kenop diputar turun: pembacaan turun sampai 15/145, simulasi baterai terkuras.
    d.add(elm.Resistor().at(bp).to((7.5, -1.0))
          .label("R1 120 kΩ 1%", loc="top", fontsize=10))
    text(d, (5.6, -1.85), "solder menempel\ndi konektor J1", size=8.5,
         color=RED, halign="center", valign="top")
    pot = d.add(elm.Potentiometer().at((7.5, -1.0)).to((7.5, -4.6))
                .label("RV1 10 kΩ\nkenop linear", loc="top", fontsize=10))
    d.add(elm.Resistor().at((7.5, -4.6)).to((7.5, -7.6))
          .label("R2 15 kΩ 1%", loc="top", fontsize=10))
    d.add(elm.Ground())
    text(d, (7.9, -1.75), "atas: tegangan asli", size=8.5, color=NAVY)
    text(d, (7.9, -3.85), "bawah: simulasi terkuras", size=8.5, color=NAVY)

    # ---------------- Node A0: C1 ----------------
    d.add(elm.Wire("-|").at(pot.tap).to((12.0, -1.8)))
    d.add(elm.Line().at((12.0, -1.8)).to((13.2, -1.8)))
    d.add(elm.Dot().at((13.2, -1.8)))
    d.add(elm.Capacitor().at((13.2, -1.8)).to((13.2, -4.8))
          .label("C1\n100 nF", loc="bottom", fontsize=10))
    d.add(elm.Ground())
    text(d, (13.4, -1.4), "A0: 1,3–2,17 V", size=8.5, color=NAVY)
    d.add(elm.Line().at((13.2, -1.8)).to((15.0, -1.8)))

    # ---------------- U1: modul ADS1115 ----------------
    ax0, ax1 = 16.0, 20.0
    box(d, ax0, 0.2, ax1, -7.4, "U1  modul ADS1115 (0x48)")
    a0 = pin(d, ax0, -1.8, "left", "A0")
    a1 = pin(d, ax0, -3.0, "left", "A1")
    a2 = pin(d, ax0, -4.2, "left", "A2")
    a3 = pin(d, ax0, -5.4, "left", "A3")
    d.add(elm.Line().at(a1).to((15.0, -5.4)))
    d.add(elm.Dot().at(a2))
    d.add(elm.Line().at(a3).to((15.0, -6.0)))
    d.add(elm.Ground())

    vdd = pin(d, ax1, -0.6, "right", "VDD")
    gnd = pin(d, ax1, -1.8, "right", "GND")
    scl = pin(d, ax1, -3.0, "right", "SCL")
    sda = pin(d, ax1, -4.2, "right", "SDA")
    addr = pin(d, ax1, -5.4, "right", "ADDR")
    alrt = pin(d, ax1, -6.6, "right", "ALRT")
    d.add(elm.Line().at(vdd).to((22.0, -0.6)))
    d.add(elm.Vdd().label("3V3", fontsize=9))
    d.add(elm.Line().at(gnd).to((22.0, -1.8)))
    d.add(elm.Ground())
    d.add(elm.Line().at(addr).to((22.0, -5.4)))
    d.add(elm.Ground())
    text(d, (alrt[0] + 0.2, alrt[1]), "NC", size=9, color=GREY)

    # ---------------- J2: Pmod KV260 ----------------
    px0, px1 = 27.0, 35.0
    box(d, px0, -2.2, px1, -9.8, "J2  Pmod KV260 (nomor resmi pin)")
    p1 = pin(d, px0, -3.0, "left", "1  SCL  H12")
    p2 = pin(d, px0, -4.2, "left", "2  SDA  E10")
    p3 = pin(d, px0, -5.4, "left", "3  src_sel  D10")
    p4 = pin(d, px0, -6.6, "left", "4  led_hb  C11")
    p5 = pin(d, px0, -7.8, "left", "5  GND")
    p6 = pin(d, px0, -9.0, "left", "6  3V3")
    p7 = pin(d, px1, -3.0, "right", "uart_tx  B10  7")
    p8 = pin(d, px1, -4.2, "right", "uart_rx  E12  8")
    p9 = pin(d, px1, -5.4, "right", "hijau  D11  9")
    p10 = pin(d, px1, -6.6, "right", "merah  B11  10")
    p11 = pin(d, px1, -7.8, "right", "GND  11")
    p12 = pin(d, px1, -9.0, "right", "3V3  12")

    d.add(elm.Line().at(scl).to(p1))
    d.add(elm.Line().at(sda).to(p2))
    d.add(elm.Ground().at(p3))
    text(d, (p3[0] - 0.25, p3[1] + 0.35), "ke GND", size=8.5, color=RED, halign="right")
    d.add(elm.Ground().at(p5))
    text(d, (p6[0] - 0.15, p6[1]), "3V3", size=9, color=NAVY, halign="right")
    d.add(elm.Ground().at(p11))
    text(d, (p12[0] + 0.2, p12[1]), "NC", size=9, color=GREY)

    # LED heartbeat dari pin 4
    d.add(elm.Line().at(p4).to((24.5, -6.6)))
    d.add(elm.Line().to((24.5, -10.5)))
    d.add(elm.Resistor().down().label("330 Ω", loc="bottom", fontsize=9))
    d.add(elm.LED().down().label("LED HB", loc="bottom", fontsize=9))
    d.add(elm.Ground())

    # LED merah (pin 10) lebih dekat, LED hijau (pin 9) lebih jauh agar tidak bersilangan
    d.add(elm.Resistor().at(p10).to((39.0, -6.6)).label("330 Ω", fontsize=9))
    d.add(elm.LED().down().color(RED).label("LED merah", loc="bottom", fontsize=9))
    d.add(elm.Ground())
    d.add(elm.Line().at(p9).to((39.5, -5.4)))
    d.add(elm.Resistor().right().label("330 Ω", fontsize=9))
    d.add(elm.LED().down().color(GREEN).label("LED hijau", loc="bottom", fontsize=9))
    d.add(elm.Ground())

    # ---------------- U2: CP2102 ----------------
    cx0, cx1 = 45.0, 49.0
    box(d, cx0, -2.2, cx1, -7.4, "U2  CP2102 → USB laptop")
    rxd = pin(d, cx0, -3.0, "left", "RXD")
    txd = pin(d, cx0, -4.2, "left", "TXD")
    cg = pin(d, cx0, -5.4, "left", "GND")
    c5 = pin(d, cx0, -6.6, "left", "5V")
    d.add(elm.Line().at(p7).to(rxd).color(NAVY))
    d.add(elm.Line().at(p8).to(txd).color(NAVY))
    d.add(elm.Ground().at(cg))
    text(d, (c5[0] - 0.2, c5[1]), "NC", size=9, color=GREY, halign="right")

    # ---------------- Catatan ----------------
    notes = [
        "Catatan",
        "1. Semua GND disatukan: (−) LiPo, ADS1115, Pmod 5/11, CP2102. Kutub (+) LiPo hanya lewat R1.",
        "2. LiPo hanya diukur. KV260 tetap memakai adaptor 12 V sendiri. Cabut J1 setelah demo (pembagi menarik ±0,09 mA).",
        "3. Kenop di posisi atas: tegangan baterai = mV di A0 × 5,8 (kalibrasi dengan multimeter).  12,6 V → 2,17 V,  11,1 V → 1,91 V,  9,0 V → 1,55 V.",
        "   Kenop diputar turun mensimulasikan baterai terkuras (LiPo 12,4 V terbaca 12,4 → 7,4 V). A0 tidak pernah melebihi 2,17 V di posisi mana pun.",
        "4. Pmod 3 (src_sel) wajib ke GND agar FPGA membaca ADS1115. Ke 3V3 = sumber tetap 3000 mV. Jangan dibiarkan terbuka.",
        "5. Modul ADS1115 diberi 3,3 V, bukan 5 V, karena pull-up SCL/SDA di modul mengikuti VDD.",
    ]
    for i, line in enumerate(notes):
        text(d, (0, -16.0 - 0.75 * i), line, size=11 if i == 0 else 10,
             color="black" if i == 0 else GREY)

    d.save(str(OUT) + ".svg")
    d.save(str(OUT) + ".png", dpi=150)


if __name__ == "__main__":
    draw()
    print("ok", OUT)
