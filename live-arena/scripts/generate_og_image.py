"""Generate the BuilderWars social card (1200x630 og-image.png) from brand assets.

Reads live-arena/public/mark.svg and renders it with PIL, overlaying the wordmark
and tagline on the brand palette defined in docs/BUILDERWARS_BRAND_ARCHITECTURE.md.

Run from live-arena/:  python scripts/generate_og_image.py
Deterministic output: fixed layout, fixed colors, no timestamps.
"""
from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "public" / "mark.svg"
OUT_PATH = ROOT / "public" / "og-image.png"

W, H = 1200, 630
DARK = "#111513"
LIME = "#c8fa75"
CREAM = "#faf8f2"
MUTED = "#9aa79e"

FONT_BOLD = r"C:\Windows\Fonts\seguisb.ttf"
FONT_REG = r"C:\Windows\Fonts\segoeuib.ttf"


def _flatten_path(d_attr: str, scale: int) -> list[list[tuple[float, float]]]:
    """Flatten an SVG path (M/m, h/H, v/V, c/C, z) into polygons.

    Supports exactly the command set used by mark.svg's glyph path.
    Cubic beziers are flattened with a fixed 32-step sampling — deterministic.
    """
    tokens = re.findall(r"[MmHhVvCcZz]|-?\d+\.?\d*(?:e-?\d+)?", d_attr)
    i = 0
    cur = (0.0, 0.0)
    start = (0.0, 0.0)
    polys: list[list[tuple[float, float]]] = []
    poly: list[tuple[float, float]] = []

    def cubic(p0, p1, p2, p3):
        pts = []
        for s in range(1, 33):
            t = s / 32.0
            mt = 1 - t
            x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
            y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
            pts.append((x, y))
        return pts

    while i < len(tokens):
        tok = tokens[i]
        if tok in "MmHhVvCcZz":
            cmd = tok
            i += 1
        else:  # implicit repeat of last command type
            cmd = last_cmd
        last_cmd = cmd
        if cmd in "Mm":
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "m":
                x, y = cur[0] + x, cur[1] + y
            if poly:
                polys.append(poly)
            poly = [(x, y)]
            cur = start = (x, y)
        elif cmd in "Hh":
            x = float(tokens[i])
            i += 1
            if cmd == "h":
                x = cur[0] + x
            poly.append((x, cur[1]))
            cur = (x, cur[1])
        elif cmd in "Vv":
            y = float(tokens[i])
            i += 1
            if cmd == "v":
                y = cur[1] + y
            poly.append((cur[0], y))
            cur = (cur[0], y)
        elif cmd in "Cc":
            x1, y1, x2, y2, x, y = (float(t) for t in tokens[i : i + 6])
            i += 6
            if cmd == "c":
                x1, y1 = cur[0] + x1, cur[1] + y1
                x2, y2 = cur[0] + x2, cur[1] + y2
                x, y = cur[0] + x, cur[1] + y
            poly.extend(cubic(cur, (x1, y1), (x2, y2), (x, y)))
            cur = (x, y)
        elif cmd in "Zz":
            if poly:
                polys.append(poly)
                poly = []
            cur = start
    if poly:
        polys.append(poly)
    return [[(x * scale, y * scale) for x, y in p] for p in polys]


def svg_to_rgba(svg_text: str, scale: int = 10) -> Image.Image:
    """Rasterize mark.svg exactly: rounded-rect tile + true glyph path fills."""
    root = ET.fromstring(svg_text)
    _, _, vw, vh = (float(v) for v in root.get("viewBox").split())
    rect = root.find("{http://www.w3.org/2000/svg}rect")
    path = root.find("{http://www.w3.org/2000/svg}path")
    bg_fill = rect.get("fill")
    glyph_fill = path.get("fill")

    img = Image.new("RGBA", (int(vw * scale), int(vh * scale)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [0, 0, int(vw * scale), int(vh * scale)], radius=int(16 * scale), fill=bg_fill
    )

    polygons = _flatten_path(path.get("d"), scale)
    # First polygon is the glyph outline; the rest are its counters (holes),
    # which we punch back out in the tile color.
    draw.polygon(polygons[0], fill=glyph_fill)
    for hole in polygons[1:]:
        draw.polygon(hole, fill=bg_fill)
    return img


def main() -> None:
    svg = SVG_PATH.read_text(encoding="utf-8")
    mark = svg_to_rgba(svg, scale=10)  # 640x640
    mark = mark.resize((256, 256), Image.LANCZOS)

    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # Subtle grid: 12 columns of hairlines in a barely-there lime at 6% alpha.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for i in range(1, 12):
        x = int(W * i / 12)
        odraw.line([(x, 0), (x, H)], fill=(200, 250, 117, 8), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    f_bold = ImageFont.truetype(FONT_BOLD, 108)
    f_reg = ImageFont.truetype(FONT_REG, 40)
    f_small = ImageFont.truetype(FONT_REG, 30)

    # Mark top-left with generous margin.
    img.paste(mark, (96, 88), mark)

    # Wordmark.
    draw.text((96, 380), "BuilderWars", font=f_bold, fill=CREAM)
    draw.text((98, 505), "Your agent. Your arena.", font=f_reg, fill=LIME)

    # Right column stat block, matching the repo's verified-result voice.
    draw.text((770, 96), "REPLAY-VERIFIED", font=f_small, fill=MUTED)
    draw.text((770, 140), "chess · checkers", font=f_small, fill=CREAM)
    draw.text((770, 186), "connect four · tic-tac-toe", font=f_small, fill=CREAM)
    draw.text((770, 268), "OPEN ARENA", font=f_small, fill=MUTED)
    draw.text((770, 312), "bring your own model", font=f_small, fill=CREAM)
    draw.text((770, 358), "keep your own key", font=f_small, fill=CREAM)
    draw.line([(770, 430), (1104, 430)], fill=LIME, width=3)
    draw.text((770, 452), "builderwars.com", font=f_reg, fill=CREAM)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PATH, "PNG", optimize=True)
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
