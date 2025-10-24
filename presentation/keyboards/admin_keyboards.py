# presentation/keyboards/admin_keyboards
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_main_keyboard():
    """Главное меню администратора (/admin)"""
    keyboard = [
        [InlineKeyboardButton(text="📈 Системная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Администраторы", callback_data="admin_admins")],
        [InlineKeyboardButton(text="👤 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🌐 Управление узлами", callback_data="admin_nodes")],
        [InlineKeyboardButton(text="📋 Тикеты поддержки", callback_data="admin_support_tickets")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_users_keyboard():
    """Клавиатура управления пользователями"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_list:0")],
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="users_search")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="user_add")],
        [InlineKeyboardButton(text="⏰ Добавить время", callback_data="users_add_time")],
        [InlineKeyboardButton(text="💽 Добавить трафик", callback_data="users_add_data")],
        [InlineKeyboardButton(text="📣 Массовая рассылка", callback_data="users_broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_admins_keyboard():
    """Клавиатура управления администраторами"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Список администраторов", callback_data="admins_list:0")],
        [InlineKeyboardButton(text="🔍 Найти администратора", callback_data="admins_search")],
        [InlineKeyboardButton(text="➕ Добавить администратора", callback_data="admins_add")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_users_add_time_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="👥 Всем", callback_data="users_add_time_all")],
        [InlineKeyboardButton(text="👤 Пользователю", callback_data="users_add_time_user")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_users_add_data_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="👥 Всем", callback_data="users_add_data_all")],
        [InlineKeyboardButton(text="👤 Пользователю", callback_data="users_add_data_user")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_search_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="users_search_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
