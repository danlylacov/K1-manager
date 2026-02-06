from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Onboarding поля
    mouse_keyboard_skill = Column(String, nullable=True)
    programming_experience = Column(String, nullable=True)
    child_age = Column(Integer, nullable=True)
    child_name = Column(String, nullable=True)
    onboarding_completed = Column(Integer, default=0)  # 0 - не завершен, 1 - завершен
    onboarding_data = Column(Text, nullable=True)  # JSON с полными данными

    messages = relationship("Message", back_populates="user")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    relevance = Column(Float, nullable=True)  # Может быть None для сообщений бота
    is_bot = Column(Integer, default=0)  # 0 - пользователь, 1 - бот
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="messages")


class ScheduledBroadcast(Base):
    __tablename__ = "scheduled_broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    telegram_ids = Column(Text, nullable=False)  # JSON array of telegram IDs
    text = Column(Text, nullable=False)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    file_name = Column(String, nullable=True)
    file_content = Column(Text, nullable=True)  # Base64 encoded file
    sent = Column(Integer, default=0)  # 0 - not sent, 1 - sent
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # dev, admin, manager
    created_at = Column(DateTime, default=datetime.utcnow)

