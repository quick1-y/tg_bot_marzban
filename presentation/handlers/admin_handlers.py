# presentation/handlers/admin_handlers.py
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from presentation.handlers.base import BaseHandler
from presentation.keyboards import (
    get_admin_main_keyboard,
    get_admin_users_keyboard,
    get_admin_admins_keyboard,
    get_support_tickets_keyboard,
    get_support_tickets_pagination_keyboard,
    get_support_ticket_search_keyboard,
    get_admin_ticket_actions_keyboard,
    get_confirmation_keyboard,
)
from infrastructure.marzban.api_client import MarzbanAPIClient
from domain.services.support_service import SupportService
from domain.services.user_service import UserService
from core.security import (
    is_admin,
    is_support,
    can_access_support_tickets,
    can_access_admin_panel
)
from core.config import config
import logging
import html
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class SupportTicketStates(StatesGroup):
    waiting_for_ticket_id = State()
    waiting_for_reply_message = State()


class AdminCreationStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_is_sudo = State()
    waiting_for_telegram_id = State()


class AdminEditStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_is_sudo = State()
    waiting_for_telegram_id = State()


class AdminSearchStates(StatesGroup):
    waiting_for_username = State()


class UserCreationStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_limit = State()
    waiting_for_reset_strategy = State()
    waiting_for_expire = State()
    waiting_for_note = State()


class UserEditStates(StatesGroup):
    waiting_for_status = State()
    waiting_for_limit = State()
    waiting_for_reset_strategy = State()
    waiting_for_expire = State()
    waiting_for_note = State()


class UserSearchStates(StatesGroup):
    waiting_for_username = State()


class MassOperationStates(StatesGroup):
    waiting_for_hours = State()
    waiting_for_traffic = State()
    waiting_for_broadcast_message = State()


