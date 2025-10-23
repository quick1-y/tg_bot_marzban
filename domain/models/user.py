from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TelegramUser:
    telegram_id: int
    marzban_username: str
    subscription_type: Optional[str] = None
    created_at: Optional[datetime] = None