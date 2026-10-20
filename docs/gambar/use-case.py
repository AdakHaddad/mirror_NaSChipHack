import cairo
import math
import os

W, H = 1640, 1180
S = 2

INK = (0x1F / 255, 0x29 / 255, 0x37 / 255)
MUTED = (0x6B / 255, 0x72 / 255, 0x80 / 255)
LINE = (0x4B / 255, 0x55 / 255, 0x63 / 255)

ORANGE = (0xC2 / 255, 0x41 / 255, 0x0C / 255)
ORANGE_DARK = (0x9A / 255, 0x34 / 255, 0x12 / 255)
ORANGE_FILL = (1.0, 0xF7 / 255, 0xED / 255)
ORANGE_CARD = (1.0, 0xED / 255, 0xD5 / 255)

BLUE = (0x1D / 255, 0x4E / 255, 0xD8 / 255)
BLUE_FILL = (0xEF / 255, 0xF6 / 255, 1.0)
BLUE_CARD = (0xDB / 255, 0xEA / 255, 0xFE / 255)

GREEN = (0x04 / 255, 0x78 / 255, 0x57 / 255)
GREEN_FILL = (0xEC / 255, 0xFD / 255, 0xF5 / 255)

RED = (0xDC / 255, 0x26 / 255, 0x26 / 255)
RED_DARK = (0x99 / 255, 0x1B / 255, 0x1B / 255)
RED_FILL = (0xFE / 255, 0xF2 / 255, 0xF2 / 255)

BOUNDARY_FILL = (1.0, 0xFB / 255, 0xF5 / 255)

surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, (0, 0, W, H))
ctx = cairo.Context(surface)
ctx.set_line_join(cairo.LINE_JOIN_ROUND)
ctx.set_line_cap(cairo.LINE_CAP_ROUND)


def font(size, bold=False, italic=False):
    slant = cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", slant, weight)
    ctx.set_font_size(size)


def text_width(s, size, bold=False, italic=False):
    font(size, bold, italic)
    return ctx.text_extents(s).width


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


def text_block(cx, cy, lines, size, color=INK, line_height=None, bold=False, italic=False):
    font(size, bold, italic)
    if line_height is None:
        line_height = size * 1.32
    n = len(lines)
    first = cy - (n - 1) * line_height / 2 + size * 0.34
    for i, s in enumerate(lines):
        text(cx, first + i * line_height, s, size, color, bold, italic, "center")


def rrect(x, y, w, h, r):
    ctx.new_path()
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def ellipse_path(cx, cy, rx, ry):
    ctx.new_path()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def usecase(cx, cy, rx, ry, lines, stroke, fill, text_color=INK, dashed=False, size=15.5):
    ellipse_path(cx, cy, rx, ry)
    ctx.set_source_rgb(*fill)
    ctx.fill_preserve()
    ctx.set_source_rgb(*stroke)
    ctx.set_line_width(1.8)
    if dashed:
        ctx.set_dash([5, 3])
    ctx.stroke()
    ctx.set_dash([])
    text_block(cx, cy, lines, size, text_color)


