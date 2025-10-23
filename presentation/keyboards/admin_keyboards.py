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
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_list")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="user_add")],
        [InlineKeyboardButton(text="⏰ Добавить время всем", callback_data="users_add_time")],
        [InlineKeyboardButton(text="💽 Добавить трафик всем", callback_data="users_add_data")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
