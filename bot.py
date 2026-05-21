import asyncio
import os
import re
import secrets
import sqlite3
from datetime import datetime
from typing import Optional

import pandas as pd
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

from bot_ui import (
    FOLDER_PAGE_SIZE,
    build_dashboard_text,
    dashboard_keyboard,
    folder_list_keyboard,
    format_submission_group_html,
    he,
    inline_yes_no,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
EXCEL_FILE = os.getenv("EXCEL_FILE", "groups.xlsx").strip()
DB_PATH = os.getenv("DB_PATH", "sklad_bot.db").strip() or "sklad_bot.db"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi. .env faylni tekshiring.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID topilmadi. .env faylni tekshiring.")
if not GROUP_ID:
    raise ValueError("GROUP_ID topilmadi. .env faylni tekshiring.")


DEFAULT_PASSWORDS = {
    "Ражаббоев Пулат": "431205",
    "Ядуллаев Умид": "582614",
    "Сагдуллаев Юнус": "764193",
    "Тохиров Муслимбек": "295731",
    "Равшанов Зиёдулло": "816452",
    "Мустафоев Абдулло": "540927",
    "Рузибоев Синдор": "673184",
}


# ==========================================
# HELPERS
# ==========================================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
        keyboard=[[KeyboardButton(text="✅ Ҳа"), KeyboardButton(text="❌ Йўқ")]],
        resize_keyboard=True
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Бекор қилиш")]],
        resize_keyboard=True
    )


def login_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔐 Кириш")]],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Ходим қўшиш"), KeyboardButton(text="👥 Барча ходимлар")],
            [KeyboardButton(text="🔐 Парол генерация"), KeyboardButton(text="📄 Пароллар рўйхати")],
            [KeyboardButton(text="➕ Папка қўшиш"), KeyboardButton(text="📁 Барча папкалар")],
            [KeyboardButton(text="🔗 Папка бириктириш"), KeyboardButton(text="📌 Бириктирмалар")],
            [KeyboardButton(text="📥 Excel импорт")],
            [KeyboardButton(text="🚀 Янги цикл очиш"), KeyboardButton(text="🛑 Циклни ёпиш")],
            [KeyboardButton(text="📂 Қолган папкалар"), KeyboardButton(text="📈 Актив цикл ҳолати")],
            [KeyboardButton(text="🗑 Ҳисоботни ўчириш")],
            [KeyboardButton(text="📋 Менга берилган папкалар"), KeyboardButton(text="📝 Актив текширувларим")],
            [KeyboardButton(text="📝 Текширув топшириш"), KeyboardButton(text="📊 Ҳолатим")],
            [KeyboardButton(text="🔓 Чиқиш"), KeyboardButton(text="❓ Ёрдам")],
        ],
        resize_keyboard=True
    )


def employee_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Бугунги иш")],
            [KeyboardButton(text="📝 Санаш")],
            [KeyboardButton(text="📌 Белгилаш")],
            [KeyboardButton(text="❓ Ёрдам"), KeyboardButton(text="🔓 Чиқиш")],
        ],
        resize_keyboard=True,
    )


def mark_folder_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Ҳаммасини белгилаш")],
            [KeyboardButton(text="✅ Белгилаш тугади")],
            [KeyboardButton(text="❌ Бекор қилиш")],
        ],
        resize_keyboard=True,
    )


EMPLOYEE_MENU_BUTTONS = frozenset({
    "📊 Бугунги иш",
    "📝 Санаш",
    "📌 Белгилаш",
    "📌 Папкаларни белгилаш",
    "📝 Текширув топшириш",
    "📝 Актив текширувларим",
    "📋 Белгиланган папкалар",
    "📋 Менга берилган папкалар",
    "📊 Ҳолатим",
    "🔓 Чиқиш",
    "❓ Ёрдам",
})


def count_submitted_folders(employee_id: int, cycle_id: int) -> int:
    cursor.execute(
        "SELECT COUNT(*) AS c FROM submissions WHERE employee_id = ? AND cycle_id = ?",
        (employee_id, cycle_id),
    )
    return int(cursor.fetchone()["c"] or 0)


def employee_work_stats(employee_id: int, cycle_id: int) -> dict:
    assigned = get_employee_assignment_folders(employee_id)
    total = len(assigned)
    unmarked = len(get_unmarked_assignment_folders(employee_id, cycle_id))
    to_submit = len(get_remaining_folders_for_employee(employee_id, cycle_id))
    done = count_submitted_folders(employee_id, cycle_id)
    return {"total": total, "unmarked": unmarked, "to_submit": to_submit, "done": done}