class AdminHandlers(BaseHandler):
    RESET_STRATEGIES = {
        "no_reset": "без сброса",
        "daily": "ежедневно",
        "weekly": "еженедельно",
        "monthly": "ежемесячно",
    }

    STATUS_CHOICES = {
        "active": "Активный",
        "on_hold": "В ожидании",
        "disabled": "Отключен",
    }

    def __init__(self, marzban_client: MarzbanAPIClient, support_service: SupportService, user_service: UserService):
        self.marzban_client = marzban_client
        self.support_service = support_service
        self.user_service = user_service
        self.users_page_limit = max(1, config.USERS_PER_PAGE)
        self.admins_page_limit = max(1, config.ADMINS_PER_PAGE)
        super().__init__()

    def _register_handlers(self):
        """Регистрация обработчиков администратора"""
        self.router.message.register(self.admin_panel, Command("admin"))
        # FSM обработчики администратора
        self.router.message.register(self._process_admin_search_input, AdminSearchStates.waiting_for_username)
        self.router.message.register(self._process_new_admin_username, AdminCreationStates.waiting_for_username)
        self.router.message.register(self._process_new_admin_password, AdminCreationStates.waiting_for_password)
        self.router.message.register(self._process_new_admin_is_sudo, AdminCreationStates.waiting_for_is_sudo)
        self.router.message.register(self._process_new_admin_telegram, AdminCreationStates.waiting_for_telegram_id)
        self.router.message.register(self._process_admin_edit_password, AdminEditStates.waiting_for_password)
        self.router.message.register(self._process_admin_edit_is_sudo, AdminEditStates.waiting_for_is_sudo)
        self.router.message.register(self._process_admin_edit_telegram, AdminEditStates.waiting_for_telegram_id)
        self.router.message.register(self._process_user_search_input, UserSearchStates.waiting_for_username)
        self.router.message.register(self._process_new_user_username, UserCreationStates.waiting_for_username)
        self.router.message.register(self._process_new_user_limit, UserCreationStates.waiting_for_limit)
        self.router.message.register(self._process_new_user_reset_strategy, UserCreationStates.waiting_for_reset_strategy)
        self.router.message.register(self._process_new_user_expire, UserCreationStates.waiting_for_expire)
        self.router.message.register(self._process_new_user_note, UserCreationStates.waiting_for_note)
        self.router.message.register(self._process_user_edit_status, UserEditStates.waiting_for_status)
        self.router.message.register(self._process_user_edit_limit, UserEditStates.waiting_for_limit)
        self.router.message.register(self._process_user_edit_reset_strategy, UserEditStates.waiting_for_reset_strategy)
        self.router.message.register(self._process_user_edit_expire, UserEditStates.waiting_for_expire)
        self.router.message.register(self._process_user_edit_note, UserEditStates.waiting_for_note)
        self.router.message.register(self._process_mass_hours_input, MassOperationStates.waiting_for_hours)
        self.router.message.register(self._process_mass_traffic_input, MassOperationStates.waiting_for_traffic)
        self.router.message.register(self._process_broadcast_message, MassOperationStates.waiting_for_broadcast_message)
        self.router.message.register(self._process_ticket_search_input, SupportTicketStates.waiting_for_ticket_id)
        self.router.message.register(self._process_ticket_reply_message, SupportTicketStates.waiting_for_reply_message)
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("admin_"))
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("users_"))
        self.router.callback_query.register(self.admin_callback_handler, F.data.startswith("admins_"))
        self.router.callback_query.register(self._cancel_support_action, F.data == "support_ticket_cancel")
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

    @staticmethod
    def _is_cancel_message(text: Optional[str]) -> bool:
        if not text:
            return False
        return text.strip().lower() in {"отмена", "cancel", "/cancel"}

    @staticmethod
    def _extract_page_from_callback(data: str, default: int = 0) -> int:
        parts = data.split(":")
        if len(parts) > 1 and parts[-1].isdigit():
            return max(0, int(parts[-1]))
        return default

    @staticmethod
    def _extract_username_and_page(data: str, default_page: int = 0) -> tuple[str, int]:
        parts = data.split(":")
        username = parts[1] if len(parts) > 1 else ""
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else default_page
        return username, max(0, page)

    @staticmethod
    def _split_username_page(payload: str) -> tuple[str, int]:
        if ":" in payload:
            username, page_str = payload.split(":", maxsplit=1)
            if page_str.isdigit():
                return username, int(page_str)
        return payload, 0

    @staticmethod
    def _format_data_limit(limit: Optional[int]) -> str:
        if not limit:
            return "Без ограничений"
        return f"{limit / (1024 ** 3):.2f} ГБ"

    @staticmethod
    def _format_expire(expire: Optional[int]) -> str:
        if not expire:
            return "Без срока"
        try:
            dt = datetime.fromtimestamp(expire)
        except (ValueError, OSError):
            return str(expire)
        return dt.strftime("%d.%m.%Y %H:%M")

    @staticmethod
    def _parse_data_limit_input(text: str) -> Optional[int]:
        cleaned = text.strip().replace(",", ".")
        if cleaned.lower() in {"0", "безлимит", "без ограничения", "нет", "none", "skip", "пропустить"}:
            return 0
        value = float(cleaned)
        if value < 0:
            raise ValueError("negative")
        return int(value * (1024 ** 3))

    @staticmethod
    def _parse_expire_input(text: str) -> Optional[int]:
        cleaned = text.strip()
        if cleaned.lower() in {"0", "безлимит", "без срока", "нет", "none", "skip", "пропустить"}:
            return None

        formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d.%m.%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return int(dt.timestamp())
            except ValueError:
                continue

        if cleaned.isdigit():
            return int(cleaned)

        raise ValueError("invalid date")

    @classmethod
    def _format_reset_strategy(cls, strategy: Optional[str]) -> str:
        if not strategy:
            return cls.RESET_STRATEGIES.get("no_reset", "Без сброса")
        return cls.RESET_STRATEGIES.get(strategy, strategy)

    @classmethod
    def _format_status(cls, status: Optional[str]) -> str:
        if not status:
            return cls.STATUS_CHOICES.get("active", "Активный")
        return cls.STATUS_CHOICES.get(status, status)

    @staticmethod
    def _parse_bool_input(text: str, current: Optional[bool] = None) -> Optional[bool]:
        cleaned = text.strip().lower()
        if cleaned in {"да", "yes", "true", "1", "ага", "y", "sudo"}:
            return True
        if cleaned in {"нет", "no", "false", "0", "n"}:
            return False
        if cleaned in {"skip", "пропустить", "оставить", "без изменений"}:
            return current
        raise ValueError("invalid bool")

    async def _cancel_operation(self, message: Message, state: FSMContext, menu: str = "users"):
        """Отменяет текущее FSM-действие и возвращает в нужное меню"""
        await state.clear()
        if menu == "admins":
            await message.answer(
                "❌ Действие отменено.",
                reply_markup=get_admin_admins_keyboard()
            )
        else:
            await message.answer(
                "❌ Действие отменено.",
                reply_markup=get_admin_users_keyboard()
            )

    async def admin_callback_handler(self, callback: CallbackQuery, state: FSMContext):
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

        if data in ["admin_stats", "admin_admins", "admin_users", "admin_nodes"] and not is_admin(user_id):
            await callback.answer("❌ Только для администраторов", show_alert=True)
            return

        try:
            if data == "admin_stats":
                await self._show_system_stats(callback)
            elif data == "admin_users":
                await state.clear()
                await self._show_users_menu(callback)
            elif data == "admin_admins":
                await state.clear()
                await self._show_admins_menu(callback)
            elif data == "admin_nodes":
                await self._show_nodes_list(callback)
            elif data == "admin_support_tickets":
                await state.clear()
                await self._show_support_tickets_menu(callback)
            elif data == "admin_back":
                await state.clear()
                await callback.message.edit_text(
                    "👨‍💼 Панель администратора Marzban",
                    reply_markup=get_admin_main_keyboard()
                )
            elif data.startswith("users_list:"):
                page = self._extract_page_from_callback(data)
                await state.clear()
                await self._show_users_list(callback, page)
            elif data.startswith("users_view:"):
                username, page = self._extract_username_and_page(data)
                await state.clear()
                await self._show_user_details(callback, username, page)
            elif data.startswith("users_edit:"):
                username, page = self._extract_username_and_page(data)
                await state.clear()
                await self._start_user_edit(callback, state, username, page)
            elif data.startswith("users_delete:"):
                username, page = self._extract_username_and_page(data)
                await self._confirm_user_deletion(callback, state, username, page)
            elif data.startswith("confirm_delete_user_"):
                payload = data[len("confirm_delete_user_"):]
                username, page = self._split_username_page(payload)
                await self._delete_user(callback, state, username, page)
            elif data == "cancel_delete_user":
                await self._cancel_delete_user(callback, state)
            elif data == "users_search":
                await state.set_state(UserSearchStates.waiting_for_username)
                await callback.message.edit_text(
                    "🔍 Введите имя пользователя Marzban (или напишите «отмена»):"
                )
                await callback.answer()
            elif data == "user_add":
                await state.clear()
                await self._start_user_creation(callback, state)
            elif data == "users_add_time":
                await state.set_state(MassOperationStates.waiting_for_hours)
                await callback.message.edit_text(
                    "⏰ Укажите количество часов для продления подписки всех пользователей с месячным тарифом (или «отмена»):"
                )
                await callback.answer()
            elif data == "users_add_data":
                await state.set_state(MassOperationStates.waiting_for_traffic)
                await callback.message.edit_text(
                    "💽 Укажите количество ГБ, которое добавить к лимиту всех пользователей с ограничением (или «отмена»):"
                )
                await callback.answer()
            elif data == "users_broadcast":
                await state.set_state(MassOperationStates.waiting_for_broadcast_message)
                await callback.message.edit_text(
                    "📣 Введите текст рассылки для всех пользователей (или «отмена»):"
                )
                await callback.answer()
            elif data.startswith("admins_list:"):
                page = self._extract_page_from_callback(data)
                await state.clear()
                await self._show_admins_list(callback, page)
            elif data == "admins_search":
                await state.set_state(AdminSearchStates.waiting_for_username)
                await callback.message.edit_text(
                    "🔍 Введите имя администратора (или напишите «отмена»):",
                    reply_markup=None
                )
                await callback.answer()
            elif data == "admins_add":
                await state.clear()
                await self._start_admin_creation(callback, state)
            elif data.startswith("admin_manage:"):
                username, page = self._extract_username_and_page(data)
                await state.clear()
                await self._show_admin_details(callback, username, page)
            elif data.startswith("admins_edit:"):
                username, page = self._extract_username_and_page(data)
                await state.clear()
                await self._start_admin_edit(callback, state, username, page)
            elif data.startswith("admins_delete:"):
                username, page = self._extract_username_and_page(data)
                await self._confirm_admin_deletion(callback, state, username, page)
            elif data.startswith("confirm_delete_admin_"):
                username = data[len("confirm_delete_admin_"):]
                await self._delete_admin(callback, state, username)
            elif data == "cancel_delete_admin":
                await self._cancel_delete_admin(callback, state)
            elif data.startswith("support_"):
                await self._handle_support_callbacks(callback, data, state)
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

    async def _handle_support_callbacks(self, callback: CallbackQuery, data: str, state: FSMContext):
        """Обработчик callback'ов поддержки"""
        if data.startswith("support_tickets_list"):
            parts = data.split(":", maxsplit=1)
            offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            await self._show_support_tickets_list(callback, offset)
        elif data == "support_ticket_search":
            await state.set_state(SupportTicketStates.waiting_for_ticket_id)
            await state.update_data(origin_message_id=callback.message.message_id)
            await callback.message.edit_text(
                "🔍 Введите ID тикета, который хотите открыть:",
                reply_markup=get_support_ticket_search_keyboard()
            )
            await callback.answer()
        elif data == "support_tickets_stats":
            await self._show_support_tickets_stats(callback)
        elif data.startswith("support_ticket_toggle:"):
            await self._toggle_ticket_status(callback, data)
        elif data.startswith("support_ticket_reply:"):
            await self._start_ticket_reply(callback, data, state)
        else:
            await callback.answer("⏳ Функция в разработке", show_alert=True)

    async def _show_support_tickets_list(self, callback: CallbackQuery, offset: int = 0):
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

            total_tickets = len(user_tickets)
            page_size = 10
            offset = max(offset, 0)

            if offset >= total_tickets:
                offset = max(total_tickets - page_size, 0)

            current_slice = user_tickets[offset:offset + page_size]

            message = "📋 **Список ваших тикетов поддержки**\n\n"

            for ticket in current_slice:
                status_icon = "🟢" if ticket.status == "open" else "🔴"
                created_date = ticket.created_at.strftime("%d.%m.%Y %H:%M") if ticket.created_at else "N/A"
                preview = ticket.message or ""
                preview = (preview[:50] + "...") if len(preview) > 50 else preview
                message += (
                    f"{status_icon} **Тикет #{ticket.id}**\n"
                    f"📅 {created_date}\n"
                    f"📝 {preview}\n"
                    f"👤 {ticket.user_name}\n\n"
                )

            if current_slice:
                start_number = offset + 1
                end_number = offset + len(current_slice)
                message += f"ℹ️ Показаны тикеты {start_number}–{end_number} из {total_tickets}\n\n"
            else:
                message += "ℹ️ Больше тикетов для отображения нет\n\n"

            message += "Для просмотра деталей тикета используйте поиск по ID"

            await callback.message.edit_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_support_tickets_pagination_keyboard(offset, total_tickets, page_size)
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

    async def _cancel_support_action(self, callback: CallbackQuery, state: FSMContext):
        """Отмена текущего действия с тикетом"""
        await state.clear()
        await callback.answer("❌ Действие отменено")
        await self._show_support_tickets_menu(callback)

    async def _toggle_ticket_status(self, callback: CallbackQuery, data: str):
        """Переключение статуса тикета"""
        if not can_access_support_tickets(callback.from_user.id):
            await callback.answer("🚫 Нет доступа", show_alert=True)
            return

        parts = data.split(":")
        if len(parts) != 3 or not parts[1].isdigit():
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        ticket_id = int(parts[1])
        new_status = parts[2]

        if new_status not in {"open", "closed"}:
            await callback.answer("❌ Некорректный статус", show_alert=True)
            return

        success = await self.support_service.update_ticket_status(ticket_id, new_status)
        if not success:
            await callback.answer("⚠️ Не удалось обновить статус", show_alert=True)
            return

        ticket = await self.support_service.get_ticket_for_admin(ticket_id)
        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        await callback.answer("✅ Статус обновлен")
        await callback.message.edit_text(
            self._format_ticket_details_for_admin(ticket),
            parse_mode="HTML",
            reply_markup=get_admin_ticket_actions_keyboard(ticket.id, ticket.status == "open")
        )

    async def _start_ticket_reply(self, callback: CallbackQuery, data: str, state: FSMContext):
        """Начинает процесс отправки ответа пользователю"""
        if not can_access_support_tickets(callback.from_user.id):
            await callback.answer("🚫 Нет доступа", show_alert=True)
            return

        parts = data.split(":")
        if len(parts) < 2 or not parts[1].isdigit():
            await callback.answer("❌ Некорректный ID тикета", show_alert=True)
            return

        ticket_id = int(parts[1])
        ticket = await self.support_service.get_ticket_for_admin(ticket_id)
        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        await state.set_state(SupportTicketStates.waiting_for_reply_message)
        await state.update_data(ticket_id=ticket_id, origin_message_id=callback.message.message_id)

        await callback.answer()
        await callback.message.answer(
            (
                f"✉️ Напишите сообщение пользователю тикета #{ticket_id}.\n"
                "Сообщение будет отправлено от имени бота."
            ),
            reply_markup=get_support_ticket_search_keyboard()
        )

    async def _process_ticket_search_input(self, message: Message, state: FSMContext):
        """Обработка введенного ID тикета"""
        if not can_access_support_tickets(message.from_user.id):
            await message.answer("🚫 У вас нет доступа к тикетам поддержки")
            await state.clear()
            return

        ticket_id_text = message.text.strip().lstrip("#")
        if not ticket_id_text.isdigit():
            await message.answer("❌ Укажите корректный ID тикета (только цифры).")
            return

        ticket_id = int(ticket_id_text)
        ticket = await self.support_service.get_ticket_for_admin(ticket_id)
        if not ticket:
            await message.answer(f"❌ Тикет #{ticket_id} не найден. Попробуйте еще раз.")
            return

        state_data = await state.get_data()
        origin_message_id = state_data.get("origin_message_id")
        reply_markup = get_admin_ticket_actions_keyboard(ticket.id, ticket.status == "open")
        ticket_text = self._format_ticket_details_for_admin(ticket)

        await state.clear()

        if origin_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=origin_message_id,
                    text=ticket_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение с тикетом: {e}")
                await message.answer(ticket_text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await message.answer(ticket_text, parse_mode="HTML", reply_markup=reply_markup)

    async def _process_ticket_reply_message(self, message: Message, state: FSMContext):
        """Отправка сообщения пользователю тикета"""
        if not can_access_support_tickets(message.from_user.id):
            await message.answer("🚫 У вас нет доступа к тикетам поддержки")
            await state.clear()
            return

        reply_text = (message.text or "").strip()
        if not reply_text:
            await message.answer("❌ Сообщение не может быть пустым.")
            return

        state_data = await state.get_data()
        ticket_id = state_data.get("ticket_id")
        origin_message_id = state_data.get("origin_message_id")

        if not ticket_id:
            await message.answer("⚠️ Не найден контекст тикета. Попробуйте снова.")
            await state.clear()
            return

        ticket = await self.support_service.get_ticket_for_admin(ticket_id)
        if not ticket:
            await message.answer("❌ Тикет не найден. Возможно, он был удален.")
            await state.clear()
            return

        try:
            await message.bot.send_message(
                chat_id=ticket.user_id,
                text=(
                    f"📩 Ответ от поддержки по тикету #{ticket.id}\n\n"
                    f"{reply_text}"
                )
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {ticket.user_id}: {e}")
            await message.answer("❌ Не удалось отправить сообщение пользователю. Попробуйте позже.")
            return

        saved = await self.support_service.add_ticket_response(ticket_id, reply_text)
        if not saved:
            await message.answer("⚠️ Ответ не удалось сохранить в базе данных.")
            return

        await message.answer("✅ Сообщение отправлено пользователю.")

        updated_ticket = await self.support_service.get_ticket_for_admin(ticket_id)
        reply_markup = None
        ticket_text = ""
        if updated_ticket:
            reply_markup = get_admin_ticket_actions_keyboard(
                updated_ticket.id,
                updated_ticket.status == "open"
            )
            ticket_text = self._format_ticket_details_for_admin(updated_ticket)

        await state.clear()

        if origin_message_id and ticket_text:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=origin_message_id,
                    text=ticket_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение с деталями тикета: {e}")
                if ticket_text:
                    await message.answer(ticket_text, parse_mode="HTML", reply_markup=reply_markup)
        elif ticket_text:
            await message.answer(ticket_text, parse_mode="HTML", reply_markup=reply_markup)

    async def _process_new_user_username(self, message: Message, state: FSMContext):
        """Обрабатывает ввод имени при создании пользователя"""
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        username = text.strip()
        if not username:
            await message.answer("Имя пользователя не может быть пустым. Попробуйте снова:")
            return

        try:
            existing = await self.marzban_client.get_user(username)
            if existing:
                await message.answer("Такой пользователь уже существует. Укажите другое имя:")
                return
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя {username}: {e}")
            await message.answer("⚠️ Не удалось проверить пользователя. Попробуйте другое имя или повторите позже.")
            return

        data = await state.get_data()
        new_user = data.get("new_user", {})
        new_user.update({"username": username})
        await state.update_data(new_user=new_user)
        await state.set_state(UserCreationStates.waiting_for_limit)
        await message.answer(
            "Укажите лимит трафика в ГБ (0 — безлимит) или напишите «отмена»."
        )

    async def _process_new_user_limit(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        try:
            limit_bytes = self._parse_data_limit_input(text)
        except ValueError:
            await message.answer("Введите число — количество ГБ (например, 50 или 0 для безлимита):")
            return

        data = await state.get_data()
        new_user = data.get("new_user", {})
        new_user["data_limit"] = limit_bytes

        if limit_bytes == 0:
            new_user["data_limit_reset_strategy"] = "no_reset"
            await state.update_data(new_user=new_user)
            await state.set_state(UserCreationStates.waiting_for_expire)
            await message.answer(
                "Введите дату окончания подписки в формате ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ.\n"
                "Укажите 0, если подписка бессрочная."
            )
            return

        await state.update_data(new_user=new_user)
        await state.set_state(UserCreationStates.waiting_for_reset_strategy)
        await message.answer(
            "Выберите стратегию сброса трафика (daily/weekly/monthly/no_reset) или напишите «пропустить»:")

    async def _process_new_user_reset_strategy(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        cleaned = text.strip().lower()
        strategy_map = {
            "daily": "daily",
            "ежедневно": "daily",
            "weekly": "weekly",
            "еженедельно": "weekly",
            "monthly": "monthly",
            "ежемесячно": "monthly",
            "no_reset": "no_reset",
            "без сброса": "no_reset",
            "пропустить": None,
            "skip": None,
        }

        strategy = strategy_map.get(cleaned)
        if strategy is None and cleaned not in {"", "пропустить", "skip"}:
            await message.answer("Укажите одну из стратегий: daily, weekly, monthly, no_reset или «пропустить».")
            return

        data = await state.get_data()
        new_user = data.get("new_user", {})
        if strategy:
            new_user["data_limit_reset_strategy"] = strategy
        elif "data_limit_reset_strategy" not in new_user:
            new_user["data_limit_reset_strategy"] = "no_reset"

        await state.update_data(new_user=new_user)
        await state.set_state(UserCreationStates.waiting_for_expire)
        await message.answer(
            "Введите дату окончания подписки в формате ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ.\n"
            "Укажите 0, если подписка бессрочная."
        )

    async def _process_new_user_expire(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        try:
            expire_value = self._parse_expire_input(text)
        except ValueError:
            await message.answer(
                "Не удалось распознать дату. Используйте формат ДД.ММ.ГГГГ или добавьте время ДД.ММ.ГГГГ ЧЧ:ММ."
            )
            return

        data = await state.get_data()
        new_user = data.get("new_user", {})
        new_user["expire"] = expire_value

        await state.update_data(new_user=new_user)
        await state.set_state(UserCreationStates.waiting_for_note)
        await message.answer("Введите примечание к пользователю или напишите «пропустить»: ")

    async def _process_new_user_note(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        note = "" if text.strip().lower() in {"", "skip", "пропустить"} else text.strip()

        data = await state.get_data()
        new_user = data.get("new_user", {})
        username = new_user.get("username")

        if not username:
            await self._cancel_operation(message, state, "users")
            return

        new_user["note"] = note

        if new_user.get("data_limit") is None:
            new_user["data_limit"] = 0
        if new_user.get("data_limit_reset_strategy") is None:
            new_user["data_limit_reset_strategy"] = "no_reset"

        try:
            await self.marzban_client.create_user(new_user)
        except Exception as e:
            logger.error(f"Не удалось создать пользователя {username}: {e}")
            await message.answer("❌ Не удалось создать пользователя. Проверьте данные и попробуйте снова.")
            await self._cancel_operation(message, state, "users")
            return

        await state.clear()
        await message.answer("✅ Пользователь успешно создан.")
        await self._send_user_details_message(message, username)

    async def _process_user_search_input(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        username = text.strip()
        if not username:
            await message.answer("Введите имя пользователя или «отмена»:")
            return

        try:
            user = await self.marzban_client.get_user(username)
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя {username}: {e}")
            await message.answer("❌ Не удалось получить данные пользователя. Попробуйте позже.")
            await state.clear()
            return

        if not user:
            await message.answer("Пользователь не найден. Попробуйте другое имя или напишите «отмена».")
            return

        await state.clear()
        await self._send_user_details_message(message, username)

    async def _process_admin_search_input(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        username = text.strip()
        if not username:
            await message.answer("Введите имя администратора или «отмена»:")
            return

        try:
            admin = await self.marzban_client.get_admin(username)
        except Exception as e:
            logger.error(f"Ошибка поиска администратора {username}: {e}")
            await message.answer("❌ Не удалось получить данные администратора. Попробуйте позже.")
            await state.clear()
            return

        if not admin:
            await message.answer("Администратор не найден. Попробуйте другое имя или напишите «отмена».")
            return

        await state.clear()
        await self._send_admin_details_message(message, username, 0)

    async def _process_new_admin_username(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        username = text.strip()
        if not username:
            await message.answer("Имя администратора не может быть пустым. Попробуйте снова:")
            return

        try:
            existing = await self.marzban_client.get_admin(username)
            if existing:
                await message.answer("Администратор с таким именем уже существует. Введите другое имя:")
                return
        except Exception:
            # если запрос завершился ошибкой 404 - админ не найден, продолжаем
            pass

        await state.update_data(new_admin={"username": username})
        await state.set_state(AdminCreationStates.waiting_for_password)
        await message.answer("Введите пароль для администратора или напишите «отмена»:")

    async def _process_new_admin_password(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        password = text.strip()
        if not password:
            await message.answer("Пароль не может быть пустым. Укажите пароль:")
            return

        data = await state.get_data()
        new_admin = data.get("new_admin", {})
        new_admin["password"] = password
        await state.update_data(new_admin=new_admin)
        await state.set_state(AdminCreationStates.waiting_for_is_sudo)
        await message.answer("Сделать администратора супер-админом? (да/нет):")

    async def _process_new_admin_is_sudo(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        data = await state.get_data()
        new_admin = data.get("new_admin", {})

        try:
            is_sudo = self._parse_bool_input(text)
            if is_sudo is None:
                raise ValueError
        except ValueError:
            await message.answer("Введите «да» или «нет»:")
            return

        new_admin["is_sudo"] = is_sudo
        await state.update_data(new_admin=new_admin)
        await state.set_state(AdminCreationStates.waiting_for_telegram_id)
        await message.answer("Укажите Telegram ID администратора или напишите «пропустить»:")

    async def _process_new_admin_telegram(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        cleaned = text.strip()
        telegram_id = None
        if cleaned.lower() not in {"", "skip", "пропустить"}:
            if not cleaned.isdigit():
                await message.answer("Telegram ID должен состоять только из цифр или используйте «пропустить».")
                return
            telegram_id = int(cleaned)

        data = await state.get_data()
        new_admin = data.get("new_admin", {})
        username = new_admin.get("username")
        password = new_admin.get("password")
        is_sudo = new_admin.get("is_sudo")

        if not username or password is None or is_sudo is None:
            await self._cancel_operation(message, state, "admins")
            return

        payload = {
            "username": username,
            "password": password,
            "is_sudo": is_sudo,
        }
        if telegram_id:
            payload["telegram_id"] = telegram_id

        try:
            await self.marzban_client.create_admin(payload)
        except Exception as e:
            logger.error(f"Не удалось создать администратора {username}: {e}")
            await message.answer("❌ Не удалось создать администратора. Попробуйте позже.")
            await self._cancel_operation(message, state, "admins")
            return

        await state.clear()
        await message.answer("✅ Администратор создан.")
        await self._send_admin_details_message(message, username, 0)

    async def _process_admin_edit_password(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        data = await state.get_data()
        context = data.get("edit_admin")
        if not context:
            await self._cancel_operation(message, state, "admins")
            return

        password = text.strip()
        if password and len(password) < 4:
            await message.answer("Пароль должен содержать минимум 4 символа или используйте «пропустить».")
            return

        if password:
            context.setdefault("changes", {})["password"] = password

        await state.update_data(edit_admin=context)
        await state.set_state(AdminEditStates.waiting_for_is_sudo)
        await message.answer(
            "Текущий статус супер-админа: {}\nОставить права? (да/нет/пропустить)".format(
                "да" if context.get("current", {}).get("is_sudo") else "нет"
            )
        )

    async def _process_admin_edit_is_sudo(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        data = await state.get_data()
        context = data.get("edit_admin")
        if not context:
            await self._cancel_operation(message, state, "admins")
            return

        current_value = context.get("current", {}).get("is_sudo", False)
        try:
            new_value = self._parse_bool_input(text, current=current_value)
            if new_value is None:
                new_value = current_value
        except ValueError:
            await message.answer("Введите «да», «нет» или «пропустить»:")
            return

        context.setdefault("changes", {})["is_sudo"] = new_value
        await state.update_data(edit_admin=context)
        await state.set_state(AdminEditStates.waiting_for_telegram_id)
        telegram_id = context.get("current", {}).get("telegram_id")
        telegram_text = telegram_id if telegram_id else "—"
        await message.answer(
            f"Текущий Telegram ID: {telegram_text}. Укажите новый ID или напишите «пропустить»."
        )

    async def _process_admin_edit_telegram(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "admins")
            return

        data = await state.get_data()
        context = data.get("edit_admin")
        if not context:
            await self._cancel_operation(message, state, "admins")
            return

        cleaned = text.strip()
        if cleaned.lower() in {"", "skip", "пропустить"}:
            telegram_id = context.get("current", {}).get("telegram_id")
        else:
            if not cleaned.isdigit():
                await message.answer("Telegram ID должен состоять только из цифр или используйте «пропустить».")
                return
            telegram_id = int(cleaned)

        context.setdefault("changes", {})["telegram_id"] = telegram_id
        await state.update_data(edit_admin=context)
        await self._apply_admin_edit_changes(message, state)

    async def _apply_admin_edit_changes(self, message: Message, state: FSMContext):
        data = await state.get_data()
        context = data.get("edit_admin") or {}
        username = context.get("username")
        page = context.get("page", 0)
        changes = context.get("changes", {})

        if not username:
            await self._cancel_operation(message, state, "admins")
            return

        payload: Dict[str, Any] = {}

        if "password" in changes:
            payload["password"] = changes["password"]
        if "is_sudo" in changes:
            payload["is_sudo"] = changes["is_sudo"]
        else:
            payload["is_sudo"] = context.get("current", {}).get("is_sudo", False)
        if "telegram_id" in changes:
            payload["telegram_id"] = changes["telegram_id"]

        try:
            await self.marzban_client.modify_admin(username, payload)
        except Exception as e:
            logger.error(f"Не удалось обновить администратора {username}: {e}")
            await message.answer("❌ Не удалось сохранить изменения. Попробуйте позже.")
            await state.clear()
            return

        await state.clear()
        await message.answer("✅ Изменения администратора сохранены.")
        await self._send_admin_details_message(message, username, page)

    async def _process_mass_hours_input(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        try:
            hours = int(text.strip())
            if hours == 0:
                raise ValueError
        except ValueError:
            await message.answer("Введите целое число часов (можно отрицательное для уменьшения) или «отмена»:")
            return

        await state.clear()
        updated, errors = await self._bulk_add_hours(hours)
        await message.answer(
            f"⏰ Добавлено {hours} ч подписки {updated} пользователям."
            + (f"\n⚠️ Ошибок: {errors}" if errors else "")
        )
        await self._show_users_menu_from_message(message)

    async def _process_mass_traffic_input(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        try:
            amount = float(text.replace(",", "."))
            if amount == 0:
                raise ValueError
        except ValueError:
            await message.answer("Введите число — количество ГБ для добавления (можно отрицательное) или «отмена»:")
            return

        await state.clear()
        updated, errors = await self._bulk_add_traffic(amount)
        await message.answer(
            f"💽 Добавлено {amount} ГБ {updated} пользователям."
            + (f"\n⚠️ Ошибок: {errors}" if errors else "")
        )
        await self._show_users_menu_from_message(message)

    async def _process_broadcast_message(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        content = text.strip()
        if not content:
            await message.answer("Сообщение не может быть пустым. Введите текст рассылки или «отмена»:")
            return

        await state.clear()
        sent, failed = await self._send_broadcast(message, content)
        await message.answer(
            f"📣 Рассылка завершена. Успешно: {sent}, ошибок: {failed}.")
        await self._show_users_menu_from_message(message)

    async def _show_users_menu_from_message(self, message: Message):
        await message.answer(
            "Выберите дальнейшее действие:",
            reply_markup=get_admin_users_keyboard()
        )

    async def _bulk_add_hours(self, hours: int) -> tuple[int, int]:
        offset = 0
        limit = max(50, self.users_page_limit)
        updated = 0
        errors = 0

        while True:
            response = await self.marzban_client.get_users(offset=offset, limit=limit)
            users = response.get("users", [])
            if not users:
                break

            for user in users:
                expire = user.get("expire")
                username = user.get("username")
                if not username or not expire:
                    continue
                try:
                    new_expire = int(expire) + hours * 3600
                    await self.marzban_client.modify_user(username, {"expire": new_expire})
                    updated += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Не удалось обновить expire пользователя {username}: {e}")

            offset += len(users)
            total = response.get("total", offset)
            if offset >= total:
                break

        return updated, errors

    async def _bulk_add_traffic(self, amount_gb: float) -> tuple[int, int]:
        offset = 0
        limit = max(50, self.users_page_limit)
        updated = 0
        errors = 0
        delta_bytes = int(amount_gb * (1024 ** 3))

        while True:
            response = await self.marzban_client.get_users(offset=offset, limit=limit)
            users = response.get("users", [])
            if not users:
                break

            for user in users:
                username = user.get("username")
                data_limit = user.get("data_limit")
                if not username or not data_limit:
                    continue
                try:
                    new_limit = int(data_limit) + delta_bytes
                    await self.marzban_client.modify_user(username, {"data_limit": max(new_limit, 0)})
                    updated += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Не удалось обновить лимит пользователя {username}: {e}")

            offset += len(users)
            total = response.get("total", offset)
            if offset >= total:
                break

        return updated, errors

    async def _send_broadcast(self, message: Message, content: str) -> tuple[int, int]:
        users = await self.user_service.get_all_users()
        bot = message.bot
        sent = 0
        failed = 0

        for user in users:
            if not user.telegram_id:
                continue
            try:
                await bot.send_message(user.telegram_id, content)
                sent += 1
            except Exception as e:
                failed += 1
                logger.error(f"Не удалось отправить сообщение {user.telegram_id}: {e}")

        return sent, failed


    async def _process_user_edit_status(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        data = await state.get_data()
        context = data.get("edit_user")
        if not context:
            await self._cancel_operation(message, state, "users")
            return

        cleaned = text.strip().lower()
        allowed = {"active", "on_hold", "disabled"}

        if cleaned in {"", "skip", "пропустить"}:
            new_status = context.get("current", {}).get("status", "active")
        elif cleaned in allowed:
            new_status = cleaned
        else:
            await message.answer("Укажите один из статусов: active, on_hold или disabled (или «пропустить»).")
            return

        context.setdefault("changes", {})["status"] = new_status
        await state.update_data(edit_user=context)
        await state.set_state(UserEditStates.waiting_for_limit)

        current_limit = context.get("current", {}).get("data_limit")
        await message.answer(
            "Текущий лимит: {}\nВведите новый лимит в ГБ (0 — безлимит) или напишите «пропустить».".format(
                self._format_data_limit(current_limit)
            )
        )

    async def _process_user_edit_limit(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        data = await state.get_data()
        context = data.get("edit_user")
        if not context:
            await self._cancel_operation(message, state, "users")
            return

        cleaned = text.strip().lower()
        if cleaned in {"", "skip", "пропустить"}:
            limit_bytes = context.get("current", {}).get("data_limit")
        else:
            try:
                limit_bytes = self._parse_data_limit_input(text)
            except ValueError:
                await message.answer("Введите число — количество ГБ (например, 100 или 0 для безлимита):")
                return

        context.setdefault("changes", {})["data_limit"] = limit_bytes
        context["working_limit"] = limit_bytes
        await state.update_data(edit_user=context)
        await state.set_state(UserEditStates.waiting_for_reset_strategy)

        current_strategy = context.get("current", {}).get("data_limit_reset_strategy") or "no_reset"
        await message.answer(
            "Текущая стратегия сброса: {}\nВведите новую стратегию (daily/weekly/monthly/no_reset) или напишите «пропустить».".format(
                self._format_reset_strategy(current_strategy)
            )
        )

    async def _process_user_edit_reset_strategy(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        data = await state.get_data()
        context = data.get("edit_user")
        if not context:
            await self._cancel_operation(message, state, "users")
            return

        cleaned = text.strip().lower()
        strategy_map = {
            "daily": "daily",
            "ежедневно": "daily",
            "weekly": "weekly",
            "еженедельно": "weekly",
            "monthly": "monthly",
            "ежемесячно": "monthly",
            "no_reset": "no_reset",
            "без сброса": "no_reset",
            "skip": None,
            "пропустить": None,
            "": None,
        }

        strategy = strategy_map.get(cleaned)
        if strategy is None and cleaned not in {"", "skip", "пропустить"}:
            await message.answer("Укажите одну из стратегий: daily, weekly, monthly, no_reset или «пропустить».")
            return

        if strategy is not None:
            context.setdefault("changes", {})["data_limit_reset_strategy"] = strategy
        elif "data_limit_reset_strategy" not in context.get("changes", {}):
            context.setdefault("changes", {})["data_limit_reset_strategy"] = context.get("current", {}).get("data_limit_reset_strategy")

        await state.update_data(edit_user=context)
        await state.set_state(UserEditStates.waiting_for_expire)

        current_expire = context.get("current", {}).get("expire")
        await message.answer(
            "Текущая дата окончания: {}\nВведите новую дату (ДД.ММ.ГГГГ или с временем) или напишите «пропустить».".format(
                self._format_expire(current_expire)
            )
        )

    async def _process_user_edit_expire(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        data = await state.get_data()
        context = data.get("edit_user")
        if not context:
            await self._cancel_operation(message, state, "users")
            return

        cleaned = text.strip().lower()
        if cleaned in {"", "skip", "пропустить"}:
            expire_value = context.get("current", {}).get("expire")
        else:
            try:
                expire_value = self._parse_expire_input(text)
            except ValueError:
                await message.answer("Не удалось распознать дату. Попробуйте снова (формат ДД.ММ.ГГГГ ЧЧ:ММ).")
                return

        context.setdefault("changes", {})["expire"] = expire_value
        await state.update_data(edit_user=context)
        await state.set_state(UserEditStates.waiting_for_note)
        current_note = context.get("current", {}).get("note") or "—"
        await message.answer(
            "Текущее примечание: {}\nВведите новое примечание или напишите «пропустить».".format(current_note)
        )

    async def _process_user_edit_note(self, message: Message, state: FSMContext):
        text = message.text or ""
        if self._is_cancel_message(text):
            await self._cancel_operation(message, state, "users")
            return

        data = await state.get_data()
        context = data.get("edit_user")
        if not context:
            await self._cancel_operation(message, state, "users")
            return

        note = "" if text.strip().lower() in {"", "skip", "пропустить"} else text.strip()
        context.setdefault("changes", {})["note"] = note
        await state.update_data(edit_user=context)
        await self._apply_user_edit_changes(message, state)

    async def _apply_user_edit_changes(self, message: Message, state: FSMContext):
        data = await state.get_data()
        context = data.get("edit_user") or {}
        username = context.get("username")
        page = context.get("page", 0)
        changes = context.get("changes", {})

        if not username:
            await self._cancel_operation(message, state, "users")
            return

        payload: Dict[str, Optional[Any]] = {}

        if "status" in changes:
            payload["status"] = changes["status"]
        if "data_limit" in changes:
            payload["data_limit"] = changes["data_limit"]
        if "data_limit_reset_strategy" in changes:
            payload["data_limit_reset_strategy"] = changes["data_limit_reset_strategy"]
        if "expire" in changes:
            payload["expire"] = changes["expire"]
        if "note" in changes:
            payload["note"] = changes["note"]

        try:
            await self.marzban_client.modify_user(username, payload)
        except Exception as e:
            logger.error(f"Не удалось обновить пользователя {username}: {e}")
            await message.answer("❌ Не удалось сохранить изменения. Попробуйте позже.")
            await state.clear()
            return

        await state.clear()
        await message.answer("✅ Изменения сохранены.")
        await self._send_user_details_message(message, username, page)

    async def _confirm_user_deletion(self, callback: CallbackQuery, state: FSMContext, username: str, page: int):
        await state.update_data(pending_delete_user={"username": username, "page": page})
        await callback.message.edit_text(
            "⚠️ <b>Удаление пользователя</b> <code>{}</code>\n\n"
            "Это действие нельзя отменить. Подтвердите удаление.".format(html.escape(username)),
            parse_mode="HTML",
            reply_markup=get_confirmation_keyboard("delete_user", f"{username}:{page}")
        )
        await callback.answer()

    async def _delete_user(self, callback: CallbackQuery, state: FSMContext, username: str, page: int):
        try:
            await self.marzban_client.delete_user(username)
        except Exception as e:
            logger.error(f"Не удалось удалить пользователя {username}: {e}")
            await callback.answer("❌ Не удалось удалить пользователя", show_alert=True)
            return

        await state.clear()
        await callback.answer("✅ Пользователь удален")
        await self._show_users_list(callback, page)

    async def _cancel_delete_user(self, callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        context = data.get("pending_delete_user")
        await state.update_data(pending_delete_user=None)
        if context:
            username = context.get("username")
            page = context.get("page", 0)
            await self._show_user_details(callback, username, page)
        else:
            await self._show_users_menu(callback)
        await callback.answer("Отменено")

    async def _confirm_admin_deletion(self, callback: CallbackQuery, state: FSMContext, username: str, page: int):
        await state.update_data(pending_delete_admin={"username": username, "page": page})
        await callback.message.edit_text(
            "⚠️ <b>Удаление администратора</b> <code>{}</code>\n\n"
            "Подтвердите удаление.".format(html.escape(username)),
            parse_mode="HTML",
            reply_markup=get_confirmation_keyboard("delete_admin", username)
        )
        await callback.answer()

    async def _delete_admin(self, callback: CallbackQuery, state: FSMContext, username: str):
        data = await state.get_data()
        context = data.get("pending_delete_admin")
        page = context.get("page", 0) if context else 0
        try:
            await self.marzban_client.delete_admin(username)
        except Exception as e:
            logger.error(f"Не удалось удалить администратора {username}: {e}")
            await callback.answer("❌ Не удалось удалить администратора", show_alert=True)
            return

        await state.clear()
        await callback.answer("✅ Администратор удален")
        await self._show_admins_list(callback, page)

    async def _cancel_delete_admin(self, callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        context = data.get("pending_delete_admin")
        await state.update_data(pending_delete_admin=None)
        if context:
            username = context.get("username")
            page = context.get("page", 0)
            await self._show_admin_details(callback, username, page)
        else:
            await self._show_admins_menu(callback)
        await callback.answer("Отменено")


    def _format_ticket_details_for_admin(self, ticket) -> str:
        """Формирует текст с деталями тикета для администратора"""
        created = ticket.created_at.strftime('%d.%m.%Y %H:%M') if ticket.created_at else '—'
        updated = ticket.updated_at.strftime('%d.%m.%Y %H:%M') if ticket.updated_at else '—'
        status_icon = '🟢' if ticket.status == 'open' else '🔴'
        user_name = html.escape(ticket.user_name) if ticket.user_name else '—'
        message_text = html.escape(ticket.message or '—')
        response_text = html.escape(ticket.response or '—')

        details = [
            f"<b>Тикет #{ticket.id}</b>",
            f"{status_icon} Статус: <b>{ticket.status.upper()}</b>",
            f"👤 Telegram ID: <code>{ticket.user_id}</code>",
            f"👥 Пользователь: {user_name}",
            f"📅 Создан: {created}",
            f"🔄 Обновлен: {updated}",
            "",
            "💬 Сообщение:",
            message_text,
        ]

        if ticket.response:
            details.extend(["", "📣 Ответ поддержки:", response_text])

        return "\n".join(details)

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
            "👤 **Управление пользователями**\n\n"
            "Доступные действия:\n"
            "• Просмотр списка и деталей пользователя\n"
            "• Создание, редактирование и удаление\n"
            "• Массовые операции и рассылки",
            parse_mode="Markdown",
            reply_markup=get_admin_users_keyboard()
        )
        await callback.answer()

    async def _show_admins_menu(self, callback: CallbackQuery):
        """Меню управления администраторами"""
        await callback.message.edit_text(
            "👥 **Управление администраторами**\n\n"
            "Доступные действия:\n"
            "• Просмотр списка\n"
            "• Поиск по имени\n"
            "• Создание, редактирование и удаление",
            parse_mode="Markdown",
            reply_markup=get_admin_admins_keyboard()
        )
        await callback.answer()

    async def _show_users_list(self, callback: CallbackQuery, page: int):
        """Показ списка пользователей с пагинацией"""
        try:
            per_page = self.users_page_limit
            offset = page * per_page
            response = await self.marzban_client.get_users(offset=offset, limit=per_page + 1)
            users = response.get("users", [])

            if not users and page > 0:
                await self._show_users_list(callback, page - 1)
                return

            has_next = len(users) > per_page
            display_users = users[:per_page]

            if not display_users:
                await callback.message.edit_text(
                    "📭 Пользователи не найдены",
                    reply_markup=get_admin_users_keyboard()
                )
                await callback.answer()
                return

            total = response.get("total", offset + len(display_users) + (1 if has_next else 0))
            current_from = offset + 1
            current_to = offset + len(display_users)

            lines = ["<b>👤 Список пользователей</b>", ""]
            for user in display_users:
                username = html.escape(user.get("username", "N/A"))
                status = self._format_status(user.get("status"))
                expire_text = self._format_expire(user.get("expire"))
                lines.append(f"<b>{status}</b> — <code>{username}</code>")
                lines.append(f"⏳ {expire_text}")
                lines.append("")

            lines.append(
                f"Показаны {current_from}–{current_to} из {total}"
            )

            keyboard_rows: List[List[InlineKeyboardButton]] = []
            for user in display_users:
                username = user.get("username", "")
                keyboard_rows.append([
                    InlineKeyboardButton(
                        text=f"ℹ️ {username}",
                        callback_data=f"users_view:{username}:{page}"
                    )
                ])

            nav_buttons: List[InlineKeyboardButton] = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"users_list:{page - 1}")
                )
            if has_next:
                nav_buttons.append(
                    InlineKeyboardButton(text="Вперед ➡️", callback_data=f"users_list:{page + 1}")
                )
            if nav_buttons:
                keyboard_rows.append(nav_buttons)

            keyboard_rows.append([
                InlineKeyboardButton(text="🔙 Меню пользователей", callback_data="admin_users")
            ])

            await callback.message.edit_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            )
            await callback.answer()
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка получения пользователей: {str(e)}")

    async def _compose_user_details(self, username: str, page: int) -> Optional[tuple[str, InlineKeyboardMarkup]]:
        """Формирует текст и клавиатуру с информацией о пользователе"""
        user = await self.marzban_client.get_user(username)
        if not user:
            return None

        tg_user = await self.user_service.get_user_by_marzban_username(username)
        telegram_id = None
        if tg_user and tg_user.telegram_id:
            telegram_id = tg_user.telegram_id
        elif user.get("telegram_id"):
            telegram_id = user.get("telegram_id")

        data_limit = self._format_data_limit(user.get("data_limit"))
        reset_strategy = self._format_reset_strategy(user.get("data_limit_reset_strategy"))
        expire = self._format_expire(user.get("expire"))
        note = html.escape(user.get("note") or "—")
        status = self._format_status(user.get("status"))
        protocols = ", ".join(user.get("proxies", {}).keys()) or "—"

        lines = [
            "<b>Информация о пользователе</b>",
            "",
            f"👤 <code>{html.escape(username)}</code>",
            f"📌 Статус: <b>{status}</b>",
        ]

        if telegram_id:
            lines.append(f"🆔 Telegram ID: <code>{telegram_id}</code>")
        else:
            lines.append("🆔 Telegram ID: —")

        lines.extend([
            f"💾 Лимит трафика: {data_limit}",
            f"♻️ Сброс трафика: {reset_strategy}",
            f"⏳ Подписка до: {expire}",
            f"🛠 Протоколы: {protocols}",
            f"🗒 Примечание: {note}",
        ])

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать",
                        callback_data=f"users_edit:{username}:{page}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить",
                        callback_data=f"users_delete:{username}:{page}"
                    )
                ],
                [
                    InlineKeyboardButton(text="⬅️ К списку", callback_data=f"users_list:{page}"),
                    InlineKeyboardButton(text="🔙 Меню", callback_data="admin_users")
                ]
            ]
        )

        return "\n".join(lines), keyboard

    async def _show_user_details(self, callback: CallbackQuery, username: str, page: int):
        """Выводит детальную информацию о пользователе"""
        try:
            result = await self._compose_user_details(username, page)
            if not result:
                await callback.answer("Пользователь не найден", show_alert=True)
                await self._show_users_list(callback, max(page - 1, 0))
                return

            text, keyboard = result
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error showing user details: {e}")
            await callback.answer("❌ Не удалось получить данные пользователя", show_alert=True)

    async def _send_user_details_message(self, message: Message, username: str, page: int = 0):
        """Отправляет сообщение с деталями пользователя после FSM"""
        result = await self._compose_user_details(username, page)
        if not result:
            await message.answer(
                "⚠️ Не удалось получить обновленные данные пользователя.",
                reply_markup=get_admin_users_keyboard()
            )
            return

        text, keyboard = result
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    async def _start_user_creation(self, callback: CallbackQuery, state: FSMContext):
        """Инициирует процесс создания пользователя"""
        await state.set_state(UserCreationStates.waiting_for_username)
        await state.update_data(new_user={"page": 0})
        await callback.message.edit_text(
            "➕ <b>Создание нового пользователя</b>\n\n"
            "Введите имя пользователя (только латинские символы и цифры) или напишите «отмена».",
            parse_mode="HTML"
        )
        await callback.answer()

    async def _start_user_edit(self, callback: CallbackQuery, state: FSMContext, username: str, page: int):
        """Начинает процесс редактирования пользователя"""
        user = await self.marzban_client.get_user(username)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            await self._show_users_list(callback, max(page - 1, 0))
            return

        current_data = {
            "status": user.get("status"),
            "data_limit": user.get("data_limit"),
            "data_limit_reset_strategy": user.get("data_limit_reset_strategy"),
            "expire": user.get("expire"),
            "note": user.get("note"),
        }

        await state.update_data(
            edit_user={
                "username": username,
                "page": page,
                "current": current_data,
                "changes": {}
            }
        )
        await state.set_state(UserEditStates.waiting_for_status)
        await callback.message.edit_text(
            "✏️ <b>Редактирование пользователя</b> <code>{}</code>\n\n"
            "Текущий статус: {}\n"
            "Введите новый статус (active/on_hold/disabled) или напишите «пропустить».".format(
                html.escape(username),
                self._format_status(current_data.get("status"))
            ),
            parse_mode="HTML"
        )
        await callback.answer()

    async def _start_admin_creation(self, callback: CallbackQuery, state: FSMContext):
        """Инициирует процесс создания администратора"""
        await state.set_state(AdminCreationStates.waiting_for_username)
        await state.update_data(new_admin={})
        await callback.message.edit_text(
            "➕ <b>Создание администратора</b>\n\n"
            "Введите имя администратора или напишите «отмена».",
            parse_mode="HTML"
        )
        await callback.answer()

    async def _start_admin_edit(self, callback: CallbackQuery, state: FSMContext, username: str, page: int):
        admin = await self.marzban_client.get_admin(username)
        if not admin:
            await callback.answer("Администратор не найден", show_alert=True)
            await self._show_admins_list(callback, max(page - 1, 0))
            return

        current = {
            "is_sudo": admin.get("is_sudo", False),
            "telegram_id": admin.get("telegram_id"),
        }

        await state.update_data(
            edit_admin={
                "username": username,
                "page": page,
                "current": current,
                "changes": {}
            }
        )
        await state.set_state(AdminEditStates.waiting_for_password)
        await callback.message.edit_text(
            "✏️ <b>Редактирование администратора</b> <code>{}</code>\n\n"
            "Введите новый пароль или напишите «пропустить».".format(html.escape(username)),
            parse_mode="HTML"
        )
        await callback.answer()

    async def _show_admins_list(self, callback: CallbackQuery, page: int):
        """Показ списка администраторов"""
        try:
            per_page = self.admins_page_limit
            offset = page * per_page
            admins = await self.marzban_client.get_admins(offset=offset, limit=per_page + 1)

            if not admins and page > 0:
                await self._show_admins_list(callback, page - 1)
                return

            has_next = len(admins) > per_page
            display_admins = admins[:per_page]

            if not display_admins:
                await callback.message.edit_text(
                    "📭 Администраторы не найдены",
                    reply_markup=get_admin_admins_keyboard()
                )
                await callback.answer()
                return

            current_from = offset + 1
            current_to = offset + len(display_admins)
            total = offset + len(display_admins) + (1 if has_next else 0)

            lines = ["<b>👥 Список администраторов</b>", ""]
            for admin in display_admins:
                username = html.escape(admin.get("username", "N/A"))
                role = "🔧 Супер-админ" if admin.get("is_sudo") else "👤 Админ"
                lines.append(f"{role}: <code>{username}</code>")
                telegram_id = admin.get("telegram_id")
                if telegram_id:
                    lines.append(f"🆔 Telegram ID: <code>{telegram_id}</code>")
                lines.append("")

            lines.append(f"Показаны {current_from}–{current_to} из {total}")

            keyboard_rows: List[List[InlineKeyboardButton]] = []
            for admin in display_admins:
                username = admin.get("username", "")
                keyboard_rows.append([
                    InlineKeyboardButton(
                        text=f"ℹ️ {username}",
                        callback_data=f"admin_manage:{username}:{page}"
                    )
                ])

            nav_buttons: List[InlineKeyboardButton] = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admins_list:{page - 1}")
                )
            if has_next:
                nav_buttons.append(
                    InlineKeyboardButton(text="Вперед ➡️", callback_data=f"admins_list:{page + 1}")
                )
            if nav_buttons:
                keyboard_rows.append(nav_buttons)

            keyboard_rows.append([
                InlineKeyboardButton(text="🔙 Меню администраторов", callback_data="admin_admins")
            ])

            await callback.message.edit_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            )
            await callback.answer()
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

    async def _compose_admin_details(self, username: str, page: int) -> Optional[tuple[str, InlineKeyboardMarkup]]:
        admin = await self.marzban_client.get_admin(username)
        if not admin:
            return None

        role_text = "Супер-админ" if admin.get("is_sudo") else "Администратор"
        telegram_id = admin.get("telegram_id")
        users_usage = admin.get("users_usage")

        lines = [
            "<b>Информация об администраторе</b>",
            "",
            f"👤 <code>{html.escape(username)}</code>",
            f"🔧 Роль: <b>{role_text}</b>",
        ]

        if telegram_id:
            lines.append(f"🆔 Telegram ID: <code>{telegram_id}</code>")
        else:
            lines.append("🆔 Telegram ID: —")

        if users_usage is not None:
            lines.append(f"📊 Использование: {users_usage}")

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Редактировать",
                        callback_data=f"admins_edit:{username}:{page}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Удалить",
                        callback_data=f"admins_delete:{username}:{page}"
                    )
                ],
                [
                    InlineKeyboardButton(text="⬅️ К списку", callback_data=f"admins_list:{page}"),
                    InlineKeyboardButton(text="🔙 Меню", callback_data="admin_admins")
                ]
            ]
        )

        return "\n".join(lines), keyboard

    async def _show_admin_details(self, callback: CallbackQuery, username: str, page: int):
        try:
            result = await self._compose_admin_details(username, page)
            if not result:
                await callback.answer("Администратор не найден", show_alert=True)
                await self._show_admins_list(callback, max(page - 1, 0))
                return

            text, keyboard = result
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка отображения администратора {username}: {e}")
            await callback.answer("❌ Не удалось получить данные администратора", show_alert=True)

    async def _send_admin_details_message(self, message: Message, username: str, page: int = 0):
        result = await self._compose_admin_details(username, page)
        if not result:
            await message.answer(
                "⚠️ Не удалось получить данные администратора.",
                reply_markup=get_admin_admins_keyboard()
            )
            return

        text, keyboard = result
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
