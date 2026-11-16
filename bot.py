import asyncio
import logging
import os
import re
import secrets
import sqlite3
from datetime import datetime

from time_util import now_str
from typing import Optional

import pandas as pd
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

from persist_data import bootstrap_persistence, persistence_status_line, resolve_db_path

from bot_ui import (
    FOLDER_PAGE_SIZE,
    build_dashboard_text,
    dashboard_keyboard,
    folder_list_keyboard,
    format_submission_group_html,
    he,
    inline_yes_no,
)
from report_card import build_report_card_data, render_report_card_png
from texts import (
    BTN_ACTIVE_CHECKS_ALL,
    BTN_ADD_EMP,
    BTN_ADD_EMP_ALL,
    BTN_ADD_FOLDER,
    BTN_ADD_FOLDER_ALL,
    BTN_ALL_EMP,
    BTN_ALL_EMP_ALL,
    BTN_ALL_FOLDERS,
    BTN_ALL_FOLDERS_ALL,
    BTN_ASSIGN,
    BTN_ASSIGN_ALL,
    BTN_ASSIGNMENTS,
    BTN_ASSIGNMENTS_ALL,
    BTN_CANCEL,
    BTN_CANCEL_ALL,
    BTN_CLOSE_CYCLE,
    BTN_CLOSE_CYCLE_ALL,
    BTN_COUNT,
    BTN_COUNT_ALL,
    BTN_CYCLE_STATUS,
    BTN_CYCLE_STATUS_ALL,
    BTN_DEL_REPORT,
    BTN_DEL_REPORT_ALL,
    BTN_EXCEL,
    BTN_EXCEL_ALL,
    BTN_GEN_PASS,
    BTN_GEN_PASS_ALL,
    BTN_HELP,
    BTN_HELP_ALL,
    BTN_LOGIN,
    BTN_LOGIN_ALL,
    BTN_LOGOUT,
    BTN_LOGOUT_ALL,
    BTN_MARK,
    BTN_MARK_ALL,
    BTN_MARK_ALL_BTN_ALL,
    BTN_MARK_ALL_SET,
    BTN_MARK_DONE,
    BTN_MARK_DONE_ALL,
    BTN_MARK_FOLDERS,
    BTN_MY_FOLDERS,
    BTN_MY_FOLDERS_ALL,
    BTN_MY_STATUS,
    BTN_SUBMIT_CHECK,
    BTN_NO,
    BTN_OPEN_CYCLE,
    BTN_OPEN_CYCLE_ALL,
    BTN_PASS_LIST,
    BTN_PASS_LIST_ALL,
    BTN_REMAINING,
    BTN_REMAINING_ALL,
    BTN_STATUS_ALL,
    BTN_TODAY,
    BTN_TODAY_ALL,
    BTN_YES,
    EMPLOYEE_MENU_BUTTONS,
    is_cancel,
    is_no,
    is_yes,
)
from yordamchi_push import (
    push_session_end_background,
    push_session_start_background,
    push_to_yordamchi_hub,
    push_to_yordamchi_hub_background,
    today_iso,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
EXCEL_FILE = os.getenv("EXCEL_FILE", "groups.xlsx").strip()
_DB_BOOT = bootstrap_persistence(
    resolve_db_path(default_filename="sklad_bot.db"),
    legacy_names=("sklad_bot.db",),
)
DB_PATH = _DB_BOOT["db_path"]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi. .env faylni tekshiring.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID topilmadi. .env faylni tekshiring.")
if not GROUP_ID:
    raise ValueError("GROUP_ID topilmadi. .env faylni tekshiring.")


from employee_registry import (
    CANONICAL_DILNOZA,
    CANONICAL_PULAT,
    DILNOZA_TG_ID,
    SHOXIJAXON_TG_ID,
    SKLAD_PULAT_NAME,
    migrate_sqlite_employee_row,
    sklad_employee_name,
)

# Faqat groups.xlsx dagi sanalovchi xodimlar (Sagdullaev — papka yo'q, ro'yxatdan chiqarilgan)
ACTIVE_SKLAD_EMPLOYEE_NAMES: frozenset[str] = frozenset(
    {
        "Ражаббоев Пулат",
        "Ibodullaev Shoxijaxon",
        "Тохиров Муслимбек",
        "Равшанов Зиёдулло",
        "Мустафоев Абдулло",
        "Azatova Dilnoza",
    }
)

DEFAULT_PASSWORDS = {
    name: pwd
    for name, pwd in {
        "Ражаббоев Пулат": "431205",
        "Ibodullaev Shoxijaxon": "582614",
        "Тохиров Муслимбек": "295731",
        "Равшанов Зиёдулло": "816452",
        "Мустафоев Абдулло": "540927",
        "Azatova Dilnoza": "673184",
    }.items()
    if name in ACTIVE_SKLAD_EMPLOYEE_NAMES
}

LEGACY_INACTIVE_EMPLOYEE_NAMES: tuple[str, ...] = (
    "Сагдуллаев Юнус",
    "Sagdullaev Yunus",
    "Tuvalov Farrux",
    "Тувалов Фаррух",
    "Тувалов Farrux",
    "Rajabboev Pulat",
    "Rahabboev Pulat",
    "Рахаббоев Пулат",
    "Ядуллаев Умид",
    "Yadullaev Umid",
    "Yadullaev Umidjon",
    "Ядуллаев Умиджон",
    "Ergashev Ozodbek",
    "Ozodbek",
    "Samadov To'lqin",
    "Samadov Tulqin",
    "Anvarov Daurbek",
    "Рузибоев Синдор",
    "Ruziboev Sindor",
    "Ruziboev sindorbek",
    "Ruziboev Sindorbek",
    "Zaynitdinov Diyorbek",
    "Mustafoev Abdullo",
    "Abdullo Mustafoyev",
    "Ravshanov Oxunjon",
    "Oxunjon",
    "Охунжон",
    "Shernazarov Tolib",
)

SKLAD_DB_CANONICAL_NAMES: dict[str, str] = {
    "Ravshanov Ziyodullo": "Равшанов Зиёдулло",
    "Mustafoev Abdullo": "Мустафоев Абдулло",
    "Rajabboev Pulat": "Ражаббоев Пулат",
    "Rahabboev Pulat": "Ражаббоев Пулат",
    "Toxirov Muslimbek": "Тохиров Муслимбек",
}


# ==========================================
# HELPERS
# ==========================================
def use_group_report_card() -> bool:
    return os.getenv("GROUP_REPORT_CARD", "1").strip().lower() not in ("0", "false", "no", "off")


def get_submitted_folder_names(employee_id: int, cycle_id: int) -> list[str]:
    cursor.execute(
        """
        SELECT f.name
        FROM submissions s
        JOIN folders f ON f.id = s.folder_id
        WHERE s.employee_id = ? AND s.cycle_id = ?
        ORDER BY s.submitted_at ASC, s.id ASC
        """,
        (employee_id, cycle_id),
    )
    return [row["name"] for row in cursor.fetchall()]


async def send_submission_to_group(
    bot: Bot,
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
    counted_folders: list[str],
) -> str:
    """Guruhga PNG kartochka (yoki matn fallback). Qaytadi: xodim uchun qisqa xabar."""
    if use_group_report_card():
        try:
            card = build_report_card_data(
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
                counted_folders=counted_folders,
            )
            png = render_report_card_png(card)
            photo = BufferedInputFile(png, filename="hisobot.png")
            await bot.send_photo(GROUP_ID, photo)
            return "Карточка отправлена в группу."
        except Exception:
            pass  # matn fallback

    report_text = format_submission_group_html(
        cycle_title,
        employee_name,
        folder_name,
        counted_ok=counted_ok,
        location_ok=location_ok,
        wrong_location_count=wrong_location_count,
        fixed_now=fixed_now,
        comment=comment,
        submitted_at=submitted_at,
        day_done=day_done,
        day_total=day_total,
    )
    try:
        await bot.send_message(GROUP_ID, report_text, parse_mode=ParseMode.HTML)
        return "Отправлено в группу."
    except Exception as e:
        return f"⚠️ Не удалось отправить в группу: {e}"


def clean_text(value) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[◼▪•●■\-\s]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_private(message: Message) -> bool:
    return message.chat.type == ChatType.PRIVATE


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_YES), KeyboardButton(text=BTN_NO)]],
        resize_keyboard=True
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True
    )


def login_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_LOGIN)]],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_EMP), KeyboardButton(text=BTN_ALL_EMP)],
            [KeyboardButton(text=BTN_GEN_PASS), KeyboardButton(text=BTN_PASS_LIST)],
            [KeyboardButton(text=BTN_ADD_FOLDER), KeyboardButton(text=BTN_ALL_FOLDERS)],
            [KeyboardButton(text=BTN_ASSIGN), KeyboardButton(text=BTN_ASSIGNMENTS)],
            [KeyboardButton(text=BTN_EXCEL)],
            [KeyboardButton(text=BTN_OPEN_CYCLE), KeyboardButton(text=BTN_CLOSE_CYCLE)],
            [KeyboardButton(text=BTN_REMAINING), KeyboardButton(text=BTN_CYCLE_STATUS)],
            [KeyboardButton(text=BTN_DEL_REPORT)],
            [KeyboardButton(text=BTN_MY_FOLDERS), KeyboardButton(text=BTN_ACTIVE_CHECKS)],
            [KeyboardButton(text=BTN_SUBMIT_CHECK), KeyboardButton(text=BTN_MY_STATUS)],
            [KeyboardButton(text=BTN_LOGOUT), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True
    )


def employee_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TODAY)],
            [KeyboardButton(text=BTN_COUNT)],
            [KeyboardButton(text=BTN_MARK)],
            [KeyboardButton(text=BTN_HELP), KeyboardButton(text=BTN_LOGOUT)],
        ],
        resize_keyboard=True,
    )


