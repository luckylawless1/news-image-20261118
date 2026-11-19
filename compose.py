#!/usr/bin/env python3
"""Compose the "World on Wednesday" poster: ONE 1024x1024 image summing up
the world's news of Wednesday 18 November 2026.

Bold editorial poster style: cream #F4EDE1, crimson red #C8102E, black
#111111. Anton for headlines, Archivo Black for smaller labels.

Layout, top to bottom:
  1. Black band with the date line.
  2. Thin red strapline band.
  3. Full-width hero panel (Shenzhen summit) with a red caption block.
  4. A 2x3 grid of story cells: five photo cells with black headline bars
     and one black text cell with the "also on Wednesday" briefs.
  5. Black footer band with the date in large type.

The output is deterministic: the same inputs always produce byte-identical
bytes. It is saved as PNG, or as JPEG (quality 88) if the PNG would exceed
1,000,000 bytes; either way the file is named entry.png in this directory.
"""

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"

W = H = 1024
CREAM = (244, 237, 225)
RED = (200, 16, 46)
BLACK = (17, 17, 17)

TOP_BAND_H = 64
RED_BAND_H = 30
HERO_H = 356
FOOTER_H = 86
GUTTER = 6

MAX_BYTES = 1_000_000


def load_font(filename, size, fallback_names):
    """Load a bundled font, falling back to a system bold font if missing."""
    path = FONTS / filename
    if path.exists():
        return ImageFont.truetype(str(path), size)
    for name in fallback_names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def anton(size):
    return load_font("Anton-Regular.ttf", size, ["DejaVuSans-Bold.ttf"])


