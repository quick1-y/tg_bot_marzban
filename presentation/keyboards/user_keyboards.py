# presentation/keyboards/user_keyboards
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from core.config import config


def get_user_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Главное меню для пользователя, поддержки и админа.
    """
    keyboard = [
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription")],
        [InlineKeyboardButton(text="🆘 Техническая поддержка", callback_data="support")],
    ]

    # --- Расширенные роли ---
    if config.is_support(user_id):
        keyboard.extend([
            [InlineKeyboardButton(text="--- ПОДДЕРЖКА ---", callback_data="support_header")],
            [InlineKeyboardButton(text="📋 Тикеты поддержки", callback_data="admin_support_tickets")],
        ])

    if config.is_admin(user_id):
        keyboard.extend([
            [InlineKeyboardButton(text="--- АДМИНИСТРИРОВАНИЕ ---", callback_data="admin_header")],
            [InlineKeyboardButton(text="📈 Системная статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="👥 Администраторы", callback_data="admin_admins")],
            [InlineKeyboardButton(text="👤 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="🌐 Управление узлами", callback_data="admin_nodes")],
            [InlineKeyboardButton(text="📋 Тикеты поддержки", callback_data="admin_support_tickets")],
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_extend_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура при наличии активной месячной подписки.
    """
    keyboard = [
        [InlineKeyboardButton(text="🔁 Продлить подписку", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_add_gb_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура при наличии активной подписки по трафику.
    """
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить ГБ", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