def mark_folder_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MARK_ALL)],
            [KeyboardButton(text=BTN_MARK_DONE)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def count_submitted_folders(employee_id: int, cycle_id: int) -> int:
    cursor.execute(
        "SELECT COUNT(*) AS c FROM submissions WHERE employee_id = ? AND cycle_id = ?",
        (employee_id, cycle_id),
    )
    return int(cursor.fetchone()["c"] or 0)


def count_marked_folders(employee_id: int, cycle_id: int) -> int:
    cursor.execute(
        "SELECT COUNT(*) AS c FROM folder_marks WHERE employee_id = ? AND cycle_id = ?",
        (employee_id, cycle_id),
    )
    return int(cursor.fetchone()["c"] or 0)


def get_sanash_queue_folders(employee_id: int, cycle_id: int) -> list:
    """Санаш рўйхати: бириктирилган, ҳали саналмаган ва белгиланмаган."""
    cursor.execute(
        """
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ?
          AND f.id NOT IN (
              SELECT folder_id FROM submissions
              WHERE employee_id = ? AND cycle_id = ?
          )
          AND f.id NOT IN (
              SELECT folder_id FROM folder_marks
              WHERE employee_id = ? AND cycle_id = ?
          )
        ORDER BY f.name
        """,
        (employee_id, employee_id, cycle_id, employee_id, cycle_id),
    )
    return cursor.fetchall()


def employee_work_stats(employee_id: int, cycle_id: int) -> dict:
    assigned = get_employee_assignment_folders(employee_id)
    total = len(assigned)
    submitted = count_submitted_folders(employee_id, cycle_id)
    marked = count_marked_folders(employee_id, cycle_id)
    done = submitted + marked
    to_sanash = len(get_sanash_queue_folders(employee_id, cycle_id))
    return {"total": total, "submitted": submitted, "marked": marked, "to_sanash": to_sanash, "done": done}


async def send_dashboard(message: Message, employee, cycle, *, edit_message: Optional[Message] = None):
    stats = employee_work_stats(employee["id"], cycle["id"])
    text = build_dashboard_text(
        employee_name=employee["name"],
        cycle_title=cycle["title"],
        total=stats["total"],
        to_sanash=stats["to_sanash"],
        done=stats["done"],
    )
    kb = dashboard_keyboard()
    if edit_message:
        await edit_message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def show_folder_picker(
    target: Message,
    employee,
    cycle,
    *,
    mode: str,
    page: int = 0,
    edit: bool = False,
):
    """mode: p = sanash, m = belgilash"""
    if mode == "p":
        rows = get_sanash_queue_folders(employee["id"], cycle["id"])
        title = "📝 <b>Пересчёт</b>"
        assigned_n = len(get_employee_assignment_folders(employee["id"]))
        if assigned_n == 0:
            empty_hint = (
                "⚠️ Вам не назначены папки по Excel.\n"
                "Скажите админу: 📥 Импорт Excel."
            )
        elif not rows:
            empty_hint = "✅ Всё готово — папок для пересчёта не осталось."
        else:
            empty_hint = ""
        pick_prefix = "p"
        mark_all = False
    else:
        rows = get_sanash_queue_folders(employee["id"], cycle["id"])
        title = "📌 <b>Отметить как готовые</b> <i>(необязательно)</i>"
        empty_hint = "✅ Папок для пересчёта или отметки не осталось."
        pick_prefix = "m"
        mark_all = True

    if not rows:
        if edit:
            try:
                await target.edit_text(empty_hint, reply_markup=employee_menu())
            except Exception:
                await target.answer(empty_hint, reply_markup=employee_menu())
        else:
            await target.answer(empty_hint, reply_markup=employee_menu())
        return

    start = page * FOLDER_PAGE_SIZE
    text = (
        f"{title}\n"
        f"{he(cycle['title'])}\n\n"
        f"Выберите ({start + 1}–{min(start + FOLDER_PAGE_SIZE, len(rows))} / {len(rows)}):\n"
    )
    kb = folder_list_keyboard(rows, page, pick_prefix, show_mark_all=mark_all)
    if edit:
        await target.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await target.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


def current_menu(user_id: int):
    return admin_menu() if is_admin(user_id) else employee_menu()


def get_marked_folders(employee_id: int, cycle_id: int) -> list:
    cursor.execute(
        """
        SELECT f.id, f.name
        FROM folder_marks m
        JOIN folders f ON f.id = m.folder_id
        WHERE m.employee_id = ? AND m.cycle_id = ?
        ORDER BY f.name
        """,
        (employee_id, cycle_id),
    )
    return cursor.fetchall()


def get_employee_assignment_folders(employee_id: int) -> list:
    cursor.execute(
        """
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ?
        ORDER BY f.name
        """,
        (employee_id,),
    )
    return cursor.fetchall()


def is_folder_assigned_to_employee(employee_id: int, folder_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM assignments WHERE employee_id = ? AND folder_id = ?",
        (employee_id, folder_id),
    )
    return cursor.fetchone() is not None


def get_folder_for_sanash(employee_id: int, cycle_id: int, folder_id: int):
    cursor.execute(
        """
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ? AND f.id = ?
          AND f.id NOT IN (
              SELECT folder_id FROM submissions
              WHERE employee_id = ? AND cycle_id = ?
          )
          AND f.id NOT IN (
              SELECT folder_id FROM folder_marks
              WHERE employee_id = ? AND cycle_id = ?
          )
        """,
        (employee_id, folder_id, employee_id, cycle_id, employee_id, cycle_id),
    )
    return cursor.fetchone()


def mark_all_assignment_folders(employee_id: int, cycle_id: int) -> int:
    rows = get_sanash_queue_folders(employee_id, cycle_id)
    added = 0
    for row in rows:
        try:
            cursor.execute(
                "INSERT INTO folder_marks (cycle_id, employee_id, folder_id, marked_at) VALUES (?, ?, ?, ?)",
                (cycle_id, employee_id, row["id"], now_str()),
            )
            conn.commit()
            added += 1
        except sqlite3.IntegrityError:
            pass
    return added


def parse_folder_id_list(text: str) -> list[int]:
    ids = []
    for part in re.split(r"[,;\s]+", clean_text(text)):
        if part.isdigit():
            ids.append(int(part))
    return ids


def format_submission_group_text(cycle_title: str, employee_name: str, folder_name: str, row) -> str:
    counted_ok = row["counted_ok"]
    location_ok = row["location_ok"]
    wrong_location_count = row["wrong_location_count"] or 0
    fixed_now = row["fixed_now"]
    comment = row["comment"] or "-"
    submitted_at = row["submitted_at"]

    report_text = (
        f"📦 Завершённый отчёт склада\n\n"
        f"Цикл: {cycle_title}\n"
        f"Сотрудник: {employee_name}\n"
        f"Папка: {folder_name}\n"
        f"Остаток верный: {'Да' if counted_ok else 'Нет'}\n"
        f"Место хранения верное: {'Да' if location_ok else 'Нет'}\n"
    )
    if location_ok == 0:
        report_text += (
            f"Ошибочных мест: {wrong_location_count}\n"
            f"Исправлено: {'Да' if fixed_now else 'Нет'}\n"
        )
    report_text += f"Комментарий: {comment}\nВремя: {submitted_at}"
    return report_text


def build_admin_remaining_folders_report(cycle) -> list[str]:
    cycle_id = cycle["id"]
    cycle_title = cycle["title"]

    cursor.execute(
        """
        SELECT DISTINCT e.id, e.name
        FROM employees e
        JOIN assignments a ON a.employee_id = e.id
        ORDER BY e.name
        """
    )
    employees = cursor.fetchall()
    if not employees:
        return ["Никому не назначены папки (Excel)."]

    header = (
        f"📂 КОНТРОЛЬ (активная проверка)\n\n"
        f"Цикл: {cycle_title}\n"
        f"📝 = нужен пересчёт (отчёт в группу ещё не ушёл)\n\n"
    )
    parts = []
    current = header

    for emp in employees:
        pending = get_sanash_queue_folders(emp["id"], cycle_id)
        block = f"🔹 {emp['name']}\n"
        if pending:
            block += f"   📝 Нужен пересчёт ({len(pending)}):\n"
            for row in pending:
                block += f"      • {row['name']}\n"
        else:
            block += "   ✅ Готово\n"
        block += "\n"

        if len(current) + len(block) > 3500:
            parts.append(current)
            current = block
        else:
            current += block

    if current.strip():
        parts.append(current)
    return parts


def chunk_text(text: str, limit: int = 3500) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    current = ""
    for line in text.splitlines(True):
        if len(current) + len(line) > limit:
            parts.append(current)
            current = line
        else:
            current += line
    if current:
        parts.append(current)
    return parts


# ==========================================
# DATABASE
# ==========================================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()


def table_columns(table_name: str) -> set:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def ensure_column(table_name: str, column_name: str, sql_def: str):
    cols = table_columns(table_name)
    if column_name not in cols:
        # SQLite ALTER TABLE орқали UNIQUE qo‘shib bo‘lmaydi
        safe_sql_def = sql_def.replace(" UNIQUE", "")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {safe_sql_def}")


def setup_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    ensure_column("employees", "telegram_id", "INTEGER")
    ensure_column("employees", "password", "TEXT")
    ensure_column("employees", "role", "TEXT NOT NULL DEFAULT 'employee'")
    ensure_column("employees", "is_active", "INTEGER NOT NULL DEFAULT 1")
    ensure_column("employees", "created_at", "TEXT NOT NULL DEFAULT ''")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    ensure_column("folders", "created_at", "TEXT NOT NULL DEFAULT ''")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        folder_id INTEGER NOT NULL,
        UNIQUE(employee_id, folder_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        folder_id INTEGER NOT NULL,
        counted_ok INTEGER NOT NULL,
        location_ok INTEGER NOT NULL,
        wrong_location_count INTEGER NOT NULL DEFAULT 0,
        fixed_now INTEGER,
        comment TEXT,
        submitted_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_sessions (
        telegram_id INTEGER PRIMARY KEY,
        employee_id INTEGER NOT NULL,
        logged_in_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS folder_marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        folder_id INTEGER NOT NULL,
        marked_at TEXT NOT NULL,
        UNIQUE(cycle_id, folder_id),
        UNIQUE(cycle_id, employee_id, folder_id)
    )
    """)

    ensure_column("submissions", "posted_to_group", "INTEGER NOT NULL DEFAULT 0")

    # telegram_id uchun unique index
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_telegram_id
    ON employees(telegram_id)
    WHERE telegram_id IS NOT NULL
    """)

    conn.commit()

    cursor.execute(
        "UPDATE employees SET created_at = ? WHERE created_at = '' OR created_at IS NULL",
        (now_str(),)
    )
    cursor.execute(
        "UPDATE folders SET created_at = ? WHERE created_at = '' OR created_at IS NULL",
        (now_str(),)
    )
    conn.commit()

    import_default_employees()
    ensure_default_passwords()
    migrate_sqlite_employee_row(
        cursor,
        default_password=DEFAULT_PASSWORDS.get("Ражаббоев Пулат")
        or DEFAULT_PASSWORDS.get(CANONICAL_PULAT, "431205"),
        now_iso=now_str(),
    )
    _migrate_shoxijaxon_telegram(cursor)
    _migrate_shoxijaxon_assignments(cursor)
    _migrate_canonical_db_names(cursor)
    _migrate_dilnoza_replaces_sindor(cursor)
    deactivated = _migrate_deactivate_legacy_staff(cursor)
    if deactivated:
        logging.info("Deactivated legacy/inactive employees: %s", ", ".join(deactivated))
    conn.commit()


def _migrate_canonical_db_names(cursor) -> None:
    for old, new in SKLAD_DB_CANONICAL_NAMES.items():
        cursor.execute("SELECT id FROM employees WHERE name = ? LIMIT 1", (new,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE employees SET is_active = 0, telegram_id = NULL WHERE name = ?",
                (old,),
            )
            continue
        cursor.execute(
            "UPDATE employees SET name = ? WHERE name = ?",
            (new, old),
        )


def _migrate_dilnoza_replaces_sindor(cursor) -> None:
    """Sindor papkalari → Azatova Dilnoza; Sindor deactivate."""
    canon = CANONICAL_DILNOZA
    sindor_names = (
        "Рузибоев Синдор",
        "Ruziboev Sindor",
        "Ruziboev sindorbek",
        "Ruziboev Sindorbek",
    )

    cursor.execute("SELECT id FROM employees WHERE name = ? LIMIT 1", (canon,))
    dil_row = cursor.fetchone()
    if not dil_row:
        pwd = DEFAULT_PASSWORDS.get(canon, "673184")
        cursor.execute(
            """
            INSERT INTO employees (name, role, is_active, created_at, password, telegram_id)
            VALUES (?, 'employee', 1, ?, ?, ?)
            """,
            (canon, now_str(), pwd, DILNOZA_TG_ID),
        )
        dil_id = int(cursor.lastrowid)
    else:
        dil_id = int(dil_row["id"])
        cursor.execute(
            "UPDATE employees SET is_active = 1, password = COALESCE(NULLIF(password, ''), ?), telegram_id = ? WHERE id = ?",
            (DEFAULT_PASSWORDS.get(canon, "673184"), DILNOZA_TG_ID, dil_id),
        )

    for old_name in sindor_names:
        cursor.execute("SELECT id FROM employees WHERE name = ? AND id != ?", (old_name, dil_id))
        for row in cursor.fetchall():
            old_id = int(row["id"])
            cursor.execute(
                """
                DELETE FROM assignments
                WHERE employee_id = ? AND folder_id IN (
                    SELECT folder_id FROM assignments WHERE employee_id = ?
                )
                """,
                (old_id, dil_id),
            )
            cursor.execute(
                "UPDATE assignments SET employee_id = ? WHERE employee_id = ?",
                (dil_id, old_id),
            )
            cursor.execute(
                "UPDATE auth_sessions SET employee_id = ? WHERE employee_id = ?",
                (dil_id, old_id),
            )
            cursor.execute(
                "UPDATE employees SET is_active = 0, telegram_id = NULL WHERE id = ?",
                (old_id,),
            )


def _migrate_deactivate_legacy_staff(cursor) -> list[str]:
    """Eski nomlar va groups.xlsx ro'yxatida yo'q xodimlarni o'chiradi (is_active=0)."""
    changed: list[str] = []

    for name in LEGACY_INACTIVE_EMPLOYEE_NAMES:
        cursor.execute(
            "UPDATE employees SET is_active = 0, telegram_id = NULL WHERE name = ? AND is_active = 1",
            (name,),
        )
        if cursor.rowcount:
            changed.append(name)

    cursor.execute("SELECT id, name FROM employees WHERE is_active = 1")
    for row in cursor.fetchall():
        raw = (row["name"] or "").strip()
        canon = sklad_employee_name(raw)
        if canon in ACTIVE_SKLAD_EMPLOYEE_NAMES or raw in ACTIVE_SKLAD_EMPLOYEE_NAMES:
            continue
        cursor.execute(
            "UPDATE employees SET is_active = 0, telegram_id = NULL WHERE id = ?",
            (int(row["id"]),),
        )
        changed.append(raw)
    return changed


def _migrate_shoxijaxon_assignments(cursor) -> int:
    """Umid/Yadullaev/Ozodbek papkalarini Ibodullaev Shoxijaxon ga ko'chirish."""
    from employee_registry import SKLAD_SHOXIJAXON_NAME

    canon = SKLAD_SHOXIJAXON_NAME
    legacy_names = (
        "Ядуллаев Умид",
        "Yadullaev Umid",
        "Yadullaev Umidjon",
        "Ядуллаев Умиджон",
    )

    cursor.execute("SELECT id FROM employees WHERE name = ? AND is_active = 1 LIMIT 1", (canon,))
    oz_row = cursor.fetchone()
    if not oz_row:
        return 0
    oz_id = int(oz_row["id"])

    moved = 0
    for old_name in legacy_names:
        cursor.execute(
            "SELECT id FROM employees WHERE name = ? AND id != ?",
            (old_name, oz_id),
        )
        for row in cursor.fetchall():
            old_id = int(row["id"])
            cursor.execute(
                """
                DELETE FROM assignments
                WHERE employee_id = ? AND folder_id IN (
                    SELECT folder_id FROM assignments WHERE employee_id = ?
                )
                """,
                (old_id, oz_id),
            )
            cursor.execute(
                "UPDATE assignments SET employee_id = ? WHERE employee_id = ?",
                (oz_id, old_id),
            )
            moved += cursor.rowcount
            cursor.execute(
                "UPDATE employees SET is_active = 0, telegram_id = NULL WHERE id = ?",
                (old_id,),
            )
    return moved


def _migrate_shoxijaxon_telegram(cursor) -> None:
    """Eski TG → Ibodullaev Shoxijaxon (8922128075)."""
    new_tg = 8922128075
    old_tgs = (924612402, 7844168817, 6706402440)
    canon = "Ibodullaev Shoxijaxon"
    legacy_names = (
        "Ядуллаев Умид",
        "Yadullaev Umid",
        "Yadullaev Umidjon",
        "Ergashev Ozodbek",
        "Ibodullaev Shoxijaxon",
        canon,
    )

    for old_tg in old_tgs:
        cursor.execute("UPDATE employees SET telegram_id = NULL WHERE telegram_id = ?", (old_tg,))

    target_id = None
    for old in legacy_names:
        cursor.execute("SELECT id FROM employees WHERE name = ? LIMIT 1", (old,))
        row = cursor.fetchone()
        if row:
            target_id = int(row["id"])
            break

    if target_id is None:
        return

    cursor.execute(
        "UPDATE employees SET telegram_id = NULL WHERE telegram_id = ? AND id != ?",
        (new_tg, target_id),
    )
    cursor.execute(
        "UPDATE employees SET name = ?, telegram_id = ? WHERE id = ?",
        (canon, new_tg, target_id),
    )

    for old in legacy_names:
        if old == canon:
            continue
        cursor.execute(
            "UPDATE employees SET is_active = 0, telegram_id = NULL WHERE name = ? AND id != ?",
            (old, target_id),
        )


def get_employee_by_tg(telegram_id: int) -> Optional[sqlite3.Row]:
    from employee_registry import tg_id_lookup_variants

    for tid in sorted(tg_id_lookup_variants(telegram_id)):
        cursor.execute("SELECT * FROM employees WHERE telegram_id = ?", (tid,))
        row = cursor.fetchone()
        if row:
            return row
    return None


def get_employee_by_id(employee_id: int) -> Optional[sqlite3.Row]:
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    return cursor.fetchone()


def get_folder_by_id(folder_id: int) -> Optional[sqlite3.Row]:
    cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
    return cursor.fetchone()


def get_logged_in_employee(telegram_id: int) -> Optional[sqlite3.Row]:
    cursor.execute("""
        SELECT e.*
        FROM auth_sessions s
        JOIN employees e ON e.id = s.employee_id
        WHERE s.telegram_id = ?
    """, (telegram_id,))
    return cursor.fetchone()


def get_active_cycle() -> Optional[sqlite3.Row]:
    cursor.execute("SELECT * FROM cycles WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()


def get_latest_cycle() -> Optional[sqlite3.Row]:
    cursor.execute("SELECT * FROM cycles ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()


def get_cycle_for_reports() -> Optional[sqlite3.Row]:
    active = get_active_cycle()
    return active if active else get_latest_cycle()


def set_session(telegram_id: int, employee_id: int):
    cursor.execute(
        "INSERT OR REPLACE INTO auth_sessions (telegram_id, employee_id, logged_in_at) VALUES (?, ?, ?)",
        (telegram_id, employee_id, now_str())
    )
    conn.commit()


def clear_session(telegram_id: int):
    cursor.execute("DELETE FROM auth_sessions WHERE telegram_id = ?", (telegram_id,))
    conn.commit()


def ensure_default_passwords():
    for name, pwd in DEFAULT_PASSWORDS.items():
        cursor.execute("SELECT id, password FROM employees WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            current_pwd = (row["password"] or "").strip()
            if not current_pwd:
                cursor.execute("UPDATE employees SET password = ? WHERE id = ?", (pwd, row["id"]))
    conn.commit()


def import_default_employees():
    for name in DEFAULT_PASSWORDS.keys():
        cursor.execute("SELECT id FROM employees WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO employees (name, role, is_active, created_at, password) VALUES (?, 'employee', 1, ?, ?)",
                (name, now_str(), DEFAULT_PASSWORDS[name])
            )
    conn.commit()


setup_db()


def import_from_excel(excel_path: str):
    import_default_employees()

    if not os.path.exists(excel_path):
        ensure_default_passwords()
        return f"Excel file topilmadi: {excel_path}"

    df = pd.read_excel(excel_path)

    required_cols = {"Наименование", "Центральный склад"}
    if not required_cols.issubset(set(df.columns)):
        ensure_default_passwords()
        return "Excel format mos emas. Керакли устунлар: Наименование, Центральный склад"

    added_employees = 0
    added_folders = 0
    added_assignments = 0

    for _, row in df.iterrows():
        folder_name = clean_text(row.get("Наименование"))
        employee_name = sklad_employee_name(clean_text(row.get("Центральный склад")))

        if not folder_name or not employee_name:
            continue
        if folder_name.lower() == "nan" or employee_name.lower() == "nan":
            continue

        cursor.execute("SELECT id FROM employees WHERE name = ?", (employee_name,))
        emp = cursor.fetchone()
        if not emp:
            cursor.execute(
                "INSERT INTO employees (name, role, is_active, created_at) VALUES (?, 'employee', 1, ?)",
                (employee_name, now_str())
            )
            employee_id = cursor.lastrowid
            added_employees += 1
        else:
            employee_id = emp["id"]

        cursor.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
        fld = cursor.fetchone()
        if not fld:
            cursor.execute(
                "INSERT INTO folders (name, created_at) VALUES (?, ?)",
                (folder_name, now_str())
            )
            folder_id = cursor.lastrowid
            added_folders += 1
        else:
            folder_id = fld["id"]

        try:
            cursor.execute(
                "INSERT INTO assignments (employee_id, folder_id) VALUES (?, ?)",
                (employee_id, folder_id)
            )
            added_assignments += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    ensure_default_passwords()
    return f"Импорт готов: сотрудники={added_employees}, папки={added_folders}, назначения={added_assignments}"


def sync_assignments_from_excel(excel_path: str) -> str:
    """Excel bo‘yicha biriktmalarni DB bilan moslashtiradi (ortiqchalarini o‘chiradi)."""
    import_default_employees()

    if not os.path.exists(excel_path):
        ensure_default_passwords()
        return f"Excel file topilmadi: {excel_path}"

    df = pd.read_excel(excel_path)
    required_cols = {"Наименование", "Центральный склад"}
    if not required_cols.issubset(set(df.columns)):
        ensure_default_passwords()
        return "Excel format mos emas. Керакли устунлар: Наименование, Центральный склад"

    added_employees = 0
    added_folders = 0
    desired_ids = set()
    desired_folder_names: set[str] = set()

    for _, row in df.iterrows():
        folder_name = clean_text(row.get("Наименование"))
        employee_name = sklad_employee_name(clean_text(row.get("Центральный склад")))

        if not folder_name or not employee_name:
            continue
        if folder_name.lower() == "nan" or employee_name.lower() == "nan":
            continue

        cursor.execute("SELECT id FROM employees WHERE name = ?", (employee_name,))
        emp = cursor.fetchone()
        if not emp:
            cursor.execute(
                "INSERT INTO employees (name, role, is_active, created_at) VALUES (?, 'employee', 1, ?)",
                (employee_name, now_str())
            )
            employee_id = cursor.lastrowid
            added_employees += 1
        else:
            employee_id = emp["id"]

        cursor.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
        fld = cursor.fetchone()
        if not fld:
            cursor.execute(
                "INSERT INTO folders (name, created_at) VALUES (?, ?)",
                (folder_name, now_str())
            )
            folder_id = cursor.lastrowid
            added_folders += 1
        else:
            folder_id = fld["id"]

        desired_ids.add((employee_id, folder_id))
        desired_folder_names.add(folder_name)

    cursor.execute("SELECT id, employee_id, folder_id FROM assignments")
    removed = 0
    for row in cursor.fetchall():
        if (row["employee_id"], row["folder_id"]) not in desired_ids:
            cursor.execute("DELETE FROM assignments WHERE id = ?", (row["id"],))
            removed += 1

    added = 0
    for employee_id, folder_id in desired_ids:
        try:
            cursor.execute(
                "INSERT INTO assignments (employee_id, folder_id) VALUES (?, ?)",
                (employee_id, folder_id)
            )
            added += 1
        except sqlite3.IntegrityError:
            pass

    removed_folders: list[str] = []
    cursor.execute("SELECT id, name FROM folders")
    for frow in cursor.fetchall():
        fname = (frow["name"] or "").strip()
        fid = int(frow["id"])
        if fname in desired_folder_names:
            continue
        cursor.execute("SELECT 1 FROM assignments WHERE folder_id = ? LIMIT 1", (fid,))
        if cursor.fetchone():
            continue
        for table in ("submissions", "folder_marks"):
            cursor.execute(f"SELECT 1 FROM {table} WHERE folder_id = ? LIMIT 1", (fid,))
            if cursor.fetchone():
                break
        else:
            cursor.execute("DELETE FROM folders WHERE id = ?", (fid,))
            removed_folders.append(fname)

    conn.commit()
    ensure_default_passwords()
    _migrate_deactivate_legacy_staff(cursor)
    conn.commit()
    folders_part = f", papkalar_o'chirildi={len(removed_folders)}"
    if removed_folders:
        folders_part += f" ({'; '.join(removed_folders[:8])}{'…' if len(removed_folders) > 8 else ''})"
    return (
        f"Синхронизация готова: всего={len(desired_ids)}, добавлено={added}, удалено={removed}, "
        f"сотрудники+={added_employees}, папки+={added_folders}{folders_part}"
    )


startup_import_result = sync_assignments_from_excel(EXCEL_FILE)


# ==========================================
# BOT / STATES
# ==========================================
dp = Dispatcher()


class LoginState(StatesGroup):
    waiting_password = State()


class AddEmployeeState(StatesGroup):
    waiting_name = State()
    waiting_tg_id = State()


class AddFolderState(StatesGroup):
    waiting_folder_name = State()


class AssignState(StatesGroup):
    waiting_employee_id = State()
    waiting_folder_id = State()


class OpenCycleState(StatesGroup):
    waiting_title = State()


class DeleteReportState(StatesGroup):
    waiting_submission_id = State()


class MarkFoldersState(StatesGroup):
    waiting_folder_ids = State()


class SubmitState(StatesGroup):
    waiting_folder_id = State()
    waiting_counted_ok = State()
    waiting_location_ok = State()
    waiting_wrong_location_count = State()
    waiting_fixed_now = State()
    waiting_comment = State()


# ==========================================
# GROUP COMMANDS
# ==========================================
@dp.message(Command("hisobot"), F.chat.id == GROUP_ID)
async def group_full_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_cycle_for_reports()
    if not cycle:
        return await message.answer("Циклов пока нет.")

    cycle_id = cycle["id"]
    cycle_title = cycle["title"]

    cursor.execute("SELECT COUNT(*) AS c FROM folder_marks WHERE cycle_id = ?", (cycle_id,))
    total_assignments = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle_id,))
    total_submitted = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ? AND counted_ok = 1", (cycle_id,))
    counted_ok = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ? AND location_ok = 1", (cycle_id,))
    location_ok = cursor.fetchone()["c"]

    cursor.execute("SELECT COALESCE(SUM(wrong_location_count), 0) AS total_wrong FROM submissions WHERE cycle_id = ?", (cycle_id,))
    total_wrong_locations = cursor.fetchone()["total_wrong"]

    report = (
        f"📊 ОБЩИЙ ОТЧЁТ СКЛАДА\n\n"
        f"Цикл: {cycle_title}\n"
        f"Всего назначенных папок: {total_assignments}\n"
        f"Сданных отчётов: {total_submitted}\n"
        f"Оставшиеся папки: {max(total_assignments - total_submitted, 0)}\n\n"
        f"✅ Остаток верный: {counted_ok}\n"
        f"✅ Место хранения верное: {location_ok}\n"
        f"❌ Всего ошибочных мест: {total_wrong_locations}\n"
    )

    await message.answer(report)


@dp.message(Command("hodimlar"), F.chat.id == GROUP_ID)
async def group_employee_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_cycle_for_reports()
    if not cycle:
        return await message.answer("Циклов пока нет.")

    cycle_id = cycle["id"]
    cycle_title = cycle["title"]

    cursor.execute("""
        SELECT 
            e.id,
            e.name,
            COUNT(DISTINCT fm.folder_id) AS assigned_count,
            COUNT(DISTINCT s.folder_id) AS submitted_count,
            SUM(CASE WHEN s.counted_ok = 1 THEN 1 ELSE 0 END) AS counted_ok_count,
            SUM(CASE WHEN s.location_ok = 1 THEN 1 ELSE 0 END) AS location_ok_count,
            COALESCE(SUM(s.wrong_location_count), 0) AS wrong_locations
        FROM employees e
        LEFT JOIN folder_marks fm ON fm.employee_id = e.id AND fm.cycle_id = ?
        LEFT JOIN submissions s 
            ON s.employee_id = e.id 
           AND s.cycle_id = ?
        GROUP BY e.id, e.name
        ORDER BY e.name
    """, (cycle_id, cycle_id,))
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Пока нет данных для отчёта по сотрудникам.")

    text = f"👥 ОТЧЁТ ПО СОТРУДНИКАМ\n\nЦикл: {cycle_title}\n\n"
    for row in rows:
        assigned = row["assigned_count"] or 0  # белгиланган папкалар
        submitted = row["submitted_count"] or 0
        counted_ok = row["counted_ok_count"] or 0
        location_ok = row["location_ok_count"] or 0
        wrong_locations = row["wrong_locations"] or 0
        remaining = max(assigned - submitted, 0)

        text += (
            f"🔹 {row['name']}\n"
            f"   • Назначено папок: {assigned}\n"
            f"   • Сдано: {submitted}\n"
            f"   • Осталось: {remaining}\n"
            f"   • Остаток верный: {counted_ok}\n"
            f"   • Место верное: {location_ok}\n"
            f"   • Ошибочных мест: {wrong_locations}\n\n"
        )

    for part in chunk_text(text):
        await message.answer(part)


@dp.message(Command("qolgan"), F.chat.id == GROUP_ID)
async def group_remaining_folders_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_active_cycle() or get_cycle_for_reports()
    if not cycle:
        return await message.answer("Активный или последний цикл не найден.")

    for part in build_admin_remaining_folders_report(cycle):
        await message.answer(part)


@dp.message(Command("papkalar"), F.chat.id == GROUP_ID)
async def group_folder_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_cycle_for_reports()
    if not cycle:
        return await message.answer("Циклов пока нет.")

    cycle_id = cycle["id"]
    cycle_title = cycle["title"]

    cursor.execute("""
        SELECT
            f.name AS folder_name,
            e.name AS employee_name,
            s.counted_ok,
            s.location_ok,
            s.wrong_location_count,
            s.fixed_now,
            s.comment,
            s.submitted_at
        FROM submissions s
        JOIN folders f ON f.id = s.folder_id
        JOIN employees e ON e.id = s.employee_id
        WHERE s.cycle_id = ?
        ORDER BY f.name
    """, (cycle_id,))
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Пока нет данных для отчёта по папкам.")

    text = f"📁 ОТЧЁТ ПО ПАПКАМ\n\nЦикл: {cycle_title}\n\n"
    for row in rows:
        text += (
            f"📦 {row['folder_name']}\n"
            f"   • Сотрудник: {row['employee_name']}\n"
            f"   • Остаток: {'Верно' if row['counted_ok'] else 'Неверно'}\n"
            f"   • Место: {'Верно' if row['location_ok'] else 'Неверно'}\n"
        )
        if row["location_ok"] == 0:
            text += (
                f"   • Ошибочных мест: {row['wrong_location_count']}\n"
                f"   • Исправлено: {'Да' if row['fixed_now'] else 'Нет'}\n"
            )
        text += (
            f"   • Комментарий: {row['comment']}\n"
            f"   • Время: {row['submitted_at']}\n\n"
        )

    for part in chunk_text(text):
        await message.answer(part)


# ==========================================
# AUTH
# ==========================================
@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return

    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            f"🔥 Вы вошли как администратор.\n\n{startup_import_result}\n\n"
            "📂 Оставшиеся папки · /qolgan",
            reply_markup=admin_menu(),
        )
        return

    existing = get_employee_by_tg(message.from_user.id)
    if existing:
        set_session(message.from_user.id, existing["id"])
        await message.answer(
            f"🔥 Добро пожаловать, {he(existing['name'])}\n\n📊 Работа сегодня — начать.",
            reply_markup=employee_menu(),
            parse_mode=ParseMode.HTML,
        )
        return

    session_emp = get_logged_in_employee(message.from_user.id)
    if session_emp:
        await message.answer(
            f"🔥 Добро пожаловать, {he(session_emp['name'])}\n\n📊 Работа сегодня — начать.",
            reply_markup=employee_menu(),
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(
        "Нужно войти по паролю.\nВведите пароль, который выдал администратор.",
        reply_markup=login_keyboard()
    )


@dp.message(F.text.in_(BTN_LOGIN_ALL))
async def login_begin(message: Message, state: FSMContext):
    if not is_private(message):
        return

    if is_admin(message.from_user.id):
        return await message.answer("Вы администратор.", reply_markup=admin_menu())

    await state.set_state(LoginState.waiting_password)
    await message.answer("Введите пароль:", reply_markup=cancel_keyboard())


@dp.message(LoginState.waiting_password)
async def login_password(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=login_keyboard())

    password = clean_text(message.text)
    cursor.execute("SELECT * FROM employees WHERE password = ? AND is_active = 1", (password,))
    employee = cursor.fetchone()

    if not employee:
        return await message.answer("Неверный пароль.")

    from employee_registry import same_telegram_person

    uid = int(message.from_user.id)
    stored_tg = employee["telegram_id"]
    if stored_tg is None:
        cursor.execute("UPDATE employees SET telegram_id = ? WHERE id = ?", (uid, employee["id"]))
        conn.commit()
    elif not same_telegram_person(int(stored_tg), uid):
        return await message.answer(
            "Этот пароль привязан к другому Telegram-аккаунту.\nОбратитесь к администратору."
        )
    elif int(stored_tg) != uid:
        cursor.execute("UPDATE employees SET telegram_id = ? WHERE id = ?", (uid, employee["id"]))
        conn.commit()

    set_session(message.from_user.id, employee["id"])
    await state.clear()
    await message.answer(
        f"✅ Вход выполнен.\nСотрудник: {employee['name']}",
        reply_markup=employee_menu()
    )


@dp.message(F.text.in_(BTN_LOGOUT_ALL))
async def logout_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return

    await state.clear()
    clear_session(message.from_user.id)

    if is_admin(message.from_user.id):
        return await message.answer("Администратору выход не нужен.", reply_markup=admin_menu())

    await message.answer("Вы вышли.", reply_markup=login_keyboard())


def require_login_or_admin(message: Message) -> bool:
    if is_admin(message.from_user.id):
        return True
    return get_logged_in_employee(message.from_user.id) is not None or get_employee_by_tg(message.from_user.id) is not None


# ==========================================
# USER / ADMIN COMMON
# ==========================================
@dp.message(F.text.in_(BTN_HELP_ALL))
async def help_handler(message: Message):
    if not is_private(message):
        return
    text = (
        "Этот бот для контроля склада.\n\n"
        "• Сотрудники работают в личке\n"
        "• В группу уходит только завершённый отчёт\n"
        "• В группе работают команды /hisobot /hodimlar /papkalar /qolgan\n"
        "• 📊 Работа сегодня — прогресс и краткий статус\n"
        "• 📝 Пересчёт — выбрать папку, отчёт уйдёт в группу\n"
        "• 📌 Отметить как готовые — необязательно (в группу не уходит, считается пересчитанным)\n"
        "• /sanash /holat — быстрые команды\n"
        "• Если меню не обновилось: /start или /menu"
    )
    markup = admin_menu() if is_admin(message.from_user.id) else None
    await message.answer(text, reply_markup=markup)


@dp.message(Command("menu"))
async def menu_refresh_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    await state.clear()
    if is_admin(message.from_user.id):
        return await message.answer(
            "✅ Меню администратора обновлено.\n📂 Оставшиеся папки — эта кнопка или /qolgan",
            reply_markup=admin_menu(),
        )
    session_emp = get_logged_in_employee(message.from_user.id) or get_employee_by_tg(message.from_user.id)
    if session_emp:
        return await message.answer(
            "✅ Меню обновлено.\n📊 Работа сегодня · 📝 Пересчёт · 📌 Отметить",
            reply_markup=employee_menu(),
        )
    await message.answer("Сначала войдите.", reply_markup=login_keyboard())


@dp.message(F.text.in_(BTN_MY_FOLDERS_ALL))
async def my_folders_handler(message: Message):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())

    if is_admin(message.from_user.id):
        return await message.answer("Этот раздел администратору не нужен.")

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Вы не найдены как сотрудник.")
    if not cycle:
        return await message.answer("Нет активного цикла.")

    assigned = get_employee_assignment_folders(employee["id"])
    if not assigned:
        return await message.answer("По Excel вам не назначены папки.", reply_markup=employee_menu())

    stats = employee_work_stats(employee["id"], cycle["id"])
    text = (
        f"📋 Назначенные вам папки\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Всего: {stats['total']} | Готово: {stats['done']} | Нужен пересчёт: {stats['to_sanash']}\n\n"
    )
    for row in assigned[:50]:
        text += f"• {row['name']}\n"
    if len(assigned) > 50:
        text += f"\n… и ещё {len(assigned) - 50}"
    await message.answer(text, reply_markup=employee_menu())


@dp.message(F.text.in_(BTN_ACTIVE_CHECKS_ALL))
async def active_checks_handler(message: Message):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Пока нет активного цикла.")

    if is_admin(message.from_user.id):
        for part in build_admin_remaining_folders_report(cycle):
            await message.answer(part, reply_markup=admin_menu())
        return

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    if not employee:
        return await message.answer("Вы не найдены как сотрудник.")

    rows = get_sanash_queue_folders(employee["id"], cycle["id"])

    if not rows:
        return await message.answer(
            f"✅ Всё выполнено.\n\nЦикл: {cycle['title']}",
            reply_markup=employee_menu(),
        )

    text = f"📝 Нужен пересчёт ({len(rows)})\n\nЦикл: {cycle['title']}\n\n"
    for row in rows:
        text += f"• {row['name']}\n"
    text += "\n📝 Отправьте отчёт через кнопку Пересчёт."
    await message.answer(text, reply_markup=employee_menu())


@dp.message(F.text.in_(BTN_REMAINING_ALL))
async def admin_remaining_folders_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer(
            "Нет активного цикла.\nОткройте новый цикл или смотрите последний в группе через /qolgan."
        )

    for part in build_admin_remaining_folders_report(cycle):
        await message.answer(part, reply_markup=admin_menu())


@dp.message(Command("qolgan"))
async def admin_remaining_folders_command(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cycle = get_active_cycle() or get_cycle_for_reports()
    if not cycle:
        return await message.answer("Активный или последний цикл не найден.")

    for part in build_admin_remaining_folders_report(cycle):
        await message.answer(part, reply_markup=admin_menu())


@dp.message(F.text.in_(BTN_STATUS_ALL))
async def status_handler(message: Message):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Нет активного цикла.")

    if is_admin(message.from_user.id):
        cursor.execute("SELECT COUNT(*) AS c FROM folder_marks WHERE cycle_id = ?", (cycle["id"],))
        total = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle["id"],))
        done = cursor.fetchone()["c"]
        return await message.answer(
            f"📈 Статус администратора\n\n"
            f"Цикл: {cycle['title']}\n"
            f"Отмеченные папки: {total}\n"
            f"Сданные отчёты: {done}\n"
            f"Осталось: {max(total - done, 0)}\n\n"
            f"Подробнее: 📂 Оставшиеся папки"
        )

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    if not employee:
        return await message.answer("Вы не найдены как сотрудник.")

    stats = employee_work_stats(employee["id"], cycle["id"])
    await message.answer(
        f"📊 Ваш статус\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Всего: {stats['total']}\n"
        f"Готово (пересчитано): {stats['done']}\n"
        f"Нужен пересчёт: {stats['to_sanash']}"
    )


# ==========================================
# ADMIN: EMPLOYEES
# ==========================================
@dp.message(F.text.in_(BTN_ADD_EMP_ALL))
async def add_employee_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")
    await state.set_state(AddEmployeeState.waiting_name)
    await message.answer("Введите имя сотрудника:", reply_markup=cancel_keyboard())


@dp.message(AddEmployeeState.waiting_name)
async def add_employee_name(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    name = clean_text(message.text)
    if not name:
        return await message.answer("Имя не должно быть пустым.")

    await state.update_data(name=name)
    await state.set_state(AddEmployeeState.waiting_tg_id)
    await message.answer("Отправьте Telegram ID. Если пока нет — напишите 0.")


@dp.message(AddEmployeeState.waiting_tg_id)
async def add_employee_tg(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    value = (message.text or "").strip()
    if not re.fullmatch(r"-?\d+", value):
        return await message.answer("ID должен быть числом.")

    tg_id = int(value)
    tg_value = None if tg_id == 0 else tg_id
    data = await state.get_data()
    name = data["name"]

    try:
        cursor.execute(
            "INSERT INTO employees (name, telegram_id, role, is_active, created_at) VALUES (?, ?, 'employee', 1, ?)",
            (name, tg_value, now_str())
        )
        conn.commit()
        if name in DEFAULT_PASSWORDS:
            cursor.execute("UPDATE employees SET password = ? WHERE name = ?", (DEFAULT_PASSWORDS[name], name))
            conn.commit()
        await message.answer(
            f"✅ Сотрудник добавлен:\nИмя: {name}\nTelegram ID: {tg_value or 'нет'}",
            reply_markup=admin_menu()
        )
    except sqlite3.IntegrityError:
        cursor.execute("SELECT * FROM employees WHERE telegram_id = ?", (tg_value,))
        existing = cursor.fetchone()
        if existing:
            await message.answer(
                f"⚠️ Этот Telegram ID уже привязан к другому сотруднику:\n{existing['name']}",
                reply_markup=admin_menu()
            )
        else:
            await message.answer("⚠️ Этот сотрудник уже добавлен.", reply_markup=admin_menu())

    await state.clear()


@dp.message(F.text.in_(BTN_ALL_EMP_ALL))
async def all_employees_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("SELECT id, name, telegram_id, password FROM employees ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Сотрудников нет.")

    text = "👥 Все сотрудники:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']} | TG: {row['telegram_id'] or 'нет'} | Пароль: {row['password'] or 'нет'}\n"
    await message.answer(text)


@dp.message(F.text.in_(BTN_GEN_PASS_ALL))
async def generate_passwords_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("SELECT id, name FROM employees ORDER BY id")
    rows = cursor.fetchall()
    changed = 0

    for row in rows:
        name = row["name"]
        new_pwd = DEFAULT_PASSWORDS.get(name) or "".join(secrets.choice("0123456789") for _ in range(6))
        cursor.execute("UPDATE employees SET password = ? WHERE id = ?", (new_pwd, row["id"]))
        changed += 1

    conn.commit()
    await message.answer(f"✅ Пароли назначены {changed} сотрудникам.", reply_markup=admin_menu())


@dp.message(F.text.in_(BTN_PASS_LIST_ALL))
async def passwords_list_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("SELECT id, name, password FROM employees ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Сотрудников нет.")

    text = "📄 Список паролей:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']} → {row['password'] or 'нет'}\n"
    for part in chunk_text(text):
        await message.answer(part)


# ==========================================
# ADMIN: FOLDERS / ASSIGNMENTS
# ==========================================
@dp.message(F.text.in_(BTN_ADD_FOLDER_ALL))
async def add_folder_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")
    await state.set_state(AddFolderState.waiting_folder_name)
    await message.answer("Введите название новой папки:", reply_markup=cancel_keyboard())


@dp.message(AddFolderState.waiting_folder_name)
async def add_folder_save(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    folder_name = clean_text(message.text)
    if not folder_name:
        return await message.answer("Название папки не должно быть пустым.")

    try:
        cursor.execute("INSERT INTO folders (name, created_at) VALUES (?, ?)", (folder_name, now_str()))
        conn.commit()
        await message.answer(f"✅ Папка добавлена:\n{folder_name}", reply_markup=admin_menu())
    except sqlite3.IntegrityError:
        await message.answer(f"⚠️ Эта папка уже добавлена:\n{folder_name}", reply_markup=admin_menu())

    await state.clear()


@dp.message(F.text.in_(BTN_ALL_FOLDERS_ALL))
async def all_folders_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("SELECT id, name FROM folders ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Папок нет.")

    text = "📁 Все папки:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"
    for part in chunk_text(text):
        await message.answer(part)


@dp.message(F.text.in_(BTN_ASSIGN_ALL))
async def assign_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("SELECT id, name, telegram_id FROM employees ORDER BY id")
    employees = cursor.fetchall()
    if not employees:
        return await message.answer("Сначала добавьте сотрудника.")

    text = "Отправьте ID сотрудника.\n\n👥 Сотрудники:\n"
    for row in employees:
        text += f"{row['id']}. {row['name']} — TG ID: {row['telegram_id'] or 'нет'}\n"

    await state.set_state(AssignState.waiting_employee_id)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(AssignState.waiting_employee_id)
async def assign_get_employee(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    if not (message.text or "").isdigit():
        return await message.answer("ID сотрудника должен быть числом.")

    employee_id = int(message.text)
    employee = get_employee_by_id(employee_id)
    if not employee:
        return await message.answer("Такой ID сотрудника не найден.")

    await state.update_data(employee_id=employee_id)

    cursor.execute("SELECT id, name FROM folders ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        await state.clear()
        return await message.answer("Сначала добавьте папку.", reply_markup=admin_menu())

    text = "Теперь отправьте ID папки.\n\n📁 Папки:\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"

    await state.set_state(AssignState.waiting_folder_id)
    await message.answer(text)


@dp.message(AssignState.waiting_folder_id)
async def assign_save(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    if not (message.text or "").isdigit():
        return await message.answer("ID папки должен быть числом.")

    folder_id = int(message.text)
    data = await state.get_data()
    employee_id = data["employee_id"]

    employee = get_employee_by_id(employee_id)
    folder = get_folder_by_id(folder_id)

    if not employee:
        await state.clear()
        return await message.answer("Сотрудник не найден.", reply_markup=admin_menu())
    if not folder:
        return await message.answer("Папка не найдена.")

    try:
        cursor.execute(
            "INSERT INTO assignments (employee_id, folder_id) VALUES (?, ?)",
            (employee_id, folder_id)
        )
        conn.commit()
        await message.answer(
            f"✅ Назначено:\nСотрудник: {employee['name']}\nПапка: {folder['name']}",
            reply_markup=admin_menu()
        )
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Эта папка уже назначена этому сотруднику.", reply_markup=admin_menu())

    await state.clear()


@dp.message(F.text.in_(BTN_ASSIGNMENTS_ALL))
async def assignments_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("""
        SELECT a.id, e.name AS employee_name, e.telegram_id, f.name AS folder_name
        FROM assignments a
        JOIN employees e ON e.id = a.employee_id
        JOIN folders f ON f.id = a.folder_id
        ORDER BY a.id
    """)
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Назначений нет.")

    text = "📌 Назначения:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['employee_name']} ({row['telegram_id'] or 'нет'}) → {row['folder_name']}\n"
    for part in chunk_text(text):
        await message.answer(part)


# ==========================================
# ADMIN: IMPORT / CYCLES
# ==========================================
@dp.message(F.text.in_(BTN_EXCEL_ALL))
async def excel_import_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    result = sync_assignments_from_excel(EXCEL_FILE)
    await message.answer(f"✅ {result}")


@dp.message(F.text.in_(BTN_OPEN_CYCLE_ALL))
async def open_cycle_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    active = get_active_cycle()
    if active:
        return await message.answer(f"Уже есть активный цикл: {active['title']}\nСначала закройте его.")

    await state.set_state(OpenCycleState.waiting_title)
    await message.answer("Введите название нового цикла:", reply_markup=cancel_keyboard())


@dp.message(OpenCycleState.waiting_title)
async def open_cycle_save(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    title = clean_text(message.text)
    if not title:
        return await message.answer("Название цикла не должно быть пустым.")

    cursor.execute(
        "INSERT INTO cycles (title, is_active, created_at) VALUES (?, 1, ?)",
        (title, now_str())
    )
    conn.commit()

    await state.clear()
    await message.answer(f"✅ Новый цикл открыт:\n{title}", reply_markup=admin_menu())


@dp.message(F.text.in_(BTN_CLOSE_CYCLE_ALL))
async def close_cycle_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    active = get_active_cycle()
    if not active:
        return await message.answer("Нет активного цикла.")

    cursor.execute("UPDATE cycles SET is_active = 0 WHERE id = ?", (active["id"],))
    conn.commit()
    await message.answer(f"🛑 Цикл закрыт:\n{active['title']}", reply_markup=admin_menu())


@dp.message(F.text.in_(BTN_CYCLE_STATUS_ALL))
async def active_cycle_status_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Нет активного цикла.")

    cursor.execute("SELECT COUNT(*) AS c FROM folder_marks WHERE cycle_id = ?", (cycle["id"],))
    total_marks = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle["id"],))
    submitted = cursor.fetchone()["c"]
    text = (
        f"📈 Статус активного цикла\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Отмеченные папки: {total_marks}\n"
        f"Сданные отчёты: {submitted}\n"
        f"Осталось: {max(total_marks - submitted, 0)}"
    )
    await message.answer(text)


# ==========================================
# FOLDER MARKING (ходим ўзи белгилайди)
# ==========================================
@dp.message(F.text.in_({BTN_MARK_FOLDERS, "📌 Папкаларни белгилаш"}))
async def mark_folders_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Этот раздел для администратора не используется.")

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Вы не найдены как сотрудник.")
    if not cycle:
        return await message.answer("Пока нет активного цикла.")

    assigned = get_employee_assignment_folders(employee["id"])
    if not assigned:
        return await message.answer(
            f"По Excel вам не назначены папки.\n"
            f"Обратитесь к администратору (📥 Импорт Excel).\n\nСотрудник: {employee['name']}",
            reply_markup=employee_menu(),
        )

    stats = employee_work_stats(employee["id"], cycle["id"])
    queue = get_sanash_queue_folders(employee["id"], cycle["id"])
    if not queue:
        return await message.answer(
            f"✅ Всё готово ({stats['done']} / {stats['total']}).",
            reply_markup=employee_menu(),
        )

    text = (
        f"📌 Отметить как готовые (необязательно)\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Сотрудник: {employee['name']}\n"
        f"Всего: {stats['total']} | Готово: {stats['done']} | Осталось: {stats['to_sanash']}\n\n"
    )
    for row in queue:
        text += f"{row['id']}. {row['name']}\n"

    text += (
        "\n➕ Отправьте ID (например: 12 45) или ✅ Отметить все\n"
        "✅ Готово — кнопка\n"
    )

    await state.set_state(MarkFoldersState.waiting_folder_ids)
    for part in chunk_text(text):
        await message.answer(part, reply_markup=mark_folder_keyboard())


@dp.message(MarkFoldersState.waiting_folder_ids)
async def mark_folders_add(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=employee_menu())

    if message.text in BTN_MARK_DONE_ALL:
        await state.clear()
        employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
        cycle = get_active_cycle()
        if not employee or not cycle:
            return await message.answer("Сотрудник или цикл не найден.", reply_markup=employee_menu())
        stats = employee_work_stats(employee["id"], cycle["id"])
        return await message.answer(
            f"✅ Готово: {stats['done']} / {stats['total']}\n"
            "📝 Пересчёт — отчёт уйдёт в группу.",
            reply_markup=employee_menu(),
        )

    if message.text in BTN_MARK_ALL_BTN_ALL:
        employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
        cycle = get_active_cycle()
        if not employee or not cycle:
            await state.clear()
            return await message.answer("Сотрудник или цикл не найден.", reply_markup=employee_menu())
        added = mark_all_assignment_folders(employee["id"], cycle["id"])
        stats = employee_work_stats(employee["id"], cycle["id"])
        return await message.answer(
            f"✅ Отмечено как готовые: {added}.\n"
            f"Всего готово: {stats['done']} / {stats['total']}.",
            reply_markup=mark_folder_keyboard(),
        )

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await state.clear()
        return await message.answer("Сотрудник или цикл не найден.", reply_markup=employee_menu())

    folder_ids = parse_folder_id_list(message.text or "")
    if not folder_ids:
        return await message.answer("Отправьте ID папок. Например: 12 45 67")

    added = 0
    skipped = 0
    errors = []
    for folder_id in folder_ids:
        folder = get_folder_by_id(folder_id)
        if not folder:
            errors.append(f"ID {folder_id} не найден")
            continue
        if not get_folder_for_sanash(employee["id"], cycle["id"], folder_id):
            if not is_folder_assigned_to_employee(employee["id"], folder_id):
                errors.append(f"{folder['name']} — вам не назначена")
            else:
                errors.append(f"{folder['name']} — уже готова")
            skipped += 1
            continue
        try:
            cursor.execute(
                "INSERT INTO folder_marks (cycle_id, employee_id, folder_id, marked_at) VALUES (?, ?, ?, ?)",
                (cycle["id"], employee["id"], folder_id, now_str()),
            )
            conn.commit()
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1

    reply = f"✅ Отмечено как готовые: {added}."
    if skipped:
        reply += f"\n⚠️ Пропущено: {skipped} (уже готовы / не ваши)."
    if errors:
        reply += "\n" + "\n".join(errors[:5])
    reply += "\n\nОтправьте ещё ID или ✅ Отметка завершена."
    await message.answer(reply, reply_markup=mark_folder_keyboard())


# ==========================================
# DASHBOARD & INLINE UI
# ==========================================
@dp.message(F.text.in_(BTN_TODAY_ALL))
async def dashboard_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        cycle = get_active_cycle() or get_cycle_for_reports()
        if not cycle:
            return await message.answer("Нет активного цикла.")
        for part in build_admin_remaining_folders_report(cycle):
            await message.answer(part, reply_markup=admin_menu())
        return
    await state.clear()
    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Вы не найдены как сотрудник.")
    if not cycle:
        return await message.answer("Пока нет активного цикла.")
    await send_dashboard(message, employee, cycle)


@dp.message(Command("holat"))
async def cmd_holat(message: Message, state: FSMContext):
    return await dashboard_handler(message, state)


@dp.message(F.text.in_(BTN_COUNT_ALL))
@dp.message(Command("sanash"))
async def sanash_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Не для администратора.")
    await state.clear()
    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await message.answer("Сотрудник или цикл не найден.")
    await show_folder_picker(message, employee, cycle, mode="p", page=0, edit=False)


@dp.message(F.text.in_(BTN_MARK_ALL_SET))
async def mark_inline_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Сначала войдите.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Не для администратора.")
    await state.clear()
    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await message.answer("Сотрудник или цикл не найден.")
    assigned = get_employee_assignment_folders(employee["id"])
    if not assigned:
        return await message.answer("По Excel вам не назначены папки.", reply_markup=employee_menu())
    await show_folder_picker(message, employee, cycle, mode="m", page=0, edit=False)


# ==========================================
# REPORT SUBMISSION (матн: изоҳ, хато сони)
# ==========================================
@dp.message(SubmitState.waiting_folder_id)
async def submit_get_folder(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=employee_menu())

    if not (message.text or "").isdigit():
        return await message.answer("ID папки должен быть числом.")

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()

    if not employee or not cycle:
        await state.clear()
        return await message.answer("Сотрудник или активный цикл не найден.", reply_markup=employee_menu())

    folder_id = int(message.text)

    folder = get_folder_for_sanash(employee["id"], cycle["id"], folder_id)

    if not folder:
        return await message.answer(
            "Эта папка недоступна для пересчёта (уже готова или не назначена вам)."
        )

    cursor.execute("""
        SELECT id FROM submissions
        WHERE cycle_id = ? AND employee_id = ? AND folder_id = ?
    """, (cycle["id"], employee["id"], folder_id))
    existing = cursor.fetchone()

    if existing:
        return await message.answer("По этой папке отчёт уже сдан.")

    await state.update_data(folder_id=folder["id"], folder_name=folder["name"])
    await state.set_state(SubmitState.waiting_counted_ok)
    stats = employee_work_stats(employee["id"], cycle["id"])
    push_session_start_background(
        tg_id=message.from_user.id,
        bot_key="sklad",
        user_name=employee["name"],
        activity_type="sklad",
        metadata={"folder": folder["name"], "done": stats["done"], "total": stats["total"]},
    )
    await message.answer(
        f"Папка: {folder['name']}\n\nОстаток пересчитан на 100% верно?",
        reply_markup=yes_no_keyboard()
    )


@dp.message(SubmitState.waiting_counted_ok)
async def submit_counted_ok(message: Message, state: FSMContext):
    if not is_yes(message.text) and not is_no(message.text):
        return await message.answer("Ответьте кнопкой.")
    counted_ok = 1 if is_yes(message.text) else 0
    await state.update_data(counted_ok=counted_ok)
    await state.set_state(SubmitState.waiting_location_ok)
    await message.answer("Место хранения верно на 100%?", reply_markup=yes_no_keyboard())


@dp.message(SubmitState.waiting_location_ok)
async def submit_location_ok(message: Message, state: FSMContext):
    if not is_yes(message.text) and not is_no(message.text):
        return await message.answer("Ответьте кнопкой.")

    location_ok = 1 if is_yes(message.text) else 0
    await state.update_data(location_ok=location_ok)

    if location_ok == 1:
        await state.update_data(wrong_location_count=0, fixed_now=None)
        await state.set_state(SubmitState.waiting_comment)
        return await message.answer(
            "Напишите комментарий.\nЕсли комментария нет: -",
            reply_markup=ReplyKeyboardRemove()
        )

    await state.set_state(SubmitState.waiting_wrong_location_count)
    await message.answer("Сколько мест ошибочны? Напишите число:", reply_markup=ReplyKeyboardRemove())


@dp.message(SubmitState.waiting_wrong_location_count)
async def submit_wrong_location_count(message: Message, state: FSMContext):
    value = clean_text(message.text)
    if not value.isdigit():
        return await message.answer("Напишите число. Например: 3")

    await state.update_data(wrong_location_count=int(value))
    await state.set_state(SubmitState.waiting_fixed_now)
    await message.answer("Ошибочные места исправлены?", reply_markup=yes_no_keyboard())


@dp.message(SubmitState.waiting_fixed_now)
async def submit_fixed_now(message: Message, state: FSMContext):
    if not is_yes(message.text) and not is_no(message.text):
        return await message.answer("Ответьте кнопкой.")
    fixed_now = 1 if is_yes(message.text) else 0
    await state.update_data(fixed_now=fixed_now)
    await state.set_state(SubmitState.waiting_comment)
    await message.answer("Напишите комментарий.\nЕсли комментария нет: -", reply_markup=ReplyKeyboardRemove())


@dp.message(SubmitState.waiting_comment)
async def submit_comment(message: Message, state: FSMContext, bot: Bot):
    comment = clean_text(message.text) or "-"

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()

    if not employee or not cycle:
        await state.clear()
        return await message.answer("Сотрудник или активный цикл не найден.", reply_markup=employee_menu())

    data = await state.get_data()

    submitted_at = now_str()
    counted_ok = data["counted_ok"]
    location_ok = data["location_ok"]
    wrong_location_count = data.get("wrong_location_count", 0)
    fixed_now = data.get("fixed_now")
    folder_name = data["folder_name"]

    cursor.execute("""
        INSERT INTO submissions (
            cycle_id, employee_id, folder_id,
            counted_ok, location_ok, wrong_location_count,
            fixed_now, comment, submitted_at, posted_to_group
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        cycle["id"],
        employee["id"],
        data["folder_id"],
        counted_ok,
        location_ok,
        wrong_location_count,
        data.get("fixed_now"),
        comment,
        submitted_at,
    ))
    conn.commit()

    stats = employee_work_stats(employee["id"], cycle["id"])
    counted_folders = get_submitted_folder_names(employee["id"], cycle["id"])
    group_note = await send_submission_to_group(
        bot,
        cycle_title=cycle["title"],
        employee_name=employee["name"],
        folder_name=folder_name,
        counted_ok=counted_ok,
        location_ok=location_ok,
        wrong_location_count=wrong_location_count,
        fixed_now=fixed_now,
        comment=comment,
        submitted_at=submitted_at,
        day_done=stats["done"],
        day_total=stats["total"],
        counted_folders=counted_folders,
    )

    await state.clear()
    push_session_end_background(tg_id=message.from_user.id, bot_key="sklad", activity_type="sklad")
    push_to_yordamchi_hub_background(
        tg_id=message.from_user.id,
        bot_key="sklad",
        summary=(
            f"Papka {folder_name}: sanaldi {counted_ok}, joy {location_ok}, "
            f"xato {wrong_location_count}, kun {stats['done']}/{stats['total']}"
        ),
    )
    await message.answer(
        f"✅ Отчёт принят.\n{group_note}",
        reply_markup=employee_menu(),
        parse_mode=ParseMode.HTML,
    )
    await send_dashboard(message, employee, cycle)


# ==========================================
# ADMIN: DELETE REPORTS
# ==========================================
@dp.message(F.text.in_(BTN_DEL_REPORT_ALL))
async def delete_report_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")

    cursor.execute("""
        SELECT s.id, c.title, e.name AS employee_name, f.name AS folder_name, s.submitted_at
        FROM submissions s
        JOIN cycles c ON c.id = s.cycle_id
        JOIN employees e ON e.id = s.employee_id
        JOIN folders f ON f.id = s.folder_id
        ORDER BY s.id DESC
        LIMIT 20
    """)
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Нет отчётов для удаления.")

    text = "Отправьте ID отчёта для удаления.\n\nПоследние 20 отчётов:\n"
    for row in rows:
        text += f"{row['id']}. {row['employee_name']} | {row['folder_name']} | {row['title']} | {row['submitted_at']}\n"

    await state.set_state(DeleteReportState.waiting_submission_id)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(DeleteReportState.waiting_submission_id)
async def delete_report_save(message: Message, state: FSMContext):
    if is_cancel(message.text):
        await state.clear()
        return await message.answer("Отменено.", reply_markup=admin_menu())

    if not (message.text or "").isdigit():
        return await message.answer("ID отчёта должен быть числом.")

    submission_id = int(message.text)

    cursor.execute("SELECT id FROM submissions WHERE id = ?", (submission_id,))
    row = cursor.fetchone()
    if not row:
        return await message.answer("Такой отчёт не найден.")

    cursor.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    conn.commit()

    await state.clear()
    await message.answer(f"🗑 Отчёт удалён. ID: {submission_id}", reply_markup=admin_menu())


# ==========================================
# INLINE CALLBACKS
# ==========================================
@dp.callback_query(F.data == "ui:x")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отмена")
    try:
        await callback.message.edit_text("❌ Отменено.")
    except Exception:
        pass
    await callback.message.answer("Выберите пункт меню.", reply_markup=current_menu(callback.from_user.id))


@dp.callback_query(F.data == "ui:go:dash")
async def cb_go_dashboard(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await callback.message.answer("Сотрудник или цикл не найден.")
    stats = employee_work_stats(employee["id"], cycle["id"])
    text = build_dashboard_text(
        employee_name=employee["name"],
        cycle_title=cycle["title"],
        total=stats["total"],
        to_sanash=stats["to_sanash"],
        done=stats["done"],
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=dashboard_keyboard())


@dp.callback_query(F.data == "ui:go:submit")
async def cb_go_submit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await callback.message.answer("Сотрудник или цикл не найден.")
    await show_folder_picker(callback.message, employee, cycle, mode="p", page=0, edit=True)


@dp.callback_query(F.data == "ui:go:mark")
async def cb_go_mark(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await callback.message.answer("Сотрудник или цикл не найден.")
    await show_folder_picker(callback.message, employee, cycle, mode="m", page=0, edit=True)


@dp.callback_query(F.data == "ui:go:list")
async def cb_go_list(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return
    await send_dashboard(callback.message, employee, cycle)


@dp.callback_query(F.data.regexp(r"^ui:[pm]:p:\d+$"))
async def cb_folder_page(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    mode = parts[1]
    page = int(parts[3])
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return
    await show_folder_picker(callback.message, employee, cycle, mode=mode, page=page, edit=True)


@dp.callback_query(F.data == "ui:m:all")
async def cb_mark_all(callback: CallbackQuery, state: FSMContext):
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await callback.answer("Ошибка", show_alert=True)
        return
    added = mark_all_assignment_folders(employee["id"], cycle["id"])
    await callback.answer(f"✅ Отмечено как готовые: {added}", show_alert=True)
    await show_folder_picker(callback.message, employee, cycle, mode="m", page=0, edit=True)


@dp.callback_query(F.data.regexp(r"^ui:m:f:\d+$"))
async def cb_mark_one(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[-1])
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await callback.answer("Ошибка", show_alert=True)
        return
    if not get_folder_for_sanash(employee["id"], cycle["id"], folder_id):
        await callback.answer("Недоступно для пересчёта", show_alert=True)
        return
    try:
        cursor.execute(
            "INSERT INTO folder_marks (cycle_id, employee_id, folder_id, marked_at) VALUES (?, ?, ?, ?)",
            (cycle["id"], employee["id"], folder_id, now_str()),
        )
        conn.commit()
        await callback.answer("✅ Готово")
    except sqlite3.IntegrityError:
        await callback.answer("Уже готово")
    await show_folder_picker(callback.message, employee, cycle, mode="m", page=0, edit=True)


@dp.callback_query(F.data.regexp(r"^ui:p:f:\d+$"))
async def cb_pick_folder_submit(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[-1])
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await callback.answer("Ошибка", show_alert=True)
        return
    folder = get_folder_for_sanash(employee["id"], cycle["id"], folder_id)
    if not folder:
        await callback.answer("Недоступно для пересчёта", show_alert=True)
        return
    cursor.execute(
        "SELECT id FROM submissions WHERE cycle_id = ? AND employee_id = ? AND folder_id = ?",
        (cycle["id"], employee["id"], folder_id),
    )
    if cursor.fetchone():
        await callback.answer("Уже сдано", show_alert=True)
        return
    await callback.answer()
    await state.update_data(folder_id=folder["id"], folder_name=folder["name"])
    await state.set_state(SubmitState.waiting_counted_ok)
    stats = employee_work_stats(employee["id"], cycle["id"])
    push_session_start_background(
        tg_id=callback.from_user.id,
        bot_key="sklad",
        user_name=employee["name"],
        activity_type="sklad",
        metadata={"folder": folder["name"], "done": stats["done"], "total": stats["total"]},
    )
    await callback.message.edit_text(
        f"📦 <b>{he(folder['name'])}</b>\n\nОстаток пересчитан на 100% верно?",
        parse_mode=ParseMode.HTML,
        reply_markup=inline_yes_no("c"),
    )


@dp.callback_query(F.data.regexp(r"^ui:y:[clf]:[01]$"))
async def cb_yes_no(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    phase, val = parts[2], int(parts[3])
    data = await state.get_data()
    if not data.get("folder_id"):
        await callback.answer("Сессия завершена", show_alert=True)
        return
    folder_name = data.get("folder_name", "Папка")

    if phase == "c":
        await callback.answer()
        await state.update_data(counted_ok=val)
        await state.set_state(SubmitState.waiting_location_ok)
        await callback.message.edit_text(
            f"📦 <b>{he(folder_name)}</b>\n\nМесто хранения верно на 100%?",
            parse_mode=ParseMode.HTML,
            reply_markup=inline_yes_no("l"),
        )
        return

    if phase == "l":
        await callback.answer()
        await state.update_data(location_ok=val)
        if val == 1:
            await state.update_data(wrong_location_count=0, fixed_now=None)
            await state.set_state(SubmitState.waiting_comment)
            await callback.message.edit_text(
                f"📦 <b>{he(folder_name)}</b>\n\nНапишите комментарий (- если нет):",
                parse_mode=ParseMode.HTML,
            )
            return
        await state.set_state(SubmitState.waiting_wrong_location_count)
        await callback.message.edit_text(
            f"📦 <b>{he(folder_name)}</b>\n\nСколько мест ошибочны? Отправьте число:",
            parse_mode=ParseMode.HTML,
        )
        return

    if phase == "f":
        await callback.answer()
        await state.update_data(fixed_now=val)
        await state.set_state(SubmitState.waiting_comment)
        await callback.message.edit_text(
            f"📦 <b>{he(folder_name)}</b>\n\nНапишите комментарий (- если нет):",
            parse_mode=ParseMode.HTML,
        )


# ==========================================
# GLOBAL
# ==========================================
@dp.message(F.text.in_(BTN_CANCEL_ALL))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=current_menu(message.from_user.id))


@dp.message(Command("reimport"))
async def reimport_command(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Вы не администратор.")
    result = sync_assignments_from_excel(EXCEL_FILE)
    await message.answer(f"✅ {result}")


async def route_employee_menu(message: Message, state: FSMContext):
    """Меню тугмаси — FSM дан чиқиб, керакли бўлимга ўтadi."""
    text = message.text or ""
    if text in BTN_TODAY_ALL:
        return await dashboard_handler(message, state)
    if text in BTN_STATUS_ALL:
        return await status_handler(message)
    if text in BTN_COUNT_ALL:
        return await sanash_handler(message, state)
    if text in BTN_MARK_ALL_SET:
        return await mark_inline_handler(message, state)
    if text in {BTN_MARK_FOLDERS, "📌 Папкаларни белгилаш"}:
        return await mark_folders_start(message, state)
    if text in BTN_ACTIVE_CHECKS_ALL:
        return await active_checks_handler(message)
    if text in BTN_MY_FOLDERS_ALL:
        return await my_folders_handler(message)
    if text in BTN_LOGOUT_ALL:
        return await logout_handler(message, state)
    if text in BTN_HELP_ALL:
        return await help_handler(message)


@dp.message(StateFilter(MarkFoldersState), F.text.in_(EMPLOYEE_MENU_BUTTONS))
async def mark_state_menu_escape(message: Message, state: FSMContext):
    await state.clear()
    return await route_employee_menu(message, state)


@dp.message(StateFilter(SubmitState), F.text.in_(EMPLOYEE_MENU_BUTTONS))
async def submit_state_menu_escape(message: Message, state: FSMContext):
    await state.clear()
    return await route_employee_menu(message, state)


@dp.message()
async def fallback_handler(message: Message):
    if not is_private(message):
        return
    if is_admin(message.from_user.id):
        return await message.answer("Выберите нужный пункт меню.", reply_markup=admin_menu())
    if require_login_or_admin(message):
        return await message.answer("Выберите нужный пункт меню.", reply_markup=employee_menu())
    return await message.answer("Сначала войдите.", reply_markup=login_keyboard())


# ==========================================
# MAIN
# ==========================================
async def main():
    logging.info(persistence_status_line(DB_PATH))
    try:
        day = today_iso()
        cursor.execute(
            """
            SELECT a.telegram_id AS tg_id,
                   SUM(s.counted_ok) AS counted_sum
            FROM submissions s
            JOIN auth_sessions a ON a.employee_id = s.employee_id
            WHERE s.submitted_at LIKE ?
            GROUP BY a.telegram_id
            """,
            (f"{day}%",),
        )
        for row in cursor.fetchall():
            tg_id = int(row["tg_id"] or 0)
            counted = int(row["counted_sum"] or 0)
            if tg_id and counted > 0:
                await push_to_yordamchi_hub(
                    tg_id=tg_id,
                    bot_key="sklad",
                    summary=f"Sklad (bugun jami): sanaldi {counted}",
                    day_iso=day,
                )
    except Exception:
        logging.exception("sklad hub backfill xato")
    from telegram_polling_guard import ensure_polling_mode, webhook_watchdog

    bot = Bot(token=BOT_TOKEN)
    await ensure_polling_mode(bot)
    asyncio.create_task(webhook_watchdog(bot))
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
