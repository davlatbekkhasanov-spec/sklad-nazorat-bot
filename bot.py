import asyncio
import os
import re
import secrets
import sqlite3
from datetime import datetime

import pandas as pd
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
EXCEL_FILE = os.getenv("EXCEL_FILE", "Группы.xlsx")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID topilmadi.")
if not GROUP_ID:
    raise ValueError("GROUP_ID topilmadi.")

DB_PATH = "sklad_bot.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    telegram_id INTEGER UNIQUE,
    password TEXT,
    role TEXT NOT NULL DEFAULT 'employee',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    folder_id INTEGER NOT NULL,
    UNIQUE(employee_id, folder_id),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (folder_id) REFERENCES folders(id)
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
    submitted_at TEXT NOT NULL,
    FOREIGN KEY (cycle_id) REFERENCES cycles(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (folder_id) REFERENCES folders(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS auth_sessions (
    telegram_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    logged_in_at TEXT NOT NULL
)
""")
conn.commit()

dp = Dispatcher()


# =========================
# HELPERS
# =========================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def is_private(message: Message) -> bool:
    return message.chat.type == ChatType.PRIVATE


def clean_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[◼▪•●■\-\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def get_active_cycle():
    cursor.execute("SELECT * FROM cycles WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()


def get_session(telegram_id: int):
    cursor.execute("""
        SELECT s.telegram_id, s.employee_id, e.name, e.role
        FROM auth_sessions s
        JOIN employees e ON e.id = s.employee_id
        WHERE s.telegram_id = ?
    """, (telegram_id,))
    return cursor.fetchone()


def get_employee_by_tg(telegram_id: int):
    cursor.execute("SELECT * FROM employees WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone()


def employee_by_id(employee_id: int):
    cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
    return cursor.fetchone()


def folder_by_id(folder_id: int):
    cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
    return cursor.fetchone()


def require_admin_or_return(message: Message):
    if not is_admin(message.from_user.id):
        return False
    return True


def build_main_menu(user_id: int, employee_role: str | None = None) -> ReplyKeyboardMarkup:
    buttons = []

    if user_id == ADMIN_ID:
        buttons.extend([
            [KeyboardButton(text="➕ Ходим қўшиш"), KeyboardButton(text="👥 Барча ходимлар")],
            [KeyboardButton(text="🔐 Парол генерация"), KeyboardButton(text="📄 Пароллар рўйхати")],
            [KeyboardButton(text="➕ Папка қўшиш"), KeyboardButton(text="📁 Барча папкалар")],
            [KeyboardButton(text="🔗 Папка бириктириш"), KeyboardButton(text="📌 Бириктирмалар")],
            [KeyboardButton(text="📥 Excel импорт")],
            [KeyboardButton(text="🚀 Янги цикл очиш"), KeyboardButton(text="🛑 Циклни ёпиш")],
            [KeyboardButton(text="📈 Актив цикл ҳолати"), KeyboardButton(text="🗑 Ҳисоботни ўчириш")],
        ])

    buttons.extend([
        [KeyboardButton(text="📋 Менга берилган папкалар")],
        [KeyboardButton(text="📝 Актив текширувларим"), KeyboardButton(text="📝 Текширув топшириш")],
        [KeyboardButton(text="📊 Ҳолатим"), KeyboardButton(text="🔓 Чиқиш")],
        [KeyboardButton(text="❓ Ёрдам")],
    ])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


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


def import_from_excel_if_exists(excel_path: str):
    if not os.path.exists(excel_path):
        return "Excel file topilmadi"

    df = pd.read_excel(excel_path)
    if "Наименование" not in df.columns or "Центральный склад" not in df.columns:
        return "Excel format mos emas"

    added_employees = 0
    added_folders = 0
    added_assignments = 0

    for _, row in df.iterrows():
        folder_name = clean_name(row.get("Наименование"))
        employee_name = clean_name(row.get("Центральный склад"))

        if not folder_name or not employee_name or folder_name.lower() == "nan" or employee_name.lower() == "nan":
            continue

        cursor.execute("SELECT id FROM employees WHERE name = ?", (employee_name,))
        emp = cursor.fetchone()
        if not emp:
            cursor.execute(
                "INSERT INTO employees (name, role) VALUES (?, 'employee')",
                (employee_name,)
            )
            added_employees += 1
            employee_id = cursor.lastrowid
        else:
            employee_id = emp["id"]

        cursor.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
        fld = cursor.fetchone()
        if not fld:
            cursor.execute("INSERT INTO folders (name) VALUES (?)", (folder_name,))
            added_folders += 1
            folder_id = cursor.lastrowid
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
    return f"Импорт тайёр: employees={added_employees}, folders={added_folders}, assignments={added_assignments}"


# =========================
# STATES
# =========================
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


class SubmitState(StatesGroup):
    waiting_folder_id = State()
    waiting_counted_ok = State()
    waiting_location_ok = State()
    waiting_wrong_location_count = State()
    waiting_fixed_now = State()
    waiting_comment = State()


# =========================
# STARTUP IMPORT
# =========================
startup_import_result = import_from_excel_if_exists(EXCEL_FILE)


# =========================
# GROUP GUARD
# =========================
@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def group_guard(message: Message):
    await message.reply(
        "Бу бот билан ишлаш фақат личкада.\n"
        "Якунланган ҳисобот эса гуруҳга автомат юборилади."
    )


# =========================
# AUTH
# =========================
@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return

    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            "🔥 Админ режимида кирдингиз.",
            reply_markup=build_main_menu(message.from_user.id, "admin")
        )
        return

    session = get_session(message.from_user.id)
    if session:
        await message.answer(
            f"🔥 Хуш келибсиз, {session['name']}",
            reply_markup=build_main_menu(message.from_user.id, session["role"])
        )
        return

    employee = get_employee_by_tg(message.from_user.id)
    if employee:
        cursor.execute(
            "INSERT OR REPLACE INTO auth_sessions (telegram_id, employee_id, logged_in_at) VALUES (?, ?, ?)",
            (message.from_user.id, employee["id"], now_str())
        )
        conn.commit()
        await message.answer(
            f"🔥 Хуш келибсиз, {employee['name']}",
            reply_markup=build_main_menu(message.from_user.id, employee["role"])
        )
        return

    await message.answer(
        "Сизга пароль орқали кириш керак.\n"
        "Админ берган пароль билан киринг.",
        reply_markup=login_keyboard()
    )


@dp.message(F.text == "🔐 Кириш")
async def login_begin(message: Message, state: FSMContext):
    if not is_private(message):
        return

    if is_admin(message.from_user.id):
        return await message.answer("Сиз админсиз.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    await state.set_state(LoginState.waiting_password)
    await message.answer("Паролни киритинг:", reply_markup=cancel_keyboard())


@dp.message(LoginState.waiting_password)
async def login_by_password(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=login_keyboard())

    password = (message.text or "").strip()

    cursor.execute("SELECT * FROM employees WHERE password = ? AND is_active = 1", (password,))
    employee = cursor.fetchone()

    if not employee:
        return await message.answer("Пароль нотўғри.")

    if employee["telegram_id"] is None:
        cursor.execute(
            "UPDATE employees SET telegram_id = ? WHERE id = ?",
            (message.from_user.id, employee["id"])
        )
    elif employee["telegram_id"] != message.from_user.id:
        return await message.answer(
            "Бу пароль бошқа Telegram аккаунтга бириктирилган.\n"
            "Админга мурожаат қилинг."
        )

    cursor.execute(
        "INSERT OR REPLACE INTO auth_sessions (telegram_id, employee_id, logged_in_at) VALUES (?, ?, ?)",
        (message.from_user.id, employee["id"], now_str())
    )
    conn.commit()

    await state.clear()
    await message.answer(
        f"✅ Кириш муваффақиятли.\nХодим: {employee['name']}",
        reply_markup=build_main_menu(message.from_user.id, employee["role"])
    )


@dp.message(F.text == "🔓 Чиқиш")
async def logout_handler(message: Message, state: FSMContext):
    if not is_private(message):
        return

    await state.clear()
    cursor.execute("DELETE FROM auth_sessions WHERE telegram_id = ?", (message.from_user.id,))
    conn.commit()

    await message.answer("Чиқиб кетдингиз.", reply_markup=login_keyboard())


def require_login(message: Message):
    if is_admin(message.from_user.id):
        return True
    return get_session(message.from_user.id) is not None


# =========================
# SIMPLE USER
# =========================
@dp.message(F.text == "❓ Ёрдам")
async def help_handler(message: Message):
    if not is_private(message):
        return

    await message.answer(
        "Ишлаш тартиби:\n"
        "1) Ходим личкада киради\n"
        "2) Ўзига бириктирилган папкаларни кўради\n"
        "3) Актив циклда ҳисобот топширади\n"
        "4) Якунланган ҳисобот гуруҳга боради\n\n"
        f"Excel импорт ҳолати: {startup_import_result}"
    )


@dp.message(F.text == "📋 Менга берилган папкалар")
async def my_folders_handler(message: Message):
    if not is_private(message):
        return
    if not require_login(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())

    if is_admin(message.from_user.id):
        return await message.answer("Админ учун бу бўлим шарт эмас.")

    employee = get_employee_by_tg(message.from_user.id)
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")

    cursor.execute("""
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ?
        ORDER BY f.id
    """, (employee["id"],))
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Сизга ҳали папка бириктирилмаган.")

    text = "📋 Сизга бириктирилган папкалар:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"

    await message.answer(text)


@dp.message(F.text == "📝 Актив текширувларим")
async def active_checks_handler(message: Message):
    if not is_private(message):
        return
    if not require_login(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())

    if is_admin(message.from_user.id):
        return await message.answer("Админ учун алоҳида цикл статистикаси бор.")

    employee = get_employee_by_tg(message.from_user.id)
    cycle = get_active_cycle()

    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")
    if not cycle:
        return await message.answer("Ҳозирча актив цикл йўқ.")

    cursor.execute("""
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ?
          AND f.id NOT IN (
              SELECT folder_id
              FROM submissions
              WHERE employee_id = ? AND cycle_id = ?
          )
        ORDER BY f.id
    """, (employee["id"], employee["id"], cycle["id"]))
    rows = cursor.fetchall()

    if not rows:
        return await message.answer(f"✅ Сиз цикл бўйича ҳамма ҳисоботни топшириб бўлдингиз.\n\nЦикл: {cycle['title']}")

    text = f"📝 Актив цикл: {cycle['title']}\n\nТопширилиши керак папкалар:\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"

    await message.answer(text)


@dp.message(F.text == "📊 Ҳолатим")
async def status_handler(message: Message):
    if not is_private(message):
        return
    if not require_login(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())

    if is_admin(message.from_user.id):
        cycle = get_active_cycle()
        if not cycle:
            return await message.answer("Актив цикл йўқ.")
        cursor.execute("SELECT COUNT(*) AS c FROM assignments")
        total = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle["id"],))
        done = cursor.fetchone()["c"]
        return await message.answer(
            f"📈 Админ ҳолати\n\n"
            f"Актив цикл: {cycle['title']}\n"
            f"Жами бириктирмалар: {total}\n"
            f"Топширилган ҳисоботлар: {done}\n"
            f"Қолгани: {max(total-done, 0)}"
        )

    employee = get_employee_by_tg(message.from_user.id)
    cycle = get_active_cycle()
    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")
    if not cycle:
        return await message.answer("Актив цикл йўқ.")

    cursor.execute("SELECT COUNT(*) AS c FROM assignments WHERE employee_id = ?", (employee["id"],))
    total = cursor.fetchone()["c"]
    cursor.execute(
        "SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ? AND employee_id = ?",
        (cycle["id"], employee["id"])
    )
    done = cursor.fetchone()["c"]

    await message.answer(
        f"📊 Ҳолатингиз\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Бириктирилган папкалар: {total}\n"
        f"Топширилганлари: {done}\n"
        f"Қолгани: {max(total-done, 0)}"
    )


# =========================
# ADMIN: EMPLOYEES
# =========================
@dp.message(F.text == "➕ Ходим қўшиш")
async def add_employee_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")
    await state.set_state(AddEmployeeState.waiting_name)
    await message.answer("Ходим исмини ёзинг:", reply_markup=cancel_keyboard())


@dp.message(AddEmployeeState.waiting_name)
async def add_employee_name(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    name = clean_name(message.text)
    if not name:
        return await message.answer("Исм бўш бўлмаслиги керак.")

    await state.update_data(name=name)
    await state.set_state(AddEmployeeState.waiting_tg_id)
    await message.answer("Telegram ID ни юборинг. Агар ҳозирча йўқ бўлса 0 ёзинг.")


@dp.message(AddEmployeeState.waiting_tg_id)
async def add_employee_tg(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    value = (message.text or "").strip()
    if not re.fullmatch(r"-?\d+", value):
        return await message.answer("ID рақам бўлиши керак.")

    tg_id = int(value)
    tg_value = None if tg_id == 0 else tg_id
    data = await state.get_data()
    name = data["name"]

    try:
        cursor.execute(
            "INSERT INTO employees (name, telegram_id, role) VALUES (?, ?, 'employee')",
            (name, tg_value)
        )
        conn.commit()
        await message.answer(
            f"✅ Ходим қўшилди:\n"
            f"Исм: {name}\n"
            f"Telegram ID: {tg_value or 'йўқ'}",
            reply_markup=build_main_menu(message.from_user.id, "admin")
        )
    except sqlite3.IntegrityError as e:
        await message.answer(f"⚠️ Ходим қўшилмади:\n{e}", reply_markup=build_main_menu(message.from_user.id, "admin"))

    await state.clear()


@dp.message(F.text == "👥 Барча ходимлар")
async def all_employees_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
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
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id FROM employees WHERE password IS NULL OR password = ''")
    rows = cursor.fetchall()

    if not rows:
        return await message.answer("Ҳамма ходимларда пароль бор.")

    generated = []
    for row in rows:
        pwd = "".join(secrets.choice("0123456789") for _ in range(6))
        cursor.execute("UPDATE employees SET password = ? WHERE id = ?", (pwd, row["id"]))
        generated.append(row["id"])

    conn.commit()
    await message.answer(
        f"✅ {len(generated)} та ходим учун пароль генерация қилинди.\n"
        f"Кўриш учун: 📄 Пароллар рўйхати"
    )


@dp.message(F.text == "📄 Пароллар рўйхати")
async def passwords_list_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name, password FROM employees ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Ходимлар йўқ.")

    text = "📄 Пароллар рўйхати:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']} → {row['password'] or 'йўқ'}\n"
    await message.answer(text)


# =========================
# ADMIN: FOLDERS / ASSIGNMENTS
# =========================
@dp.message(F.text == "➕ Папка қўшиш")
async def add_folder_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")
    await state.set_state(AddFolderState.waiting_folder_name)
    await message.answer("Янги папка номини ёзинг:", reply_markup=cancel_keyboard())


@dp.message(AddFolderState.waiting_folder_name)
async def add_folder_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    folder_name = clean_name(message.text)
    if not folder_name:
        return await message.answer("Папка номи бўш бўлмаслиги керак.")

    try:
        cursor.execute("INSERT INTO folders (name) VALUES (?)", (folder_name,))
        conn.commit()
        await message.answer(f"✅ Папка қўшилди:\n{folder_name}", reply_markup=build_main_menu(message.from_user.id, "admin"))
    except sqlite3.IntegrityError:
        await message.answer(f"⚠️ Бу папка аввал қўшилган:\n{folder_name}", reply_markup=build_main_menu(message.from_user.id, "admin"))

    await state.clear()


@dp.message(F.text == "📁 Барча папкалар")
async def all_folders_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cursor.execute("SELECT id, name FROM folders ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        return await message.answer("Папкалар йўқ.")

    text = "📁 Барча папкалар:\n\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"
    await message.answer(text)


@dp.message(F.text == "🔗 Папка бириктириш")
async def assign_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
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
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    if not (message.text or "").isdigit():
        return await message.answer("Ходим ID рақам бўлиши керак.")

    employee_id = int(message.text)
    employee = employee_by_id(employee_id)
    if not employee:
        return await message.answer("Бундай ходим ID топилмади.")

    await state.update_data(employee_id=employee_id)

    cursor.execute("SELECT id, name FROM folders ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        await state.clear()
        return await message.answer("Аввал папка қўшинг.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    text = "Энди папка ID рақамини юборинг.\n\n📁 Папкалар:\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"

    await state.set_state(AssignState.waiting_folder_id)
    await message.answer(text)


@dp.message(AssignState.waiting_folder_id)
async def assign_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    if not (message.text or "").isdigit():
        return await message.answer("Папка ID рақам бўлиши керак.")

    folder_id = int(message.text)
    data = await state.get_data()
    employee_id = data["employee_id"]

    employee = employee_by_id(employee_id)
    folder = folder_by_id(folder_id)

    if not employee:
        await state.clear()
        return await message.answer("Ходим топилмади.", reply_markup=build_main_menu(message.from_user.id, "admin"))
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
            reply_markup=build_main_menu(message.from_user.id, "admin")
        )
    except sqlite3.IntegrityError:
        await message.answer(
            "⚠️ Бу папка шу ходимга аввал бириктирилган.",
            reply_markup=build_main_menu(message.from_user.id, "admin")
        )

    await state.clear()


@dp.message(F.text == "📌 Бириктирмалар")
async def assignments_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
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
    await message.answer(text)


# =========================
# ADMIN: CYCLES
# =========================
@dp.message(F.text == "🚀 Янги цикл очиш")
async def open_cycle_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
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
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

    title = clean_name(message.text)
    if not title:
        return await message.answer("Цикл номи бўш бўлмаслиги керак.")

    cursor.execute(
        "INSERT INTO cycles (title, is_active, created_at) VALUES (?, 1, ?)",
        (title, now_str())
    )
    conn.commit()

    await state.clear()
    await message.answer(f"✅ Янги цикл очилди:\n{title}", reply_markup=build_main_menu(message.from_user.id, "admin"))


@dp.message(F.text == "🛑 Циклни ёпиш")
async def close_cycle_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")

    active = get_active_cycle()
    if not active:
        return await message.answer("Актив цикл йўқ.")

    cursor.execute("UPDATE cycles SET is_active = 0 WHERE id = ?", (active["id"],))
    conn.commit()
    await message.answer(f"🛑 Цикл ёпилди:\n{active['title']}", reply_markup=build_main_menu(message.from_user.id, "admin"))


@dp.message(F.text == "📈 Актив цикл ҳолати")
async def active_cycle_status_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")

    cycle = get_active_cycle()
    if not cycle:
        return await message.answer("Актив цикл йўқ.")

    cursor.execute("SELECT COUNT(*) AS c FROM assignments")
    total_assignments = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM submissions WHERE cycle_id = ?", (cycle["id"],))
    submitted = cursor.fetchone()["c"]

    cursor.execute("""
        SELECT e.name, COUNT(a.id) AS total_assigned
        FROM employees e
        LEFT JOIN assignments a ON a.employee_id = e.id
        GROUP BY e.id, e.name
        ORDER BY e.name
    """)
    employees = cursor.fetchall()

    text = (
        f"📈 Актив цикл ҳолати\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Жами бириктирмалар: {total_assignments}\n"
        f"Топширилган ҳисоботлар: {submitted}\n"
        f"Қолгани: {max(total_assignments - submitted, 0)}\n\n"
        f"Ходимлар кесими:\n"
    )

    for emp in employees:
        cursor.execute("""
            SELECT COUNT(*) AS c
            FROM submissions s
            JOIN employees e ON e.id = s.employee_id
            WHERE s.cycle_id = ? AND e.name = ?
        """, (cycle["id"], emp["name"]))
        done = cursor.fetchone()["c"]
        text += f"- {emp['name']}: {done}/{emp['total_assigned']}\n"

    await message.answer(text)


# =========================
# ADMIN: IMPORT CURRENT EXCEL AGAIN
# =========================
@dp.message(F.text == "📥 Excel импорт")
async def excel_import_handler(message: Message):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
        return await message.answer("⛔ Сиз админ эмассиз.")

    result = import_from_excel_if_exists(EXCEL_FILE)
    await message.answer(f"✅ {result}")


# =========================
# REPORT SUBMISSION
# =========================
@dp.message(F.text == "📝 Текширув топшириш")
async def submit_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_login(message):
        return await message.answer("Аввал киринг.", reply_markup=login_keyboard())
    if is_admin(message.from_user.id):
        return await message.answer("Админ учун бу бўлим ишлатилмайди.")

    employee = get_employee_by_tg(message.from_user.id)
    cycle = get_active_cycle()

    if not employee:
        return await message.answer("Сиз ходим сифатида топилмадингиз.")
    if not cycle:
        return await message.answer("Ҳозирча актив цикл йўқ.")

    cursor.execute("""
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ?
          AND f.id NOT IN (
              SELECT folder_id
              FROM submissions
              WHERE cycle_id = ? AND employee_id = ?
          )
        ORDER BY f.id
    """, (employee["id"], cycle["id"], employee["id"]))
    rows = cursor.fetchall()

    if not rows:
        return await message.answer(
            f"✅ Сиз цикл бўйича барча ҳисоботни топшириб бўлдингиз.\n\nЦикл: {cycle['title']}"
        )

    text = f"Қайси папка бўйича ҳисобот топширасиз?\n\nЦикл: {cycle['title']}\n"
    for row in rows:
        text += f"{row['id']}. {row['name']}\n"

    await state.set_state(SubmitState.waiting_folder_id)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(SubmitState.waiting_folder_id)
async def submit_get_folder(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "employee"))

    if not (message.text or "").isdigit():
        return await message.answer("Папка ID рақам бўлиши керак.")

    employee = get_employee_by_tg(message.from_user.id)
    cycle = get_active_cycle()

    if not employee or not cycle:
        await state.clear()
        return await message.answer("Ходим ёки актив цикл топилмади.", reply_markup=build_main_menu(message.from_user.id, "employee"))

    folder_id = int(message.text)

    cursor.execute("""
        SELECT f.id, f.name
        FROM assignments a
        JOIN folders f ON f.id = a.folder_id
        WHERE a.employee_id = ? AND f.id = ?
    """, (employee["id"], folder_id))
    folder = cursor.fetchone()

    if not folder:
        return await message.answer("Бу папка сизга бириктирилмаган.")

    cursor.execute("""
        SELECT id FROM submissions
        WHERE cycle_id = ? AND employee_id = ? AND folder_id = ?
    """, (cycle["id"], employee["id"], folder_id))
    existing = cursor.fetchone()
    if existing:
        return await message.answer("Бу папка бўйича актив циклда ҳисобот аввал топширилган.")

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
    value = (message.text or "").strip()
    if not value.isdigit():
        return await message.answer("Рақам ёзинг. Масалан: 3")

    wrong_count = int(value)
    await state.update_data(wrong_location_count=wrong_count)
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
    comment = (message.text or "").strip() or "-"

    employee = get_employee_by_tg(message.from_user.id)
    cycle = get_active_cycle()
    if not employee or not cycle:
        await state.clear()
        return await message.answer("Ходим ёки актив цикл топилмади.", reply_markup=build_main_menu(message.from_user.id, "employee"))

    data = await state.get_data()

    cursor.execute("""
        INSERT INTO submissions (
            cycle_id, employee_id, folder_id,
            counted_ok, location_ok, wrong_location_count,
            fixed_now, comment, submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cycle["id"],
        employee["id"],
        data["folder_id"],
        data["counted_ok"],
        data["location_ok"],
        data.get("wrong_location_count", 0),
        data.get("fixed_now"),
        comment,
        now_str()
    ))
    conn.commit()

    counted_ok = data["counted_ok"]
    location_ok = data["location_ok"]
    wrong_location_count = data.get("wrong_location_count", 0)
    fixed_now = data.get("fixed_now")
    folder_name = data["folder_name"]

    report_text = (
        f"📦 Якунланган склад ҳисоботи\n\n"
        f"Цикл: {cycle['title']}\n"
        f"Ходим: {employee['name']}\n"
        f"Папка: {folder_name}\n"
        f"Остаток тўғри: {'Ҳа' if counted_ok else 'Йўқ'}\n"
        f"Место хранения тўғри: {'Ҳа' if location_ok else 'Йўқ'}\n"
    )

    if location_ok == 0:
        report_text += (
            f"Хато место сони: {wrong_location_count}\n"
            f"Тўғирланди: {'Ҳа' if fixed_now else 'Йўқ'}\n"
        )

    report_text += f"Изоҳ: {comment}\nВақт: {now_str()}"

    try:
        await bot.send_message(GROUP_ID, report_text)
    except Exception as e:
        await message.answer(f"⚠️ Гуруҳга юборишда муаммо: {e}")

    await state.clear()
    await message.answer(
        "✅ Ҳисобот қабул қилинди.\nГуруҳга якунланган ҳисобот юборилди.",
        reply_markup=build_main_menu(message.from_user.id, "employee")
    )


# =========================
# ADMIN: DELETE REPORT
# =========================
@dp.message(F.text == "🗑 Ҳисоботни ўчириш")
async def delete_report_start(message: Message, state: FSMContext):
    if not is_private(message):
        return
    if not require_admin_or_return(message):
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

    text = "Ўчириш учун ҳисобот ID рақамини юборинг.\n\nСўнгги ҳисоботлар:\n"
    for row in rows:
        text += f"{row['id']}. {row['employee_name']} | {row['folder_name']} | {row['title']} | {row['submitted_at']}\n"

    await state.set_state(DeleteReportState.waiting_submission_id)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(DeleteReportState.waiting_submission_id)
async def delete_report_save(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        return await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))

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
    await message.answer(
        f"🗑 Ҳисобот ўчирилди. ID: {submission_id}",
        reply_markup=build_main_menu(message.from_user.id, "admin")
    )


# =========================
# GLOBAL CANCEL / FALLBACK
# =========================
@dp.message(F.text == "❌ Бекор қилиш")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "admin"))
    else:
        await message.answer("Бекор қилинди.", reply_markup=build_main_menu(message.from_user.id, "employee"))


@dp.message()
async def fallback_handler(message: Message):
    if not is_private(message):
        return
    if is_admin(message.from_user.id):
        return await message.answer("Менюдан керакли бўлимни танланг.", reply_markup=build_main_menu(message.from_user.id, "admin"))
    if require_login(message):
        return await message.answer("Менюдан керакли бўлимни танланг.", reply_markup=build_main_menu(message.from_user.id, "employee"))
    return await message.answer("Аввал киринг.", reply_markup=login_keyboard())


# =========================
# MAIN
# =========================
async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
