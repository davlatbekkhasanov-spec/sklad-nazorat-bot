"""ASSIGNMENTS_CURRENT.txt → groups.xlsx (Пулат папкалари → Тувалов Фаррух)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS = ROOT / "ASSIGNMENTS_CURRENT.txt"
OUT_XLSX = ROOT / "groups.xlsx"

FARRUX = "Тувалов Фаррух"

# Ражаббоев Пулатнинг папкалари (REDISTRIBUTION.md)
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
    missing = sorted(PULAT_FOLDERS - set(mapping.keys()))
    if missing:
        raise SystemExit(f"Papkalar topilmadi: {missing}")

    for folder in PULAT_FOLDERS:
        mapping[folder] = FARRUX

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
