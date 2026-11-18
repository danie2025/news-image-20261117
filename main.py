#!/usr/bin/env python3
"""Draws a one-image summary of the world's news of Tuesday 17 November 2026.

Standard library only; fully deterministic (no randomness, no clock).
"""
import math
import os
import struct
import zlib

W = H = 1024
buf = bytearray(W * H * 3)

# ---------------------------------------------------------------- font 5x7
_G = """
A 01110,10001,10001,11111,10001,10001,10001
B 11110,10001,10001,11110,10001,10001,11110
C 01110,10001,10000,10000,10000,10001,01110
D 11110,10001,10001,10001,10001,10001,11110
E 11111,10000,10000,11110,10000,10000,11111
F 11111,10000,10000,11110,10000,10000,10000
G 01110,10001,10000,10111,10001,10001,01111
H 10001,10001,10001,11111,10001,10001,10001
I 01110,00100,00100,00100,00100,00100,01110
J 00111,00010,00010,00010,00010,10010,01100
K 10001,10010,10100,11000,10100,10010,10001
L 10000,10000,10000,10000,10000,10000,11111
M 10001,11011,10101,10101,10001,10001,10001
N 10001,11001,10101,10011,10001,10001,10001
O 01110,10001,10001,10001,10001,10001,01110
P 11110,10001,10001,11110,10000,10000,10000
Q 01110,10001,10001,10001,10101,10010,01101
R 11110,10001,10001,11110,10100,10010,10001
S 01111,10000,10000,01110,00001,00001,11110
T 11111,00100,00100,00100,00100,00100,00100
U 10001,10001,10001,10001,10001,10001,01110
V 10001,10001,10001,10001,10001,01010,00100
W 10001,10001,10001,10101,10101,11011,10001
X 10001,10001,01010,00100,01010,10001,10001
Y 10001,10001,01010,00100,00100,00100,00100
Z 11111,00001,00010,00100,01000,10000,11111
0 01110,10001,10011,10101,11001,10001,01110
1 00100,01100,00100,00100,00100,00100,01110
2 01110,10001,00001,00010,00100,01000,11111
3 11110,00001,00001,01110,00001,00001,11110
4 00010,00110,01010,10010,11111,00010,00010
5 11111,10000,11110,00001,00001,10001,01110
6 00110,01000,10000,11110,10001,10001,01110
7 11111,00001,00010,00100,01000,01000,01000
8 01110,10001,10001,01110,10001,10001,01110
9 01110,10001,10001,01111,00001,00010,01100
- 00000,00000,00000,11111,00000,00000,00000
, 00000,00000,00000,00000,00110,00100,01000
: 00000,00110,00110,00000,00110,00110,00000
. 00000,00000,00000,00000,00000,00110,00110
; 00000,00110,00110,00000,00110,00100,01000
& 01100,10010,10100,01000,10101,10010,01101
"""
FONT = {}
for _l in _G.strip().splitlines():
    _k, _rows = _l.split(" ", 1)
    FONT[_k] = _rows.split(",")


# ------------------------------------------------------------- primitives
def rect(x0, y0, x1, y1, c):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for y in range(y0, y1):
        buf[(y * W + x0) * 3:(y * W + x1) * 3] = row


def circle(cx, cy, r, c):
    for y in range(cy - r, cy + r + 1):
        dx = int(math.sqrt(max(0, r * r - (y - cy) ** 2)))
        rect(cx - dx, y, cx + dx + 1, y + 1, c)


def poly(pts, c):
    ys = [p[1] for p in pts]
    n = len(pts)
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, c)


def line(x0, y0, x1, y1, w, c):
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy) or 1
    nx, ny = -dy / d * w / 2, dx / d * w / 2
    poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
          (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)


def burst(cx, cy, r1, r2, n, c, rot=0.0):
    pts = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2
        a = rot + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    poly(pts, c)


def textw(s, sc):
    return len(s) * 6 * sc - sc


def text(s, x, y, sc, c):
    for ch in s:
        g = FONT.get(ch)
        if g:
            for r, bits in enumerate(g):
                for k, b in enumerate(bits):
                    if b == "1":
                        rect(x + k * sc, y + r * sc, x + (k + 1) * sc,
                             y + (r + 1) * sc, c)
        x += 6 * sc


