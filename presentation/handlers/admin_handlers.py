# presentation/handlers/admin_handlers.py
from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from presentation.handlers.base import BaseHandler
from presentation.keyboards import (
    get_admin_main_keyboard,
    get_admin_users_keyboard,
    get_pagination_keyboard,
    get_support_tickets_keyboard
)
from infrastructure.marzban.api_client import MarzbanAPIClient
from domain.services.support_service import SupportService
from core.security import (
    is_admin,
    is_support,
    can_access_support_tickets,
    can_access_admin_panel
)
from core.config import config
import logging

logger = logging.getLogger(__name__)


class AdminHandlers(BaseHandler):
    def __init__(self, marzban_client: MarzbanAPIClient, support_service: SupportService):
        self.marzban_client = marzban_client
        self.support_service = support_service
        super().__init__()

    def _register_handlers(self):
        """Регистрация обработчиков администратора"""
        self.router.message.register(self.admin_panel, Command("admin"))
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("admin_"))
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("users_"))
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("admins_"))
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("support_"))

    async def admin_panel(self, message: Message):
        """Показ панели администратора"""
        if not can_access_admin_panel(message.from_user.id):
            await message.answer("❌ У вас нет доступа к панели администратора")
            return

        await message.answer(
            "👨‍💼 Панель администратора Marzban",
            reply_markup=get_admin_main_keyboard()
        )

    async def admin_callback_handler(self, callback: CallbackQuery):
        """Обработчик callback'ов администратора"""
        user_id = callback.from_user.id

        # Проверяем доступ для разных типов callback'ов
        data = callback.data

        if data.startswith("admin_"):
            # доступ к тикетам поддержки: админ или саппорт
            if data == "admin_support_tickets":
                if not can_access_support_tickets(user_id):
                    await callback.answer("🚫 У вас нет доступа к тикетам поддержки", show_alert=True)
                    return
            # остальные админские действия — только для админов
            elif not can_access_admin_panel(user_id):
                await callback.answer("🚫 У вас нет прав администратора", show_alert=True)
                return

        if data in ["admin_stats", "admin_admins", "admin_users", "admin_nodes"] and not self._is_admin(user_id):
            await callback.answer("❌ Только для администраторов", show_alert=True)
            return

        try:
            if data == "admin_stats":
                await self._show_system_stats(callback)
            elif data == "admin_users":
                await self._show_users_menu(callback)
            elif data == "admin_admins":
                await self._show_admins_list(callback, 0)
            elif data == "admin_nodes":
                await self._show_nodes_list(callback)
            elif data == "admin_support_tickets":
                await self._show_support_tickets_menu(callback)
            elif data == "admin_back":
                await callback.message.edit_text(
                    "👨‍💼 Панель администратора Marzban",
                    reply_markup=get_admin_main_keyboard()
                )
            elif data.startswith("users_list"):
                await self._show_users_list(callback, 0)
            elif data.startswith("users_page_"):
                page = int(data.split("_")[2])
                await self._show_users_list(callback, page)
            elif data.startswith("admins_page_"):
                page = int(data.split("_")[2])
                await self._show_admins_list(callback, page)
            elif data.startswith("support_"):
                await self._handle_support_callbacks(callback, data)
        except Exception as e:
            logger.error(f"Error in admin callback handler: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)

    async def _show_support_tickets_menu(self, callback: CallbackQuery):
        """Показ меню управления тикетами поддержки"""
        try:
            user_id = callback.from_user.id
            # Получаем статистику тикетов
            user_tickets = await self.support_service.get_user_tickets(user_id)
            total_tickets = len(user_tickets)
            open_tickets = len([t for t in user_tickets if t.status == "open"])

            message = (
                "📋 **Управление тикетами поддержки**\n\n"
                f"📊 **Статистика:**\n"
                f"• Всего тикетов: {total_tickets}\n"
                f"• Открытых: {open_tickets}\n"
                f"• Закрытых: {total_tickets - open_tickets}\n\n"
                "Выберите действие:"
            )

            await callback.message.edit_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_support_tickets_keyboard()  # Используем обновленную клавиатуру
            )
        except Exception as e:
            logger.error(f"Error showing support tickets menu: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка загрузки меню тикетов: {str(e)}"
            )

    async def _handle_support_callbacks(self, callback: CallbackQuery, data: str):
        """Обработчик callback'ов поддержки"""
        if data == "support_tickets_list":
            await self._show_support_tickets_list(callback)
        elif data == "support_ticket_search":
            await callback.answer("🔍 Функция поиска тикетов в разработке", show_alert=True)
        elif data == "support_tickets_stats":
            await self._show_support_tickets_stats(callback)
        else:
            await callback.answer("⏳ Функция в разработке", show_alert=True)

    async def _show_support_tickets_list(self, callback: CallbackQuery):
        """Показ списка тикетов поддержки"""
        try:
            user_id = callback.from_user.id
            user_tickets = await self.support_service.get_user_tickets(user_id)

            if not user_tickets:
                await callback.message.edit_text(
                    "📭 Тикеты поддержки не найдены",
                    reply_markup=get_support_tickets_keyboard()  # Обновлено
                )
                return

            message = "📋 **Список ваших тикетов поддержки**\n\n"

            for i, ticket in enumerate(user_tickets[:10], 1):
                status_icon = "🟢" if ticket.status == "open" else "🔴"
                created_date = ticket.created_at.strftime("%d.%m.%Y %H:%M") if ticket.created_at else "N/A"
                message += (
                    f"{status_icon} **Тикет #{ticket.id}**\n"
                    f"📅 {created_date}\n"
                    f"📝 {ticket.message[:50]}...\n"
                    f"👤 {ticket.user_name}\n\n"
                )

            if len(user_tickets) > 10:
                message += f"ℹ️ Показано 10 из {len(user_tickets)} тикетов\n\n"

            message += "Для просмотра деталей тикета используйте поиск по ID"

            await callback.message.edit_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_support_tickets_keyboard()  # Обновлено
            )

        except Exception as e:
            logger.error(f"Error showing support tickets list: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка загрузки списка тикетов: {str(e)}",
                reply_markup=get_support_tickets_keyboard()  # Обновлено
            )

    async def _show_support_tickets_stats(self, callback: CallbackQuery):
        """Показ статистики тикетов"""
        try:
            user_id = callback.from_user.id
            user_tickets = await self.support_service.get_user_tickets(user_id)

            total_tickets = len(user_tickets)
            open_tickets = len([t for t in user_tickets if t.status == "open"])
            closed_tickets = total_tickets - open_tickets

            # Группировка по месяцам
            from collections import defaultdict
            monthly_stats = defaultdict(int)
            for ticket in user_tickets:
                if ticket.created_at:
                    month_key = ticket.created_at.strftime("%Y-%m")
                    monthly_stats[month_key] += 1

            message = (
                "📊 **Статистика тикетов поддержки**\n\n"
                f"**Общая статистика:**\n"
                f"• Всего тикетов: {total_tickets}\n"
                f"• Открытых: {open_tickets}\n"
                f"• Закрытых: {closed_tickets}\n"
            )

            if total_tickets > 0:
                message += f"• Процент закрытых: {closed_tickets / total_tickets * 100:.1f}%\n\n"
            else:
                message += "\n"

            if monthly_stats:
                message += "**Статистика по месяцам:**\n"
                for month, count in sorted(monthly_stats.items())[-6:]:
                    message += f"• {month}: {count} тикетов\n"

            await callback.message.edit_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_support_tickets_keyboard()  # Обновлено
            )

        except Exception as e:
            logger.error(f"Error showing support tickets stats: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка загрузки статистики: {str(e)}",
                reply_markup=get_support_tickets_keyboard()  # Обновлено
            )

    # Остальные методы остаются без изменений
    async def _show_system_stats(self, callback: CallbackQuery):
        """Показ системной статистики"""
        try:
            stats = await self.marzban_client.get_system_stats()

            cores = stats.get('cores', 1)
            cpu_usage = stats.get('cpu_usage', 0)
            ram_usage = stats.get('ram_usage', 0)
            ram_total = stats.get('ram_total', 1)
            ram_usage_percent = (ram_usage / ram_total) * 100

            message = (
                "📊 **Системная статистика**\n\n"
                f"🖥️ **ЦП:** {cores} ядер\n"
                f"📈 **Загрузка ЦП:** {cpu_usage:.1f}%\n"
                f"💾 **Используется ОЗУ:** {ram_usage / 1024 / 1024:.1f} МБ ({ram_usage_percent:.1f}%)\n"
                f"🆓 **Доступно ОЗУ:** {(ram_total - ram_usage) / 1024 / 1024:.1f} МБ\n"
                f"🔽 **Использовано трафика:** {stats.get('total_traffic', 0) / (1024 ** 3):.2f} ГБ\n\n"
                f"👥 **Всего пользователей:** {stats.get('total_users', 0)}\n"
                f"🟢 **Активные пользователи:** {stats.get('active_users', 0)}\n"
                f"⏸️ **В режиме ожидания:** {stats.get('on_hold_users', 0)}\n"
                f"🔴 **Неактивные пользователи:** {stats.get('disabled_users', 0)}"
            )

            await callback.message.edit_text(message, parse_mode="Markdown")

        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка получения статистики: {str(e)}")

    async def _show_users_menu(self, callback: CallbackQuery):
        """Меню управления пользователями"""
        await callback.message.edit_text(
            "👤 **Управление пользователей**\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_admin_users_keyboard()
        )

    async def _show_users_list(self, callback: CallbackQuery, page: int):
        """Показ списка пользователей с пагинацией"""
        try:
            users = await self.marzban_client.get_users(page * config.USERS_PER_PAGE, config.USERS_PER_PAGE)
            total_users = len(users)

            if not users:
                await callback.message.edit_text("📭 Пользователи не найдены")
                return

            message = "👤 **Список пользователей**\n\n"
            for i, user in enumerate(users, start=1):
                status_icon = "🟢" if user.get('status', 'active') == 'active' else "🔴"
                message += f"{status_icon} `{user.get('username', 'N/A')}`\n"

            total_pages = max(1, (total_users + config.USERS_PER_PAGE - 1) // config.USERS_PER_PAGE)
            pagination_keyboard = get_pagination_keyboard(page, total_pages, "users")

            await callback.message.edit_text(
                message,
                parse_mode="Markdown",
                reply_markup=pagination_keyboard
            )

        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка получения пользователей: {str(e)}")

    async def _show_admins_list(self, callback: CallbackQuery, page: int):
        """Показ списка администраторов"""
        try:
            admins = await self.marzban_client.get_admins(page * config.ADMINS_PER_PAGE, config.ADMINS_PER_PAGE)

            message = "👨‍💼 **Список администраторов**\n\n"
            for admin in admins:
                role = "🔧 Супер-админ" if admin.get('is_sudo', False) else "👤 Админ"
                message += f"{role}: `{admin.get('username', 'N/A')}`\n"

            await callback.message.edit_text(
                message,
                parse_mode="Markdown"
            )

        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка получения администраторов: {str(e)}")

    async def _show_nodes_list(self, callback: CallbackQuery):
        """Показ списка узлов"""
        try:
            nodes = await self.marzban_client.get_nodes()

            message = "🌐 **Список узлов**\n\n"
            for node in nodes:
                status = "🟢 Онлайн" if node.get('status', 'healthy') == 'healthy' else "🔴 Офлайн"
                message += f"{status} {node.get('name', 'N/A')}\n"
                message += f"   📍 {node.get('address', 'N/A')}\n"
                message += f"   👥 Пользователей: {node.get('user_count', 0)}\n\n"

            await callback.message.edit_text(
                message,
                parse_mode="Markdown"
            )

        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка получения узлов: {str(e)}")