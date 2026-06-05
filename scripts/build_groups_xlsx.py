"""ASSIGNMENTS_CURRENT.txt → groups.xlsx (Пулат папкалари → Тувалов Фаррух)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS = ROOT / "ASSIGNMENTS_CURRENT.txt"
OUT_XLSX = ROOT / "groups.xlsx"

FARRUX = "Тувалов Фаррух"
SINDOR = "Рузибоев Синдор"

# Qo‘lda ko‘chirishlar: papka → xodim
MANUAL_TRANSFERS: dict[str, str] = {
    "Лампы": SINDOR,
    "Фонари": SINDOR,
    "LCD-планшеты": SINDOR,
    "Планшеты для документов": SINDOR,
    "Планшет для рисования": SINDOR,
    "Оснастки для печатей и штампов": SINDOR,  # Trodat
    "Подставки для ручек": SINDOR,  # стаканы для ручек
    "Ручки": SINDOR,  # Pilot va b.
    "Фоторамки": FARRUX,
}

# Ражаббоев Пулатнинг папкалари (REDISTRIBUTION.md) — bir martalik
PULAT_FOLDERS: frozenset[str] = frozenset(
    {
        "Батарейки",
        "Бегунок для документов",
        "Бокалы",
        "Бумага гофрированная цветная",
        "Бумага цветная и картон",
        "Глобусы",
        "Журналы регистрации",
        "Инкассаторские мешки",
        "Клеи различного назначения",
        "Лезвия для канцелярского ножа",
        "Лотки для бумаг",
        "Наклейки",
        "Ножницы",
        "Обложки для книг",
        "Освежители воздуха",
        "Папка файловая",
        "Папки-сумки для документов",
        "Почтовые конверты",
        "Рабочие тетради",
        "Раскраски",
        "Резинки для денег",
        "Стикеры",
        "Сублимационная / печат / бумага",
        "Типография",
        "Тушь и чернила",
        "Универсальные обложки",
        "Фото бумаги",
        "Безалкогольные напитки",
    }
)


def parse_assignments(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping: dict[str, str] = {}
    employee: str | None = None
    for line in text.splitlines():
        m_emp = re.match(r"^(.+?) — \d+ ta papka", line.strip())
        if m_emp:
            employee = m_emp.group(1).strip()
            continue
        m_folder = re.match(r"^\s+\d+\.\s+(.+)$", line)
        if m_folder and employee:
            mapping[m_folder.group(1).strip()] = employee
    return mapping


def write_summary(mapping: dict[str, str], path: Path) -> None:
  by_emp: dict[str, list[str]] = {}
  for folder, emp in sorted(mapping.items(), key=lambda x: x[0]):
      by_emp.setdefault(emp, []).append(folder)
  lines = [
      "SKLAD — HOZIRGI PAPKA TAQSIMOTI (groups.xlsx)",
      "=" * 60,
      "",
  ]
  total = 0
  for emp in sorted(by_emp.keys()):
      folders = by_emp[emp]
      total += len(folders)
      lines.append(f"{emp} — {len(folders)} ta papka")
      lines.append("-" * 40)
      for i, f in enumerate(folders, 1):
          lines.append(f"  {i:2d}. {f}")
      lines.append("")
  lines.append(f"JAMI: {len(by_emp)} xodim, {total} papka")
  path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    mapping = parse_assignments(ASSIGNMENTS)

    for folder, emp in MANUAL_TRANSFERS.items():
        if folder not in mapping:
            raise SystemExit(f"Ko'chirish: papka topilmadi: {folder}")
        mapping[folder] = emp

    rows = [
        {"Наименование": folder, "Центральный склад": emp}
        for folder, emp in sorted(mapping.items(), key=lambda x: x[0])
    ]
    df = pd.DataFrame(rows)
    df.to_excel(OUT_XLSX, index=False)
    write_summary(mapping, ASSIGNMENTS)
    print(f"Wrote {OUT_XLSX} ({len(rows)} rows)")
    for emp in sorted({r["Центральный склад"] for r in rows}):
        n = sum(1 for r in rows if r["Центральный склад"] == emp)
        print(f"  {emp}: {n}")


if __name__ == "__main__":
    main()
