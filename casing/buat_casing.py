"""Generator casing "Smart Battery Module" SeBatt (badan dan tutup) dalam format STL.

Casing ditempel ke baterai 12 V dengan strap/velcro 25 mm, berisi perfboard 3x4 cm
(pembagi tegangan dan MCP3202), potensiometer, saklar LIVE/DEMO, dan dua LED 10 mm.

Menjalankan (butuh manifold3d, trimesh, numpy; matplotlib untuk pratinjau):
    python buat_casing.py
Keluaran: sebatt_badan.stl, sebatt_tutup.stl, sebatt_plat_cetak.stl (keduanya
berdampingan untuk dicetak bersamaan), dan pratinjau.png di folder yang sama.
Satuan milimeter. Ukuran utama dapat diubah di bagian PARAMETER.
"""
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import Manifold, OpType

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- PARAMETER
L, W, H = 80.0, 52.0, 28.0       # ukuran luar badan (x, y, z)
R_SUDUT = 4.5                     # jari-jari sudut luar
DINDING = 2.4                     # tebal dinding
LANTAI = 2.0                      # tebal lantai
TUTUP = 2.4                       # tebal pelat tutup
BIBIR_T, BIBIR_H = 1.6, 4.0       # bibir tutup yang masuk ke badan
CELAH = 0.25                      # toleransi pas
BOS_D, BOS_LUBANG = 7.0, 2.6      # bos sekrup sudut (M3 self-tapping)
BAUT_LUBANG, BAUT_KEPALA = 3.4, 6.2
SEG = 64                          # kehalusan lingkaran

# Perfboard 3x4 cm (dipotong), posisi di sisi kanan (x besar)
PCB_X0, PCB_Y0, PCB_L, PCB_W = 32.0, 11.0, 40.0, 30.0
DUDUKAN_H, DUDUKAN_D, DUDUKAN_LUBANG, DUDUKAN_INSET = 3.5, 5.5, 2.5, 2.5

# Komponen di tutup (koordinat tampak atas, x sepanjang L, y sepanjang W)
POT = (14.0, 16.0, 7.5)           # (x, y, diameter lubang bushing M7)
SAKLAR = (17.0, 37.0, 6.2)        # saklar toggle mini
LED_HIJAU = (41.5, 12.0, 10.2)
LED_MERAH = (56.0, 12.0, 10.2)

# Flens strap di sisi panjang
FLENS_LEBAR, FLENS_T = 8.0, 3.0
STRAP_W, STRAP_T = 26.0, 3.5
STRAP_X = (20.0, 60.0)

UKIR = 0.7                        # kedalaman ukiran tutup
TIMBUL = 0.8                      # tinggi huruf timbul di dinding
JARAK_PLAT = 8.0                  # jarak badan dan tutup di plat cetak

# ------------------------------------------------------------ BENTUK DASAR


def kotak(x, y, z, sx, sy, sz):
    return Manifold.cube([sx, sy, sz]).translate([x, y, z])


def silinder(x, y, z, d, h, seg=SEG):
    return Manifold.cylinder(h, d / 2, d / 2, seg).translate([x, y, z])


def kotak_bulat(x, y, z, sx, sy, sz, r):
    """Kotak dengan sudut vertikal membulat."""
    r = max(0.01, min(r, sx / 2, sy / 2))
    tiang = [silinder(x + cx, y + cy, z, 2 * r, sz)
             for cx in (r, sx - r) for cy in (r, sy - r)]
    return Manifold.batch_hull(tiang)


def gabung(bagian):
    bagian = [b for b in bagian if b is not None]
    return Manifold.batch_boolean(bagian, OpType.Add) if bagian else Manifold()


