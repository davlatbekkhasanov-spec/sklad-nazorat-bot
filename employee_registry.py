"""Barcha botlar uchun yagona xodim → Telegram ID."""

from __future__ import annotations

import re

PULAT_TG_ID = 7987730795
CANONICAL_PULAT = "Rajabboev Pulat"
SHOXIJAXON_TG_ID = 6706402440
CANONICAL_SHOXIJAXON = "Ibodullaev Shoxijaxon"
OXUNJON_TG_ID = 8663341753

# Eski importlar (botlar ichidagi backward compat)
TUVALOV_FARRUX_TG_ID = PULAT_TG_ID
CANONICAL_TUVALOV = CANONICAL_PULAT
OZODBEK_TG_ID = SHOXIJAXON_TG_ID
CANONICAL_OZODBEK = CANONICAL_SHOXIJAXON

TUVALOV_LEGACY_NAMES: frozenset[str] = frozenset(
    {
        "tuvalov farrux",
        "тувалов фаррух",
        "тувалов farrux",
        "фаррух",
        "farrux",
    }
)

PULAT_NAME_KEYS: frozenset[str] = frozenset(
    {
        "rajabboev pulat",
        "rahabboev pulat",
        "ражаббоев пулат",
        "рахаббоев пулат",
        "pulat",
    }
)

OZODBEK_LEGACY_NAMES: frozenset[str] = frozenset(
    {
        "ergashev ozodbek",
        "ozodbek",
        "эргашев",
        "yadullaev umid",
        "yadullaev umidjon",
        "ядуллаев умид",
        "ядуллаев умиджон",
        "umid",
        "umidjon",
    }
)

SHOXIJAXON_NAME_KEYS: frozenset[str] = frozenset(
    {
        "ibodullaev shoxijaxon",
        "ibodullaev shohijaxon",
        "шохижахон",
        "ибодуллаев шохижахон",
        "shoxijaxon",
        "shohijaxon",
    }
)

PULAT_LEGACY_NAMES = PULAT_NAME_KEYS

TG_EMPLOYEE: dict[int, str] = {
    SHOXIJAXON_TG_ID: CANONICAL_SHOXIJAXON,
    OXUNJON_TG_ID: "Ravshanov Oxunjon",
    8547365654: "Ruziboev Sindor",
    6931958983: "Mustafoev Abdullo",
    6991673998: "Sagdullaev Yunus",
    5465963344: "Shernazarov Tolib",
    6001619806: "Samadov Tulqin",
    5732350707: "Toxirov Muslimbek",
    8440127425: "Ravshanov Ziyodullo",
    PULAT_TG_ID: CANONICAL_PULAT,
}

EMPLOYEE_NAME_ALIASES: dict[str, int] = {
    CANONICAL_SHOXIJAXON: SHOXIJAXON_TG_ID,
    "Ibodullaev Shohijaxon": SHOXIJAXON_TG_ID,
    "Ergashev Ozodbek": SHOXIJAXON_TG_ID,
    "Ozodbek": SHOXIJAXON_TG_ID,
    "Yadullaev Umidjon": SHOXIJAXON_TG_ID,
    "Yadullaev Umid": SHOXIJAXON_TG_ID,
    "Samadov To'lqin": 6001619806,
    "Samadov Tulqin": 6001619806,
    "Ravshanov Oxunjon": OXUNJON_TG_ID,
    "Oxunjon": OXUNJON_TG_ID,
    "Охунжон": OXUNJON_TG_ID,
    "Ravshanov Ziyodullo": 8440127425,
    "Ravshanov_Z_": 8440127425,
    "Mustafoev Abdullo": 6931958983,
    "Abdullo Mustafoyev": 6931958983,
    "Ruziboev Sindor": 8547365654,
    "Ruziboev sindorbek": 8547365654,
    "Toxirov Muslimbek": 5732350707,
    "Тохиров Муслимбек": 5732350707,
    "Shernazarov Tolib": 5465963344,
    "Толиб Шерназаров": 5465963344,
    "Sagdullaev Yunus": 6991673998,
    "Sagdullaev": 6991673998,
    CANONICAL_PULAT: PULAT_TG_ID,
    "Rahabboev Pulat": PULAT_TG_ID,
    "Ражаббоев Пулат": PULAT_TG_ID,
    "Рахаббоев Пулат": PULAT_TG_ID,
    "Tuvalov Farrux": PULAT_TG_ID,
    "Тувалов Фаррух": PULAT_TG_ID,
    "Тувалов Farrux": PULAT_TG_ID,
}

