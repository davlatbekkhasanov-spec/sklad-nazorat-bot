"""Telegram inline UI — dashboard, sahifalash, callback tugmalar."""

from __future__ import annotations

import html as html_lib
from typing import Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

FOLDER_PAGE_SIZE = 6


def he(text) -> str:
    return html_lib.escape(str(text or ""))


def progress_bar(done: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(round(width * done / total)))
    return "█" * filled + "░" * (width - filled)


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
        buttons.append([InlineKeyboardButton(text="✅ Ҳаммасини белгилаш", callback_data="ui:m:all")])
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
            [InlineKeyboardButton(text="📝 Кейингисини санаш", callback_data="ui:go:submit")],
            [
                InlineKeyboardButton(text="📌 Белгилаш", callback_data="ui:go:mark"),
                InlineKeyboardButton(text="📋 Рўйхат", callback_data="ui:go:list"),
            ],
            [InlineKeyboardButton(text="🔄 Янгилаш", callback_data="ui:go:dash")],
        ]
    )


def build_dashboard_text(
    *,
    employee_name: str,
    cycle_title: str,
    total: int,
    unmarked: int,
    to_submit: int,
    done: int,
) -> str:
    today = __import__("datetime").datetime.now().strftime("%d.%m.%Y")
    bar = progress_bar(done, total)
    return (
        f"<b>📊 Бугунги иш</b>\n"
        f"<i>{he(today)}</i> · {he(cycle_title)}\n\n"
        f"👤 <b>{he(employee_name)}</b>\n"
        f"<code>{bar}</code>  <b>{done}</b> / {total}\n\n"
        f"📌 Белгилаш керак: <b>{unmarked}</b>\n"
        f"📝 Санаш керак: <b>{to_submit}</b>\n"
        f"✅ Тайёр: <b>{done}</b>"
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
) -> str:
    lines = [
        "<b>📦 Склад текшируви</b>",
        "",
        f"👤 {he(employee_name)}",
        f"📁 <b>{he(folder_name)}</b>",
        f"🗓 {he(cycle_title)}",
        "",
        f"Остаток: {'✅' if counted_ok else '❌'}",
        f"Жой: {'✅' if location_ok else '❌'}",
    ]
    if not location_ok:
        lines.append(f"Хато жой: <b>{wrong_location_count}</b>")
        lines.append(f"Тўғирланди: {'✅' if fixed_now else '❌'}")
    lines.extend(["", f"💬 {he(comment)}", f"🕐 {he(submitted_at)}"])
    return "\n".join(lines)
