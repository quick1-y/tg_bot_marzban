from typing import Optional, List
from infrastructure.database.repositories import UserRepository
from domain.models.user import TelegramUser


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_or_create_user(self, telegram_id: int) -> TelegramUser:
        """Получает или создает пользователя"""
        marzban_username = f"qwqvpn_{telegram_id}"

        existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
        if existing_user:
            if not existing_user.marzban_username:
                existing_user.marzban_username = marzban_username
                await self.user_repository.save(existing_user)
            return existing_user

        new_user = TelegramUser(
            telegram_id=telegram_id,
            marzban_username=marzban_username
        )
        await self.user_repository.save(new_user)
        return new_user

    async def get_user_marzban_username(self, telegram_id: int) -> Optional[str]:
        """Получает имя пользователя Marzban по Telegram ID"""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        return user.marzban_username if user else None

    async def get_user_by_marzban_username(self, username: str) -> Optional[TelegramUser]:
        """Получает пользователя по имени в Marzban"""
        return await self.user_repository.get_by_marzban_username(username)

    async def get_all_users(self) -> List[TelegramUser]:
        """Возвращает всех пользователей бота"""
        return await self.user_repository.get_all()

    async def update_user_subscription_type(self, telegram_id: int, subscription_type: str):
        """Обновляет тип подписки пользователя"""
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            user = TelegramUser(
                telegram_id=telegram_id,
                marzban_username=f"qwqvpn_{telegram_id}",
                subscription_type=subscription_type
            )
        else:
            user.subscription_type = subscription_type
            if not user.marzban_username:
                user.marzban_username = f"qwqvpn_{telegram_id}"
        await self.user_repository.save(user)