SHORT_NAME_ALIASES: dict[str, str] = {
    "охунжон": "Ravshanov Oxunjon",
    "oxunjon": "Ravshanov Oxunjon",
    "ravshanov oxunjon": "Ravshanov Oxunjon",
    "ravshanov_z_": "Ravshanov Ziyodullo",
    "ravshanov z": "Ravshanov Ziyodullo",
    "ziyodullo": "Ravshanov Ziyodullo",
    "abdullo mustafoyev": "Mustafoev Abdullo",
    "mustafoyev abdullo": "Mustafoev Abdullo",
    "mustafoev abdullo": "Mustafoev Abdullo",
    "ruziboev sindorbek": "Ruziboev Sindor",
    "sindorbek": "Ruziboev Sindor",
    "тохиров муслимбек": "Toxirov Muslimbek",
    "toxirov muslimbek": "Toxirov Muslimbek",
    "толиб шерназаров": "Shernazarov Tolib",
    "shernazarov tolib": "Shernazarov Tolib",
    "толиб": "Shernazarov Tolib",
    "tolib": "Shernazarov Tolib",
    "samadov tolqin": "Samadov To'lqin",
    "samadov to'lqin": "Samadov To'lqin",
    "to'lqin": "Samadov To'lqin",
    "sagdullaev": "Sagdullaev Yunus",
    "yunus": "Sagdullaev Yunus",
    "shoxijaxon": CANONICAL_SHOXIJAXON,
    "shohijaxon": CANONICAL_SHOXIJAXON,
    "ozodbek": CANONICAL_SHOXIJAXON,
    "эргашев": CANONICAL_SHOXIJAXON,
    "pulat": CANONICAL_PULAT,
    "rajabboev pulat": CANONICAL_PULAT,
    "rahabboev pulat": CANONICAL_PULAT,
    "tuvalov farrux": CANONICAL_PULAT,
    "farrux": CANONICAL_PULAT,
    "тувалов фаррух": CANONICAL_PULAT,
}

PULAT_DISPLAY_NAMES: tuple[str, ...] = (
    CANONICAL_PULAT,
    "Rahabboev Pulat",
    "Ражаббоев Пулат",
    "Рахаббоев Пулат",
)

TUVALOV_DISPLAY_NAMES: tuple[str, ...] = (
    "Tuvalov Farrux",
    "Тувалов Фаррух",
    "Тувалов Farrux",
)

SHOXIJAXON_DISPLAY_NAMES: tuple[str, ...] = (
    CANONICAL_SHOXIJAXON,
    "Ibodullaev Shohijaxon",
)

OZODBEK_DISPLAY_NAMES: tuple[str, ...] = (
    "Ergashev Ozodbek",
    "Ядуллаев Умид",
    "Yadullaev Umid",
    "Yadullaev Umidjon",
    "Ядуллаев Умиджон",
)


def _alias_key(raw: str) -> str:
    s = (raw or "").strip().lower()
    for ch in ("õ", "ö", "ó", "ô", "'", "'", "`", "ʻ", "ʼ", "’"):
        s = s.replace(ch, "o" if ch in ("õ", "ö", "ó", "ô") else "")
    s = re.sub(r"[_]+", " ", s)
    return " ".join(s.split())


def is_tuvalov_legacy(name: str) -> bool:
    return _alias_key(name) in TUVALOV_LEGACY_NAMES


def is_pulat_name(name: str) -> bool:
    key = _alias_key(name)
    return key in PULAT_NAME_KEYS or name.strip() == CANONICAL_PULAT


def is_pulat_legacy(name: str) -> bool:
    return is_pulat_name(name)


def is_tuvalov_name(name: str) -> bool:
    return is_tuvalov_legacy(name) or is_pulat_name(name)


def is_ozodbek_legacy(name: str) -> bool:
    return _alias_key(name) in OZODBEK_LEGACY_NAMES


def is_umid_legacy(name: str) -> bool:
    return is_ozodbek_legacy(name)


def is_shoxijaxon_name(name: str) -> bool:
    key = _alias_key(name)
    return key in SHOXIJAXON_NAME_KEYS or name.strip() == CANONICAL_SHOXIJAXON


