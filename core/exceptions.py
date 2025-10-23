class SubscriptionError(Exception):
    """Базовое исключение для ошибок подписки"""
    pass


class SubscriptionNotFoundError(SubscriptionError):
    """Подписка не найдена"""
    pass


class SubscriptionAlreadyExistsError(SubscriptionError):
    """Подписка уже существует"""
    pass


class MarzbanAPIError(SubscriptionError):
    """Ошибка API Marzban"""
    pass