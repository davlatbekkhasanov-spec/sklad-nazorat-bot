"""Guruh uchun PNG kartochka — HD, progress fokus, aniq layout."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot_ui import day_progress_percent, submission_quality_percent
from time_util import format_submitted_at_display

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
OUTPUT_W = 1280
SCALE = 3
MARGIN = 48
ROW_H = 40
LIST_LINE = 30
MAX_FOLDER_LINES = 12
BASE_H = 480
FOOTER_ZONE = 52


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
    counted_folders: list[str]


THEMES = {
    "success": {
        "bg": (14, 20, 30),
        "header": (0, 168, 140),
        "accent": (90, 230, 210),
        "bar": (0, 200, 170),
        "title": "Yaxshi ish!",
    },
    "warn": {
        "bg": (26, 14, 12),
        "header": (220, 110, 40),
        "accent": (255, 195, 100),
        "bar": (255, 150, 50),
        "title": "Diqqat kerak",
    },
    "done": {
        "bg": (18, 12, 36),
        "header": (130, 90, 220),
        "accent": (255, 220, 130),
        "bar": (170, 120, 255),
        "title": "Hammasi tayyor!",
    },
}


def _pick_theme(data: ReportCardData) -> str:
    q = submission_quality_percent(
        counted_ok=data.counted_ok,
        location_ok=data.location_ok,
        wrong_location_count=data.wrong_location_count,
        fixed_now=data.fixed_now,
    )
    day_left = max(0, data.day_total - data.day_done)
    if data.day_total > 0 and day_left == 0 and q >= 100:
        return "done"
    if q >= 100:
        return "success"
    return "warn"


def _card_height(folder_count: int) -> int:
    h = BASE_H
    if folder_count > 0:
        shown = min(folder_count, MAX_FOLDER_LINES)
        h += 48 + shown * LIST_LINE
        if folder_count > MAX_FOLDER_LINES:
            h += LIST_LINE
        h += 24
    h += FOOTER_ZONE
    return h


def _truncate(text: str, limit: int = 48) -> str:
    text = str(text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _load_fonts(scale: int):
    fallbacks_reg = [
        FONT_DIR / "NotoSans-Regular.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    fallbacks_bold = [
        FONT_DIR / "NotoSans-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    reg_path = next((p for p in fallbacks_reg if p.is_file()), None)
    bold_path = next((p for p in fallbacks_bold if p.is_file()), None)
    if not reg_path or not bold_path:
        d = ImageFont.load_default()
        return d, d, d, d, d
    return (
        ImageFont.truetype(str(bold_path), 36 * scale),
        ImageFont.truetype(str(bold_path), 52 * scale),
        ImageFont.truetype(str(bold_path), 30 * scale),
        ImageFont.truetype(str(reg_path), 26 * scale),
        ImageFont.truetype(str(reg_path), 20 * scale),
    )


def _text_h(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def _draw_text_row(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    line_h: int,
    text: str,
    font,
    fill: tuple,
):
    th = _text_h(draw, text, font)
    draw.text((x, y + (line_h - th) // 2), text, fill=fill, font=font)


def _draw_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, pct: int, fill: tuple, track: tuple):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=track)
    fw = max(0, int(w * max(0, min(100, pct)) / 100))
    if fw >= 3:
        draw.rounded_rectangle((x, y, x + fw, y + h), radius=h // 2, fill=fill)


def _draw_progress_ring(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, done: int, total: int, font_main):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255), width=5)
    label = f"{done}/{total}"
    tw = draw.textlength(label, font=font_main)
    th = _text_h(draw, label, font_main)
    draw.text((cx - tw // 2, cy - th // 2), label, fill=(255, 255, 255), font=font_main)


def render_report_card(data: ReportCardData, *, theme_key: str | None = None) -> Image.Image:
    theme_key = theme_key or _pick_theme(data)
    theme = THEMES[theme_key]
    folders = data.counted_folders or []
    card_h = _card_height(len(folders))
    W = OUTPUT_W * SCALE
    H = card_h * SCALE
    M = MARGIN * SCALE
    LH = ROW_H * SCALE
    LL = LIST_LINE * SCALE

    font_title, font_ring, font_main, font_body, font_small = _load_fonts(SCALE)
    white = (250, 252, 255)
    muted = (175, 185, 205)
    track = (38, 46, 62)

    img = Image.new("RGB", (W, H), theme["bg"])
    draw = ImageDraw.Draw(img)

    quality = submission_quality_percent(
        counted_ok=data.counted_ok,
        location_ok=data.location_ok,
        wrong_location_count=data.wrong_location_count,
        fixed_now=data.fixed_now,
    )
    day_pct = day_progress_percent(data.day_done, data.day_total)
    day_left = max(0, data.day_total - data.day_done)

    draw.rounded_rectangle((M, M, W - M, H - M), radius=22 * SCALE, outline=theme["header"], width=4 * SCALE)

    header_h = 96 * SCALE
    hy1 = M + header_h
    draw.rounded_rectangle((M + 10 * SCALE, M + 10 * SCALE, W - M - 10 * SCALE, hy1), radius=18 * SCALE, fill=theme["header"])
    _draw_text_row(draw, M + 28 * SCALE, M + 24 * SCALE, 52 * SCALE, theme["title"], font_title, white)

    ring_x = W - M - 78 * SCALE
    ring_y = M + 52 * SCALE
    _draw_progress_ring(draw, ring_x, ring_y, 42 * SCALE, data.day_done, data.day_total, font_ring)

    y = hy1 + 20 * SCALE
    _draw_text_row(draw, M + 20 * SCALE, y, LH, _truncate(data.employee_name, 44), font_main, white)
    y += LH
    _draw_text_row(draw, M + 20 * SCALE, y, LH, _truncate(data.folder_name, 50), font_body, theme["accent"])
    y += LH
    _draw_text_row(draw, M + 20 * SCALE, y, LH - 8 * SCALE, _truncate(data.cycle_title, 55), font_small, muted)

    y += 36 * SCALE
    bar_w = W - 2 * M - 40 * SCALE
    bx = M + 20 * SCALE
    bar_h = 26 * SCALE

    _draw_text_row(draw, bx, y, LH, "Sifat", font_small, muted)
    _draw_text_row(draw, bx + bar_w - 90 * SCALE, y, LH, f"{quality}%", font_body, theme["accent"])
    y += LH
    _draw_bar(draw, bx, y, bar_w, bar_h, quality, theme["bar"], track)
    y += LH + 8 * SCALE

    _draw_text_row(draw, bx, y, LH, "Kunlik progress", font_small, muted)
    prog_lbl = f"{data.day_done} / {data.day_total}"
    _draw_text_row(draw, bx + bar_w - int(draw.textlength(prog_lbl, font=font_body)) - 4 * SCALE, y, LH, prog_lbl, font_body, theme["accent"])
    y += LH
    _draw_bar(draw, bx, y, bar_w, bar_h, day_pct, theme["accent"], track)
    y += LH + 12 * SCALE

    chips = [
        f"Sanaldi {data.day_done}",
        f"Qoldi {day_left}",
        f"Jami {data.day_total}",
    ]
    cx = bx
    chip_h = 38 * SCALE
    for label in chips:
        tw = int(draw.textlength(label, font=font_small)) + 28 * SCALE
        draw.rounded_rectangle((cx, y, cx + tw, y + chip_h), radius=16 * SCALE, outline=theme["accent"], width=3 * SCALE)
        _draw_text_row(draw, cx + 14 * SCALE, y, chip_h, label, font_small, theme["accent"])
        cx += tw + 14 * SCALE
    y += chip_h + 16 * SCALE

    panel_lines = 2 + (1 if not data.location_ok else 0) + (1 if data.comment and data.comment != "-" else 0)
    panel_h = (20 + panel_lines * ROW_H) * SCALE
    draw.rounded_rectangle(
        (M + 14 * SCALE, y, W - M - 14 * SCALE, y + panel_h),
        radius=14 * SCALE,
        fill=(24, 30, 44),
        outline=theme["header"],
        width=3 * SCALE,
    )

    def yn(ok: int) -> tuple[str, tuple]:
        return ("Ha", (40, 200, 120)) if ok else ("Yo'q", (240, 90, 90))

    iy = y + 16 * SCALE
    for lbl, ok in [("Ostatok", data.counted_ok), ("Joy", data.location_ok)]:
        t, col = yn(ok)
        _draw_text_row(draw, M + 28 * SCALE, iy, LH, f"{lbl}:", font_small, white)
        _draw_text_row(draw, M + 160 * SCALE, iy, LH, t, font_body, col)
        iy += LH
    if not data.location_ok:
        t, col = yn(1 if data.fixed_now else 0)
        msg = f"Xato joy: {data.wrong_location_count}  |  Tuzatildi: {t}"
        _draw_text_row(draw, M + 28 * SCALE, iy, LH, msg, font_small, col)
        iy += LH
    if data.comment and data.comment != "-":
        _draw_text_row(draw, M + 28 * SCALE, iy, LH, f"Izoh: {_truncate(data.comment, 52)}", font_small, muted)

    y += panel_h + 20 * SCALE
    content_bottom = y
    if folders:
        shown = folders[-MAX_FOLDER_LINES:]
        hidden = len(folders) - len(shown)
        list_rows = len(shown) + (1 if hidden > 0 else 0)
        list_h = (44 + list_rows * LIST_LINE) * SCALE
        draw.rounded_rectangle(
            (M + 14 * SCALE, y, W - M - 14 * SCALE, y + list_h),
            radius=14 * SCALE,
            fill=(24, 30, 44),
            outline=theme["accent"],
            width=3 * SCALE,
        )
        _draw_text_row(draw, M + 28 * SCALE, y + 10 * SCALE, 36 * SCALE, "Sanalgan papkalar", font_small, theme["accent"])
        ly = y + 48 * SCALE
        current = data.folder_name.strip()
        start_n = len(folders) - len(shown) + 1
        for i, name in enumerate(shown, start=start_n):
            is_new = name.strip() == current and i == len(folders)
            mark = ">> " if is_new else "   "
            line = f"{i}.{mark}{_truncate(name, 46)}"
            col = theme["accent"] if is_new else muted
            _draw_text_row(draw, M + 28 * SCALE, ly, LL, line, font_small, col)
            ly += LL
        if hidden > 0:
            _draw_text_row(draw, M + 28 * SCALE, ly, LL, f"... yana {hidden} ta", font_small, muted)
            ly += LL
        content_bottom = y + list_h

    footer_y = content_bottom + 24 * SCALE
    bottom_needed = int(footer_y + 40 * SCALE)
    if bottom_needed > H:
        extended = Image.new("RGB", (W, bottom_needed), theme["bg"])
        extended.paste(img, (0, 0))
        img = extended
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((M, M, W - M, bottom_needed - M), radius=22 * SCALE, outline=theme["header"], width=4 * SCALE)

    time_lbl = format_submitted_at_display(data.submitted_at)
    _draw_text_row(draw, M + 20 * SCALE, footer_y, 36 * SCALE, time_lbl, font_small, muted)
    brand = "SKLAD NAZORAT"
    bw = int(draw.textlength(brand, font=font_small))
    _draw_text_row(draw, W - M - 20 * SCALE - bw, footer_y, 36 * SCALE, brand, font_small, theme["header"])

    out_h = max(card_h, int(bottom_needed / SCALE) + 6)
    cropped = img.crop((0, 0, W, min(bottom_needed, img.height)))
    return cropped.resize((OUTPUT_W, out_h), Image.Resampling.LANCZOS)


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
    counted_folders: list[str] | None = None,
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
        counted_folders=list(counted_folders or []),
    )


def render_report_card_png(data: ReportCardData) -> bytes:
    buf = BytesIO()
    img = render_report_card(data)
    img.save(buf, format="PNG", compress_level=1, dpi=(144, 144))
    return buf.getvalue()
