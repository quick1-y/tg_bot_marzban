#domain/services/support_service.py
import logging
from typing import Optional, List
from datetime import datetime
from domain.models.support import SupportTicket
from infrastructure.database.repositories import SupportRepository
from core.config import config

logger = logging.getLogger(__name__)


class SupportService:
    MAX_OPEN_TICKETS = 3  # Максимум открытых тикетов на одного пользователя

    def __init__(self, support_repository: SupportRepository):
        self.support_repository = support_repository

    # === Создание тикета ===
    async def create_support_ticket(self, user_id: int, user_name: str, message: str) -> Optional[SupportTicket]:
        """Создает новый тикет поддержки, если не превышен лимит открытых тикетов"""
        tickets = await self.support_repository.get_tickets_by_user(user_id)
        open_tickets = [t for t in tickets if t.status == "open"]

        if len(open_tickets) >= 3:
            logger.warning(f"❗ Пользователь {user_name} ({user_id}) пытается создать слишком много тикетов.")
            return None  # сигнализируем, что тикет не создан

        ticket = SupportTicket(
            user_id=user_id,
            user_name=user_name,
            message=message,
            created_at=datetime.now()
        )

        saved_ticket = await self.support_repository.save_ticket(ticket)
        logger.info(f"Создан тикет #{saved_ticket.id} для пользователя {user_name}")
        return saved_ticket


    # === Получение тикетов пользователя ===
    async def get_user_tickets(self, user_id: int) -> List[SupportTicket]:
        """Возвращает все тикеты пользователя"""
        return await self.support_repository.get_tickets_by_user(user_id)

    # === Получение одного тикета ===
    async def get_ticket_details(self, ticket_id: int, user_id: int) -> Optional[SupportTicket]:
        """Возвращает конкретный тикет, если он принадлежит пользователю"""
        tickets = await self.support_repository.get_tickets_by_user(user_id)
        for t in tickets:
            if t.id == ticket_id:
                return t
        return None

    # === Форматирование списка тикетов ===
    async def format_ticket_list_for_user(self, tickets: List[SupportTicket]) -> str:
        """Формирует сообщение со списком тикетов пользователя"""
        if not tickets:
            return "📭 У вас пока нет обращений в поддержку."

        msg_lines = ["📬 Ваши обращения:\n"]
        for t in tickets[:10]:
            status_emoji = "🟢" if t.status == "open" else "🔴"
            created_str = t.created_at.strftime("%d.%m %H:%M") if t.created_at else "?"
            msg_lines.append(f"{status_emoji} #{t.id} — {t.message[:35]}... ({created_str})")
        msg_lines.append("\n🕹 Нажмите на номер обращения, чтобы открыть его.")
        return "\n".join(msg_lines)

    # === Форматирование деталей тикета ===
    async def format_ticket_details(self, ticket: SupportTicket) -> str:
        """Формирует детальное сообщение о тикете"""
        status_emoji = "🟢" if ticket.status == "open" else "🔴"
        created = ticket.created_at.strftime("%d.%m.%Y %H:%M") if ticket.created_at else "?"
        updated = ticket.updated_at.strftime("%d.%m.%Y %H:%M") if ticket.updated_at else "?"

        msg = (
            f"📨 Обращение #{ticket.id}\n\n"
            f"👤 Пользователь: {ticket.user_name}\n"
            f"📅 Создано: {created}\n"
            f"🔄 Обновлено: {updated}\n"
            f"Статус: {status_emoji} {ticket.status.upper()}\n\n"
            f"💬 Сообщение:\n{ticket.message}\n\n"
        )

        if ticket.status == "open":
            msg += "⌛ Поддержка пока не ответила.\n"
        else:
            msg += "✅ Тикет закрыт. Спасибо за обращение!\n"

        return msg

    # === Форматирование для админа ===
    async def format_support_message_for_admin(self, user_id: int, user_name: str, message: str) -> str:
        """Форматирует сообщение для отправки администратору"""
        return (
            "🆘 Новое обращение в поддержку\n\n"
            f"👤 Пользователь: @{user_name}\n"
            f"🆔 ID: {user_id}\n"
            f"💬 Сообщение:\n{message}\n\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    def get_support_contact_info(self) -> str:
        """Возвращает информацию о контакте поддержки"""
        support_id = config.SUPPORT_TG_IDS
        if support_id:
            return f"📞 Техническая поддержка: @{support_id}"
        return "📞 Для связи с техподдержкой используйте кнопку ниже"

    # === Закрытие тикета ===
    async def close_ticket(self, ticket_id: int) -> bool:
        """Закрывает тикет"""
        return await self.support_repository.update_ticket_status(ticket_id, "closed")

