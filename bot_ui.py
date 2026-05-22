"""Telegram inline UI — dashboard, sahifalash, callback tugmalar."""

from __future__ import annotations

import html as html_lib
from typing import Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from time_util import format_submitted_at_display, today_display

FOLDER_PAGE_SIZE = 6


def he(text) -> str:
    return html_lib.escape(str(text or ""))


def progress_bar(done: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(round(width * done / total)))
    return "█" * filled + "░" * (width - filled)


def percent_bar(percent: int, width: int = 14) -> str:
    pct = max(0, min(100, int(percent)))
    filled = min(width, int(round(width * pct / 100)))
    return "█" * filled + "░" * (width - filled)


def day_progress_percent(done: int, total: int) -> int:
    if total <= 0:
        return 0
    return min(100, int(round(100 * done / total)))


def submission_quality_percent(
    *,
    counted_ok: int,
    location_ok: int,
    wrong_location_count: int,
    fixed_now,
) -> int:
    """Бу текширув натижаси: 0–100% (остаток + жой + тўғирлаш)."""
    if counted_ok and location_ok:
        return 100
    score = 0
    if counted_ok:
        score += 50
    if location_ok:
        score += 50
    elif fixed_now:
        score += 25
    if not location_ok and wrong_location_count:
        score = max(0, score - min(35, int(wrong_location_count) * 5))
    return min(100, score)


def truncate_label(name: str, limit: int = 36) -> str:
    name = str(name or "").strip()
    return name if len(name) <= limit else name[: limit - 1] + "…"


def inline_cancel_row() -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="❌ Бекор", callback_data="ui:x")]]


def inline_yes_no(prefix: str) -> InlineKeyboardMarkup:
    """prefix: c | l | f (counted, location, fixed)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ҳа", callback_data=f"ui:y:{prefix}:1"),
                InlineKeyboardButton(text="❌ Йўқ", callback_data=f"ui:y:{prefix}:0"),
            ],
            *inline_cancel_row(),
        ]
    )


def folder_list_keyboard(
    rows: list,
    page: int,
    pick_prefix: str,
    *,
    show_mark_all: bool = False,
) -> InlineKeyboardMarkup:
    """pick_prefix: p (sanash) yoki m (belgilash)"""
    start = page * FOLDER_PAGE_SIZE
    chunk = rows[start : start + FOLDER_PAGE_SIZE]
    buttons: list[list[InlineKeyboardButton]] = []
    for row in chunk:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📁 {truncate_label(row['name'])}",
                    callback_data=f"ui:{pick_prefix}:f:{row['id']}",
                )
            ]
        )
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"ui:{pick_prefix}:p:{page - 1}"))
    if start + FOLDER_PAGE_SIZE < len(rows):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"ui:{pick_prefix}:p:{page + 1}"))
    if nav:
        buttons.append(nav)
    if show_mark_all:
        buttons.append([InlineKeyboardButton(text="✅ Ҳаммасини тайёр деб белгилаш", callback_data="ui:m:all")])
    buttons.append(
        [
            InlineKeyboardButton(text="🔄 Янгилаш", callback_data="ui:go:dash"),
            InlineKeyboardButton(text="❌ Бекор", callback_data="ui:x"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Санаш", callback_data="ui:go:submit")],
            [InlineKeyboardButton(text="📌 Тайёр деб белгилаш (ихтиёрий)", callback_data="ui:go:mark")],
            [InlineKeyboardButton(text="🔄 Янгилаш", callback_data="ui:go:dash")],
        ]
    )


def build_dashboard_text(
    *,
    employee_name: str,
    cycle_title: str,
    total: int,
    to_sanash: int,
    done: int,
) -> str:
    today = today_display()
    bar = progress_bar(done, total)
    return (
        f"<b>📊 Бугунги иш</b>\n"
        f"<i>{he(today)}</i> · {he(cycle_title)}\n\n"
        f"👤 <b>{he(employee_name)}</b>\n"
        f"<code>{bar}</code>  <b>{done}</b> / {total}\n\n"
        f"📝 Санаш керак: <b>{to_sanash}</b>\n"
        f"✅ Тайёр (саналган): <b>{done}</b>"
    )


def format_submission_group_html(
    cycle_title: str,
    employee_name: str,
    folder_name: str,
    *,
    counted_ok: int,
    location_ok: int,
    wrong_location_count: int,
    fixed_now,
    comment: str,
    submitted_at: str,
    day_done: int,
    day_total: int,
) -> str:
    quality = submission_quality_percent(
        counted_ok=counted_ok,
        location_ok=location_ok,
        wrong_location_count=wrong_location_count,
        fixed_now=fixed_now,
    )
    day_pct = day_progress_percent(day_done, day_total)
    day_left = max(0, day_total - day_done)
    q_bar = percent_bar(quality)
    d_bar = percent_bar(day_pct)

    day_left = max(0, day_total - day_done)
    if quality >= 100 and day_total > 0 and day_left == 0:
        header = "🎉 <b>ТЕКШИРУВ ТУГАДИ — 100%</b>"
    elif quality >= 100:
        header = "✅ <b>ТЕКШИРУВ — АЪЛО</b>"
    elif quality >= 60:
        header = "⚠️ <b>ТЕКШИРУВ — ДИҚҚАТ</b>"
    else:
        header = "❌ <b>ТЕКШИРУВ — МУАММО</b>"

    lines = [
        header,
        "",
        f"👤 <b>{he(employee_name)}</b>",
        f"📁 <u>{he(folder_name)}</u>",
        f"🗓 <i>{he(cycle_title)}</i>",
        "",
        f"<b>📊 Бу текширув</b>",
        f"<code>{q_bar}</code>  <b>{quality}%</b>",
        "",
        f"<b>📈 Кунлик юкланиш</b>",
        f"<code>{d_bar}</code>  <b>{day_pct}%</b>",
        f"✅ Саналди: <b>{day_done}</b>  ·  📝 Қолди: <b>{day_left}</b>  ·  📦 Жами: <b>{day_total}</b>",
        "",
        "┌ <b>Натижа</b> ─────────",
        f"│ Санаш    {'✅' if counted_ok else '❌'}",
        f"│ Жой      {'✅' if location_ok else '❌'}",
    ]
    if not location_ok:
        lines.append(f"│ Хато жой <b>{wrong_location_count}</b> та")
        lines.append(f"│ Тўғирланди {'✅' if fixed_now else '❌'}")
    lines.append("└────────────────")

    if comment and comment != "-":
        lines.extend(["", f"<blockquote>💬 {he(comment)}</blockquote>"])

    lines.extend(["", f"🕐 {he(format_submitted_at_display(submitted_at))}"])
    return "\n".join(lines)
