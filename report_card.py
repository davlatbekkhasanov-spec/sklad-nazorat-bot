"""Guruh uchun PNG kartochka — premium neon / glass."""

from __future__ import annotations

import random
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot_ui import day_progress_percent, submission_quality_percent
from time_util import format_submitted_at_display

CARD_W = 960
CARD_H = 620
MARGIN = 40


@dataclass
class ReportCardData:
    cycle_title: str
    employee_name: str
    folder_name: str
    counted_ok: int
    location_ok: int
    wrong_location_count: int
    fixed_now: int | None
    comment: str
    submitted_at: str
    day_done: int
    day_total: int


THEMES = {
    "success": {
        "bg_top": (4, 8, 22),
        "bg_bottom": (8, 62, 88),
        "spot": (0, 255, 220),
        "header": ((0, 255, 200), (0, 140, 255), (180, 0, 255)),
        "border": (0, 255, 210),
        "glow": (0, 255, 220),
        "bar1": ((0, 255, 200), (0, 180, 255)),
        "bar2": ((100, 220, 255), (200, 120, 255)),
        "title": "TEKSHIRUV — A'LO",
        "accent": (120, 255, 230),
        "sparkle": False,
    },
    "warn": {
        "bg_top": (18, 4, 4),
        "bg_bottom": (72, 18, 8),
        "spot": (255, 100, 40),
        "header": ((255, 60, 30), (255, 180, 0), (255, 80, 120)),
        "border": (255, 140, 50),
        "glow": (255, 120, 40),
        "bar1": ((255, 90, 30), (255, 200, 60)),
        "bar2": ((255, 200, 80), (255, 100, 80)),
        "title": "TEKSHIRUV — DIQQAT",
        "accent": (255, 200, 100),
        "sparkle": False,
    },
    "done": {
        "bg_top": (8, 4, 32),
        "bg_bottom": (40, 12, 100),
        "spot": (200, 120, 255),
        "header": ((140, 60, 255), (255, 200, 80), (255, 100, 200)),
        "border": (220, 180, 255),
        "glow": (200, 150, 255),
        "bar1": ((160, 100, 255), (255, 200, 120)),
        "bar2": ((255, 220, 100), (255, 120, 200)),
        "title": "TEKSHIRUV TUGADI",
        "accent": (255, 230, 140),
        "sparkle": True,
    },
}


def _pick_theme(data: ReportCardData) -> str:
    q = submission_quality_percent(
        counted_ok=data.counted_ok,
        location_ok=data.location_ok,
        wrong_location_count=data.wrong_location_count,
        fixed_now=data.fixed_now,
    )
    if data.day_total > 0 and data.day_done >= data.day_total and q >= 100:
        return "done"
    if q >= 100:
        return "success"
    return "warn"


def _load_fonts():
    bold_candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    reg_candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    bold_path = next((p for p in bold_candidates if p.exists()), None)
    reg_path = next((p for p in reg_candidates if p.exists()), bold_path)
    if not bold_path:
        d = ImageFont.load_default()
        return d, d, d, d
    return (
        ImageFont.truetype(str(bold_path), 32),
        ImageFont.truetype(str(bold_path), 56),
        ImageFont.truetype(str(reg_path), 22),
        ImageFont.truetype(str(reg_path), 16),
    )


def _vertical_gradient(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        row = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    return img


def _horizontal_gradient_3(w: int, h: int, c0: tuple, c1: tuple, c2: tuple) -> Image.Image:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for x in range(w):
        t = x / max(w - 1, 1)
        if t < 0.5:
            u = t * 2
            col = tuple(int(c0[i] * (1 - u) + c1[i] * u) for i in range(3))
        else:
            u = (t - 0.5) * 2
            col = tuple(int(c1[i] * (1 - u) + c2[i] * u) for i in range(3))
        for y in range(h):
            px[x, y] = col
    return img


def _paste_rounded(base: Image.Image, patch: Image.Image, box: tuple, radius: int):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if patch.size != (w, h):
        patch = patch.resize((w, h), Image.Resampling.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    base.paste(patch, (x0, y0), mask)


def _add_spotlight(img: Image.Image, color: tuple, cx: int, cy: int, radius: int):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for r in range(radius, 0, -8):
        alpha = int(28 * (1 - r / radius))
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, alpha))
    img_rgba = img.convert("RGBA")
    img_rgba.alpha_composite(overlay)
    return img_rgba.convert("RGB")


def _draw_neon_border(img: Image.Image, color: tuple):
    draw = ImageDraw.Draw(img)
    for i, a in enumerate((220, 140, 70)):
        inset = 6 + i * 2
        c = tuple(min(255, int(v * (0.5 + 0.5 * (1 - i / 3)))) for v in color)
        draw.rounded_rectangle(
            (inset, inset, CARD_W - inset, CARD_H - inset),
            radius=22 - i,
            outline=c,
            width=3 - i,
        )


