# Marzban Telegram Bot - Refactored Version

## Project Structure


## marz_tg_bot/
## ├── core/                    # Ядро приложения
## │   ├── __init__.py
## │   ├── config.py           # Конфигурация
## │   └── exceptions.py       # Кастомные исключения
## ├── domain/                  # Бизнес-логика и модели
## │   ├── __init__.py
## │   ├── models/             # Модели данных
## │   │   ├── __init__.py
## │   │   ├── user.py
## │   │   └── subscription.py
## │   └── services/           # Бизнес-сервисы
## │       ├── __init__.py
## │       ├── subscription_service.py
## │       └── user_service.py
## ├── infrastructure/          # Внешние зависимости и инфраструктура
## │   ├── __init__.py
## │   ├── database/
## │   │   ├── __init__.py
## │   │   └── repositories.py
## │   └── marzban/
## │       ├── __init__.py
## │       └── api_client.py
## ├── presentation/            # Презентационный слой
## │   ├── __init__.py
## │   ├── handlers/
## │   │   ├── __init__.py
## │   │   ├── base.py
## │   │   ├── user_handlers.py
## │   │   └── admin_handlers.py
## │   └── keyboards/
## │       ├── __init__.py
## │       └── inline.py
## └── main.py                 # Точка входа


## Key Changes from Original:
- Clean Architecture implementation
- Separated business logic from presentation
- Added DTO objects for data transfer
- Improved error handling

## Recent Modifications:
- Date: 2024-01-15
- Refactored user_handlers.py to use service layer
- Fixed data_limit None handling
- Removed MarkdownV2 to avoid parsing issues