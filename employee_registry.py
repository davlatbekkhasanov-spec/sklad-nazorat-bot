"""Barcha botlar uchun yagona xodim → Telegram ID."""

from __future__ import annotations

import re

PULAT_TG_ID = 7987730795
CANONICAL_PULAT = "Rajabboev Pulat"
SHOXIJAXON_TG_ID = 8922128075
CANONICAL_SHOXIJAXON = "Ibodullaev Shoxijaxon"
OXUNJON_TG_ID = 8663341753
SINDOR_LEGACY_TG_ID = 8547365654
DILNOZA_TG_ID = 1174833646
CANONICAL_DILNOZA = "Azatova Dilnoza"

ABDULLO_TG_ID = 6931958983
CANONICAL_ABDULLO = "Mustafoev Abdullo"
DIYORBEK_LEGACY_TG_ID = 5603088321
ABDULLO_LEGACY_TG_ID = ABDULLO_TG_ID
DIYORBEK_TG_ID = ABDULLO_TG_ID
CANONICAL_DIYORBEK = CANONICAL_ABDULLO
DAURBEK_TG_ID = 1800401851
CANONICAL_DAURBEK = "Anvarov Daurbek"
TULQIN_LEGACY_TG_ID = 6001619806

# Eski importlar (botlar ichidagi backward compat)
TUVALOV_FARRUX_TG_ID = PULAT_TG_ID
CANONICAL_TUVALOV = CANONICAL_PULAT
OZODBEK_TG_ID = SHOXIJAXON_TG_ID
CANONICAL_OZODBEK = CANONICAL_SHOXIJAXON

# Eski Telegram akkauntlar → joriy ID (Shoxijaxon yangi: 8922128075)
LEGACY_TG_ID_MAP: dict[int, int] = {
    6706402440: SHOXIJAXON_TG_ID,
    924612402: SHOXIJAXON_TG_ID,
    7844168817: SHOXIJAXON_TG_ID,
    7703650930: PULAT_TG_ID,
    5412958249: OXUNJON_TG_ID,
    8547365654: DILNOZA_TG_ID,
    5603088321: ABDULLO_TG_ID,
    6001619806: DAURBEK_TG_ID,
}


def canonical_tg_id(telegram_id: int | None) -> int | None:
    if telegram_id is None:
        return None
    u = int(telegram_id)
    return LEGACY_TG_ID_MAP.get(u, u)


def tg_id_lookup_variants(telegram_id: int | None) -> frozenset[int]:
    """Bir xodimning barcha Telegram ID lari (eski + joriy)."""
    if telegram_id is None:
        return frozenset()
    u = int(telegram_id)
    canon = canonical_tg_id(u)
    ids: set[int] = {u}
    if canon is not None:
        ids.add(int(canon))
    for old, new in LEGACY_TG_ID_MAP.items():
        if u in (old, new) or canon in (old, new):
            ids.add(int(old))
            ids.add(int(new))
    return frozenset(ids)


def same_telegram_person(stored_id: int | None, user_id: int | None) -> bool:
    if stored_id is None or user_id is None:
        return stored_id is user_id
    return int(stored_id) in tg_id_lookup_variants(user_id)


def is_registered_team_member(telegram_id: int | None) -> bool:
    if telegram_id is None:
        return False
    u = int(telegram_id)
    if u in TG_EMPLOYEE or u in LEGACY_TG_ID_MAP:
        return True
    return canonical_tg_id(u) in TG_EMPLOYEE


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

ABDULLO_LEGACY_NAMES: frozenset[str] = frozenset(
    {
        "mustafoev abdullo",
        "abdullo mustafoev",
        "abdullo mustafoyev",
        "mustafoyev abdullo",
        "abdullo",
        "мустаfoev abdullo",
        "мустаfoев абдулло",
        "абдулло",
    }
)

DIYORBEK_NAME_KEYS: frozenset[str] = frozenset(
    {
        "zaynitdinov diyorbek",
        "diyorbek",
        "зайнетдинов дiyorbek",
        "дiyorbek",
    }
)

PULAT_LEGACY_NAMES = PULAT_NAME_KEYS

SINDOR_LEGACY_NAMES: frozenset[str] = frozenset(
    {
        "ruziboev sindor",
        "ruziboev sindorbek",
        "sindorbek",
        "sindor",
        "рузибоев синдор",
        "рузибоев синдорбек",
    }
)

DILNOZA_NAME_KEYS: frozenset[str] = frozenset(
    {
        "azatova dilnoza",
        "dilnoza",
        "азатова дилноза",
        "дилноза",
    }
)

