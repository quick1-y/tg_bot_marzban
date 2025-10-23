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
        [InlineKeyboardButton(text="📋 Список тикетов", callback_data="support_tickets_list")],
        [InlineKeyboardButton(text="🔍 Поиск тикета по ID", callback_data="support_ticket_search")],
        [InlineKeyboardButton(text="📊 Статистика тикетов", callback_data="support_tickets_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_from_tickets")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_support_ticket_search_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при запросе ID тикета"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_support_tickets")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="support_ticket_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_support_tickets_pagination_keyboard(offset: int, total: int, page_size: int = 10) -> InlineKeyboardMarkup:
    """Клавиатура для постраничного просмотра тикетов поддержки"""
    buttons = []

    if offset + page_size < total:
        next_offset = offset + page_size
        buttons.append([
            InlineKeyboardButton(
                text="▶️ Показать ещё",
                callback_data=f"support_tickets_list:{next_offset}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_support_tickets")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_ticket_actions_keyboard(ticket_id: int, is_open: bool) -> InlineKeyboardMarkup:
    """Клавиатура действий с конкретным тикетом"""
    buttons = [
        [InlineKeyboardButton(text="✉️ Ответить пользователю", callback_data=f"support_ticket_reply:{ticket_id}")]
    ]

    if is_open:
        buttons.append(
            [InlineKeyboardButton(text="🔒 Закрыть тикет", callback_data=f"support_ticket_toggle:{ticket_id}:closed")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="🔓 Открыть тикет", callback_data=f"support_ticket_toggle:{ticket_id}:open")]
        )

    buttons.append([InlineKeyboardButton(text="🔙 К списку", callback_data="admin_support_tickets")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
