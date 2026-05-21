"""Вақт — сервер UTC бўлса ҳам Тошкент (ёки TZ) бўйича."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Tashkent"


def app_timezone() -> ZoneInfo:
    name = (os.getenv("TZ") or DEFAULT_TZ).strip() or DEFAULT_TZ
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def now_dt() -> datetime:
    return datetime.now(app_timezone())


def now_str() -> str:
    return now_dt().strftime("%Y-%m-%d %H:%M:%S")


def today_display() -> str:
    return now_dt().strftime("%d.%m.%Y")


def format_submitted_at_display(submitted_at: str) -> str:
    raw = str(submitted_at or "").strip()
    if not raw:
        return ""
    tz = app_timezone()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            else:
                dt = dt.astimezone(tz)
            return dt.strftime("%d.%m.%Y · %H:%M")
        except ValueError:
            continue
    return raw
