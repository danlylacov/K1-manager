from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    phone: Optional[str]
    created_at: datetime
    mouse_keyboard_skill: Optional[str] = None
    programming_experience: Optional[str] = None
    child_age: Optional[int] = None
    child_name: Optional[str] = None
    onboarding_completed: int = 0

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    user_id: int
    text: str
    relevance: Optional[float] = None
    is_bot: int = 0  # 0 - пользователь, 1 - бот


class MessageResponse(BaseModel):
    id: int
    user_id: int
    text: str
    relevance: Optional[float]
    is_bot: int
    created_at: datetime

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    telegram_id: int
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    relevance: float


class OnboardingStatusResponse(BaseModel):
    onboarding_completed: bool
    current_question: Optional[int] = None  # 1-4 или None если завершен


class OnboardingAnswerRequest(BaseModel):
    question_number: int  # 1-4
    answer: str


class OnboardingAnswerAllRequest(BaseModel):
    answer: str  # Ответ на все вопросы сразу


class OnboardingAnswerResponse(BaseModel):
    extracted: dict
    needs_clarification: bool
    clarification_question: Optional[str] = None
    question_completed: bool


class OnboardingAnswerAllResponse(BaseModel):
    extracted: dict
    needs_clarification: bool
    clarification_question: Optional[str] = None
    onboarding_completed: bool


class OnboardingDataResponse(BaseModel):
    extracted: dict
    needs_clarification: bool
    clarification_question: Optional[str] = None


class SendMessageRequest(BaseModel):
    telegram_id: int
    text: str


class BroadcastRequest(BaseModel):
    telegram_ids: list[int]
    text: str


class ScheduleBroadcastRequest(BaseModel):
    telegram_ids: list[int]
    text: str
    scheduled_at: datetime


# Схемы для аутентификации и управления админ-пользователями
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    username: str
    role: str
    message: str


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: str  # dev, admin, manager


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


class AdminUserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class CurrentUserResponse(BaseModel):
    username: str
    role: str