def _draw_sparkles(img: Image.Image, color: tuple, seed: int = 42):
    rng = random.Random(seed)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(55):
        x = rng.randint(20, CARD_W - 20)
        y = rng.randint(20, CARD_H - 120)
        s = rng.randint(2, 5)
        a = rng.randint(80, 200)
        draw.ellipse((x, y, x + s, y + s), fill=(*color, a))
    base = img.convert("RGBA")
    base.alpha_composite(overlay)
    return base.convert("RGB")


def _draw_premium_bar(
    img: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    percent: int,
    grad: tuple,
    glow: tuple,
):
    track = (18, 22, 38)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=track)
    fw = max(0, int(w * max(0, min(100, percent)) / 100))
    if fw < 2:
        return
    pad = 8
    glow_c = tuple(min(255, int(c * 0.35 + 30)) for c in glow)
    draw.rounded_rectangle(
        (x - 3, y - pad, x + fw + pad, y + h + pad),
        radius=(h + pad) // 2,
        fill=glow_c,
    )
    g0, g1 = grad[0], grad[1]
    g2 = grad[2] if len(grad) > 2 else grad[1]
    bar_img = _horizontal_gradient_3(fw, h, g0, g1, g2)
    mask = Image.new("L", (fw, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw, h), radius=h // 2, fill=255)
    img.paste(bar_img, (x, y), mask)
    shine = ImageDraw.Draw(img)
    shine.rounded_rectangle((x + 4, y + 2, x + max(8, fw - 6), y + h // 2), radius=3, fill=(255, 255, 255))


def _draw_percent_ring(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    percent: int,
    ring: tuple,
    text: str,
    font,
    sub_font,
):
    dim = tuple(max(0, c // 3) for c in ring)
    draw.ellipse((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), outline=dim, width=6)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ring, width=5)
    tw = draw.textlength(text, font=font)
    draw.text((cx - tw // 2, cy - 30), text, fill=(255, 255, 255), font=font)
    sub = f"{percent}%"
    sw = draw.textlength(sub, font=sub_font)
    draw.text((cx - sw // 2, cy + 12), sub, fill=ring, font=sub_font)


def _glass_panel(img: Image.Image, box: tuple, border: tuple):
    x0, y0, x1, y1 = box
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(box, radius=16, fill=(255, 255, 255, 22))
    draw.rounded_rectangle(box, radius=16, outline=(*border, 200), width=2)
    base = img.convert("RGBA")
    base.alpha_composite(overlay)
    return base.convert("RGB")


def render_report_card(data: ReportCardData, *, theme_key: str | None = None) -> Image.Image:
    theme_key = theme_key or _pick_theme(data)
    theme = THEMES[theme_key]
    img = _vertical_gradient((CARD_W, CARD_H), theme["bg_top"], theme["bg_bottom"])
    img = _add_spotlight(img, theme["spot"], CARD_W // 2, 140, 380)
    if theme.get("sparkle"):
        img = _draw_sparkles(img, theme["accent"], seed=7)

    font_title, font_huge, font_main, font_small = _load_fonts()
    white = (255, 255, 255)
    muted = (190, 200, 225)

    _draw_neon_border(img, theme["border"])

    hx0, hy0, hx1, hy1 = MARGIN, MARGIN, CARD_W - MARGIN, 108
    shadow = Image.new("RGB", (hx1 - hx0, hy1 - hy0), (0, 0, 0))
    _paste_rounded(img, shadow, (hx0 + 4, hy0 + 6, hx1 + 4, hy1 + 6), 20)
    header_patch = _horizontal_gradient_3(
        hx1 - hx0, hy1 - hy0, theme["header"][0], theme["header"][1], theme["header"][2]
    )
    _paste_rounded(img, header_patch, (hx0, hy0, hx1, hy1), 20)
    draw = ImageDraw.Draw(img)
    draw.line((hx0 + 16, hy0 + 8, hx1 - 16, hy0 + 8), fill=(255, 255, 255), width=2)
    draw.text((hx0 + 24, hy0 + 30), theme["title"], fill=white, font=font_title)

    quality = submission_quality_percent(
        counted_ok=data.counted_ok,
        location_ok=data.location_ok,
        wrong_location_count=data.wrong_location_count,
        fixed_now=data.fixed_now,
    )
    ring_label = "100" if quality >= 100 else str(quality)
    _draw_percent_ring(
        draw,
        CARD_W - MARGIN - 58,
        hy0 + 54,
        52,
        quality,
        theme["accent"],
        ring_label,
        font_huge,
        font_small,
    )

    y = 128
    draw.text((MARGIN, y), data.employee_name, fill=white, font=font_main)
    y += 36
    draw.text((MARGIN, y), data.folder_name, fill=theme["accent"], font=font_main)
    y += 32
    draw.text((MARGIN, y), data.cycle_title, fill=muted, font=font_small)

    day_pct = day_progress_percent(data.day_done, data.day_total)
    day_left = max(0, data.day_total - data.day_done)

    y += 44
    bar_w = CARD_W - 2 * MARGIN - 120
    bx = MARGIN
    draw.text((bx, y), "BU TEKSHIRUV", fill=muted, font=font_small)
    draw.text((bx + bar_w - 60, y), f"{quality}%", fill=theme["accent"], font=font_main)
    y += 26
    _draw_premium_bar(img, bx, y, bar_w, 24, quality, theme["bar1"], theme["glow"])
    y += 44

    draw.text((bx, y), "KUNLIK PROGRESS", fill=muted, font=font_small)
    draw.text((bx + bar_w - 100, y), f"{data.day_done}/{data.day_total}", fill=theme["accent"], font=font_main)
    y += 26
    _draw_premium_bar(img, bx, y, bar_w, 24, day_pct, theme["bar2"], theme["glow"])
    y += 44

    chip_y = y
    chips = [
        (f"Sanaldi {data.day_done}", theme["bar1"][0]),
        (f"Qoldi {day_left}", theme["bar2"][1]),
        (f"Jami {data.day_total}", theme["accent"]),
    ]
    cx = MARGIN
    for label, col in chips:
        tw = int(draw.textlength(label, font=font_small)) + 28
        draw.rounded_rectangle((cx, chip_y, cx + tw, chip_y + 32), radius=16, fill=(20, 26, 42))
        draw.rounded_rectangle((cx, chip_y, cx + tw, chip_y + 32), radius=16, outline=col, width=2)
        draw.text((cx + 14, chip_y + 7), label, fill=col, font=font_small)
        cx += tw + 12

    y = chip_y + 48
    box_h = 118 if not data.location_ok else 92
    img = _glass_panel(img, (MARGIN, y, CARD_W - MARGIN, y + box_h), theme["border"])
    draw = ImageDraw.Draw(img)

    def pill(ok: int) -> tuple[str, tuple, tuple]:
        if ok:
            return ("HA", (16, 48, 32), (80, 255, 160))
        return ("YO'Q", (52, 18, 18), (255, 90, 90))

    iy = y + 20
    for label, val, ok in [
        ("Ostatok", data.counted_ok, data.counted_ok),
        ("Joy", data.location_ok, data.location_ok),
    ]:
        p_lbl, p_bg, p_fg = pill(ok)
        draw.text((MARGIN + 20, iy), f"{label}:", fill=white, font=font_small)
        pw = int(draw.textlength(p_lbl, font=font_small)) + 24
        px = MARGIN + 130
        draw.rounded_rectangle((px, iy - 4, px + pw, iy + 24), radius=12, fill=p_bg, outline=p_fg, width=2)
        draw.text((px + 12, iy), p_lbl, fill=p_fg, font=font_small)
        iy += 34

    if not data.location_ok:
        f_lbl, f_bg, f_fg = pill(1 if data.fixed_now else 0)
        draw.text(
            (MARGIN + 20, iy),
            f"Xato: {data.wrong_location_count}  ·  Tuzatildi: {f_lbl}",
            fill=theme["accent"],
            font=font_small,
        )

    if data.comment and data.comment != "-":
        c = data.comment if len(data.comment) <= 52 else data.comment[:51] + "…"
        draw.text((MARGIN, y + box_h + 16), f"Izoh: {c}", fill=muted, font=font_small)

    draw.text((MARGIN, CARD_H - 44), format_submitted_at_display(data.submitted_at), fill=muted, font=font_small)
    draw.text((CARD_W - MARGIN - 130, CARD_H - 44), "SKLAD NAZORAT", fill=theme["border"], font=font_small)

    return img


def build_report_card_data(
    *,
    cycle_title: str,
    employee_name: str,
    folder_name: str,
    counted_ok: int,
    location_ok: int,
    wrong_location_count: int,
    fixed_now,
    comment: str,
    submitted_at: str,
    day_done: int,
    day_total: int,
) -> ReportCardData:
    return ReportCardData(
        cycle_title=cycle_title,
        employee_name=employee_name,
        folder_name=folder_name,
        counted_ok=counted_ok,
        location_ok=location_ok,
        wrong_location_count=wrong_location_count,
        fixed_now=fixed_now,
        comment=comment,
        submitted_at=submitted_at,
        day_done=day_done,
        day_total=day_total,
    )


def render_report_card_png(data: ReportCardData) -> bytes:
    buf = BytesIO()
    render_report_card(data).save(buf, format="PNG", optimize=True)
    return buf.getvalue()