def actor(x, head_y, label_lines):
    ctx.new_path()
    r = 11.5
    ctx.set_source_rgb(1, 1, 1)
    ctx.arc(x, head_y, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgb(*LINE)
    ctx.set_line_width(1.8)
    ctx.arc(x, head_y, r, 0, 2 * math.pi)
    ctx.stroke()
    body_top = head_y + r
    body_bottom = head_y + 42
    ctx.move_to(x, body_top)
    ctx.line_to(x, body_bottom)
    ctx.move_to(x - 18, head_y + 21)
    ctx.line_to(x + 18, head_y + 21)
    ctx.move_to(x, body_bottom)
    ctx.line_to(x - 14, head_y + 62)
    ctx.move_to(x, body_bottom)
    ctx.line_to(x + 14, head_y + 62)
    ctx.stroke()
    text_block(x, head_y + 86, label_lines, 14.5, INK, 18)


def association(points, color=LINE, width=1.4):
    ctx.new_path()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(width)
    ctx.move_to(*points[0])
    if len(points) == 2:
        ctx.line_to(*points[1])
    else:
        for p in points[1:]:
            ctx.line_to(*p)
    ctx.stroke()


def open_arrow(x, y, angle, color=MUTED, size=8):
    ctx.new_path()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(1.3)
    for da in (-0.42, 0.42):
        ctx.move_to(x, y)
        ctx.line_to(x - size * math.cos(angle + da), y - size * math.sin(angle + da))
    ctx.stroke()


def filled_arrow(x, y, angle, color=RED, size=9):
    ctx.new_path()
    ctx.set_source_rgb(*color)
    ctx.move_to(x, y)
    ctx.line_to(x - size * math.cos(angle - 0.38), y - size * math.sin(angle - 0.38))
    ctx.line_to(x - size * math.cos(angle + 0.38), y - size * math.sin(angle + 0.38))
    ctx.close_path()
    ctx.fill()


def tag(cx, cy, s, color=MUTED, size=12, bg=BOUNDARY_FILL, bold=False):
    font(size, bold, italic=True)
    w = ctx.text_extents(s).width
    h = size * 1.25
    ctx.set_source_rgb(*bg)
    rrect(cx - w / 2 - 4, cy - h * 0.62, w + 8, h + 4, 3)
    ctx.fill()
    text(cx, cy + size * 0.34, s, size, color, bold, True, "center")


def include_line(start, end, label="«include»", color=MUTED, lx=None, ly=None):
    ctx.new_path()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(1.25)
    ctx.set_dash([5.5, 4])
    ctx.move_to(*start)
    ctx.line_to(*end)
    ctx.stroke()
    ctx.set_dash([])
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    open_arrow(end[0], end[1], angle, color)
    mx = (start[0] + end[0]) / 2 if lx is None else lx
    my = (start[1] + end[1]) / 2 if ly is None else ly
    tag(mx, my, label, color)


def note(cx, y, s, size=11.8, color=MUTED):
    text(cx, y, s, size, color, italic=True, align="center")


ctx.set_source_rgb(1, 1, 1)
ctx.paint()

text(70, 62, "Diagram Use Case — SeBatt", 31, INK, True)
text(70, 96, "Keaslian identitas dan integritas riwayat tegangan baterai kendaraan listrik", 16.5, MUTED)

ctx.set_source_rgba(0, 0, 0, 0.07)
rrect(368, 143, 880, 895, 12)
ctx.fill()
ctx.set_source_rgb(*BOUNDARY_FILL)
rrect(360, 135, 880, 895, 12)
ctx.fill_preserve()
ctx.set_source_rgb(*ORANGE)
ctx.set_line_width(2)
ctx.stroke()

text(388, 178, "Sistem SeBatt", 23, ORANGE_DARK, True)
text(389, 201, "chip SeBatt (FPGA) + emulator stasiun + basis data identitas", 13.5, MUTED)
ctx.set_source_rgba(0xC2 / 255, 0x41 / 255, 0x0C / 255, 0.25)
ctx.set_line_width(1)
ctx.move_to(378, 218)
ctx.line_to(1222, 218)
ctx.stroke()

actor(170, 250, ["Produsen baterai"])
actor(170, 610, ["Pemilik baterai"])
actor(1440, 350, ["Server identitas"])
actor(1440, 690, ["BMS kendaraan", "(jalur data)"])
actor(1440, 950, ["Penyerang", "BMS curang"])

association([(205, 268), (430, 270)])
association([(205, 626), (447, 674)])
association([(205, 626), (437, 842)])
association([(1405, 350), (1170, 270)])
association([(1405, 362), (1190, 464)])
association([(1405, 690), (1190, 680)])
association([(1405, 950), (975, 950)])

usecase(580, 270, 150, 44, ["Mendaftarkan baterai", "dan kunci"], GREEN, GREEN_FILL)
note(580, 337, "ID unik + kunci K dicatat di server")

usecase(580, 470, 145, 44, ["Mencatat riwayat", "tegangan"], ORANGE, ORANGE_FILL)
note(580, 536, "otomatis tiap 1 detik, tanpa perangkat lunak")

usecase(580, 680, 135, 42, ["Menukar baterai"], BLUE, BLUE_FILL)
usecase(580, 860, 150, 44, ["Menampilkan kesehatan", "baterai"], BLUE, BLUE_FILL)
note(570, 918, "dihitung dari riwayat terverifikasi")

usecase(1030, 270, 140, 42, ["Memverifikasi", "keaslian chip"], ORANGE, ORANGE_FILL)
note(1105, 326, "nonce baru tiap penukaran", 11.5)
note(1105, 343, "3× gagal → chip terkunci", 11.5)

usecase(1030, 470, 160, 44, ["Memeriksa integritas", "riwayat"], BLUE, BLUE_FILL)
note(1030, 536, "tag HMAC dan urutan seq diperiksa", 11.5)
note(1030, 553, "tidak cocok → DITOLAK", 11.5, RED_DARK)

usecase(1030, 680, 160, 44, ["Mengirim riwayat", "bertanda tangan"], ORANGE, ORANGE_FILL)

usecase(800, 950, 175, 45, ["Memalsukan atau", "menghapus riwayat"], RED, RED_FILL, RED_DARK, True)
note(800, 1012, "tanpa kunci K, tag tidak dapat dibuat ulang", 11.5)

include_line((690, 656), (926, 298), lx=808, ly=477)
include_line((714, 674), (885, 489), lx=802, ly=580)
include_line((715, 680), (870, 680), lx=793, ly=668)

threat_start = (911, 925)
threat_end = (928, 714)
ctx.set_source_rgb(*RED)
ctx.set_line_width(1.5)
ctx.set_dash([6, 4])
ctx.move_to(*threat_start)
ctx.line_to(*threat_end)
ctx.stroke()
ctx.set_dash([])
filled_arrow(threat_end[0], threat_end[1], math.atan2(threat_end[1] - threat_start[1], threat_end[0] - threat_start[0]))
tag(968, 822, "«mengancam»", RED, 11.5, BOUNDARY_FILL)

text(70, 1108, "Keterangan", 12.5, INK, True)
legend = [
    (220, ORANGE, ORANGE_CARD, "fungsi chip SeBatt"),
    (420, BLUE, BLUE_CARD, "stasiun dan server"),
    (605, GREEN, GREEN_FILL, "provisioning"),
    (750, RED, RED_FILL, "ancaman / misuse"),
]
for x, stroke, fill, label in legend:
    ctx.new_path()
    ctx.save()
    ctx.translate(x, 1102)
    ctx.scale(15, 9)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*fill)
    ctx.fill_preserve()
    ctx.set_source_rgb(*stroke)
    ctx.set_line_width(1.3)
    ctx.stroke()
    text(x + 22, 1107, label, 12.5, MUTED)

