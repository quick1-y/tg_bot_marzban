from .user_keyboards import get_user_main_keyboard
from .support_keyboards import (
    get_support_keyboard,
    get_support_confirmation_keyboard,
    get_support_tickets_keyboard,
    get_support_tickets_pagination_keyboard,
    get_user_tickets_list_keyboard,
    get_user_support_menu_keyboard
)
from .admin_keyboards import (
    get_admin_main_keyboard,
    get_admin_users_keyboard
)
from .common_keyboards import (
    get_pagination_keyboard,
    get_confirmation_keyboard
)

__all__ = [
    'get_user_main_keyboard',
    'get_support_keyboard',
    'get_support_confirmation_keyboard',
    'get_support_tickets_keyboard',
    'get_support_tickets_pagination_keyboard',
    'get_user_tickets_list_keyboard',
    'get_user_support_menu_keyboard',
    'get_admin_main_keyboard',
    'get_admin_users_keyboard',
    'get_pagination_keyboard',
    'get_confirmation_keyboard'
]
