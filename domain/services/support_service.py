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
        open_tickets_count = await self.support_repository.get_open_ticket_count(user_id)

        if open_tickets_count >= self.MAX_OPEN_TICKETS:
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
        return await self.support_repository.get_ticket_by_id(ticket_id, user_id)

    async def get_ticket_for_admin(self, ticket_id: int) -> Optional[SupportTicket]:
        """Возвращает тикет по ID для администратора/саппорта"""
        return await self.support_repository.get_ticket_by_id_admin(ticket_id)

    async def get_all_tickets(self, limit: Optional[int] = None) -> List[SupportTicket]:
        """Возвращает список всех тикетов для административного просмотра"""
        return await self.support_repository.get_all_tickets(limit=limit)

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
            if len(support_id) == 1:
                return f"📞 Техническая поддержка: tg://user?id={support_id[0]}"
            lines = ["📞 Техническая поддержка:"]
            for index, contact_id in enumerate(support_id, start=1):
                lines.append(f"• Контакт {index}: tg://user?id={contact_id}")
            return "\n".join(lines)
        return "📞 Для связи с техподдержкой используйте кнопку ниже"

    # === Закрытие тикета ===
    async def close_ticket(self, ticket_id: int) -> bool:
        """Закрывает тикет"""
        return await self.support_repository.update_ticket_status(ticket_id, "closed")

    async def reopen_ticket(self, ticket_id: int) -> bool:
        """Переоткрывает тикет"""
        return await self.support_repository.update_ticket_status(ticket_id, "open")

    async def update_ticket_status(self, ticket_id: int, status: str) -> bool:
        """Обновляет статус тикета произвольно"""
        return await self.support_repository.update_ticket_status(ticket_id, status)

    async def add_ticket_response(self, ticket_id: int, response: str) -> bool:
        """Сохраняет ответ поддержки"""
        return await self.support_repository.update_ticket_response(ticket_id, response)

