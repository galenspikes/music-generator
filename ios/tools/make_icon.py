"""Generate the app icon (1024x1024 PNG): a modular synthesizer.

Draws a Eurorack-style modular synth — wooden case, module panels, knobs,
jacks and patch cables — with no third-party imaging deps (numpy + zlib only).

Briefcase reads ``resources/musicgen.png`` (configured via ``icon`` in
pyproject.toml) and generates the platform icon set from it. Re-run to tweak:

    python tools/make_icon.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

import numpy as np

SIZE = 1024
OUT = (Path(__file__).resolve().parent.parent
       / "src" / "musicgen" / "resources" / "musicgen.png")


def hexc(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _blend(img, x0, y0, x1, y1, alpha, color):
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(SIZE, x1); y1 = min(SIZE, y1)
    if x1 <= x0 or y1 <= y0:
        return
    region = img[y0:y1, x0:x1]
    a = alpha[..., None]
    for c in range(3):
        region[..., c] = region[..., c] * (1 - alpha) + color[c] * alpha


def rrect(img, x0, y0, x1, y1, r, color, soft=1.4):
    """Rounded-rectangle fill with soft edges."""
    gx = np.arange(x0, x1)[None, :] + 0.5
    gy = np.arange(y0, y1)[:, None] + 0.5
    # distance outside the inner (corner-centre) rectangle
    dx = np.maximum(np.maximum((x0 + r) - gx, gx - (x1 - r)), 0)
    dy = np.maximum(np.maximum((y0 + r) - gy, gy - (y1 - r)), 0)
    dist = np.sqrt(dx * dx + dy * dy)
    alpha = np.clip((r - dist) / soft, 0, 1)
    _blend(img, x0, y0, x1, y1, alpha, color)


def disc(img, cx, cy, r, color, soft=1.3):
    x0 = int(cx - r - 2); x1 = int(cx + r + 2)
    y0 = int(cy - r - 2); y1 = int(cy + r + 2)
    gx = np.arange(x0, x1)[None, :] + 0.5
    gy = np.arange(y0, y1)[:, None] + 0.5
    dist = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
    alpha = np.clip((r - dist) / soft, 0, 1)
    _blend(img, x0, y0, x1, y1, alpha, color)


def ring(img, cx, cy, r_out, width, color, soft=1.3):
    r_in = r_out - width
    x0 = int(cx - r_out - 2); x1 = int(cx + r_out + 2)
    y0 = int(cy - r_out - 2); y1 = int(cy + r_out + 2)
    gx = np.arange(x0, x1)[None, :] + 0.5
    gy = np.arange(y0, y1)[:, None] + 0.5
    dist = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
    alpha = (np.clip((r_out - dist) / soft, 0, 1)
             * np.clip((dist - r_in) / soft, 0, 1))
    _blend(img, x0, y0, x1, y1, alpha, color)


def knob(img, cx, cy, r, angle_deg):
    disc(img, cx, cy, r + 3, hexc("#0d0e11"))          # shadow ring
    disc(img, cx, cy, r, hexc("#3a3f47"))              # body
    ring(img, cx, cy, r, 3, hexc("#11131a"))           # rim
    disc(img, cx, cy, r * 0.32, hexc("#1c1f25"))       # cap
    a = math.radians(angle_deg)
    ix, iy = cx + math.cos(a) * r * 0.78, cy + math.sin(a) * r * 0.78
    # indicator line as a short string of discs
    for t in np.linspace(0.25, 1.0, 14):
        disc(img, cx + math.cos(a) * r * 0.78 * t,
             cy + math.sin(a) * r * 0.78 * t, max(2.0, r * 0.07),
             hexc("#f4f6fa"))


def jack(img, cx, cy, r=15):
    disc(img, cx, cy, r + 4, hexc("#15171c"))          # bezel shadow
    ring(img, cx, cy, r + 2, 4, hexc("#aeb6c2"))       # metal nut
    disc(img, cx, cy, r, hexc("#0c0d10"))              # hole
    disc(img, cx, cy, r * 0.45, hexc("#1b1e25"))


def cable(img, p0, p1, color, sag=170, r=13):
    x0, y0 = p0
    x3, y3 = p1
    mx, my = (x0 + x3) / 2, max(y0, y3) + sag       # control point below = gravity
    pts = []
    for t in np.linspace(0, 1, 160):
        bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x3
        by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y3
        pts.append((bx, by))
    for bx, by in pts:                               # dark underside
        disc(img, bx, by, r + 2, hexc("#101216"))
    for bx, by in pts:                               # colored sheath
        disc(img, bx, by, r, color)
    for bx, by in pts:                               # glossy highlight
        disc(img, bx - r * 0.3, by - r * 0.3, r * 0.35,
             tuple(min(255, int(c + 70)) for c in color))
    # plugs at each end
    for (px, py) in (p0, p1):
        disc(img, px, py, r + 6, color)
        disc(img, px, py, r * 0.5, hexc("#16181d"))


def render() -> np.ndarray:
    img = np.zeros((SIZE, SIZE, 3), dtype=np.float64)
    # background gradient
    top, bot = hexc("#14161c"), hexc("#23262f")
    for y in range(SIZE):
        t = y / (SIZE - 1)
        img[y, :, :] = [top[c] + (bot[c] - top[c]) * t for c in range(3)]

    # wooden case
    rrect(img, 96, 150, 928, 874, 44, hexc("#6e431f"))
    rrect(img, 120, 150, 904, 874, 30, hexc("#8a5a2c"))
    # metal rails (top & bottom)
    rrect(img, 150, 176, 874, 214, 8, hexc("#1d2027"))
    rrect(img, 150, 810, 874, 848, 8, hexc("#1d2027"))

    # module panels
    panels = [hexc("#c9ced6"), hexc("#21242b"), hexc("#2f7d77"),
              hexc("#d8c79c"), hexc("#3b4250")]
    knob_on = {0: hexc("#11131a"), 2: hexc("#0e201f"), 4: hexc("#11131a")}
    px0, px1 = 168, 856
    gap = 16
    n = len(panels)
    pw = (px1 - px0 - gap * (n - 1)) // n
    py0, py1 = 222, 802
    jacks_per_panel = []
    for i, col in enumerate(panels):
        x0 = px0 + i * (pw + gap)
        x1 = x0 + pw
        rrect(img, x0, py0, x1, py1, 6, col)
        cx = (x0 + x1) // 2
        # rack screws
        for sx in (x0 + 14, x1 - 14):
            for sy in (py0 + 14, py1 - 14):
                disc(img, sx, sy, 6, hexc("#3a3d44"))
        # knobs near the top
        for k, ky in enumerate((300, 392)):
            ang = 130 + i * 35 + k * 60
            knob(img, cx, ky, 34, ang)
        # a couple of slider/LED accents
        disc(img, cx, 470, 9, hexc("#ff5a3c") if i % 2 == 0 else hexc("#46e08a"))
        # jacks near the bottom (2x2)
        js = []
        for jx in (cx - 40, cx + 40):
            for jy in (640, 720):
                jack(img, jx, jy)
                js.append((jx, jy))
        jacks_per_panel.append(js)

    # patch cables between modules (the signature modular look)
    cable(img, jacks_per_panel[0][1], jacks_per_panel[2][0], hexc("#e23b3b"))
    cable(img, jacks_per_panel[1][3], jacks_per_panel[4][2], hexc("#f2c200"), sag=120)
    cable(img, jacks_per_panel[2][3], jacks_per_panel[3][1], hexc("#2f8fe2"), sag=90)

    return np.clip(img, 0, 255).astype(np.uint8)


def write_png(path: Path, img: np.ndarray) -> None:
    h, w, _ = img.shape
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(img[y].tobytes())
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", comp)
                     + chunk(b"IEND", b""))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_png(OUT, render())
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
