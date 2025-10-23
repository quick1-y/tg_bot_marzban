#infrastructure/marzban/api_client.py
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from marzban import MarzbanAPI
from marzban.models import UserCreate, UserModify, ProxySettings
import ssl
import logging

logger = logging.getLogger(__name__)


class MarzbanAPIClient:
    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = False, api_prefix: str = ""):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.api_prefix = api_prefix
        self.api = None
        self.token = None
        self.token_expires = None

        # SSL контекст для aiohttp
        if not verify_ssl:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        else:
            self.ssl_context = None

    async def _ensure_api(self):
        """Инициализация API клиента при необходимости"""
        if not self.api or not self.token or (self.token_expires and datetime.now() >= self.token_expires):
            await self._initialize_api()

    async def _initialize_api(self):
        """Инициализация API клиента и получение токена"""
        try:
            logger.info(f"Инициализация API с base_url: {self.base_url}, verify_ssl: {self.verify_ssl}")

            # Создаем экземпляр API клиента
            self.api = MarzbanAPI(base_url=self.base_url, verify=self.verify_ssl)
            logger.info(f"Подключение к API: {self.base_url}, verify_ssl={self.verify_ssl}, prefix={self.api_prefix}")

            # Получаем токен
            self.token = await self.api.get_token(username=self.username, password=self.password)
            self.token_expires = datetime.now() + timedelta(hours=23)

            logger.info("API клиент инициализирован, токен получен")
            logger.info(f"Токен действителен до: {self.token_expires}")

        except Exception as e:
            logger.error(f"Ошибка инициализации API: {str(e)}")
            self.api = None
            self.token = None
            raise Exception(f"Ошибка инициализации API: {str(e)}")

    # Системная статистика
    async def get_system_stats(self) -> Dict[str, Any]:
        """Получение системной статистики"""
        await self._ensure_api()
        return await self.api.get_system_stats(token=self.token.access_token)

    # Методы для работы с пользователями
    async def get_users(self, offset: int = 0, limit: int = 100, search: Optional[str] = None) -> Dict[str, Any]:
        """Получение списка пользователей с учетом пагинации"""
        await self._ensure_api()
        response = await self.api.get_users(
            token=self.token.access_token,
            offset=offset,
            limit=limit,
            search=search
        )

        if not response:
            return {"total": 0, "users": []}

        users = getattr(response, "users", [])
        total = getattr(response, "total", len(users))
        return {
            "total": total,
            "users": [user.dict() for user in users] if users else []
        }

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        await self._ensure_api()
        try:
            user = await self.api.get_user(username=username, token=self.token.access_token)
            return user.dict() if user else None
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return None
            raise e

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание нового пользователя"""
        await self._ensure_api()

        # Создаем объект пользователя
        user_create = UserCreate(
            username=user_data["username"],
            data_limit=user_data.get("data_limit", 0),
            data_limit_reset_strategy=user_data.get("data_limit_reset_strategy", "no_reset"),
            expire=user_data.get("expire"),
            note=user_data.get("note", ""),
            status=user_data.get("status", "active"),
            proxies={"vless": ProxySettings(flow="xtls-rprx-vision")}
        )

        logger.info(f"Создание пользователя через API: {user_data['username']}")
        result = await self.api.add_user(user=user_create, token=self.token.access_token)
        return result.dict() if result else {}

    async def modify_user(self, username: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Изменение пользователя"""
        await self._ensure_api()

        # Создаем объект для модификации пользователя
        user_modify = UserModify(
            data_limit=user_data.get("data_limit"),
            data_limit_reset_strategy=user_data.get("data_limit_reset_strategy"),
            expire=user_data.get("expire"),
            note=user_data.get("note"),
            status=user_data.get("status"),
            proxies={"vless": ProxySettings(flow="xtls-rprx-vision")}
        )

        logger.info(f"Обновление пользователя через API: {username}")
        result = await self.api.modify_user(username=username, user=user_modify, token=self.token.access_token)
        return result.dict() if result else {}

    async def delete_user(self, username: str) -> Dict[str, Any]:
        """Удаление пользователя"""
        await self._ensure_api()
        result = await self.api.remove_user(username=username, token=self.token.access_token)
        return result.dict() if result else {}

    async def reset_user_traffic(self, username: str) -> Dict[str, Any]:
        """Сброс трафика пользователя"""
        await self._ensure_api()
        result = await self.api.reset_user_data_usage(username=username, token=self.token.access_token)
        return result.dict() if result else {}

    # Методы для работы с администраторами
    async def get_admins(self, offset: int = 0, limit: int = 100, username: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение списка администраторов"""
        await self._ensure_api()
        admins = await self.api.get_admins(
            token=self.token.access_token,
            offset=offset,
            limit=limit,
            username=username
        )
        return [admin.dict() for admin in admins] if admins else []

    async def get_admin(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение информации об администраторе"""
        admins = await self.get_admins(username=username, limit=1)
        return admins[0] if admins else None

    async def create_admin(self, admin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание администратора"""
        await self._ensure_api()
        from marzban.models import AdminCreate
        admin_create = AdminCreate(**admin_data)
        result = await self.api.create_admin(admin=admin_create, token=self.token.access_token)
        return result.dict() if result else {}

    async def modify_admin(self, username: str, admin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Изменение администратора"""
        await self._ensure_api()
        from marzban.models import AdminModify
        admin_modify = AdminModify(**admin_data)
        result = await self.api.modify_admin(username=username, admin=admin_modify, token=self.token.access_token)
        return result.dict() if result else {}

    async def delete_admin(self, username: str) -> Dict[str, Any]:
        """Удаление администратора"""
        await self._ensure_api()
        result = await self.api.remove_admin(username=username, token=self.token.access_token)
        return result.dict() if result else {}

    # Методы для работы с узлами
    async def get_nodes(self) -> List[Dict[str, Any]]:
        """Получение списка узлов"""
        await self._ensure_api()
        nodes = await self.api.get_nodes(token=self.token.access_token)
        return [node.dict() for node in nodes] if nodes else []

    async def get_node(self, node_id: int) -> Dict[str, Any]:
        """Получение информации об узле"""
        await self._ensure_api()
        node = await self.api.get_node(node_id=node_id, token=self.token.access_token)
        return node.dict() if node else {}

    # Получение подписки пользователя
    async def get_user_subscription(self, username: str) -> str:
        """Получение рабочей ссылки на подписку через информацию о пользователе с 3 попытками"""
        max_attempts = 3
        wait_time = 2  # секунды между попытками

        for attempt in range(1, max_attempts + 1):
            try:
                await self._ensure_api()

                # Получаем информацию о пользователе - здесь содержится корректная ссылка
                user_info = await self.get_user(username)

                if user_info and user_info.get('subscription_url'):
                    subscription_url = user_info['subscription_url']
                    logger.info(f"Получена рабочая ссылка подписки (попытка {attempt}): {subscription_url}")
                    return subscription_url
                else:
                    logger.warning(f"subscription_url не найден в информации о пользователе (попытка {attempt})")

            except Exception as e:
                logger.error(f"Ошибка получения подписки для {username} (попытка {attempt}): {e}")

            # Если это не последняя попытка - ждем перед следующей
            if attempt < max_attempts:
                logger.info(f"Повторная попытка через {wait_time} секунды...")
                await asyncio.sleep(wait_time)

        # Если все попытки исчерпаны
        error_msg = f"Не удалось получить ссылку на подписку после {max_attempts} попыток."
        logger.error(error_msg)
        raise Exception(error_msg)

    async def close(self):
        """Закрытие соединения"""
        if self.api:
            await self.api.close()
            logger.info("Соединение с API закрыто")