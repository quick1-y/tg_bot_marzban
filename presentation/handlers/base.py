from abc import ABC, abstractmethod
from aiogram import Router


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков"""

    def __init__(self):
        self.router = Router()
        self._register_handlers()

    @abstractmethod
    def _register_handlers(self):
        """Регистрация обработчиков - должен быть реализован в потомках"""
        pass

    def get_router(self) -> Router:
        """Возвращает роутер с обработчиками"""
        return self.router