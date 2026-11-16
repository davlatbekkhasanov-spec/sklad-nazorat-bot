"""Русские подписи кнопок + алиасы старых узбекских текстов."""

BTN_YES = "✅ Да"
BTN_NO = "❌ Нет"
BTN_CANCEL = "❌ Отмена"
BTN_LOGIN = "🔐 Войти"
BTN_LOGOUT = "🔓 Выйти"
BTN_HELP = "❓ Помощь"
BTN_ADD_EMP = "➕ Добавить сотрудника"
BTN_ALL_EMP = "👥 Все сотрудники"
BTN_GEN_PASS = "🔐 Сгенерировать пароли"
BTN_PASS_LIST = "📄 Список паролей"
BTN_ADD_FOLDER = "➕ Добавить папку"
BTN_ALL_FOLDERS = "📁 Все папки"
BTN_ASSIGN = "🔗 Назначить папку"
BTN_ASSIGNMENTS = "📌 Назначения"
BTN_EXCEL = "📥 Импорт Excel"
BTN_OPEN_CYCLE = "🚀 Открыть новый цикл"
BTN_CLOSE_CYCLE = "🛑 Закрыть цикл"
BTN_REMAINING = "📂 Оставшиеся папки"
BTN_CYCLE_STATUS = "📈 Статус активного цикла"
BTN_DEL_REPORT = "🗑 Удалить отчёт"
BTN_MY_FOLDERS = "📋 Мои папки"
BTN_ACTIVE_CHECKS = "📝 Активные проверки"
BTN_SUBMIT_CHECK = "📝 Сдать проверку"
BTN_MY_STATUS = "📊 Мой статус"
BTN_TODAY = "📊 Работа сегодня"
BTN_COUNT = "📝 Пересчёт"
BTN_MARK = "📌 Отметить"
BTN_MARK_ALL = "✅ Отметить все"
BTN_MARK_DONE = "✅ Отметка завершена"
BTN_MARK_FOLDERS = "📌 Отметить папки"
BTN_MARKED_FOLDERS = "📋 Отмеченные папки"

BTN_YES_ALL = frozenset({BTN_YES, "✅ Ҳа", "✅ Ха", "✅ Ha"})
BTN_NO_ALL = frozenset({BTN_NO, "❌ Йўқ", "❌ Йук", "❌ Yo'q", "❌ Yo‘q"})
BTN_CANCEL_ALL = frozenset(
    {
        BTN_CANCEL,
        "❌ Бекор қилиш",
        "❌ Бекор",
        "❌ Bekor qilish",
    }
)
BTN_LOGIN_ALL = frozenset({BTN_LOGIN, "🔐 Кириш"})
BTN_LOGOUT_ALL = frozenset({BTN_LOGOUT, "🔓 Чиқиш"})
BTN_HELP_ALL = frozenset({BTN_HELP, "❓ Ёрдам"})
BTN_ADD_EMP_ALL = frozenset({BTN_ADD_EMP, "➕ Ходим қўшиш"})
BTN_ALL_EMP_ALL = frozenset({BTN_ALL_EMP, "👥 Барча ходимлар"})
BTN_GEN_PASS_ALL = frozenset({BTN_GEN_PASS, "🔐 Парол генерация"})
BTN_PASS_LIST_ALL = frozenset({BTN_PASS_LIST, "📄 Пароллар рўйхати"})
BTN_ADD_FOLDER_ALL = frozenset({BTN_ADD_FOLDER, "➕ Папка қўшиш"})
BTN_ALL_FOLDERS_ALL = frozenset({BTN_ALL_FOLDERS, "📁 Барча папкалар"})
BTN_ASSIGN_ALL = frozenset({BTN_ASSIGN, "🔗 Папка бириктириш"})
BTN_ASSIGNMENTS_ALL = frozenset({BTN_ASSIGNMENTS, "📌 Бириктирмалар"})
BTN_EXCEL_ALL = frozenset({BTN_EXCEL, "📥 Excel импорт"})
BTN_OPEN_CYCLE_ALL = frozenset({BTN_OPEN_CYCLE, "🚀 Янги цикл очиш"})
BTN_CLOSE_CYCLE_ALL = frozenset({BTN_CLOSE_CYCLE, "🛑 Циклни ёпиш"})
BTN_REMAINING_ALL = frozenset({BTN_REMAINING, "📂 Қолган папкалар"})
BTN_CYCLE_STATUS_ALL = frozenset({BTN_CYCLE_STATUS, "📈 Актив цикл ҳолати"})
BTN_DEL_REPORT_ALL = frozenset({BTN_DEL_REPORT, "🗑 Ҳисоботни ўчириш"})
BTN_MY_FOLDERS_ALL = frozenset({BTN_MY_FOLDERS, "📋 Менга берилган папкалар", BTN_MARKED_FOLDERS, "📋 Белгиланган папкалар"})
BTN_ACTIVE_CHECKS_ALL = frozenset({BTN_ACTIVE_CHECKS, "📝 Актив текширувларим"})
BTN_TODAY_ALL = frozenset({BTN_TODAY, "📊 Бугунги иш"})
BTN_STATUS_ALL = frozenset({BTN_MY_STATUS, "📊 Ҳолатим"})
BTN_COUNT_ALL = frozenset({BTN_COUNT, BTN_SUBMIT_CHECK, "📝 Санаш", "📝 Текширув топшириш"})
BTN_MARK_ALL_SET = frozenset({BTN_MARK, BTN_MARK_FOLDERS, "📌 Белгилаш", "📌 Папкаларни белгилаш"})
BTN_MARK_ALL_BTN_ALL = frozenset({BTN_MARK_ALL, "✅ Ҳаммасини белгилаш"})
BTN_MARK_DONE_ALL = frozenset({BTN_MARK_DONE, "✅ Белгилаш тугади"})

EMPLOYEE_MENU_BUTTONS = frozenset(
    {
        BTN_TODAY,
        BTN_COUNT,
        BTN_MARK,
        BTN_MARK_FOLDERS,
        BTN_SUBMIT_CHECK,
        BTN_ACTIVE_CHECKS,
        BTN_MARKED_FOLDERS,
        BTN_MY_FOLDERS,
        BTN_MY_STATUS,
        BTN_LOGOUT,
        BTN_HELP,
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
    }
)


def is_yes(text: str | None) -> bool:
    return (text or "") in BTN_YES_ALL


def is_no(text: str | None) -> bool:
    return (text or "") in BTN_NO_ALL


def is_cancel(text: str | None) -> bool:
    return (text or "") in BTN_CANCEL_ALL