ctx.set_source_rgb(*MUTED)
ctx.set_line_width(1.25)
ctx.set_dash([5.5, 4])
ctx.move_to(220, 1140)
ctx.line_to(265, 1140)
ctx.stroke()
ctx.set_dash([])
open_arrow(265, 1140, 0, MUTED)
text(275, 1145, "«include» selalu dijalankan", 12.5, MUTED)

ctx.set_source_rgb(*RED)
ctx.set_line_width(1.5)
ctx.set_dash([6, 4])
ctx.move_to(550, 1140)
ctx.line_to(595, 1140)
ctx.stroke()
ctx.set_dash([])
filled_arrow(595, 1140, 0, RED)
text(605, 1145, "«mengancam» aksi penyerang di jalur data", 12.5, RED_DARK)

BASE = os.path.dirname(os.path.abspath(__file__))

png = cairo.ImageSurface(cairo.FORMAT_ARGB32, W * S, H * S)
pctx = cairo.Context(png)
pctx.scale(S, S)
pctx.set_source_surface(surface, 0, 0)
pctx.paint()
png.write_to_png(os.path.join(BASE, "use-case.png"))

pdf = cairo.PDFSurface(os.path.join(BASE, "use-case.pdf"), W, H)
pctx = cairo.Context(pdf)
pctx.set_source_surface(surface, 0, 0)
pctx.paint()
pdf.finish()
print("ok")
