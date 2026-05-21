"""Guruh xabarlari namunasi — python scripts/preview_group_reports.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot_ui import format_submission_group_html  # noqa: E402

CASES = [
    (
        "1) Hammasi yaxshi (12/31)",
        dict(
            counted_ok=1,
            location_ok=1,
            wrong_location_count=0,
            fixed_now=None,
            comment="-",
            day_done=12,
            day_total=31,
        ),
    ),
    (
        "2) Oxirgi papka — kun tugadi (31/31)",
        dict(
            counted_ok=1,
            location_ok=1,
            wrong_location_count=0,
            fixed_now=None,
            comment="-",
            day_done=31,
            day_total=31,
        ),
    ),
    (
        "3) Diqqat — joy xato + izoh",
        dict(
            counted_ok=1,
            location_ok=0,
            wrong_location_count=3,
            fixed_now=0,
            comment="3 ta joyda noto'g'ri, ertaga tuzatamiz",
            day_done=8,
            day_total=25,
        ),
    ),
    (
        "4) Muammo — ostatok ham joy ham xato",
        dict(
            counted_ok=0,
            location_ok=0,
            wrong_location_count=5,
            fixed_now=0,
            comment="Katta farq bor",
            day_done=3,
            day_total=20,
        ),
    ),
]

TIME = "2026-05-21 19:32:05"  # Toshkent (namuna)


def main():
    parts = [
        "# Guruhga ketadigan xabar — namunalar",
        "",
        "Vaqt: Asia/Tashkent (TZ). Telegramda <b>qalin</b>, <u>chiziq</u>, progress bar ko'rinadi.",
        "",
    ]
    for title, kw in CASES:
        body = format_submission_group_html(
            "21.05.2026 — Kunlik sanash",
            "Alisher Karimov",
            "Bloknoty A-12",
            submitted_at=TIME,
            **kw,
        )
        parts.append(f"## {title}")
        parts.append("")
        parts.append("```")
        parts.append(body.replace("<b>", "").replace("</b>", "").replace("<u>", "").replace("</u>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "").replace("<blockquote>", "«").replace("</blockquote>", "»"))
        parts.append("```")
        parts.append("")

    out = ROOT / "GROUP_REPORT_SAMPLES.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"Yozildi: {out}")


if __name__ == "__main__":
    main()
