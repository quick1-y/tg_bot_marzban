# presentation/handlers/support_handlers.py
from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from presentation.handlers.base import BaseHandler
from presentation.keyboards import (
    get_support_keyboard,
    get_support_confirmation_keyboard,
    get_user_main_keyboard
)
from domain.services.support_service import SupportService
from core.security import can_access_support_tickets
from core.config import config
import logging

logger = logging.getLogger(__name__)


class SupportStates(StatesGroup):
    waiting_for_support_message = State()
    confirming_support_message = State()


class SupportHandlers(BaseHandler):
    def __init__(self, support_service: SupportService):
        self.support_service = support_service
        super().__init__()

    def _register_handlers(self):
        self.router.callback_query.register(self.support_menu_handler, F.data == "support")
        self.router.callback_query.register(self.write_to_support_handler, F.data == "write_to_support")
        self.router.message.register(self.support_message_handler, SupportStates.waiting_for_support_message)
        self.router.callback_query.register(self.support_confirmation_handler, SupportStates.confirming_support_message)

    async def support_menu_handler(self, callback: CallbackQuery):
        """Меню поддержки"""
        await callback.message.edit_text(
            "🆘 Техническая поддержка\n\n"
            "Здесь вы можете получить помощь по вопросам о подписке, настройках и т.п.",
            reply_markup=get_support_keyboard()
        )

    async def write_to_support_handler(self, callback: CallbackQuery, state: FSMContext):
        """Начало написания сообщения"""
        await callback.message.edit_text(
            "✍️ Напишите ваше сообщение в техническую поддержку\n\n"
            "Опишите проблему максимально подробно:"
        )
        await state.set_state(SupportStates.waiting_for_support_message)

    async def support_message_handler(self, message: Message, state: FSMContext):
        """Пользователь пишет сообщение"""
        user_message = message.text
        user = message.from_user

        if not user_message or len(user_message.strip()) < 5:
            await message.answer("❌ Сообщение слишком короткое. Опишите проблему подробнее.")
            return

        await state.update_data(
            support_message=user_message,
            user_name=user.full_name,
            user_id=user.id
        )

        await message.answer(
            f"📝 Ваше сообщение:\n\n{user_message}\n\nОтправить?",
            reply_markup=get_support_confirmation_keyboard()
        )
        await state.set_state(SupportStates.confirming_support_message)

    async def support_confirmation_handler(self, callback: CallbackQuery, state: FSMContext):
        """Подтверждение отправки"""
        data = callback.data
        state_data = await state.get_data()

        if not state_data:
            await callback.answer("❌ Нет данных, начните заново.", show_alert=True)
            await state.clear()
            return

        if data == "confirm_support":
            user_id = state_data['user_id']
            user_name = state_data['user_name']
            message_text = state_data['support_message']

            try:
                ticket = await self.support_service.create_support_ticket(user_id, user_name, message_text)
                admin_message = await self.support_service.format_support_message_for_admin(user_id, user_name, message_text)

                recipients = set(config.ADMIN_TG_IDS + config.SUPPORT_TG_IDS)
                for recipient in recipients:
                    try:
                        await callback.bot.send_message(chat_id=recipient, text=admin_message)
                    except Exception as e:
                        logger.error(f"Не удалось отправить сообщение саппорту {recipient}: {e}")

                await callback.message.edit_text(
                    f"✅ Ваше сообщение отправлено. Номер обращения: #{ticket.id}",
                    reply_markup=get_user_main_keyboard(user_id)
                )
            except Exception as e:
                logger.error(f"Ошибка при создании тикета: {e}")
                await callback.message.edit_text(
                    "❌ Ошибка при отправке. Попробуйте позже.",
                    reply_markup=get_user_main_keyboard(callback.from_user.id)
                )

        elif data == "edit_support":
            await callback.message.edit_text("✍️ Напишите сообщение заново:")
            await state.set_state(SupportStates.waiting_for_support_message)

        elif data == "cancel_support":
            await callback.message.edit_text(
                "❌ Отправка отменена.",
                reply_markup=get_user_main_keyboard(callback.from_user.id)
            )

        await state.clear()

    async def show_all_support_tickets(self, callback: CallbackQuery):
        """Меню тикетов поддержки (для саппортов и админов)"""
        user_id = callback.from_user.id

        if not can_access_support_tickets(user_id):
            await callback.answer("🚫 У вас нет доступа к тикетам поддержки", show_alert=True)
            return

        try:
            tickets = await self.support_service.get_all_tickets()
            if not tickets:
                await callback.message.edit_text("📭 Нет активных тикетов поддержки.")
                return

            message = "📋 **Все тикеты поддержки:**\n\n"
            for ticket in tickets[:10]:
                status_icon = "🟢" if ticket.status == "open" else "🔴"
                user_display = ticket.user_name or f"User {ticket.user_id}"
                message += (
                    f"{status_icon} **#{ticket.id}** — {user_display}\n"
                    f"📝 {ticket.message[:60]}...\n\n"
                )

            if len(tickets) > 10:
                message += f"ℹ️ Показано 10 из {len(tickets)} тикетов\n"

            await callback.message.edit_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_user_main_keyboard(user_id)
            )

        except Exception as e:
            logger.error(f"Error showing all support tickets: {e}")
            await callback.message.edit_text(
                f"❌ Ошибка загрузки тикетов: {str(e)}",
                reply_markup=get_user_main_keyboard(user_id)
            )