# ------------------------------------------------------- FONT PIKSEL 5x7
FONT = {
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "V": ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "e": ["00000", "00000", "01110", "10001", "11111", "10000", "01110"],
    "a": ["00000", "00000", "01110", "00001", "01111", "10001", "01111"],
    "t": ["01000", "01000", "11100", "01000", "01000", "01001", "00110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    " ": ["00000"] * 7,
}


def lebar_teks(teks, px):
    return (len(teks) * 6 - 1) * px


def teks_datar(teks, px, tinggi, x0, y0, z0):
    """Teks piksel di bidang XY, baris atas di y besar. (x0, y0) = pojok kiri bawah."""
    bagian = []
    for i, ch in enumerate(teks):
        glyph = FONT[ch]
        gx = x0 + i * 6 * px
        for r, baris in enumerate(glyph):
            gy = y0 + (6 - r) * px
            c = 0
            while c < 5:
                if baris[c] == "1":
                    mulai = c
                    while c < 5 and baris[c] == "1":
                        c += 1
                    bagian.append(kotak(gx + mulai * px, gy, z0,
                                        (c - mulai) * px + 0.01, px + 0.01, tinggi))
                else:
                    c += 1
    return gabung(bagian)


# ------------------------------------------------------------------ BADAN


def buat_badan():
    luar = kotak_bulat(0, 0, 0, L, W, H, R_SUDUT)
    rongga = kotak_bulat(DINDING, DINDING, LANTAI, L - 2 * DINDING, W - 2 * DINDING,
                         H, R_SUDUT - DINDING)
    badan = luar - rongga

    # Flens strap di dua sisi panjang
    for sisi in (-1, 1):
        y = -FLENS_LEBAR if sisi < 0 else W
        flens = kotak_bulat(0, y, 0, L, FLENS_LEBAR, FLENS_T, 3.0)
        for sx in STRAP_X:
            slot = kotak(sx - STRAP_W / 2, y + (FLENS_LEBAR - STRAP_T) / 2, -1,
                         STRAP_W, STRAP_T, FLENS_T + 2)
            flens = flens - slot
        badan = badan + flens

    # Bos sekrup di empat sudut dalam
    c = DINDING + BOS_D / 2
    for bx in (c, L - c):
        for by in (c, W - c):
            bos = silinder(bx, by, 0, BOS_D, H)
            lubang = silinder(bx, by, H - 14, BOS_LUBANG, 15)
            badan = (badan + bos) - lubang

    # Dudukan perfboard
    for dx in (DUDUKAN_INSET, PCB_L - DUDUKAN_INSET):
        for dy in (DUDUKAN_INSET, PCB_W - DUDUKAN_INSET):
            x, y = PCB_X0 + dx, PCB_Y0 + dy
            badan = badan + silinder(x, y, LANTAI - 0.1, DUDUKAN_D, DUDUKAN_H + 0.1)
            badan = badan - silinder(x, y, LANTAI, DUDUKAN_LUBANG, DUDUKAN_H + 1)

    # Celah kabel Pmod di dinding x = L
    badan = badan - kotak(L - DINDING - 1, W / 2 - 12, 9, DINDING + 2, 24, 8)
    # Lubang kabel baterai di dinding x = 0
    kabel = Manifold.cylinder(DINDING + 2, 3.5, 3.5, SEG).rotate([0, 90, 0])
    badan = badan - kabel.translate([-1, W - 14, 9])

    # Label timbul di dinding ujung x = L: "PMOD" di atas celah
    t = teks_datar("PMOD", 1.0, TIMBUL, 0, 0, 0)
    t = t.rotate([90, 0, 0]).rotate([0, 0, 90])
    t = t.translate([L - 0.01, W / 2 - lebar_teks("PMOD", 1.0) / 2, 19])
    badan = badan + t

    # Label "12V" dan "+ -" di dinding ujung x = 0, dekat lubang kabel
    for isi, z, px in (("12V", 14.0, 0.8), ("+ -", 0.6, 0.6)):
        t = teks_datar(isi, px, TIMBUL, 0, 0, 0)
        t = t.rotate([90, 0, 0]).rotate([0, 0, -90])
        t = t.translate([0.01, W - 14 + lebar_teks(isi, px) / 2, z])
        badan = badan + t

    # Teks timbul "NaS . UGM" di sisi depan (y = 0)
    isi, px = "NaS . UGM", 1.1
    lebar = lebar_teks(isi, px)
    t = teks_datar(isi.replace("a", "a"), px, TIMBUL, 0, 0, 0).rotate([90, 0, 0])
    badan = badan + t.translate([L / 2 - lebar / 2, 0.01, 10])

    # Sirip dekoratif di sisi belakang (y = W), mirip sekat sel baterai
    for i in range(6):
        x = 11 + i * 11
        badan = badan + kotak_bulat(x, W - 0.01, 5, 3.0, TIMBUL, 16, 0.6)

    return badan


# ------------------------------------------------------------------ TUTUP


def buat_tutup():
    """Dimodelkan dengan muka atas di z = 0 menghadap ke bawah (posisi cetak),
    bibir menghadap ke atas. Koordinat x, y sama dengan tampak atas badan,
    tetapi dicerminkan pada sumbu y agar tampak benar setelah dibalik."""
    pelat = kotak_bulat(0, 0, 0, L, W, TUTUP, R_SUDUT)

    # Bibir, terputus di sudut untuk memberi ruang bos sekrup
    dalam_x0 = DINDING + CELAH
    dalam_y0 = DINDING + CELAH
    dalam_l = L - 2 * (DINDING + CELAH)
    dalam_w = W - 2 * (DINDING + CELAH)
    bibir_luar = kotak(dalam_x0, dalam_y0, TUTUP - 0.01, dalam_l, dalam_w, BIBIR_H)
    bibir_dalam = kotak(dalam_x0 + BIBIR_T, dalam_y0 + BIBIR_T, TUTUP - 1,
                        dalam_l - 2 * BIBIR_T, dalam_w - 2 * BIBIR_T, BIBIR_H + 2)
    bibir = bibir_luar - bibir_dalam
    pojok = BOS_D + 2.0
    for px in (DINDING, L - DINDING - pojok):
        for py in (DINDING, W - DINDING - pojok):
            bibir = bibir - kotak(px - 0.5, py - 0.5, 0, pojok + 0.5, pojok + 0.5, TUTUP + BIBIR_H + 1)
    tutup = pelat + bibir

    # Semua fitur tampak atas ditulis dengan koordinat (x, y) tampak atas,
    # lalu y dicerminkan: y_cetak = W - y.
    def cermin(y):
        return W - y

    # Lubang baut tembus + ceruk kepala baut di muka atas (z = 0)
    c = DINDING + BOS_D / 2
    for bx in (c, L - c):
        for by in (c, W - c):
            tutup = tutup - silinder(bx, cermin(by), -1, BAUT_LUBANG, TUTUP + 2)
            tutup = tutup - silinder(bx, cermin(by), -1, BAUT_KEPALA, 1.0 + 1)

    # Lubang komponen
    for (x, y, d) in (POT, SAKLAR, LED_HIJAU, LED_MERAH):
        tutup = tutup - silinder(x, cermin(y), -1, d, TUTUP + 2)

    ukiran = []

    # Bingkai ukir 3 mm dari tepi
    b_luar = kotak_bulat(3.0, 3.0, -1, L - 6, W - 6, UKIR + 1, R_SUDUT - 2)
    b_dalam = kotak_bulat(3.8, 3.8, -2, L - 7.6, W - 7.6, UKIR + 3, R_SUDUT - 2.8)
    ukiran.append(b_luar - b_dalam)

    # Cincin ukir di sekeliling LED dan kenop
    for (x, y, d) in (LED_HIJAU, LED_MERAH):
        cincin = silinder(x, cermin(y), -1, d + 4.0, UKIR + 1) - silinder(x, cermin(y), -2, d + 2.6, UKIR + 3)
        ukiran.append(cincin)
    skala = silinder(POT[0], cermin(POT[1]), -1, 19.0, UKIR + 1) - silinder(POT[0], cermin(POT[1]), -2, 17.6, UKIR + 3)
    ukiran.append(skala)

    def teks_atas(isi, px, x_kiri, y_bawah):
        """Teks tampak atas yang dicerminkan agar terbaca benar setelah tutup dibalik."""
        t = teks_datar(isi, px, UKIR + 1, 0, 0, -1)
        t = t.mirror([0, 1, 0])          # y -> -y
        tinggi = 7 * px
        return t.translate([x_kiri, cermin(y_bawah), 0])

    # Judul dan subjudul
    ukiran.append(teks_atas("SeBatt", 1.3, 30.0, 31.0))
    ukiran.append(teks_atas("SIGNED HISTORY", 0.55, 30.0, 23.5))

    # Label saklar
    ukiran.append(teks_atas("LIVE", 0.6, SAKLAR[0] - lebar_teks("LIVE", 0.6) / 2, SAKLAR[1] + 5.0))
    ukiran.append(teks_atas("DEMO", 0.6, SAKLAR[0] - lebar_teks("DEMO", 0.6) / 2, SAKLAR[1] - 9.5))

    # Ikon baterai dengan petir
    bx, by, bl, bw = 64.5, 8.0, 10.0, 7.0
    badan_ikon = kotak_bulat(bx, cermin(by + bw), -1, bl, bw, UKIR + 1, 1.5)
    dalam_ikon = kotak_bulat(bx + 0.9, cermin(by + bw) + 0.9, -2, bl - 1.8, bw - 1.8, UKIR + 3, 0.8)
    ukiran.append(badan_ikon - dalam_ikon)
    ukiran.append(kotak(bx + bl, cermin(by + bw / 2 + 1.5), -1, 1.4, 3.0, UKIR + 1))
    petir = [(bx + 5.6, by + 6.0), (bx + 3.4, by + 3.4), (bx + 5.0, by + 3.4),
             (bx + 4.25, by + 1.05), (bx + 6.6, by + 3.9), (bx + 5.0, by + 3.9)]
    petir_m = [(x, cermin(y)) for (x, y) in petir]
    luas = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(petir_m, petir_m[1:] + petir_m[:1]))
    if luas < 0:                      # pencerminan membalik arah polygon
        petir_m.reverse()
    from manifold3d import CrossSection
    ukiran.append(Manifold.extrude(CrossSection([petir_m]), UKIR + 1).translate([0, 0, -1]))

    tutup = tutup - gabung(ukiran)
    return tutup


