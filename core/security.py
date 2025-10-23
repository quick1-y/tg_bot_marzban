# core/security.py
from core.config import config


def is_admin(user_id: int) -> bool:
    """Проверка: является ли пользователь администратором"""
    return user_id in config.ADMIN_TG_IDS


def is_support(user_id: int) -> bool:
    """Проверка: является ли пользователь сотрудником поддержки"""
    return user_id in config.SUPPORT_TG_IDS


def is_user(user_id: int) -> bool:
    """Проверка: обычный пользователь (не админ и не саппорт)"""
    return not (is_admin(user_id) or is_support(user_id))


def can_access_support_tickets(user_id: int) -> bool:
    """Проверка доступа к тикетам поддержки"""
    return is_admin(user_id) or is_support(user_id)


def can_access_admin_panel(user_id: int) -> bool:
    """Проверка доступа к административным функциям"""
    return is_admin(user_id)

