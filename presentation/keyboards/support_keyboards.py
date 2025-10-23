# presentation/keyboards/support_keyboards
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_support_keyboard():
    """Меню поддержки — не зависит от user_id"""
    keyboard = [
        [InlineKeyboardButton(text="📝 Написать в поддержку", callback_data="write_to_support")],
        [InlineKeyboardButton(text="📋 Мои обращения", callback_data="user_support_tickets")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_support_confirmation_keyboard():
    """Клавиатура подтверждения отправки сообщения"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_support"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_support"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_support_tickets_keyboard():
    """Меню тикетов поддержки (для саппорта и админов)"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Список открытых тикетов", callback_data="support_tickets_list")],
        [InlineKeyboardButton(text="🔍 Поиск тикета по ID", callback_data="support_ticket_search")],
        [InlineKeyboardButton(text="📊 Статистика тикетов", callback_data="support_tickets_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_from_tickets")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_tickets_list_keyboard(tickets):
    """Клавиатура со списком тикетов пользователя"""
    buttons = []
    for t in tickets[:10]:
        text = f"#{t.id} — {'🟢 Открыт' if t.status == 'open' else '🔴 Закрыт'}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"ticket_{t.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_support")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_support_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню поддержки для пользователя"""
    keyboard = [
        [InlineKeyboardButton(text="✉️ Создать обращение", callback_data="create_support_ticket")],
        [InlineKeyboardButton(text="📬 Мои обращения", callback_data="view_my_tickets")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