TG_EMPLOYEE: dict[int, str] = {
    SHOXIJAXON_TG_ID: CANONICAL_SHOXIJAXON,
    OXUNJON_TG_ID: "Ravshanov Oxunjon",
    DILNOZA_TG_ID: CANONICAL_DILNOZA,
    ABDULLO_TG_ID: CANONICAL_ABDULLO,
    6991673998: "Sagdullaev Yunus",
    5465963344: "Shernazarov Tolib",
    DAURBEK_TG_ID: CANONICAL_DAURBEK,
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
    CANONICAL_DAURBEK: DAURBEK_TG_ID,
    "Anvarov Daurbek": DAURBEK_TG_ID,
    "Samadov To'lqin": DAURBEK_TG_ID,
    "Samadov Tulqin": DAURBEK_TG_ID,
    "Ravshanov Oxunjon": OXUNJON_TG_ID,
    "Oxunjon": OXUNJON_TG_ID,
    "Охунжон": OXUNJON_TG_ID,
    "Ravshanov Ziyodullo": 8440127425,
    "Ravshanov_Z_": 8440127425,
    CANONICAL_ABDULLO: ABDULLO_TG_ID,
    "Mustafoev Abdullo": ABDULLO_TG_ID,
    "Abdullo Mustafoyev": ABDULLO_TG_ID,
    "Zaynitdinov Diyorbek": ABDULLO_TG_ID,
    CANONICAL_DILNOZA: DILNOZA_TG_ID,
    "Ruziboev Sindor": DILNOZA_TG_ID,
    "Ruziboev sindorbek": DILNOZA_TG_ID,
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
    "abdullo mustafoyev": CANONICAL_ABDULLO,
    "mustafoyev abdullo": CANONICAL_ABDULLO,
    "mustafoev abdullo": CANONICAL_ABDULLO,
    "abdullo": CANONICAL_ABDULLO,
    "diyorbek": CANONICAL_ABDULLO,
    "zaynitdinov diyorbek": CANONICAL_ABDULLO,
    "ruziboev sindorbek": CANONICAL_DILNOZA,
    "sindorbek": CANONICAL_DILNOZA,
    "sindor": CANONICAL_DILNOZA,
    "dilnoza": CANONICAL_DILNOZA,
    "azatova dilnoza": CANONICAL_DILNOZA,
    "тохиров муслимбек": "Toxirov Muslimbek",
    "toxirov muslimbek": "Toxirov Muslimbek",
    "толиб шерназаров": "Shernazarov Tolib",
    "shernazarov tolib": "Shernazarov Tolib",
    "толиб": "Shernazarov Tolib",
    "tolib": "Shernazarov Tolib",
    "samadov tolqin": CANONICAL_DAURBEK,
    "samadov to'lqin": CANONICAL_DAURBEK,
    "to'lqin": CANONICAL_DAURBEK,
    "anvarov daurbek": CANONICAL_DAURBEK,
    "daurbek": CANONICAL_DAURBEK,
    "даврбек": CANONICAL_DAURBEK,
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


def is_abdullo_legacy(name: str) -> bool:
    return _alias_key(name) in ABDULLO_LEGACY_NAMES


def is_diyorbek_name(name: str) -> bool:
    key = _alias_key(name)
    return key in DIYORBEK_NAME_KEYS or name.strip() == CANONICAL_DIYORBEK


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


def is_sindor_legacy(name: str) -> bool:
    return _alias_key(name) in SINDOR_LEGACY_NAMES


def is_dilnoza_name(name: str) -> bool:
    key = _alias_key(name)
    return key in DILNOZA_NAME_KEYS or name.strip() == CANONICAL_DILNOZA


def canonical_employee_name(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return raw
    if is_sindor_legacy(raw) or is_dilnoza_name(raw):
        return CANONICAL_DILNOZA
    if is_abdullo_legacy(raw) or is_diyorbek_name(raw):
        return CANONICAL_DIYORBEK
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
    return frozenset(TG_EMPLOYEE.keys()) | frozenset(LEGACY_TG_ID_MAP.keys())


def operator_display_name(tg_id: int) -> str:
    u = int(tg_id)
    if u in TG_EMPLOYEE:
        return TG_EMPLOYEE[u]
    canon = canonical_tg_id(u)
    if canon and canon in TG_EMPLOYEE:
        return TG_EMPLOYEE[canon]
    return f"ID {tg_id}"


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
