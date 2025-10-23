import sqlite3

DB_PATH = "vpn_bot.db"  # Укажи путь к твоей базе, если отличается

def ensure_support_table_fields():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1️⃣ — Узнаем, какие поля есть сейчас
    cursor.execute("PRAGMA table_info(support_tickets);")
    existing_columns = [col[1] for col in cursor.fetchall()]

    print(f"Существующие колонки: {existing_columns}")

    # 2️⃣ — Определяем, какие поля обязательны
    required_columns = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "user_id": "INTEGER",
        "user_name": "TEXT",
        "message": "TEXT",
        "response": "TEXT DEFAULT ''",  # <--- добавлено новое поле
        "status": "TEXT DEFAULT 'open'",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }

    # 3️⃣ — Добавляем недостающие колонки
    for col_name, col_type in required_columns.items():
        if col_name not in existing_columns:
            print(f"Добавляю колонку: {col_name}")
            cursor.execute(f"ALTER TABLE support_tickets ADD COLUMN {col_name} {col_type};")

    conn.commit()
    conn.close()
    print("✅ Проверка и обновление таблицы support_tickets завершено.")

if __name__ == "__main__":
    ensure_support_table_fields()