def archivo(size):
    return load_font("ArchivoBlack-Regular.ttf", size, ["DejaVuSans-Bold.ttf"])


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(draw, cx, y, text, font, fill):
    w, _ = text_size(draw, text, font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def draw_tracked(draw, cx, y, text, font, fill, tracking):
    """Draw letter-spaced text centred on cx."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, wch in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += wch + tracking


def wrap_text(draw, text, font, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    lines = []
    current = ""
    for word in text.split():
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def cover_crop(img, target_w, target_h):
    """Scale and centre-crop img so it exactly fills target_w x target_h."""
    sw, sh = img.size
    scale = max(target_w / sw, target_h / sh)
    nw, nh = round(sw * scale), round(sh * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def draw_photo_cell(canvas, draw, x, y, w, h, image_name, headline):
    """One grid cell: photo on top (~68%), black headline bar underneath."""
    img_h = round(h * 0.68)
    photo = Image.open(ASSETS / image_name).convert("RGB")
    canvas.paste(cover_crop(photo, w, img_h), (x, y))
    bar_y = y + img_h
    draw.rectangle([x, bar_y, x + w, y + h], fill=BLACK)
    font = anton(21)
    lines = wrap_text(draw, headline, font, w - 16)
    line_h = 25
    total_h = line_h * len(lines)
    ty = bar_y + max(4, (h - img_h - total_h) // 2)
    for line in lines:
        if ty + line_h > y + h:
            break
        draw.text((x + 8, ty), line, font=font, fill=CREAM)
        ty += line_h


def draw_text_cell(draw, x, y, w, h):
    """The sixth cell: black background, red heading, cream briefs."""
    draw.rectangle([x, y, x + w, y + h], fill=BLACK)
    pad = 12
    heading_font = anton(22)
    draw.text((x + pad, y + 10), "ALSO ON WEDNESDAY", font=heading_font, fill=RED)
    body_font = archivo(16)
    items = [
        "US loses measles-free status after 26 years",
        "Ebola cases pass 11,000 in DR Congo",
        "GTA VI launches at midnight worldwide",
        "COP31 fossil-fuel draft splits nations",
    ]
    ty = y + 48
    for item in items:
        for line in wrap_text(draw, "\u2022 " + item, body_font, w - 2 * pad):
            draw.text((x + pad, ty), line, font=body_font, fill=CREAM)
            ty += 20
        ty += 7


def build_poster():
    canvas = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(canvas)

    # 1. Top black band: the date line.
    draw.rectangle([0, 0, W, TOP_BAND_H], fill=BLACK)
    date_font = archivo(30)
    _, date_h = text_size(draw, "WEDNESDAY \u00b7 18 NOVEMBER 2026", date_font)
    draw_centered(
        draw, W // 2, (TOP_BAND_H - date_h) // 2 - 2,
        "WEDNESDAY \u00b7 18 NOVEMBER 2026", date_font, CREAM,
    )

    # 2. Thin red strapline band.
    red_y = TOP_BAND_H
    draw.rectangle([0, red_y, W, red_y + RED_BAND_H], fill=RED)
    strap_font = archivo(19)
    _, strap_h = text_size(draw, "SIX STORIES \u00b7 ONE DAY", strap_font)
    draw_tracked(
        draw, W // 2, red_y + (RED_BAND_H - strap_h) // 2 - 1,
        "SIX STORIES \u00b7 ONE DAY", strap_font, CREAM, tracking=3,
    )

    # 3. Hero panel: Shenzhen summit, with a red caption block bottom-left.
    hero_y = red_y + RED_BAND_H
    hero = Image.open(ASSETS / "shenzhen.png").convert("RGB")
    canvas.paste(cover_crop(hero, W, HERO_H), (0, hero_y))
    cap1_font = anton(44)
    cap2_font = archivo(20)
    cap1 = "SHENZHEN SUMMIT"
    cap2 = "XI & PUTIN MEET \u2014 TRUMP JOINS THURSDAY"
    cap1_box = draw.textbbox((0, 0), cap1, font=cap1_font)
    cap2_box = draw.textbbox((0, 0), cap2, font=cap2_font)
    block_w = max(cap1_box[2], cap2_box[2]) + 28
    gap = 6
    # Space the two caption lines by their real glyph extents (bbox offsets
    # included), so the strapline never overlaps the headline's descenders.
    block_h = (
        12
        + (cap1_box[3] - cap1_box[1])
        + gap
        + (cap2_box[3] - cap2_box[1])
        + 12
    )
    block_y = hero_y + HERO_H - block_h
    draw.rectangle([0, block_y, block_w, hero_y + HERO_H], fill=RED)
    cap1_y = block_y + 12 - cap1_box[1]
    draw.text((14, cap1_y), cap1, font=cap1_font, fill=CREAM)
    cap2_y = cap1_y + cap1_box[3] + gap - cap2_box[1]
    draw.text((14, cap2_y), cap2, font=cap2_font, fill=CREAM)

    # 4. Grid: 2 rows x 3 columns.
    grid_y = hero_y + HERO_H
    grid_h = H - FOOTER_H - grid_y
    row_h = (grid_h - GUTTER) // 2
    col_ws = [337, 338, 337]
    col_xs = [0, col_ws[0] + GUTTER, col_ws[0] + GUTTER + col_ws[1] + GUTTER]
    cells = [
        ("gulf.png", "GULF CLASH \u2014 US JETS STRIKE IRAN, TANKERS BURN"),
        ("kerch.png", "KERCH BRIDGE HIT AGAIN \u2014 SPAN COLLAPSES"),
        ("alaska.png", "ALASKA FLIPS \u2014 DEMOCRATS TAKE THE SENATE 56\u201344"),
        ("nvidia.png", "NVIDIA'S RECORD $115.8B QUARTER"),
        ("akvan.png", "CYCLONE AKVAN BEARS DOWN ON INDIA"),
    ]
    positions = [(col_xs[i], grid_y, col_ws[i], row_h) for i in range(3)]
    positions += [
        (col_xs[i], grid_y + row_h + GUTTER, col_ws[i], row_h) for i in range(3)
    ]
    for (image_name, headline), (x, y, w, h) in zip(cells, positions):
        draw_photo_cell(canvas, draw, x, y, w, h, image_name, headline)
    tx, ty, tw, th = positions[5]
    draw_text_cell(draw, tx, ty, tw, th)

    # 5. Bottom black band: the date in large type.
    foot_y = H - FOOTER_H
    draw.rectangle([0, foot_y, W, H], fill=BLACK)
    foot_font = anton(58)
    foot_text = "18 NOVEMBER 2026"
    _, foot_h = text_size(draw, foot_text, foot_font)
    draw_centered(draw, W // 2, foot_y + (FOOTER_H - foot_h) // 2 - 4,
                  foot_text, foot_font, CREAM)

    return canvas


def main():
    poster = build_poster()
    buf = io.BytesIO()
    poster.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()
    fmt = "PNG"
    if len(data) > MAX_BYTES:
        buf = io.BytesIO()
        poster.save(buf, format="JPEG", quality=88, optimize=True)
        data = buf.getvalue()
        fmt = "JPEG"
    out = ROOT / "entry.png"
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"entry.png: {len(data)} bytes, format {fmt}, sha256 {digest}")


if __name__ == "__main__":
    main()