# ------------------------------------------------------------------ EKSPOR


def ke_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=False)


def render(m, arah, piksel=0.12):
    """Render ortografis dengan z-buffer. arah = rotasi [rx, ry, rz] (derajat)
    sehingga mata melihat dari +z ke bawah."""
    tm = ke_trimesh(m.rotate(arah))
    v = tm.vertices
    mn, mx = v.min(0), v.max(0)
    w = int((mx[0] - mn[0]) / piksel) + 3
    h = int((mx[1] - mn[1]) / piksel) + 3
    zbuf = np.full((h, w), -np.inf)
    img = np.ones((h, w))
    n = tm.face_normals
    terang = np.clip(0.25 + 0.75 * (n @ (np.array([-0.35, 0.45, 0.82]) / 1.08)), 0.1, 1.0)
    px = (v[:, 0] - mn[0]) / piksel + 1
    py = (mx[1] - v[:, 1]) / piksel + 1
    for f, t in zip(tm.faces, terang):
        if n[f[0] if False else 0] is None:
            continue
        xs, ys, zs = px[f], py[f], v[f, 2]
        x0, x1 = int(np.floor(xs.min())), int(np.ceil(xs.max()))
        y0, y1 = int(np.floor(ys.min())), int(np.ceil(ys.max()))
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12:
            continue
        a = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        b = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        c = 1 - a - b
        dalam = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not dalam.any():
            continue
        z = a * zs[0] + b * zs[1] + c * zs[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        isub = img[y0:y1 + 1, x0:x1 + 1]
        ganti = dalam & (z > sub)
        sub[ganti] = z[ganti]
        isub[ganti] = t
    # Garis tepi dari lompatan kedalaman, agar ukiran dan huruf timbul terlihat
    zf = np.where(np.isfinite(zbuf), zbuf, np.nan)
    gy = np.abs(np.diff(zf, axis=0, prepend=zf[:1]))
    gx = np.abs(np.diff(zf, axis=1, prepend=zf[:, :1]))
    tepi = np.nan_to_num(np.maximum(gx, gy), nan=0.0) > 0.3
    img = np.where(tepi & np.isfinite(zbuf), img * 0.35, img)
    return img


def pratinjau(badan, tutup, berkas):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rakit = badan + tutup.rotate([180, 0, 0]).translate([0, 0, H + TUTUP])
    tampilan = [
        (tutup.rotate([180, 0, 0]), [0, 0, 0], "Tutup, tampak atas"),
        (badan, [-90, 0, 0], "Badan, sisi depan"),
        (badan, [90, 0, 180], "Badan, sisi belakang"),
        (rakit, [-55, 0, -30], "Rakitan"),
        (badan, [0, 0, 0], "Badan, tampak atas (isi)"),
        (badan, [0, -90, 0], "Badan, ujung kabel"),
    ]
    fig, axs = plt.subplots(2, 3, figsize=(16, 9))
    for ax, (m, arah, judul) in zip(axs.flat, tampilan):
        img = render(m, arah)
        warna = np.dstack([0.95 * img, 0.58 * img, 0.18 * img])
        warna[img == 1] = 1.0
        ax.imshow(warna)
        ax.set_title(judul)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(berkas, dpi=110)


def main():
    badan = buat_badan()
    tutup = buat_tutup()
    for m, nama in ((badan, "sebatt_badan.stl"), (tutup, "sebatt_tutup.stl")):
        jumlah_benda = len(m.decompose())
        assert jumlah_benda == 1, f"{nama} terpecah menjadi {jumlah_benda} benda"
        tm = ke_trimesh(m)
        tm.export(OUT / nama)
        print(f"{nama}: {len(tm.faces)} segitiga, watertight={tm.is_watertight}, "
              f"ukuran={np.round(tm.extents, 1)} mm, volume={tm.volume / 1000:.1f} cm3")
    # Plat cetak: badan dan tutup berdampingan, tutup dalam posisi cetak
    plat = badan + tutup.translate([0, W + FLENS_LEBAR + JARAK_PLAT, 0])
    tm = ke_trimesh(plat)
    tm.export(OUT / "sebatt_plat_cetak.stl")
    print(f"sebatt_plat_cetak.stl: {len(tm.faces)} segitiga, watertight={tm.is_watertight}, "
          f"ukuran plat={np.round(tm.extents[:2], 1)} mm")
    pratinjau(badan, tutup, OUT / "pratinjau.png")
    print("pratinjau.png")


if __name__ == "__main__":
    main()
