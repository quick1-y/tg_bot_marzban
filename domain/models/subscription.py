from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class SubscriptionInfo:
    username: str
    subscription_type: str
    status: str
    expire_date: Optional[datetime]
    used_traffic_gb: float
    data_limit_gb: Optional[float]
    subscription_url: Optional[str]
    is_active: bool
    configs: Optional[List[str]] = None
    months_count: Optional[int] = None

    @classmethod
    def from_marzban_data(cls, user_data: Dict[str, Any], subscription_url: Optional[str] = None) -> 'SubscriptionInfo':
        """Создает объект информации о подписке из данных Marzban API"""
        data_limit = user_data.get('data_limit')
        expire_timestamp = user_data.get('expire')
        expire_date = None

        if expire_timestamp:
            try:
                expire_date = datetime.fromtimestamp(expire_timestamp)
            except Exception:
                expire_date = None

        # Определяем тип подписки
        if not data_limit or data_limit == 0:
            subscription_type = "Ежемесячная подписка"
        else:
            subscription_type = "Тариф по трафику"

        # Статус
        status = "active" if user_data.get('status') == 'active' else "inactive"

        # Использованный трафик
        used_traffic = user_data.get('used_traffic', 0)
        used_traffic_gb = round(used_traffic / (1024 ** 3), 2) if used_traffic else 0.0

        # Лимит трафика
        data_limit_gb = None
        if data_limit and data_limit > 0:
            data_limit_gb = round(data_limit / (1024 ** 3), 2)

        # Конфиги (если есть)
        configs = []
        proxies = user_data.get('proxies', {}) or {}
        if isinstance(proxies, dict):
            for proto, cfg in proxies.items():
                if isinstance(cfg, dict):
                    conf_str = cfg.get('server') or cfg.get('address') or ''
                    if conf_str:
                        configs.append(f"{proto}: {conf_str}")

        # Количество месяцев (для monthly)
        months_count = None
        if expire_date:
            delta_days = (expire_date - datetime.utcnow()).days
            if delta_days > 0:
                months_count = max(1, round(delta_days / 30))

        return cls(
            username=user_data.get('username', ''),
            subscription_type=subscription_type,
            status=status,
            expire_date=expire_date,
            used_traffic_gb=used_traffic_gb,
            data_limit_gb=data_limit_gb,
            subscription_url=subscription_url,
            is_active=status == 'active',
            configs=configs,
            months_count=months_count,
        )


@dataclass
class SubscriptionResult:
    success: bool
    subscription_info: Optional[SubscriptionInfo] = None
    error_message: Optional[str] = None
    context: str = "view"
    attempted_plan: Optional[str] = None
