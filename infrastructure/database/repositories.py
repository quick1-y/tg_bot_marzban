#infrastructure/database/repositories.py
import sqlite3
from datetime import datetime
from typing import Optional, List
from domain.models.user import TelegramUser
from domain.models.support import SupportTicket


class UserRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Инициализация таблиц базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_users(
                    telegram_id INTEGER PRIMARY KEY,
                    marzban_username TEXT UNIQUE,
                    subscription_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[TelegramUser]:
        """Получает пользователя по Telegram ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT telegram_id, marzban_username, subscription_type, created_at FROM bot_users WHERE telegram_id = ?',
                (telegram_id,)
            )
            result = cursor.fetchone()

            if result:
                return TelegramUser(
                    telegram_id=result[0],
                    marzban_username=result[1],
                    subscription_type=result[2],
                    created_at=datetime.fromisoformat(result[3]) if result[3] else None
                )
            return None

    async def save(self, user: TelegramUser):
        """Сохраняет пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bot_users (telegram_id, marzban_username, subscription_type)
                VALUES (?, ?, ?)
            ''', (user.telegram_id, user.marzban_username, user.subscription_type))
            conn.commit()

    async def get_all(self) -> List[TelegramUser]:
        """Получает всех пользователей"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id, marzban_username, subscription_type, created_at FROM bot_users')
            results = cursor.fetchall()

            users = []
            for result in results:
                users.append(TelegramUser(
                    telegram_id=result[0],
                    marzban_username=result[1],
                    subscription_type=result[2],
                    created_at=datetime.fromisoformat(result[3]) if result[3] else None
                ))
            return users


class SupportRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_support_db()

    def _init_support_db(self):
        """Инициализация таблиц для поддержки"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_name TEXT,
                    message TEXT,
                    response TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES bot_users (telegram_id)
                )
            ''')
            conn.commit()

    async def save_ticket(self, ticket: SupportTicket) -> SupportTicket:
        """Сохраняет тикет поддержки"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO support_tickets (user_id, user_name, message, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket.user_id, ticket.user_name, ticket.message, ticket.status, ticket.created_at))

            ticket_id = cursor.lastrowid
            conn.commit()

            return SupportTicket(
                id=ticket_id,
                user_id=ticket.user_id,
                user_name=ticket.user_name,
                message=ticket.message,
                status=ticket.status,
                created_at=ticket.created_at
            )

    async def get_tickets_by_user(self, user_id: int, limit: int = 5) -> List[SupportTicket]:
        """Получает последние тикеты пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, user_id, user_name, message, response, status, created_at, updated_at
                   FROM support_tickets
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?''',
                (user_id, limit)
            )
            results = cursor.fetchall()

            tickets = []
            for result in results:
                tickets.append(SupportTicket(
                    id=result[0],
                    user_id=result[1],
                    user_name=result[2],
                    message=result[3],
                    response=result[4],
                    status=result[5],
                    created_at=datetime.fromisoformat(result[6]) if result[6] else None,
                    updated_at=datetime.fromisoformat(result[7]) if result[7] else None
                ))
            return tickets

    async def get_ticket_by_id(self, ticket_id: int, user_id: int) -> Optional[SupportTicket]:
        """Получает один тикет"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, user_id, user_name, message, response, status, created_at, updated_at
                   FROM support_tickets
                   WHERE id = ? AND user_id = ?''',
                (ticket_id, user_id)
            )
            result = cursor.fetchone()
            if not result:
                return None
            return SupportTicket(
                id=result[0],
                user_id=result[1],
                user_name=result[2],
                message=result[3],
                response=result[4],
                status=result[5],
                created_at=datetime.fromisoformat(result[6]) if result[6] else None,
                updated_at=datetime.fromisoformat(result[7]) if result[7] else None
            )

    async def get_open_ticket_count(self, user_id: int) -> int:
        """Считает количество открытых тикетов пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM support_tickets WHERE user_id = ? AND status = 'open'",
                (user_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0

    async def update_ticket_status(self, ticket_id: int, status: str) -> bool:
        """Обновляет статус тикета"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE support_tickets SET status = ?, updated_at = ? WHERE id = ?',
                (status, datetime.now(), ticket_id)
            )
            conn.commit()
            return cursor.rowcount > 0
