"""3 ta PNG namuna: python scripts/generate_card_samples.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from report_card import ReportCardData, render_report_card  # noqa: E402

OUT = ROOT / "samples" / "cards"
TIME = "2026-05-21 19:32:05"

SAMPLES = [
    (
        "01_a_lo.png",
        "success",
        ReportCardData(
            cycle_title="21.05.2026 — Kunlik sanash",
            employee_name="Алишер Каримов",
            folder_name="Блокноты A-12",
            counted_ok=1,
            location_ok=1,
            wrong_location_count=0,
            fixed_now=None,
            comment="-",
            submitted_at=TIME,
            day_done=12,
            day_total=31,
            counted_folders=["Блокноты A-12", "Конфеты B-1", "Ручка C-5"],
        ),
    ),
    (
        "02_diqqat.png",
        "warn",
        ReportCardData(
            cycle_title="21.05.2026 — Kunlik sanash",
            employee_name="Алишер Каримов",
            folder_name="Конфеты B-3",
            counted_ok=1,
            location_ok=0,
            wrong_location_count=3,
            fixed_now=0,
            comment="3 ta joyda noto'g'ri",
            submitted_at=TIME,
            day_done=8,
            day_total=25,
            counted_folders=[f"Guruh {i}" for i in range(1, 9)],
        ),
    ),
    (
        "03_tekshiruv_tugadi.png",
        "done",
        ReportCardData(
            cycle_title="21.05.2026 — Kunlik sanash",
            employee_name="Алишер Каримов",
            folder_name="Блокноты A-12",
            counted_ok=1,
            location_ok=1,
            wrong_location_count=0,
            fixed_now=None,
            comment="-",
            submitted_at=TIME,
            day_done=31,
            day_total=31,
            counted_folders=[f"Papka {i}" for i in range(1, 32)],
        ),
    ),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, theme, data in SAMPLES:
        path = OUT / filename
        img = render_report_card(data, theme_key=theme)
        img.save(path, "PNG", optimize=True)
        print(path)
    print(f"\nTayyor: {OUT}")


if __name__ == "__main__":
    main()