def canonical_employee_name(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return raw
    if is_tuvalov_legacy(raw) or is_pulat_name(raw):
        return CANONICAL_PULAT
    if is_ozodbek_legacy(raw) or is_shoxijaxon_name(raw):
        return CANONICAL_SHOXIJAXON
    return raw


SKLAD_PULAT_NAME = "Ражаббоев Пулат"
SKLAD_SHOXIJAXON_NAME = "Ibodullaev Shoxijaxon"
SKLAD_FARRUX_NAME = SKLAD_PULAT_NAME
SKLAD_OZODBek_NAME = SKLAD_SHOXIJAXON_NAME

UMID_LEGACY_KEYS: frozenset[str] = frozenset(
    {
        "yadullaev umid",
        "yadullaev umidjon",
        "ядуллаев умид",
        "ядуллаев умиджон",
        "umid",
        "ozodbek",
        "ergashev ozodbek",
        "ibodullaev shoxijaxon",
        "shoxijaxon",
    }
)


def sklad_employee_name(name: str) -> str:
    """Sklad Excel/DB: legacy → joriy kanonik ism."""
    raw = (name or "").strip()
    if not raw:
        return raw
    if _alias_key(raw) in UMID_LEGACY_KEYS or raw in OZODBEK_DISPLAY_NAMES + SHOXIJAXON_DISPLAY_NAMES:
        return SKLAD_SHOXIJAXON_NAME
    if is_tuvalov_legacy(raw) or is_pulat_name(raw) or raw in TUVALOV_DISPLAY_NAMES + PULAT_DISPLAY_NAMES:
        return SKLAD_PULAT_NAME
    return raw


def all_team_tg_ids() -> frozenset[int]:
    return frozenset(TG_EMPLOYEE.keys())


def operator_display_name(tg_id: int) -> str:
    return TG_EMPLOYEE.get(int(tg_id), f"ID {tg_id}")


def resolve_employee_tg_id(name: str) -> int | None:
    raw = (name or "").strip()
    if not raw:
        return None
    canon = canonical_employee_name(raw)
    if canon in EMPLOYEE_NAME_ALIASES:
        return int(EMPLOYEE_NAME_ALIASES[canon])
    key = _alias_key(raw)
    if key in SHORT_NAME_ALIASES:
        canon2 = SHORT_NAME_ALIASES[key]
        return int(EMPLOYEE_NAME_ALIASES.get(canon2, 0)) or None
    for alias, tid in EMPLOYEE_NAME_ALIASES.items():
        if _alias_key(alias) == key:
            return int(tid)
    for tid, emp in TG_EMPLOYEE.items():
        if _alias_key(emp) == _alias_key(canon):
            return int(tid)
    return None


def migrate_sqlite_employee_row(
    cursor,
    *,
    default_password: str | None = None,
    now_iso: str = "",
) -> str:
    pulat_id = None
    for nm in PULAT_DISPLAY_NAMES + TUVALOV_DISPLAY_NAMES:
        cursor.execute("SELECT id FROM employees WHERE name = ?", (nm,))
        row = cursor.fetchone()
        if row:
            pulat_id = int(row["id"])
            break

    legacy_id = None
    for nm in TUVALOV_DISPLAY_NAMES:
        cursor.execute("SELECT id FROM employees WHERE name = ? AND id != ?", (nm, pulat_id or -1))
        row = cursor.fetchone()
        if row:
            legacy_id = int(row["id"])
            break

    if legacy_id and not pulat_id:
        cursor.execute(
            "UPDATE employees SET name = ?, telegram_id = ? WHERE id = ?",
            (SKLAD_PULAT_NAME, PULAT_TG_ID, legacy_id),
        )
        return "renamed"

    if legacy_id and pulat_id and legacy_id != pulat_id:
        cursor.execute("UPDATE employees SET is_active = 0 WHERE id = ?", (legacy_id,))
        cursor.execute(
            "UPDATE employees SET name = ?, telegram_id = ? WHERE id = ?",
            (SKLAD_PULAT_NAME, PULAT_TG_ID, pulat_id),
        )
        return "deactivated_legacy"

    if not pulat_id and default_password is not None:
        cursor.execute(
            """
            INSERT INTO employees (name, role, is_active, created_at, password, telegram_id)
            VALUES (?, 'employee', 1, ?, ?, ?)
            """,
            (SKLAD_PULAT_NAME, now_iso, default_password, PULAT_TG_ID),
        )
        return "inserted"

    if pulat_id:
        cursor.execute(
            "UPDATE employees SET name = ?, telegram_id = ? WHERE id = ?",
            (SKLAD_PULAT_NAME, PULAT_TG_ID, pulat_id),
        )
    return "ok"


def build_employee_tg_ids_dict() -> dict[str, int]:
    out: dict[str, int] = {}
    for display in PULAT_DISPLAY_NAMES + TUVALOV_DISPLAY_NAMES:
        out[display] = PULAT_TG_ID
    for display in SHOXIJAXON_DISPLAY_NAMES + OZODBEK_DISPLAY_NAMES:
        out[display] = SHOXIJAXON_TG_ID
    for alias, tid in EMPLOYEE_NAME_ALIASES.items():
        out[alias] = int(tid)
    for tid, emp in TG_EMPLOYEE.items():
        out[emp] = int(tid)
    return out
