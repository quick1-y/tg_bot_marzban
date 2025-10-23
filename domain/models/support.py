from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SupportTicket:
    id: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    message: Optional[str] = None
    response: Optional[str] = None  #
    status: str = "open"  # open, in_progress, closed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SupportMessage:
    user_id: int
    user_name: str
    message: str
    timestamp: datetime