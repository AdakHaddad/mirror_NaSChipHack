"""Diagram infrastruktur cloud untuk basis data stasiun SeBatt.

Jalankan dari root repo:
    python docs/gambar/cloud-infra.py
Hasil: docs/gambar/cloud-infra.png dan cloud-infra.pdf
"""
import math
import os

import cairo

W, H = 1640, 922
S = 2

INK = (0x1F / 255, 0x29 / 255, 0x37 / 255)
MUTED = (0x6B / 255, 0x72 / 255, 0x80 / 255)
LINE = (0x4B / 255, 0x55 / 255, 0x63 / 255)
PAPER = (1.0, 1.0, 1.0)

ORANGE = (0xC2 / 255, 0x41 / 255, 0x0C / 255)
ORANGE_DARK = (0x9A / 255, 0x34 / 255, 0x12 / 255)
ORANGE_FILL = (1.0, 0xF7 / 255, 0xED / 255)

BLUE = (0x1D / 255, 0x4E / 255, 0xD8 / 255)
BLUE_FILL = (0xEF / 255, 0xF6 / 255, 1.0)
CLOUD_FILL = (0xF5 / 255, 0xF9 / 255, 1.0)

GREEN = (0x04 / 255, 0x78 / 255, 0x57 / 255)
GREEN_FILL = (0xEC / 255, 0xFD / 255, 0xF5 / 255)

CARD_FILL = (0xF9 / 255, 0xFA / 255, 0xFB / 255)

surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, (0, 0, W, H))
ctx = cairo.Context(surface)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
ctx.set_line_cap(cairo.LINE_CAP_ROUND)


def font(size, bold=False, italic=False):
    slant = cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", slant, weight)
    ctx.set_font_size(size)


def text(x, y, s, size, color=INK, bold=False, italic=False, align="left"):
    font(size, bold, italic)
    ctx.set_source_rgb(*color)
    w = ctx.text_extents(s).width
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    ctx.move_to(x, y)
    ctx.show_text(s)


def rrect(x, y, w, h, r):
    ctx.new_path()
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def box(x, y, w, h, title, subs, stroke, fill, title_size=17, sub_size=13):
    rrect(x, y, w, h, 10)
    ctx.set_source_rgb(*fill)
    ctx.fill_preserve()
    ctx.set_source_rgb(*stroke)
    ctx.set_line_width(1.6)
    ctx.stroke()

    font(title_size, True)
    tw = ctx.text_extents(title).width
    text(x + w / 2, y + 34, title, title_size, INK, True, align="center")
    top = y + 34 + max(22, title_size * 1.35)
    for i, s in enumerate(subs):
        text(x + w / 2, top + i * 20, s, sub_size, MUTED, align="center")


def arrow(x1, y1, x2, y2, color=LINE, width=1.8, dashed=False):
    ctx.new_path()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(width)
    if dashed:
        ctx.set_dash([6, 4])
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()
    ctx.set_dash([])
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 9
    ctx.new_path()
    ctx.set_source_rgb(*color)
    ctx.move_to(x2, y2)
    ctx.line_to(x2 - size * math.cos(angle - 0.38), y2 - size * math.sin(angle - 0.38))
    ctx.line_to(x2 - size * math.cos(angle + 0.38), y2 - size * math.sin(angle + 0.38))
    ctx.close_path()
    ctx.fill()


def tag(cx, cy, s, color=MUTED, size=12):
    font(size, True)
    w = ctx.text_extents(s).width
    h = size * 1.3
    ctx.set_source_rgb(*PAPER)
    rrect(cx - w / 2 - 5, cy - h * 0.62, w + 10, h + 4, 3)
    ctx.fill()
    text(cx, cy + size * 0.34, s, size, color, True, align="center")


def card(x, y, w, h, label, big, subs):
    rrect(x, y, w, h, 12)
    ctx.set_source_rgb(*CARD_FILL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*LINE)
    ctx.set_line_width(1.2)
    ctx.stroke()
    text(x + 24, y + 38, label, 13.5, MUTED, True)
    text(x + 24, y + 88, big, 31, INK, True)
    for i, s in enumerate(subs):
        text(x + 24, y + 118 + i * 21, s, 13.5, MUTED)


