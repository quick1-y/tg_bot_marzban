#main.py
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from core.config import config
from infrastructure.database.repositories import UserRepository, SupportRepository
from infrastructure.marzban.api_client import MarzbanAPIClient
from domain.services.user_service import UserService
from domain.services.subscription_service import SubscriptionService
from domain.services.support_service import SupportService
from presentation.handlers.user_handlers import UserHandlers
from presentation.handlers.admin_handlers import AdminHandlers
from presentation.handlers.support_handlers import SupportHandlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""

    # Инициализация инфраструктуры
    user_repository = UserRepository(config.DB_PATH)
    support_repository = SupportRepository(config.DB_PATH)
    marzban_client = MarzbanAPIClient(
        base_url=config.MARZBAN_API_URL,
        username=config.MARZBAN_USERNAME,
        password=config.MARZBAN_PASSWORD,
        verify_ssl=config.VERIFY_SSL,
        api_prefix=config.MARZBAN_API_PREFIX
    )

    # Инициализация сервисов
    user_service = UserService(user_repository)
    support_service = SupportService(support_repository)
    subscription_service = SubscriptionService(marzban_client, user_service)

    # Инициализация бота и диспетчера с FSM
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация обработчиков
    user_handlers = UserHandlers(subscription_service, user_service, support_service)
    admin_handlers = AdminHandlers(marzban_client, support_service, user_service)
    support_handlers = SupportHandlers(support_service)

    # Регистрация роутеров
    dp.include_router(user_handlers.get_router())
    dp.include_router(admin_handlers.get_router())
    dp.include_router(support_handlers.get_router())

    # Запуск бота
    logger.info("Бот запущен...")
    logger.info(f"Подключение к Marzban API: {config.MARZBAN_API_URL}")
    logger.info(f"API Prefix для подписок: {config.MARZBAN_API_PREFIX}")
    logger.info(f"Администраторы: {config.ADMIN_TG_IDS}")
    logger.info(f"Поддержка: {config.SUPPORT_TG_IDS}")
    logger.info(f"Проверка SSL: {'Включена' if config.VERIFY_SSL else 'Отключена'}")

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Бот остановлен")
    finally:
        # Закрытие соединения с API
        await marzban_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())