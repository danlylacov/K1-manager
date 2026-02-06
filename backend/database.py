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
        
        # Создаем таблицу admin_users если её нет
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='admin_users'
        """))
        if result.fetchone() is None:
            conn.execute(text("""
                CREATE TABLE admin_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR UNIQUE NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    role VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_admin_users_username ON admin_users(username)"))
            conn.commit()
            print("Миграция: создана таблица admin_users")


def create_dev_user():
    """Создание dev пользователя из переменных окружения"""
    from backend.models import AdminUser
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    dev_username = os.getenv("ADMIN_DEV_USERNAME")
    dev_password = os.getenv("ADMIN_DEV_PASSWORD")
    
    if not dev_username or not dev_password:
        print("ADMIN_DEV_USERNAME и ADMIN_DEV_PASSWORD не установлены, dev пользователь не создан")
        return
    
    db = SessionLocal()
    try:
        # Проверяем, существует ли уже dev пользователь
        existing_user = db.query(AdminUser).filter(AdminUser.username == dev_username).first()
        if existing_user:
            print(f"Dev пользователь {dev_username} уже существует")
            return
        
        # Создаем нового dev пользователя
        # Bcrypt ограничивает пароль 72 байтами, обрезаем заранее
        password_bytes = dev_password.encode('utf-8')
        if len(password_bytes) > 72:
            # Обрезаем до 72 байт и декодируем обратно
            password_to_hash = password_bytes[:72].decode('utf-8', errors='ignore')
        else:
            password_to_hash = dev_password
        
        password_hash = pwd_context.hash(password_to_hash)
        dev_user = AdminUser(
            username=dev_username,
            password_hash=password_hash,
            role="dev"
        )
        db.add(dev_user)
        db.commit()
        print(f"Dev пользователь {dev_username} создан успешно")
    except Exception as e:
        print(f"Ошибка при создании dev пользователя: {e}")
        db.rollback()
    finally:
        db.close()


def init_db():
    from backend.models import Base
    Base.metadata.create_all(bind=engine)
    migrate_db()
    create_dev_user()

