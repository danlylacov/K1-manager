from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/k1db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_db():
    """Миграция базы данных - добавляет недостающие колонки"""
    with engine.connect() as conn:
        # Проверяем наличие колонки is_bot
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='messages' AND column_name='is_bot'
        """))
        if result.fetchone() is None:
            # Добавляем колонку is_bot
            conn.execute(text("ALTER TABLE messages ADD COLUMN is_bot INTEGER DEFAULT 0"))
            conn.commit()
            print("Миграция: добавлена колонка is_bot в таблицу messages")
        
        # Проверяем, что relevance может быть NULL
        result = conn.execute(text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name='messages' AND column_name='relevance'
        """))
        row = result.fetchone()
        if row and row[0] == 'NO':
            # Изменяем колонку relevance чтобы она могла быть NULL
            conn.execute(text("ALTER TABLE messages ALTER COLUMN relevance DROP NOT NULL"))
            conn.commit()
            print("Миграция: колонка relevance теперь может быть NULL")
        
        # Миграция для onboarding полей в users
        onboarding_fields = [
            ("mouse_keyboard_skill", "VARCHAR"),
            ("programming_experience", "VARCHAR"),
            ("child_age", "INTEGER"),
            ("child_name", "VARCHAR"),
            ("onboarding_completed", "INTEGER DEFAULT 0"),
            ("onboarding_data", "TEXT")
        ]
        
        for field_name, field_type in onboarding_fields:
            result = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='{field_name}'
            """))
            if result.fetchone() is None:
                if "DEFAULT" in field_type:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"))
                else:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}"))
                conn.commit()
                print(f"Миграция: добавлена колонка {field_name} в таблицу users")
        
        # Создаем таблицу scheduled_broadcasts если её нет
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='scheduled_broadcasts'
        """))
        if result.fetchone() is None:
            conn.execute(text("""
                CREATE TABLE scheduled_broadcasts (
                    id SERIAL PRIMARY KEY,
                    telegram_ids TEXT NOT NULL,
                    text TEXT NOT NULL,
                    scheduled_at TIMESTAMP NOT NULL,
                    file_name VARCHAR,
                    file_content TEXT,
                    sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_scheduled_broadcasts_scheduled_at ON scheduled_broadcasts(scheduled_at)"))
            conn.execute(text("CREATE INDEX idx_scheduled_broadcasts_sent ON scheduled_broadcasts(sent)"))
            conn.commit()
            print("Миграция: создана таблица scheduled_broadcasts")


def init_db():
    from backend.models import Base
    Base.metadata.create_all(bind=engine)
    migrate_db()

