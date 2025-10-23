# presentation/keyboards/common_keyboards
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_pagination_keyboard(current_page: int, total_pages: int, data_type: str):
    """Клавиатура пагинации"""
    buttons = []

    if current_page > 0:
        buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"{data_type}_page_{current_page - 1}"
        ))

    buttons.append(InlineKeyboardButton(
        text=f"{current_page + 1}/{total_pages}",
        callback_data="current_page"
    ))

    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"{data_type}_page_{current_page + 1}"
        ))

    back_button = [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    return InlineKeyboardMarkup(inline_keyboard=[buttons, back_button])


def get_confirmation_keyboard(action: str, target: str):
    """Подтверждение действий"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{target}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