def ctext(s, cx, y, sc, c):
    text(s, cx - textw(s, sc) // 2, y, sc, c)


# ----------------------------------------------------------------- colours
WHITE = (255, 255, 255)
RED = (205, 32, 44)
BLUE = (30, 70, 160)
YEL = (255, 205, 40)
ORG = (255, 120, 20)
GRAY = (130, 138, 150)
DGRAY = (70, 76, 90)
NAVY = (12, 18, 38)
PANEL = (26, 34, 56)
GREEN = (50, 190, 110)
WATER = (40, 90, 150)


# ------------------------------------------------------------------- flags
def flag_us(x, y, w, h):
    sh = h / 7.0
    for i in range(7):
        rect(x, int(y + i * sh), x + w, int(y + (i + 1) * sh),
             RED if i % 2 == 0 else WHITE)
    cw, ch = int(w * 0.45), int(sh * 4)
    rect(x, y, x + cw, y + ch, BLUE)
    for i in range(3):
        for j in range(3):
            circle(x + 10 + i * (cw - 20) // 2, y + 9 + j * (ch - 18) // 2, 2, WHITE)


def flag_cn(x, y, w, h):
    rect(x, y, x + w, y + h, RED)
    burst(x + w // 5, y + h // 4, h // 6, h // 14, 5, YEL, -math.pi / 2)
    for sx, sy in ((0.38, 0.12), (0.46, 0.26), (0.46, 0.44), (0.38, 0.58)):
        circle(int(x + w * sx), int(y + h * sy), 3, YEL)


def flag_ru(x, y, w, h):
    t = h // 3
    rect(x, y, x + w, y + t, WHITE)
    rect(x, y + t, x + w, y + 2 * t, (0, 57, 166))
    rect(x, y + 2 * t, x + w, y + h, (213, 43, 30))


def flag_ca(x, y, w, h):
    rect(x, y, x + w, y + h, WHITE)
    rect(x, y, x + w // 4, y + h, RED)
    rect(x + 3 * w // 4, y, x + w, y + h, RED)
    cx, cy = x + w // 2, y + h // 2
    poly([(cx, cy - h // 3), (cx + h // 4, cy), (cx, cy + h // 3),
          (cx - h // 4, cy)], RED)


def flag_mn(x, y, w, h):
    t = w // 3
    rect(x, y, x + t, y + h, RED)
    rect(x + t, y, x + 2 * t, y + h, (0, 110, 190))
    rect(x + 2 * t, y, x + w, y + h, RED)
    circle(x + t // 2, y + h // 3, 7, YEL)
    rect(x + t // 2 - 4, y + h // 3 + 10, x + t // 2 + 5, y + h - 10, YEL)


def pole(x, y, h):
    rect(x - 4, y, x, y + h, GRAY)


# ------------------------------------------------------------------ layout
rect(0, 0, W, H, NAVY)
ctext("WORLD NEWS", 512, 10, 9, WHITE)
ctext("TUESDAY 17 NOVEMBER 2026", 512, 82, 6, YEL)
rect(0, 130, W, 134, RED)

PANELS = [
    ("TRUMP HEADS TO", "XI-PUTIN SUMMIT", "IN CHINA"),
    ("IRAN FIRES AT", "BAHRAIN; US", "STRIKES BACK"),
    ("KERCH & KYIV", "BRIDGES STRUCK", "IN UKRAINE WAR"),
    ("GAZA: 5 KILLED,", "AID CALLS AS", "WINTER NEARS"),
    ("CANADA-CHINA", "AGREE TARIFF", "RELIEF"),
    ("MONGOLIAN", "PRESIDENT SAYS", "HE WILL QUIT"),
]
ACCENT = [RED, ORG, YEL, GRAY, GREEN, (0, 150, 220)]

for idx, lines in enumerate(PANELS):
    col, row = idx % 2, idx // 2
    px = 10 + col * 507
    ty = 140 + row * 250
    pw, ph = 497, 244
    rect(px, ty, px + pw, ty + ph, PANEL)
    rect(px, ty, px + 8, ty + ph, ACCENT[idx])
    cx = px + 8 + (pw - 8) // 2
    iy = ty + 10
    if idx == 0:
        for k, fn in enumerate((flag_us, flag_cn, flag_ru)):
            fx = cx - 190 + k * 135
            pole(fx, iy + 4, 100)
            fn(fx, iy + 8, 110, 72)
    elif idx == 1:
        for dy in (28, 74):
            x = cx - 120
            poly([(x, iy + dy), (x - 70, iy + dy - 20), (x - 55, iy + dy),
                  (x - 70, iy + dy + 20)], DGRAY)
            poly([(x - 2, iy + dy), (x - 62, iy + dy - 14), (x - 50, iy + dy),
                  (x - 62, iy + dy + 14)], (190, 60, 60))
            for t in range(3):
                rect(x - 150 + t * 28, iy + dy - 2, x - 128 + t * 28, iy + dy + 2, GRAY)
        burst(cx + 105, iy + 52, 62, 30, 10, ORG)
        burst(cx + 105, iy + 52, 38, 18, 8, YEL, 0.3)
    elif idx == 2:
        rect(cx - 200, iy + 66, cx + 200, iy + 78, GRAY)
        rect(cx - 200, iy + 86, cx + 200, iy + 108, WATER)
        for tx in (cx - 115, cx + 115):
            rect(tx - 7, iy + 8, tx + 7, iy + 78, GRAY)
            line(tx, iy + 10, tx - 85, iy + 66, 4, GRAY)
            line(tx, iy + 10, tx + 85, iy + 66, 4, GRAY)
        burst(cx + 10, iy + 56, 52, 24, 9, ORG)
        burst(cx + 10, iy + 56, 30, 14, 7, YEL, 0.2)
    elif idx == 3:
        rect(cx - 200, iy + 98, cx + 200, iy + 108, DGRAY)
        for bx, bw, bh in ((cx - 170, 80, 70), (cx - 60, 80, 52), (cx + 50, 90, 84)):
            top = iy + 98 - bh
            poly([(bx, iy + 98), (bx, top + 14), (bx + bw * 0.3, top),
                  (bx + bw * 0.5, top + 18), (bx + bw * 0.75, top + 4),
                  (bx + bw, top + 22), (bx + bw, iy + 98)], GRAY)
            rect(bx + 14, top + 34, bx + 28, top + 48, PANEL)
            rect(bx + bw - 30, top + 34, bx + bw - 16, top + 48, PANEL)
        for sx, sy, sr in ((cx + 90, iy + 6, 16), (cx + 112, iy - 2, 13),
                           (cx - 30, iy + 22, 14), (cx - 20, iy + 8, 11)):
            circle(sx, sy + 8, sr, (95, 100, 112))
    elif idx == 4:
        flag_ca(cx - 205, iy + 18, 110, 72)
        flag_cn(cx + 95, iy + 18, 110, 72)
        poly([(cx - 15, iy + 8), (cx + 15, iy + 8), (cx + 15, iy + 48),
              (cx + 38, iy + 48), (cx, iy + 100), (cx - 38, iy + 48),
              (cx - 15, iy + 48)], GREEN)
    else:
        flag_mn(cx - 190, iy + 16, 120, 80)
        circle(cx + 40, iy + 28, 24, WHITE)
        poly([(cx - 20, iy + 100), (cx - 10, iy + 62), (cx + 90, iy + 62),
              (cx + 100, iy + 100)], WHITE)
        poly([(cx + 130, iy + 40), (cx + 165, iy + 40), (cx + 165, iy + 24),
              (cx + 200, iy + 56), (cx + 165, iy + 88), (cx + 165, iy + 72),
              (cx + 130, iy + 72)], YEL)
    for li, s in enumerate(lines):
        text(s, px + 24, ty + 118 + li * 41, 5, WHITE if li else YEL)

rect(10, 892, W - 10, H - 10, PANEL)
rect(10, 892, W - 10, 898, GRAY)
ctext("ALSO: TURKEY SEIZES SOZCU TV CHANNEL", 512, 912, 4, WHITE)
ctext("5 EU STATES PLAN RWANDA RETURN HUB", 512, 958, 4, WHITE)


# --------------------------------------------------------------- PNG output
def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3]) for y in range(H))
png = (b"\x89PNG\r\n\x1a\n" +
       chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) +
       chunk(b"IDAT", zlib.compress(raw, 9)) +
       chunk(b"IEND", b""))

out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "entry.png"), "wb") as f:
    f.write(png)
