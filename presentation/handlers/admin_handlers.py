# presentation/handlers/admin_handlers.py
from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from presentation.handlers.base import BaseHandler
from presentation.keyboards import (
    get_admin_main_keyboard,
    get_admin_users_keyboard,
    get_pagination_keyboard,
    get_support_tickets_keyboard,
    get_support_tickets_pagination_keyboard,
    get_support_ticket_search_keyboard,
    get_admin_ticket_actions_keyboard,
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
import html

logger = logging.getLogger(__name__)


class SupportTicketStates(StatesGroup):
    waiting_for_ticket_id = State()
    waiting_for_reply_message = State()


class AdminHandlers(BaseHandler):
    def __init__(self, marzban_client: MarzbanAPIClient, support_service: SupportService):
        self.marzban_client = marzban_client
        self.support_service = support_service
        super().__init__()

    def _register_handlers(self):
        """Регистрация обработчиков администратора"""
        self.router.message.register(self.admin_panel, Command("admin"))
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
                await state.clear()
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