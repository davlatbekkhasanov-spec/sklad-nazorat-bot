"""Guruh uchun PNG kartochka — aniq shrift, 2x sifat, toza layout."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot_ui import day_progress_percent, submission_quality_percent
from time_util import format_submitted_at_display

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
OUTPUT_W = 1200
SCALE = 2
MARGIN = 44
LIST_LINE = 28
MAX_FOLDER_LINES = 12
BASE_H = 500
FOOTER_ZONE = 56


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
        "bg": (15, 22, 32),
        "header": (0, 168, 140),
        "accent": (80, 220, 200),
        "bar": (0, 200, 170),
        "title": "Текширув · A'lo",
    },
    "warn": {
        "bg": (28, 16, 14),
        "header": (220, 110, 40),
        "accent": (255, 190, 90),
        "bar": (255, 150, 50),
        "title": "Текширув · Diqqat",
    },
    "done": {
        "bg": (20, 14, 38),
        "header": (130, 90, 220),
        "accent": (255, 215, 120),
        "bar": (170, 120, 255),
        "title": "Текширув tugadi",
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
        h += 44 + shown * LIST_LINE
        if folder_count > MAX_FOLDER_LINES:
            h += LIST_LINE
        h += 20
    h += FOOTER_ZONE
    return h


def _truncate(text: str, limit: int = 46) -> str:
    text = str(text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _load_fonts(scale: int):
    fallbacks_reg = [
        FONT_DIR / "NotoSans-Regular.ttf",
        FONT_DIR / "Arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    fallbacks_bold = [
        FONT_DIR / "NotoSans-Bold.ttf",
        FONT_DIR / "Arial-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    reg_path = next((p for p in fallbacks_reg if p.is_file()), None)
    bold_path = next((p for p in fallbacks_bold if p.is_file()), None)
    if not reg_path or not bold_path:
        d = ImageFont.load_default()
        return d, d, d, d
    return (
        ImageFont.truetype(str(bold_path), 34 * scale),
        ImageFont.truetype(str(bold_path), 48 * scale),
        ImageFont.truetype(str(reg_path), 24 * scale),
        ImageFont.truetype(str(reg_path), 18 * scale),
    )


def _draw_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, pct: int, fill: tuple, track: tuple):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=track)
    fw = max(0, int(w * max(0, min(100, pct)) / 100))
    if fw >= 2:
        draw.rounded_rectangle((x, y, x + fw, y + h), radius=h // 2, fill=fill)


def render_report_card(data: ReportCardData, *, theme_key: str | None = None) -> Image.Image:
    theme_key = theme_key or _pick_theme(data)
    theme = THEMES[theme_key]
    folders = data.counted_folders or []
    card_h = _card_height(len(folders))
    W = OUTPUT_W * SCALE
    H = card_h * SCALE
    M = MARGIN * SCALE

    font_title, font_big, font_main, font_small = _load_fonts(SCALE)
    white = (248, 250, 252)
    muted = (170, 180, 198)
    track = (35, 42, 58)

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

    draw.rounded_rectangle((M, M, W - M, H - M), radius=20 * SCALE, outline=theme["header"], width=3 * SCALE)

    hy1 = M + 88 * SCALE
    draw.rounded_rectangle((M + 8 * SCALE, M + 8 * SCALE, W - M - 8 * SCALE, hy1), radius=16 * SCALE, fill=theme["header"])
    draw.text((M + 28 * SCALE, M + 28 * SCALE), theme["title"], fill=white, font=font_title)

    ring_x = W - M - 70 * SCALE
    ring_y = M + 48 * SCALE
    ring_r = 38 * SCALE
    draw.ellipse(
        (ring_x - ring_r, ring_y - ring_r, ring_x + ring_r, ring_y + ring_r),
        outline=white,
        width=4 * SCALE,
    )
    pct_txt = str(quality)
    tw = draw.textlength(pct_txt, font=font_big)
    draw.text((ring_x - tw // 2, ring_y - 26 * SCALE), pct_txt, fill=white, font=font_big)
    sub = f"{quality}%"
    sw = draw.textlength(sub, font=font_small)
    draw.text((ring_x - sw // 2, ring_y + 14 * SCALE), sub, fill=white, font=font_small)

    y = hy1 + 22 * SCALE
    draw.text((M + 16 * SCALE, y), _truncate(data.employee_name, 42), fill=white, font=font_main)
    y += 36 * SCALE
    draw.text((M + 16 * SCALE, y), _truncate(data.folder_name, 48), fill=theme["accent"], font=font_main)
    y += 32 * SCALE
    draw.text((M + 16 * SCALE, y), _truncate(data.cycle_title, 55), fill=muted, font=font_small)

    y += 40 * SCALE
    bar_w = W - 2 * M - 32 * SCALE
    bx = M + 16 * SCALE
    draw.text((bx, y), "Бу текширув", fill=muted, font=font_small)
    draw.text((bx + bar_w - 80 * SCALE, y), f"{quality}%", fill=theme["accent"], font=font_main)
    y += 26 * SCALE
    _draw_bar(draw, bx, y, bar_w, 22 * SCALE, quality, theme["bar"], track)
    y += 40 * SCALE

    draw.text((bx, y), "Кунлик прогресс", fill=muted, font=font_small)
    draw.text((bx + bar_w - 100 * SCALE, y), f"{data.day_done} / {data.day_total}", fill=theme["accent"], font=font_main)
    y += 26 * SCALE
    _draw_bar(draw, bx, y, bar_w, 22 * SCALE, day_pct, theme["accent"], track)
    y += 42 * SCALE

    chips = [
        f"Саналди {data.day_done}",
        f"Қолди {day_left}",
        f"Жами {data.day_total}",
    ]
    cx = bx
    for label in chips:
        tw = int(draw.textlength(label, font=font_small)) + 24 * SCALE
        draw.rounded_rectangle((cx, y, cx + tw, y + 34 * SCALE), radius=14 * SCALE, outline=theme["accent"], width=2 * SCALE)
        draw.text((cx + 12 * SCALE, y + 8 * SCALE), label, fill=theme["accent"], font=font_small)
        cx += tw + 12 * SCALE

    y += 50 * SCALE
    panel_lines = 2 + (1 if not data.location_ok else 0) + (1 if data.comment and data.comment != "-" else 0)
    panel_h = (24 + panel_lines * 34) * SCALE
    draw.rounded_rectangle(
        (M + 12 * SCALE, y, W - M - 12 * SCALE, y + panel_h),
        radius=14 * SCALE,
        fill=(22, 28, 40),
        outline=theme["header"],
        width=2 * SCALE,
    )

    def yn(ok: int) -> tuple[str, tuple]:
        return ("Ҳа", (30, 90, 55)) if ok else ("Йўқ", (120, 40, 40))

    iy = y + 20 * SCALE
    for lbl, ok in [("Остаток", data.counted_ok), ("Жой", data.location_ok)]:
        t, col = yn(ok)
        draw.text((M + 28 * SCALE, iy), f"{lbl}:", fill=white, font=font_small)
        draw.text((M + 150 * SCALE, iy), t, fill=col, font=font_main)
        iy += 34 * SCALE
    if not data.location_ok:
        t, col = yn(1 if data.fixed_now else 0)
        draw.text(
            (M + 28 * SCALE, iy),
            f"Хато жой: {data.wrong_location_count}  ·  Тузатилди: {t}",
            fill=col,
            font=font_small,
        )
        iy += 34 * SCALE
    if data.comment and data.comment != "-":
        draw.text(
            (M + 28 * SCALE, iy),
            f"Изоҳ: {_truncate(data.comment, 50)}",
            fill=muted,
            font=font_small,
        )

    y += panel_h + 24 * SCALE
    content_bottom = y
    if folders:
        shown = folders[-MAX_FOLDER_LINES:]
        hidden = len(folders) - len(shown)
        list_rows = len(shown) + (1 if hidden > 0 else 0)
        list_h = (40 + list_rows * LIST_LINE) * SCALE
        draw.rounded_rectangle(
            (M + 12 * SCALE, y, W - M - 12 * SCALE, y + list_h),
            radius=14 * SCALE,
            fill=(22, 28, 40),
            outline=theme["accent"],
            width=2 * SCALE,
        )
        draw.text((M + 28 * SCALE, y + 12 * SCALE), "Саналган папкалар", fill=theme["accent"], font=font_small)
        ly = y + 40 * SCALE
        current = data.folder_name.strip()
        start_n = len(folders) - len(shown) + 1
        for i, name in enumerate(shown, start=start_n):
            is_new = name.strip() == current and i == len(folders)
            mark = "▸ " if is_new else "  "
            line = f"{i}.{mark}{_truncate(name, 44)}"
            col = theme["accent"] if is_new else muted
            draw.text((M + 28 * SCALE, ly), line, fill=col, font=font_small)
            ly += LIST_LINE * SCALE
        if hidden > 0:
            draw.text((M + 28 * SCALE, ly), f"… ва яна {hidden} та (юқорида)", fill=muted, font=font_small)
            ly += LIST_LINE * SCALE
        content_bottom = y + list_h

    footer_y = content_bottom + 20 * SCALE
    bottom_needed = int(footer_y + 36 * SCALE)
    if bottom_needed > H:
        extended = Image.new("RGB", (W, bottom_needed), theme["bg"])
        extended.paste(img, (0, 0))
        img = extended
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((M, M, W - M, bottom_needed - M), radius=20 * SCALE, outline=theme["header"], width=3 * SCALE)

    draw.text((M + 16 * SCALE, footer_y), format_submitted_at_display(data.submitted_at), fill=muted, font=font_small)
    brand = "SKLAD NAZORAT"
    bw = draw.textlength(brand, font=font_small)
    draw.text((W - M - 16 * SCALE - bw, footer_y), brand, fill=theme["header"], font=font_small)

    out_h = max(card_h, int(bottom_needed / SCALE) + 4)
    return img.crop((0, 0, W, min(bottom_needed, img.height))).resize((OUTPUT_W, out_h), Image.Resampling.LANCZOS)


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
    render_report_card(data).save(buf, format="PNG", compress_level=2)
    return buf.getvalue()
