# core/config.py
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    STAR_PRICE_PER_MONTH = int(os.getenv("STAR_PRICE_PER_MONTH", 1))
    STAR_PRICE_PER_GB = int(os.getenv("STAR_PRICE_PER_GB", 1))
    MARZBAN_API_URL = os.getenv("MARZBAN_API_URL")
    MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
    MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
    ADMIN_TG_IDS = [int(x.strip()) for x in os.getenv("ADMIN_TG_IDS", "").split(",") if x.strip()]
    SUPPORT_TG_IDS = [int(x.strip()) for x in os.getenv("SUPPORT_TG_IDS", "").split(",") if x.strip()]
    DB_PATH = os.getenv("DB_PATH", "vpn_bot.db")
    MARZBAN_API_PREFIX = os.getenv("MARZBAN_API_PREFIX", "")
    VERIFY_SSL = os.getenv("VERIFY_SSL", "False").lower() == "true"
    USERS_PER_PAGE = int(os.getenv("USERS_PER_PAGE", "20"))
    ADMINS_PER_PAGE = int(os.getenv("ADMINS_PER_PAGE", "50"))

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        return user_id in cls.ADMIN_TG_IDS

    @classmethod
    def is_support(cls, user_id: int) -> bool:
        return user_id in cls.SUPPORT_TG_IDS and user_id not in cls.ADMIN_TG_IDS

    @classmethod
    def has_support_access(cls, user_id: int) -> bool:
        return user_id in cls.SUPPORT_TG_IDS or user_id in cls.ADMIN_TG_IDS

config = Config()