async def send_dashboard(message: Message, employee, cycle, *, edit_message: Optional[Message] = None):
    stats = employee_work_stats(employee["id"], cycle["id"])
    text = build_dashboard_text(
        employee_name=employee["name"],
        cycle_title=cycle["title"],
        total=stats["total"],
        unmarked=stats["unmarked"],
        to_submit=stats["to_submit"],
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
        rows = get_remaining_folders_for_employee(employee["id"], cycle["id"])
        title = "📝 <b>Санаш</b>"
        empty_hint = "📌 Аввал папкаларни белгиланг ёки ҳаммаси саналган."
        pick_prefix = "p"
        mark_all = False
    else:
        rows = get_unmarked_assignment_folders(employee["id"], cycle["id"])
        title = "📌 <b>Белгилаш</b>"
        empty_hint = "✅ Барча папкалар белгиланган."
        pick_prefix = "m"
        mark_all = True

    if not rows:
        if edit:
            try:
                await target.edit_text(empty_hint)
            except Exception:
                pass
        else:
            await target.answer(empty_hint, reply_markup=employee_menu())
        return

    start = page * FOLDER_PAGE_SIZE
    text = (
        f"{title}\n"
        f"{he(cycle['title'])}\n\n"
        f"Танланг ({start + 1}–{min(start + FOLDER_PAGE_SIZE, len(rows))} / {len(rows)}):\n"
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


def get_remaining_folders_for_employee(employee_id: int, cycle_id: int) -> list:
    cursor.execute(
        """
        SELECT f.id, f.name
        FROM folder_marks m
        JOIN folders f ON f.id = m.folder_id
        WHERE m.employee_id = ? AND m.cycle_id = ?
          AND f.id NOT IN (
              SELECT folder_id
              FROM submissions
              WHERE employee_id = ? AND cycle_id = ?
          )
        ORDER BY f.name
        """,
        (employee_id, cycle_id, employee_id, cycle_id),
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


def get_unmarked_assignment_folders(employee_id: int, cycle_id: int) -> list:
    cursor.execute(
        """
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ?
          AND f.id NOT IN (
              SELECT folder_id FROM folder_marks
              WHERE cycle_id = ? AND employee_id = ?
          )
        ORDER BY f.name
        """,
        (employee_id, cycle_id, employee_id),
    )
    return cursor.fetchall()


def is_folder_assigned_to_employee(employee_id: int, folder_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM assignments WHERE employee_id = ? AND folder_id = ?",
        (employee_id, folder_id),
    )
    return cursor.fetchone() is not None


def mark_all_assignment_folders(employee_id: int, cycle_id: int) -> int:
    rows = get_unmarked_assignment_folders(employee_id, cycle_id)
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
        f"📦 Якунланган склад ҳисоботи\n\n"
        f"Цикл: {cycle_title}\n"
        f"Ходим: {employee_name}\n"
        f"Папка: {folder_name}\n"
        f"Остаток тўғри: {'Ҳа' if counted_ok else 'Йўқ'}\n"
        f"Место хранения тўғри: {'Ҳа' if location_ok else 'Йўқ'}\n"
    )
    if location_ok == 0:
        report_text += (
            f"Хато место сони: {wrong_location_count}\n"
            f"Тўғирланди: {'Ҳа' if fixed_now else 'Йўқ'}\n"
        )
    report_text += f"Изоҳ: {comment}\nВақт: {submitted_at}"
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
        return ["Ҳеч кимга папка бириктирилмаган (Excel)."]

    header = (
        f"📂 НАЗОРАТ (актив текширув)\n\n"
        f"Цикл: {cycle_title}\n"
        f"📌 = белгилаш керак | 📝 = ҳисобот керак (гуруҳга ҳали кетмаган)\n\n"
    )
    parts = []
    current = header

    for emp in employees:
        unmarked = get_unmarked_assignment_folders(emp["id"], cycle_id)
        pending_submit = get_remaining_folders_for_employee(emp["id"], cycle_id)
        block = f"🔹 {emp['name']}\n"
        if unmarked:
            block += f"   📌 Белгилаш керак ({len(unmarked)}):\n"
            for row in unmarked:
                block += f"      • {row['name']}\n"
        if pending_submit:
            block += f"   📝 Ҳисобот керак ({len(pending_submit)}):\n"
            for row in pending_submit:
                block += f"      • {row['name']}\n"
        if not unmarked and not pending_submit:
            block += "   ✅ Тайёр\n"
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


setup_db()


def get_employee_by_tg(telegram_id: int) -> Optional[sqlite3.Row]:
    cursor.execute("SELECT * FROM employees WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone()


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
        employee_name = clean_text(row.get("Центральный склад"))

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
    return f"Импорт тайёр: ходим={added_employees}, папка={added_folders}, бириктириш={added_assignments}"


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

    for _, row in df.iterrows():
        folder_name = clean_text(row.get("Наименование"))
        employee_name = clean_text(row.get("Центральный склад"))

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

    conn.commit()
    ensure_default_passwords()
    return (
        f"Синхрон тайёр: жами={len(desired_ids)}, қўшилди={added}, ўчирилди={removed}, "
        f"ходим+={added_employees}, папка+={added_folders}"
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
        return await message.answer("Ҳали цикллар йўқ.")

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
        f"📊 УМУМИЙ СКЛАД ҲИСОБОТИ\n\n"
        f"Цикл: {cycle_title}\n"
        f"Жами белгиланган папкалар: {total_assignments}\n"
        f"Топширилган ҳисоботлар: {total_submitted}\n"
        f"Қолган папкалар: {max(total_assignments - total_submitted, 0)}\n\n"
        f"✅ Остаток тўғри: {counted_ok}\n"
        f"✅ Место хранения тўғри: {location_ok}\n"
        f"❌ Жами хато место сони: {total_wrong_locations}\n"
    )

    await message.answer(report)


@dp.message(Command("hodimlar"), F.chat.id == GROUP_ID)
async def group_employee_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_cycle_for_reports()
    if not cycle:
        return await message.answer("Ҳали цикллар йўқ.")

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
        return await message.answer("Ҳозирча ходимлар ҳисоботи учун маълумот йўқ.")

    text = f"👥 ХОДИМЛАР ҲИСОБОТИ\n\nЦикл: {cycle_title}\n\n"
    for row in rows:
        assigned = row["assigned_count"] or 0  # белгиланган папкалар
        submitted = row["submitted_count"] or 0
        counted_ok = row["counted_ok_count"] or 0
        location_ok = row["location_ok_count"] or 0
        wrong_locations = row["wrong_locations"] or 0
        remaining = max(assigned - submitted, 0)

        text += (
            f"🔹 {row['name']}\n"
            f"   • Бириктирилган папка: {assigned}\n"
            f"   • Топширилгани: {submitted}\n"
            f"   • Қолгани: {remaining}\n"
            f"   • Остаток тўғри: {counted_ok}\n"
            f"   • Место тўғри: {location_ok}\n"
            f"   • Хато место сони: {wrong_locations}\n\n"
        )

    for part in chunk_text(text):
        await message.answer(part)


@dp.message(Command("qolgan"), F.chat.id == GROUP_ID)
async def group_remaining_folders_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_active_cycle() or get_cycle_for_reports()
    if not cycle:
        return await message.answer("Актив ёки охирги цикл топилмади.")

    for part in build_admin_remaining_folders_report(cycle):
        await message.answer(part)


@dp.message(Command("papkalar"), F.chat.id == GROUP_ID)
async def group_folder_report(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cycle = get_cycle_for_reports()
    if not cycle:
        return await message.answer("Ҳали цикллар йўқ.")

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
        return await message.answer("Ҳозирча папкалар ҳисоботи учун маълумот йўқ.")

    text = f"📁 ПАПКАЛАР ҲИСОБОТИ\n\nЦикл: {cycle_title}\n\n"
    for row in rows:
        text += (
            f"📦 {row['folder_name']}\n"
            f"   • Ходим: {row['employee_name']}\n"
            f"   • Остаток: {'Тўғри' if row['counted_ok'] else 'Нотўғри'}\n"
            f"   • Место: {'Тўғри' if row['location_ok'] else 'Нотўғри'}\n"
        )
        if row["location_ok"] == 0:
            text += (
                f"   • Хато место сони: {row['wrong_location_count']}\n"
                f"   • Тўғирланди: {'Ҳа' if row['fixed_now'] else 'Йўқ'}\n"
            )
        text += (
            f"   • Изоҳ: {row['comment']}\n"
            f"   • Вақт: {row['submitted_at']}\n\n"
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
            f"🔥 Админ режимида кирдингиз.\n\n{startup_import_result}\n\n"
            "📂 Қолган папкалар · /qolgan",
            reply_markup=admin_menu(),
        )
        return

    existing = get_employee_by_tg(message.from_user.id)
    if existing:
        set_session(message.from_user.id, existing["id"])
        await message.answer(
            f"🔥 Хуш келибсиз, {he(existing['name'])}\n\n📊 Бугунги иш — бошлаш.",
            reply_markup=employee_menu(),
            parse_mode=ParseMode.HTML,
        )
        return

    session_emp = get_logged_in_employee(message.from_user.id)
    if session_emp:
        await message.answer(
            f"🔥 Хуш келибсиз, {he(session_emp['name'])}\n\n📊 Бугунги иш — бошлаш.",
            reply_markup=employee_menu(),
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(
        "Сизга пароль орқали кириш керак.\nАдмин берган пароль билан киринг.",
        reply_markup=login_keyboard()
    )


@dp.message(F.text == "🔐 Кириш")
async def login_begin(message: Message, state: FSMContext):
    if not is_private(message):
        return

    if is_admin(message.from_user.id):
        return await message.answer("Сиз админсиз.", reply_markup=admin_menu())

    await state.set_state(LoginState.waiting_password)
    await message.answer("Паролни киритинг:", reply_markup=cancel_keyboard())


@dp.message(LoginState.waiting_password)
async def login_password(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=login_keyboard())

    password = clean_text(message.text)
    cursor.execute("SELECT * FROM employees WHERE password = ? AND is_active = 1", (password,))
    employee = cursor.fetchone()

    if not employee:
        return await message.answer("Пароль нотўғри.")

    if employee["telegram_id"] is None:
        cursor.execute("UPDATE employees SET telegram_id = ? WHERE id = ?", (message.from_user.id, employee["id"]))
        conn.commit()
    elif int(employee["telegram_id"]) != int(message.from_user.id):
        return await message.answer(
            "Бу пароль бошқа Telegram аккаунтга бириктирилган.\nАдминга мурожаат қилинг."
        )

    set_session(message.from_user.id, employee["id"])
    await state.clear()
    await message.answer(
        f"✅ Кириш муваффақиятли.\nХодим: {employee['name']}",
        reply_markup=employee_menu()
    )


@dp.message(F.text == "🔓 Чиқиш")
async def logout_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return

    await state.clear()
    clear_session(message.from_user.id)

    if is_admin(message.from_user.id):
        return await message.answer("Админ чиқиши шарт эмас.", reply_markup=admin_menu())

    await message.answer("Чиқиб кетдингиз.", reply_markup=login_keyboard())


def require_login_or_admin(message: Message) -> bool:
    if is_admin(message.from_user.id):
        return True
    return get_logged_in_employee(message.from_user.id) is not None or get_employee_by_tg(message.from_user.id) is not None


# ==========================================
# USER / ADMIN COMMON
# ==========================================
@dp.message(F.text == "❓ Ёрдам")
async def help_handler(message: Message):
    if not is_private(message):
        return
    text = (
        "Бу бот склад назорати учун.\n\n"
        "• Ходимлар личкада ишлайди\n"
        "• Гуруҳга фақат якунланган ҳисобот кетади\n"
        "• Гуруҳда /hisobot /hodimlar /papkalar /qolgan командалари ишлайди\n"
        "• 📊 Бугунги иш — прогресс ва қисқа холат\n"
        "• 📌 Белгилаш — inline тугма (гуруҳга кетмайди)\n"
        "• 📝 Санаш — inline тугма (гуруҳга кетади)\n"
        "• /sanash /holat — тез буйруқлар\n"
        "• Меню янгиланмаса: /start ёки /menu"
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
            "✅ Админ меню янгиланди.\n📂 Қолган папкалар — шу тугма ёки /qolgan",
            reply_markup=admin_menu(),
        )
    session_emp = get_logged_in_employee(message.from_user.id) or get_employee_by_tg(message.from_user.id)
    if session_emp:
        return await message.answer(
            "✅ Меню янгиланди.\n📊 Бугунги иш · 📝 Санаш · 📌 Белгилаш",
            reply_markup=employee_menu(),
        )
    await message.answer("Аввал киринг.", reply_markup=login_keyboard())


@dp.message(F.text.in_({"📋 Менга берилган папкалар", "📋 Белгиланган папкалар"}))
async def my_folders_handler(message: Message):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())

    if is_admin(message.from_user.id):
        return await message.answer("Админ учун бу бўлим шарт эмас.")

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")
    if not cycle:
        return await message.answer("Актив цикл йўқ.")

    rows = get_marked_folders(employee["id"], cycle["id"])
    if not rows:
        return await message.answer(
            "Ҳали папка белгиламагансиз.\n📌 Папкаларни белгилаш тугмасини босинг.",
            reply_markup=employee_menu(),
        )

    text = f"📋 Белгиланган папкалар ({cycle['title']}):\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"
    await message.answer(text, reply_markup=employee_menu())


@dp.message(F.text == "📝 Актив текширувларим")
async def active_checks_handler(message: Message):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Ҳозирча актив цикл йўқ.")

    if is_admin(message.from_user.id):
        for part in build_admin_remaining_folders_report(cycle):
            await message.answer(part, reply_markup=admin_menu())
        return

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")

    rows = get_unmarked_assignment_folders(employee["id"], cycle["id"])

    if not rows:
        pending = get_remaining_folders_for_employee(employee["id"], cycle["id"])
        if pending:
            return await message.answer(
                f"✅ Барча папкалар белгиланган.\n"
                f"📝 Текширув топшириш: {len(pending)} та ҳисобот қолди.\n\nЦикл: {cycle['title']}",
                reply_markup=employee_menu(),
            )
        return await message.answer(
            f"✅ Ҳаммаси бажарилди.\n\nЦикл: {cycle['title']}",
            reply_markup=employee_menu(),
        )

    text = (
        f"📝 Актив текширувларим\n\nЦикл: {cycle['title']}\n"
        f"📌 Аввал белгиланг (гуруҳга кетмайди):\n\n"
    )
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"
    text += "\n📌 Папкаларни белгилаш тугмаси орқали белгиланг."
    await message.answer(text, reply_markup=employee_menu())


@dp.message(F.text == "📂 Қолган папкалар")
async def admin_remaining_folders_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer(
            "Актив цикл йўқ.\nЯнги цикл очинг ёки охирги циклни кўриш учун гуруҳда /qolgan ишлатинг."
        )

    for part in build_admin_remaining_folders_report(cycle):
        await message.answer(part, reply_markup=admin_menu())


@dp.message(Command("qolgan"))
async def admin_remaining_folders_command(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cycle = get_active_cycle() or get_cycle_for_reports()
    if not cycle:
        return await message.answer("Актив ёки охирги цикл топилмади.")

    for part in build_admin_remaining_folders_report(cycle):
        await message.answer(part, reply_markup=admin_menu())


@dp.message(F.text == "📊 Ҳолатим")
async def status_handler(message: Message):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Актив цикл йўқ.")

    if is_admin(message.from_user.id):
        cursor.execute("SELECT COUNT(*) AS c FROM folder_marks WHERE cycle_id = ?", (cycle["id"],))
        total = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle["id"],))
        done = cursor.fetchone()["c"]
        return await message.answer(
            f"📈 Админ ҳолати\n\n"
            f"Цикл: {cycle['title']}\n"
            f"Белгиланган папкалар: {total}\n"
            f"Топширилган ҳисоботлар: {done}\n"
            f"Қолгани: {max(total - done, 0)}\n\n"
            f"Батафсил: 📂 Қолган папкалар"
        )

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")

    cursor.execute("SELECT COUNT(*) AS c FROM folder_marks WHERE employee_id = ? AND cycle_id = ?", (employee["id"], cycle["id"]))
    total = cursor.fetchone()["c"]
    cursor.execute(
        "SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ? AND employee_id = ?",
        (cycle["id"], employee["id"])
    )
    done = cursor.fetchone()["c"]

    await message.answer(
        f"📊 Ҳолатингиз\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Белгиланган папкалар: {total}\n"
        f"Топширилганлари: {done}\n"
        f"Қолгани: {max(total - done, 0)}"
    )


# ==========================================
# ADMIN: EMPLOYEES
# ==========================================
@dp.message(F.text == "➕ Ходим қўшиш")
async def add_employee_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")
    await state.set_state(AddEmployeeState.waiting_name)
    await message.answer("Ходим исмини ёзинг:", reply_markup=cancel_keyboard())


@dp.message(AddEmployeeState.waiting_name)
async def add_employee_name(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    name = clean_text(message.text)
    if not name:
        return await message.answer("Исм бўш бўлмаслиги керак.")

    await state.update_data(name=name)
    await state.set_state(AddEmployeeState.waiting_tg_id)
    await message.answer("Telegram ID ни юборинг. Агар ҳозирча йўқ бўлса 0 ёзинг.")


@dp.message(AddEmployeeState.waiting_tg_id)
async def add_employee_tg(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    value = (message.text or "").strip()
    if not re.fullmatch(r"-?\d+", value):
        return await message.answer("ID рақам бўлиши керак.")

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
            f"✅ Ходим қўшилди:\nИсм: {name}\nTelegram ID: {tg_value or 'йўқ'}",
            reply_markup=admin_menu()
        )
    except sqlite3.IntegrityError:
        cursor.execute("SELECT * FROM employees WHERE telegram_id = ?", (tg_value,))
        existing = cursor.fetchone()
        if existing:
            await message.answer(
                f"⚠️ Бу Telegram ID аллақачон бошқа ходимга бириктирилган:\n{existing['name']}",
                reply_markup=admin_menu()
            )
        else:
            await message.answer("⚠️ Бу ходим аввал қўшилган.", reply_markup=admin_menu())

    await state.clear()


@dp.message(F.text == "👥 Барча ходимлар")
async def all_employees_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name, telegram_id, password FROM employees ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Ходимлар йўқ.")

    text = "👥 Барча ходимлар:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']} | TG: {row['telegram_id'] or 'йўқ'} | Пароль: {row['password'] or 'йўқ'}\n"
    await message.answer(text)


@dp.message(F.text == "🔐 Парол генерация")
async def generate_passwords_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name FROM employees ORDER BY id")
    rows = cursor.fetchall()
    changed = 0

    for row in rows:
        name = row["name"]
        new_pwd = DEFAULT_PASSWORDS.get(name) or "".join(secrets.choice("0123456789") for _ in range(6))
        cursor.execute("UPDATE employees SET password = ? WHERE id = ?", (new_pwd, row["id"]))
        changed += 1

    conn.commit()
    await message.answer(f"✅ {changed} та ходимга пароль тайинланди.", reply_markup=admin_menu())


@dp.message(F.text == "📄 Пароллар рўйхати")
async def passwords_list_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name, password FROM employees ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Ходимлар йўқ.")

    text = "📄 Пароллар рўйхати:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']} → {row['password'] or 'йўқ'}\n"
    for part in chunk_text(text):
        await message.answer(part)


# ==========================================
# ADMIN: FOLDERS / ASSIGNMENTS
# ==========================================
@dp.message(F.text == "➕ Папка қўшиш")
async def add_folder_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")
    await state.set_state(AddFolderState.waiting_folder_name)
    await message.answer("Янги папка номини ёзинг:", reply_markup=cancel_keyboard())


@dp.message(AddFolderState.waiting_folder_name)
async def add_folder_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    folder_name = clean_text(message.text)
    if not folder_name:
        return await message.answer("Папка номи бўш бўлмаслиги керак.")

    try:
        cursor.execute("INSERT INTO folders (name, created_at) VALUES (?, ?)", (folder_name, now_str()))
        conn.commit()
        await message.answer(f"✅ Папка қўшилди:\n{folder_name}", reply_markup=admin_menu())
    except sqlite3.IntegrityError:
        await message.answer(f"⚠️ Бу папка аввал қўшилган:\n{folder_name}", reply_markup=admin_menu())

    await state.clear()


@dp.message(F.text == "📁 Барча папкалар")
async def all_folders_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name FROM folders ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Папкалар йўқ.")

    text = "📁 Барча папкалар:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"
    for part in chunk_text(text):
        await message.answer(part)


@dp.message(F.text == "🔗 Папка бириктириш")
async def assign_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name, telegram_id FROM employees ORDER BY id")
    employees = cursor.fetchall()
    if not employees:
        return await message.answer("Аввал ходим қўшинг.")

    text = "Ходим ID рақамини юборинг.\n\n👥 Ходимлар:\n"
    for row in employees:
        text += f"{row['id']}. {row['name']} — TG ID: {row['telegram_id'] or 'йўқ'}\n"

    await state.set_state(AssignState.waiting_employee_id)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(AssignState.waiting_employee_id)
async def assign_get_employee(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    if not (message.text or "").isdigit():
        return await message.answer("Ходим ID рақам бўлиши керак.")

    employee_id = int(message.text)
    employee = get_employee_by_id(employee_id)
    if not employee:
        return await message.answer("Бундай ходим ID топилмади.")

    await state.update_data(employee_id=employee_id)

    cursor.execute("SELECT id, name FROM folders ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        await state.clear()
        return await message.answer("Аввал папка қўшинг.", reply_markup=admin_menu())

    text = "Энди папка ID рақамини юборинг.\n\n📁 Папкалар:\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"

    await state.set_state(AssignState.waiting_folder_id)
    await message.answer(text)


@dp.message(AssignState.waiting_folder_id)
async def assign_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    if not (message.text or "").isdigit():
        return await message.answer("Папка ID рақам бўлиши керак.")

    folder_id = int(message.text)
    data = await state.get_data()
    employee_id = data["employee_id"]

    employee = get_employee_by_id(employee_id)
    folder = get_folder_by_id(folder_id)

    if not employee:
        await state.clear()
        return await message.answer("Ходим топилмади.", reply_markup=admin_menu())
    if not folder:
        return await message.answer("Папка топилмади.")

    try:
        cursor.execute(
            "INSERT INTO assignments (employee_id, folder_id) VALUES (?, ?)",
            (employee_id, folder_id)
        )
        conn.commit()
        await message.answer(
            f"✅ Бириктирилди:\nХодим: {employee['name']}\nПапка: {folder['name']}",
            reply_markup=admin_menu()
        )
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Бу папка шу ходимга аввал бириктирилган.", reply_markup=admin_menu())

    await state.clear()


@dp.message(F.text == "📌 Бириктирмалар")
async def assignments_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("""
        SELECT a.id, e.name AS employee_name, e.telegram_id, f.name AS folder_name
        FROM assignments a
        JOIN employees e ON e.id = a.employee_id
        JOIN folders f ON f.id = a.folder_id
        ORDER BY a.id
    """)
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Бириктирмалар йўқ.")

    text = "📌 Бириктирмалар:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['employee_name']} ({row['telegram_id'] or 'йўқ'}) → {row['folder_name']}\n"
    for part in chunk_text(text):
        await message.answer(part)


# ==========================================
# ADMIN: IMPORT / CYCLES
# ==========================================
@dp.message(F.text == "📥 Excel импорт")
async def excel_import_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    result = sync_assignments_from_excel(EXCEL_FILE)
    await message.answer(f"✅ {result}")


@dp.message(F.text == "🚀 Янги цикл очиш")
async def open_cycle_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    active = get_active_cycle()
    if active:
        return await message.answer(f"Актив цикл бор: {active['title']}\nАввал уни ёпинг.")

    await state.set_state(OpenCycleState.waiting_title)
    await message.answer("Янги цикл номи/сарлавҳасини ёзинг:", reply_markup=cancel_keyboard())


@dp.message(OpenCycleState.waiting_title)
async def open_cycle_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    title = clean_text(message.text)
    if not title:
        return await message.answer("Цикл номи бўш бўлмаслиги керак.")

    cursor.execute(
        "INSERT INTO cycles (title, is_active, created_at) VALUES (?, 1, ?)",
        (title, now_str())
    )
    conn.commit()

    await state.clear()
    await message.answer(f"✅ Янги цикл очилди:\n{title}", reply_markup=admin_menu())


@dp.message(F.text == "🛑 Циклни ёпиш")
async def close_cycle_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    active = get_active_cycle()
    if not active:
        return await message.answer("Актив цикл йўқ.")

    cursor.execute("UPDATE cycles SET is_active = 0 WHERE id = ?", (active["id"],))
    conn.commit()
    await message.answer(f"🛑 Цикл ёпилди:\n{active['title']}", reply_markup=admin_menu())


@dp.message(F.text == "📈 Актив цикл ҳолати")
async def active_cycle_status_handler(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Актив цикл йўқ.")

    cursor.execute("SELECT COUNT(*) AS c FROM folder_marks WHERE cycle_id = ?", (cycle["id"],))
    total_marks = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle["id"],))
    submitted = cursor.fetchone()["c"]
    text = (
        f"📈 Актив цикл ҳолати\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Белгиланган папкалар: {total_marks}\n"
        f"Топширилган ҳисоботлар: {submitted}\n"
        f"Қолгани: {max(total_marks - submitted, 0)}"
    )
    await message.answer(text)


# ==========================================
# FOLDER MARKING (ходим ўзи белгилайди)
# ==========================================
@dp.message(F.text == "📌 Папкаларни белгилаш")
async def mark_folders_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Админ учун бу бўлим ишлатилмайди.")

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")
    if not cycle:
        return await message.answer("Ҳозирча актив цикл йўқ.")

    assigned = get_employee_assignment_folders(employee["id"])
    if not assigned:
        return await message.answer(
            f"Сизга Excel бўйича папка бириктирилмаган.\n"
            f"Админга мурожаат қилинг (📥 Excel импорт).\n\nХодим: {employee['name']}",
            reply_markup=employee_menu(),
        )

    marked = get_marked_folders(employee["id"], cycle["id"])
    marked_ids = {r["id"] for r in marked}
    unmarked = [r for r in assigned if r["id"] not in marked_ids]

    text = (
        f"📌 Сизнинг папкаларингиз\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Ходим: {employee['name']}\n"
        f"Жами сизга: {len(assigned)} та | Белгиланган: {len(marked)} | Қолди: {len(unmarked)}\n\n"
    )
    for row in assigned:
        flag = "✅" if row["id"] in marked_ids else "⬜"
        text += f"{flag} {row['id']}. {row['name']}\n"

    text += (
        "\n➕ ID юборинг (масалан: 12 45) ёки ✅ Ҳаммасини белгилаш\n"
        "✅ Белгилаш тугади — тугмаси\n"
    )

    await state.set_state(MarkFoldersState.waiting_folder_ids)
    for part in chunk_text(text):
        await message.answer(part, reply_markup=mark_folder_keyboard())


@dp.message(MarkFoldersState.waiting_folder_ids)
async def mark_folders_add(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=employee_menu())

    if message.text == "✅ Белгилаш тугади":
        await state.clear()
        employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
        cycle = get_active_cycle()
        if not employee or not cycle:
            return await message.answer("Ходим ёки цикл топилмади.", reply_markup=employee_menu())
        marked = get_marked_folders(employee["id"], cycle["id"])
        return await message.answer(
            f"✅ {len(marked)} та папка белгиланган (активдан чиқди).\n"
            "📝 Текширув топшириш — ҳисобот гуруҳга кетади.",
            reply_markup=employee_menu(),
        )

    if message.text == "✅ Ҳаммасини белгилаш":
        employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
        cycle = get_active_cycle()
        if not employee or not cycle:
            await state.clear()
            return await message.answer("Ходим ёки цикл топилмади.", reply_markup=employee_menu())
        added = mark_all_assignment_folders(employee["id"], cycle["id"])
        marked = get_marked_folders(employee["id"], cycle["id"])
        return await message.answer(
            f"✅ {added} та янги папка белгиланди.\nЖами: {len(marked)} та.\n"
            "Актив рўйхатдан чиқди. Энди 📝 Текширув топшириш.",
            reply_markup=mark_folder_keyboard(),
        )

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await state.clear()
        return await message.answer("Ходим ёки цикл топилмади.", reply_markup=employee_menu())

    folder_ids = parse_folder_id_list(message.text or "")
    if not folder_ids:
        return await message.answer("Папка ID рақамларини юборинг. Масалан: 12 45 67")

    added = 0
    skipped = 0
    errors = []
    for folder_id in folder_ids:
        folder = get_folder_by_id(folder_id)
        if not folder:
            errors.append(f"ID {folder_id} топилмади")
            continue
        if not is_folder_assigned_to_employee(employee["id"], folder_id):
            errors.append(f"{folder['name']} — сизга бириктирилмаган")
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

    reply = f"✅ {added} та папка белгиланди."
    if skipped:
        reply += f"\n⚠️ {skipped} та ўтказилди (аввал банд/сизда бор)."
    if errors:
        reply += "\n" + "\n".join(errors[:5])
    reply += "\n\nЯна ID юборинг ёки ✅ Белгилаш тугади."
    await message.answer(reply, reply_markup=mark_folder_keyboard())


# ==========================================
# DASHBOARD & INLINE UI
# ==========================================
@dp.message(F.text.in_({"📊 Бугунги иш", "📊 Ҳолатим"}))
async def dashboard_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        cycle = get_active_cycle() or get_cycle_for_reports()
        if not cycle:
            return await message.answer("Актив цикл йўқ.")
        for part in build_admin_remaining_folders_report(cycle):
            await message.answer(part, reply_markup=admin_menu())
        return
    await state.clear()
    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")
    if not cycle:
        return await message.answer("Ҳозирча актив цикл йўқ.")
    await send_dashboard(message, employee, cycle)


@dp.message(Command("holat"))
async def cmd_holat(message: Message, state: FSMContext):
    return await dashboard_handler(message, state)


@dp.message(F.text.in_({"📝 Санаш", "📝 Текширув топшириш"}))
@dp.message(Command("sanash"))
async def sanash_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Админ учун эмас.")
    await state.clear()
    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await message.answer("Ходим ёки цикл топилмади.")
    await show_folder_picker(message, employee, cycle, mode="p", page=0, edit=False)


@dp.message(F.text.in_({"📌 Белгилаш", "📌 Папкаларни белгилаш"}))
async def mark_inline_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login_or_admin(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Админ учун эмас.")
    await state.clear()
    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await message.answer("Ходим ёки цикл топилмади.")
    assigned = get_employee_assignment_folders(employee["id"])
    if not assigned:
        return await message.answer("Сизга Excel бўйича папка бириктирилмаган.", reply_markup=employee_menu())
    await show_folder_picker(message, employee, cycle, mode="m", page=0, edit=False)


# ==========================================
# REPORT SUBMISSION (матн: изоҳ, хато сони)
# ==========================================
@dp.message(SubmitState.waiting_folder_id)
async def submit_get_folder(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=employee_menu())

    if not (message.text or "").isdigit():
        return await message.answer("Папка ID рақам бўлиши керак.")

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()

    if not employee or not cycle:
        await state.clear()
        return await message.answer("Ходим ёки актив цикл топилмади.", reply_markup=employee_menu())

    folder_id = int(message.text)

    cursor.execute("""
        SELECT f.id, f.name
        FROM folder_marks m
        JOIN folders f ON f.id = m.folder_id
        WHERE m.employee_id = ? AND m.cycle_id = ? AND f.id = ?
    """, (employee["id"], cycle["id"], folder_id))
    folder = cursor.fetchone()

    if not folder:
        return await message.answer("Бу папка сиз белгиламагансиз. Аввал 📌 Папкаларни белгилаш.")

    cursor.execute("""
        SELECT id FROM submissions
        WHERE cycle_id = ? AND employee_id = ? AND folder_id = ?
    """, (cycle["id"], employee["id"], folder_id))
    existing = cursor.fetchone()

    if existing:
        return await message.answer("Бу папка бўйича ҳисобот аввал топширилган.")

    await state.update_data(folder_id=folder["id"], folder_name=folder["name"])
    await state.set_state(SubmitState.waiting_counted_ok)
    await message.answer(
        f"Папка: {folder['name']}\n\nОстаток 100% тўғри саналдими?",
        reply_markup=yes_no_keyboard()
    )


@dp.message(SubmitState.waiting_counted_ok)
async def submit_counted_ok(message: Message, state: FSMContext):
    if message.text not in ["✅ Ҳа", "❌ Йўқ"]:
        return await message.answer("Тугмадан жавоб беринг.")
    counted_ok = 1 if message.text == "✅ Ҳа" else 0
    await state.update_data(counted_ok=counted_ok)
    await state.set_state(SubmitState.waiting_location_ok)
    await message.answer("Место хранения 100% тўғрими?", reply_markup=yes_no_keyboard())


@dp.message(SubmitState.waiting_location_ok)
async def submit_location_ok(message: Message, state: FSMContext):
    if message.text not in ["✅ Ҳа", "❌ Йўқ"]:
        return await message.answer("Тугмадан жавоб беринг.")

    location_ok = 1 if message.text == "✅ Ҳа" else 0
    await state.update_data(location_ok=location_ok)

    if location_ok == 1:
        await state.update_data(wrong_location_count=0, fixed_now=None)
        await state.set_state(SubmitState.waiting_comment)
        return await message.answer(
            "Изоҳ ёзинг.\nАгар изоҳ йўқ бўлса: -",
            reply_markup=ReplyKeyboardRemove()
        )

    await state.set_state(SubmitState.waiting_wrong_location_count)
    await message.answer("Нечта место хато чиққан? Рақам билан ёзинг:", reply_markup=ReplyKeyboardRemove())


@dp.message(SubmitState.waiting_wrong_location_count)
async def submit_wrong_location_count(message: Message, state: FSMContext):
    value = clean_text(message.text)
    if not value.isdigit():
        return await message.answer("Рақам ёзинг. Масалан: 3")

    await state.update_data(wrong_location_count=int(value))
    await state.set_state(SubmitState.waiting_fixed_now)
    await message.answer("Хато местолар тўғирландими?", reply_markup=yes_no_keyboard())


@dp.message(SubmitState.waiting_fixed_now)
async def submit_fixed_now(message: Message, state: FSMContext):
    if message.text not in ["✅ Ҳа", "❌ Йўқ"]:
        return await message.answer("Тугмадан жавоб беринг.")
    fixed_now = 1 if message.text == "✅ Ҳа" else 0
    await state.update_data(fixed_now=fixed_now)
    await state.set_state(SubmitState.waiting_comment)
    await message.answer("Изоҳ ёзинг.\nАгар изоҳ йўқ бўлса: -", reply_markup=ReplyKeyboardRemove())


@dp.message(SubmitState.waiting_comment)
async def submit_comment(message: Message, state: FSMContext, bot: Bot):
    comment = clean_text(message.text) or "-"

    employee = get_employee_by_tg(message.from_user.id) or get_logged_in_employee(message.from_user.id)
    cycle = get_active_cycle()

    if not employee or not cycle:
        await state.clear()
        return await message.answer("Ходим ёки актив цикл топилмади.", reply_markup=employee_menu())

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

    report_text = format_submission_group_html(
        cycle["title"],
        employee["name"],
        folder_name,
        counted_ok=counted_ok,
        location_ok=location_ok,
        wrong_location_count=wrong_location_count,
        fixed_now=fixed_now,
        comment=comment,
        submitted_at=submitted_at,
    )
    try:
        await bot.send_message(GROUP_ID, report_text, parse_mode=ParseMode.HTML)
        group_note = "Гуруҳга юборилди."
    except Exception as e:
        group_note = f"⚠️ Гуруҳга юборишда муаммо: {e}"

    await state.clear()
    await message.answer(
        f"✅ Ҳисобот қабул қилинди.\n{group_note}",
        reply_markup=employee_menu(),
        parse_mode=ParseMode.HTML,
    )
    await send_dashboard(message, employee, cycle)


# ==========================================
# ADMIN: DELETE REPORTS
# ==========================================
@dp.message(F.text == "🗑 Ҳисоботни ўчириш")
async def delete_report_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")

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
        return await message.answer("Ўчириладиган ҳисоботлар йўқ.")

    text = "Ўчириш учун ҳисобот ID рақамини юборинг.\n\nСўнгги 20 ҳисобот:\n"
    for row in rows:
        text += f"{row['id']}. {row['employee_name']} | {row['folder_name']} | {row['title']} | {row['submitted_at']}\n"

    await state.set_state(DeleteReportState.waiting_submission_id)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(DeleteReportState.waiting_submission_id)
async def delete_report_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=admin_menu())

    if not (message.text or "").isdigit():
        return await message.answer("Ҳисобот ID рақам бўлиши керак.")

    submission_id = int(message.text)

    cursor.execute("SELECT id FROM submissions WHERE id = ?", (submission_id,))
    row = cursor.fetchone()
    if not row:
        return await message.answer("Бундай ҳисобот топилмади.")

    cursor.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    conn.commit()

    await state.clear()
    await message.answer(f"🗑 Ҳисобот ўчирилди. ID: {submission_id}", reply_markup=admin_menu())


# ==========================================
# INLINE CALLBACKS
# ==========================================
@dp.callback_query(F.data == "ui:x")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Бекор")
    try:
        await callback.message.edit_text("❌ Бекор қилинди.")
    except Exception:
        pass
    await callback.message.answer("Менюдан танланг.", reply_markup=current_menu(callback.from_user.id))


@dp.callback_query(F.data == "ui:go:dash")
async def cb_go_dashboard(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await callback.message.answer("Ходим ёки цикл топилмади.")
    stats = employee_work_stats(employee["id"], cycle["id"])
    text = build_dashboard_text(
        employee_name=employee["name"],
        cycle_title=cycle["title"],
        total=stats["total"],
        unmarked=stats["unmarked"],
        to_submit=stats["to_submit"],
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
        return await callback.message.answer("Ходим ёки цикл топилмади.")
    await show_folder_picker(callback.message, employee, cycle, mode="p", page=0, edit=True)


@dp.callback_query(F.data == "ui:go:mark")
async def cb_go_mark(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return await callback.message.answer("Ходим ёки цикл топилмади.")
    await show_folder_picker(callback.message, employee, cycle, mode="m", page=0, edit=True)


@dp.callback_query(F.data == "ui:go:list")
async def cb_go_list(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        return
    rows = get_marked_folders(employee["id"], cycle["id"])
    text = f"<b>📋 Белгиланган</b> ({len(rows)}):\n\n"
    for row in rows[:40]:
        text += f"• {he(row['name'])}\n"
    if len(rows) > 40:
        text += f"\n<i>… ва яна {len(rows) - 40} та</i>"
    await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=employee_menu())


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
        await callback.answer("Хато", show_alert=True)
        return
    added = mark_all_assignment_folders(employee["id"], cycle["id"])
    await callback.answer(f"✅ {added} та белгиланди", show_alert=True)
    await show_folder_picker(callback.message, employee, cycle, mode="m", page=0, edit=True)


@dp.callback_query(F.data.regexp(r"^ui:m:f:\d+$"))
async def cb_mark_one(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[-1])
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await callback.answer("Хато", show_alert=True)
        return
    if not is_folder_assigned_to_employee(employee["id"], folder_id):
        await callback.answer("Сизга бириктирилмаган", show_alert=True)
        return
    try:
        cursor.execute(
            "INSERT INTO folder_marks (cycle_id, employee_id, folder_id, marked_at) VALUES (?, ?, ?, ?)",
            (cycle["id"], employee["id"], folder_id, now_str()),
        )
        conn.commit()
        await callback.answer("✅ Белгиланди")
    except sqlite3.IntegrityError:
        await callback.answer("Аввал белгиланган")
    await show_folder_picker(callback.message, employee, cycle, mode="m", page=0, edit=True)


@dp.callback_query(F.data.regexp(r"^ui:p:f:\d+$"))
async def cb_pick_folder_submit(callback: CallbackQuery, state: FSMContext):
    folder_id = int(callback.data.split(":")[-1])
    employee = get_employee_by_tg(callback.from_user.id) or get_logged_in_employee(callback.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await callback.answer("Хато", show_alert=True)
        return
    cursor.execute(
        """
        SELECT f.id, f.name FROM folder_marks m
        JOIN folders f ON f.id = m.folder_id
        WHERE m.employee_id = ? AND m.cycle_id = ? AND f.id = ?
        """,
        (employee["id"], cycle["id"], folder_id),
    )
    folder = cursor.fetchone()
    if not folder:
        await callback.answer("Аввал белгиланг", show_alert=True)
        return
    cursor.execute(
        "SELECT id FROM submissions WHERE cycle_id = ? AND employee_id = ? AND folder_id = ?",
        (cycle["id"], employee["id"], folder_id),
    )
    if cursor.fetchone():
        await callback.answer("Аввал топширилган", show_alert=True)
        return
    await callback.answer()
    await state.update_data(folder_id=folder["id"], folder_name=folder["name"])
    await state.set_state(SubmitState.waiting_counted_ok)
    await callback.message.edit_text(
        f"📦 <b>{he(folder['name'])}</b>\n\nОстаток 100% тўғри саналдими?",
        parse_mode=ParseMode.HTML,
        reply_markup=inline_yes_no("c"),
    )


@dp.callback_query(F.data.regexp(r"^ui:y:[clf]:[01]$"))
async def cb_yes_no(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    phase, val = parts[2], int(parts[3])
    data = await state.get_data()
    if not data.get("folder_id"):
        await callback.answer("Сессия тугади", show_alert=True)
        return
    folder_name = data.get("folder_name", "Папка")

    if phase == "c":
        await callback.answer()
        await state.update_data(counted_ok=val)
        await state.set_state(SubmitState.waiting_location_ok)
        await callback.message.edit_text(
            f"📦 <b>{he(folder_name)}</b>\n\nМесто хранения 100% тўғрими?",
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
                f"📦 <b>{he(folder_name)}</b>\n\nИзоҳ ёзинг (- агар йўқ бўлса):",
                parse_mode=ParseMode.HTML,
            )
            return
        await state.set_state(SubmitState.waiting_wrong_location_count)
        await callback.message.edit_text(
            f"📦 <b>{he(folder_name)}</b>\n\nНечта жой хато? Рақам юборинг:",
            parse_mode=ParseMode.HTML,
        )
        return

    if phase == "f":
        await callback.answer()
        await state.update_data(fixed_now=val)
        await state.set_state(SubmitState.waiting_comment)
        await callback.message.edit_text(
            f"📦 <b>{he(folder_name)}</b>\n\nИзоҳ ёзинг (- агар йўқ бўлса):",
            parse_mode=ParseMode.HTML,
        )


# ==========================================
# GLOBAL
# ==========================================
@dp.message(F.text == "❌ Бекор қилиш")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Бекор қилинди.", reply_markup=current_menu(message.from_user.id))


@dp.message(Command("reimport"))
async def reimport_command(message: Message):
    if not is_private(message):
        return
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Сиз админ эмассиз.")
    result = sync_assignments_from_excel(EXCEL_FILE)
    await message.answer(f"✅ {result}")


async def route_employee_menu(message: Message, state: FSMContext):
    """Меню тугмаси — FSM дан чиқиб, керакли бўлимга ўтadi."""
    text = message.text or ""
    if text in ("📊 Бугунги иш", "📊 Ҳолатим"):
        return await dashboard_handler(message, state)
    if text in ("📝 Санаш", "📝 Текширув топшириш"):
        return await sanash_handler(message, state)
    if text in ("📌 Белгилаш", "📌 Папкаларни белгилаш"):
        return await mark_inline_handler(message, state)
    if text == "📝 Актив текширувларим":
        return await active_checks_handler(message)
    if text in ("📋 Белгиланган папкалар", "📋 Менга берилган папкалар"):
        return await my_folders_handler(message)
    if text == "🔓 Чиқиш":
        return await logout_handler(message, state)
    if text == "❓ Ёрдам":
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
        return await message.answer("Менюдан керакли бўлимни танланг.", reply_markup=admin_menu())
    if require_login_or_admin(message):
        return await message.answer("Менюдан керакли бўлимни танланг.", reply_markup=employee_menu())
    return await message.answer("Аввал киринг.", reply_markup=login_keyboard())


# ==========================================
# MAIN
# ==========================================
async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
