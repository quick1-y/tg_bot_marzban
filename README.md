# Marzban Telegram Bot

Этот проект представляет собой Telegram-бота для управления доступом к VPN через панель Marzban. Репозиторий содержит исходный код, инфраструктурные компоненты и инструменты для локального развертывания.

## Возможности

- Управление пользователями VPN через API Marzban.
- Управление подписками и объёмом трафика.
- Отдельные панели для администраторов и службы поддержки.

## Требования

- Python 3.11+
- Доступ к рабочему экземпляру Marzban
- Токен Telegram-бота и (опционально) токен Telegram Stars

## Установка

1. Склонируйте репозиторий и перейдите в директорию проекта:
   ```bash
   git clone <your-repo-url>
   cd tg_bot_marzban
   ```
2. Создайте и активируйте виртуальное окружение (рекомендуется):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Скопируйте файл `.env` и заполните его значениями вашей среды.

## Конфигурация

Файл `.env` содержит настройки проекта. Ниже приведены доступные переменные окружения:

```env
BOT_TOKEN=your-telegram-bot-token
TG_STAR_PROVIDER_TOKEN=your-telegram-stars-token
STAR_PRICE_PER_MONTH=1
STAR_PRICE_PER_GB=1
MARZBAN_API_URL=https://your-marzban-host
MARZBAN_USERNAME=your-marzban-username
MARZBAN_PASSWORD=your-marzban-password
ADMIN_TG_IDS=comma-separated-admin-ids
SUPPORT_TG_IDS=comma-separated-support-ids
DB_PATH=vpn_bot.db
MARZBAN_API_PREFIX=/your-api-prefix
VERIFY_SSL=True
USERS_PER_PAGE=10
ADMINS_PER_PAGE=10
```

> **Примечание:** Убедитесь, что в файле `.env` не остаётся чувствительных данных перед публикацией. Для локальной разработки можно хранить файл вне системы контроля версий.

## Работа с базой данных

При первом запуске бот автоматически создаёт файл базы данных SQLite. В репозиторий база данных не попадает и должна генерироваться заново в каждой среде.

## Запуск

После настройки окружения выполните:

```bash
python main.py
```