ctx.set_source_rgb(*PAPER)
ctx.paint()

text(60, 62, "Infrastruktur Cloud & Basis Data Stasiun", 31, INK, True)
text(60, 96, "Verifikasi HMAC dijalankan ulang di server operator; kunci tidak pernah disimpan di kios.",
     16.5, MUTED)

box(60, 250, 190, 140, "Paket baterai", ["chip SeBatt (FPGA)", "nonce → tag HMAC"],
    ORANGE, ORANGE_FILL, 17, 13)
box(300, 250, 210, 140, "Kios / stasiun", ["thin client", "tidak menyimpan K"],
    BLUE, BLUE_FILL, 17, 13)

ctx.set_source_rgb(*BLUE)
rrect(560, 150, 1020, 400, 16)
ctx.set_line_width(2)
ctx.set_dash([9, 6])
ctx.stroke_preserve()
ctx.set_source_rgb(*CLOUD_FILL)
ctx.fill()
ctx.set_dash([])

text(584, 186, "Operator cloud (VPC)", 21, BLUE, True)
text(584, 210, "satu transaksi per penukaran", 13.5, MUTED)

box(595, 285, 160, 100, "API gateway", ["HTTPS / TLS", "autentikasi kios"],
    BLUE, PAPER, 16, 12.5)
box(810, 255, 270, 160, "Layanan auth", ["hitung ulang HMAC-SHA-256",
                                         "cek nonce + seq ≥ jangkar",
                                         "putuskan VALID / INVALID"],
    ORANGE, PAPER, 17, 13)
box(1140, 210, 230, 145, "Basis data", ["PostgreSQL terkelola",
                                        "battery_id, seq_anchor",
                                        "status, ringkasan, audit",
                                        "replika + backup"],
    BLUE, PAPER, 17, 13)
box(1140, 390, 230, 110, "KMS / HSM", ["kunci terbungkus", "operasi HMAC"],
    GREEN, PAPER, 17, 13)

arrow(250, 320, 300, 320)
tag(275, 300, "UART", MUTED, 12)

arrow(510, 320, 595, 320)
tag(552, 300, "HTTPS / TLS", MUTED, 12)

arrow(755, 335, 810, 335)
arrow(1080, 305, 1140, 282)
tag(1110, 274, "SQL", MUTED, 11.5)
arrow(1080, 368, 1140, 430)
tag(1105, 386, "HMAC / K", GREEN, 12)

text(1070, 592, "Tanda tangan tetap dibuat di silikon; cloud hanya menghitung ulang dan menyimpan jangkar.",
     14.5, MUTED, italic=True, align="center")

card(60, 640, 470, 150, "BASIS DATA INTI", "4 MB",
     ["100.000 baterai × 40 byte", "ID, K, seq, status (tanpa tanda tangan)"])
card(575, 640, 470, 150, "RIWAYAT", "±15 GB/tahun",
     ["riwayat lengkap 400 B/penukaran", "ringkasan peristiwa jauh lebih kecil"])
card(1090, 640, 470, 150, "BIAYA INFRASTRUKTUR", "Rp 10–30 jt/tahun",
     ["cloud + KMS/HSM (asumsi)", "100 ribuan baterai; lihat pitch-dan-angka.md"])

text(820, 852, "Tahap 1 (HMAC): kios wajib online setiap penukaran. Tahap 2 (ECDSA): verifikasi cukup public key,",
     14, MUTED, align="center")
text(820, 874, "kios boleh offline; cloud menyimpan status dan revokasi.",
     14, MUTED, align="center")

BASE = os.path.dirname(os.path.abspath(__file__))

png = cairo.ImageSurface(cairo.FORMAT_ARGB32, W * S, H * S)
pctx = cairo.Context(png)
pctx.scale(S, S)
pctx.set_source_surface(surface, 0, 0)
pctx.paint()
png.write_to_png(os.path.join(BASE, "cloud-infra.png"))

pdf = cairo.PDFSurface(os.path.join(BASE, "cloud-infra.pdf"), W, H)
pctx = cairo.Context(pdf)
pctx.set_source_surface(surface, 0, 0)
pctx.paint()
pdf.finish()
print("ok")
