#domain/services/subscription_service.py
import logging
from typing import Optional
from datetime import datetime, timedelta
from infrastructure.marzban.api_client import MarzbanAPIClient
from domain.services.user_service import UserService
from domain.models.subscription import SubscriptionInfo, SubscriptionResult

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, marzban_client: MarzbanAPIClient, user_service: UserService):
        self.marzban_client = marzban_client
        self.user_service = user_service

    async def get_subscription_info(self, telegram_id: int) -> SubscriptionResult:
        """Получает информацию о текущей подписке пользователя"""
        try:
            username = f"qwqvpn_{telegram_id}"
            user_data = await self.marzban_client.get_user(username)

            if not user_data:
                return SubscriptionResult(
                    success=False,
                    error_message="Подписка не найдена",
                    context="view"
                )

            subscription_url = await self._get_subscription_url_with_retry(username)
            subscription_info = SubscriptionInfo.from_marzban_data(user_data, subscription_url)

            return SubscriptionResult(
                success=True,
                subscription_info=subscription_info,
                context="view"
            )

        except Exception as e:
            logger.error(f"Ошибка при получении подписки: {e}")
            return SubscriptionResult(
                success=False,
                error_message=f"Ошибка при загрузке информации: {str(e)}",
                context="view"
            )

    # ✅ Покупка/продление месячной подписки
    async def purchase_monthly_subscription(self, telegram_id: int, months: int) -> SubscriptionResult:
        try:
            username = f"qwqvpn_{telegram_id}"
            existing_user = await self.marzban_client.get_user(username)

            now = datetime.utcnow()
            additional_days = 30 * months

            # Если пользователь уже существует — продлеваем срок
            if existing_user:
                current_expire_ts = existing_user.get("expire")
                if current_expire_ts:
                    current_expire = datetime.fromtimestamp(current_expire_ts)
                    # если подписка ещё активна — добавляем сверху
                    if current_expire > now:
                        new_expire = current_expire + timedelta(days=additional_days)
                    else:
                        # если истекла — начинаем отсчёт от текущего момента
                        new_expire = now + timedelta(days=additional_days)
                else:
                    new_expire = now + timedelta(days=additional_days)

                await self.marzban_client.modify_user(username, {
                    "expire": int(new_expire.timestamp()),
                    "status": "active",
                })
                logger.info(f"Продлена подписка пользователю {telegram_id} до {new_expire}")

            else:
                # создаём новую
                new_expire = now + timedelta(days=additional_days)
                await self.marzban_client.create_user({
                    "username": username,
                    "expire": int(new_expire.timestamp()),
                    "data_limit": 0,
                    "data_limit_reset_strategy": "no_reset",
                    "note": f"Monthly plan {months}m, Telegram ID: {telegram_id}",
                    "status": "active"
                })
                logger.info(f"Создана новая месячная подписка пользователю {telegram_id} на {months} мес.")

            await self.user_service.update_user_subscription_type(telegram_id, "monthly")

            # Получаем обновлённые данные
            user_data = await self.marzban_client.get_user(username)
            subscription_url = await self._get_subscription_url_with_retry(username)
            subscription_info = SubscriptionInfo.from_marzban_data(user_data, subscription_url)

            return SubscriptionResult(success=True, subscription_info=subscription_info)

        except Exception as e:
            logger.error(f"Ошибка при создании месячной подписки: {e}")
            return SubscriptionResult(success=False, error_message=str(e))


    # ✅ Покупка/добавление ГБ
    async def purchase_gb_subscription(self, telegram_id: int, gb: int) -> SubscriptionResult:
        """
        Создаёт новую подписку по трафику или добавляет указанное количество ГБ
        к существующей. Если пользователь был неактивен — активирует.
        """
        try:
            username = f"qwqvpn_{telegram_id}"
            existing_user = await self.marzban_client.get_user(username)
            add_bytes = gb * 1024 * 1024 * 1024  # 1 ГБ → байты

            if existing_user:
                current_limit = existing_user.get("data_limit") or 0
                current_usage = existing_user.get("used_traffic") or 0
                new_limit = current_limit + add_bytes

                await self.marzban_client.modify_user(username, {
                    "data_limit": new_limit,
                    "status": "active",
                })
                logger.info(
                    f"Пользователю {telegram_id} добавлено {gb} ГБ "
                    f"(старый лимит: {current_limit / 1e9:.1f} ГБ, новый лимит: {new_limit / 1e9:.1f} ГБ)"
                )

            else:
                # создаём нового пользователя с заданным лимитом
                await self.marzban_client.create_user({
                    "username": username,
                    "data_limit": add_bytes,
                    "data_limit_reset_strategy": "no_reset",
                    "note": f"Traffic plan {gb}GB, Telegram ID: {telegram_id}",
                    "status": "active",
                })
                logger.info(f"Создан новый трафиковый тариф {gb} ГБ для пользователя {telegram_id}")

            await self.user_service.update_user_subscription_type(telegram_id, "traffic")

            # Обновляем данные подписки
            user_data = await self.marzban_client.get_user(username)
            subscription_url = await self._get_subscription_url_with_retry(username)
            subscription_info = SubscriptionInfo.from_marzban_data(user_data, subscription_url)

            return SubscriptionResult(success=True, subscription_info=subscription_info)

        except Exception as e:
            logger.error(f"Ошибка при добавлении трафика: {e}", exc_info=True)
            return SubscriptionResult(success=False, error_message=str(e))


    async def _get_subscription_url_with_retry(self, username: str, max_attempts: int = 3) -> Optional[str]:
        """Получает ссылку на подписку с повторными попытками"""
        for attempt in range(max_attempts):
            try:
                return await self.marzban_client.get_user_subscription(username)
            except Exception:
                if attempt == max_attempts - 1:
                    raise
        return None
