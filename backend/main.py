from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form, Request
from starlette.requests import Request as StarletteRequest
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import httpx
import os
import json
from typing import List, Optional
from datetime import datetime
from passlib.context import CryptContext

from backend.database import get_db, init_db
from backend.models import User, Message, ScheduledBroadcast, AdminUser
from backend.schemas import (
    UserCreate, UserUpdate, UserResponse,
    MessageCreate, MessageResponse,
    QueryRequest, QueryResponse,
    OnboardingStatusResponse, OnboardingAnswerRequest, OnboardingAnswerResponse,
    OnboardingAnswerAllRequest, OnboardingAnswerAllResponse,
    OnboardingDataResponse,
    LoginRequest, LoginResponse, CurrentUserResponse,
    AdminUserCreate, AdminUserUpdate, AdminUserResponse
)

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Backend API", description="API для управления пользователями и сообщениями")

# Добавляем SessionMiddleware
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

RAG_API_URL = os.getenv("RAG_API_URL", "http://rag-api:8000")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8002")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None


# Вспомогательные функции для аутентификации
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    """Получить текущего пользователя из сессии"""
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


def require_role(allowed_roles: List[str]):
    """Зависимость для проверки роли"""
    def check_role(current_user: AdminUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return check_role


@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Создать пользователя"""
    db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if db_user:
        return db_user
    
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """Получить всех пользователей"""
    users = db.query(User).all()
    return users


@app.get("/users/{telegram_id}", response_model=UserResponse)
def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Получить пользователя по telegram_id"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{telegram_id}", response_model=UserResponse)
def update_user(telegram_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Обновить пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.phone is not None:
        user.phone = user_update.phone
    
    db.commit()
    db.refresh(user)
    return user


@app.post("/messages", response_model=MessageResponse)
def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    """Создать сообщение"""
    db_message = Message(**message.model_dump())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


@app.get("/messages", response_model=List[MessageResponse])
def get_messages(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Получить сообщения пользователя по user_id"""
    messages = db.query(Message).filter(Message.user_id == user_id).order_by(Message.created_at.desc()).all()
    return messages


@app.get("/users/{telegram_id}/messages", response_model=List[MessageResponse])
def get_user_messages(telegram_id: int, db: Session = Depends(get_db)):
    """Получить все сообщения (вопросы и ответы) пользователя по telegram_id"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    messages = db.query(Message).filter(Message.user_id == user.id).order_by(Message.created_at.asc()).all()
    return messages


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, db: Session = Depends(get_db)):
    """Запрос к RAG API с сохранением сообщения"""
    # Получаем или создаем пользователя
    user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
    if not user:
        user = User(telegram_id=request.telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Получаем последние 10 сообщений (5 пар вопрос-ответ) для контекста
    # Исключаем текущий вопрос, получая сообщения до текущего момента
    recent_messages = db.query(Message).filter(
        Message.user_id == user.id
    ).order_by(Message.created_at.desc()).limit(10).all()
    
    # Формируем conversation_history в обратном порядке (от старых к новым)
    conversation_history = []
    if recent_messages:
        # Переворачиваем список, чтобы получить хронологический порядок
        messages_chronological = list(reversed(recent_messages))
        for msg in messages_chronological:
            role = "assistant" if msg.is_bot == 1 else "user"
            conversation_history.append({
                "role": role,
                "text": msg.text
            })
    
    # Запрос к RAG API
    async with httpx.AsyncClient() as client:
        try:
            rag_request = {
                "question": request.question,
                "conversation_history": conversation_history if conversation_history else None
            }
            response = await client.post(
                f"{RAG_API_URL}/query",
                json=rag_request,
                timeout=60.0
            )
            response.raise_for_status()
            rag_result = response.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"RAG API returned {e.response.status_code}: {e.response.text[:200]}"
            print(f"RAG API HTTP error: {error_msg}")
            raise HTTPException(status_code=500, detail=f"RAG API error: {error_msg}")
        except Exception as e:
            error_msg = f"RAG API connection error: {str(e)}"
            print(f"RAG API error: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
    
    # Сохраняем вопрос пользователя с релевантностью
    relevance = rag_result.get("avg_similirity", 0.0) or 0.0
    bot_answer = rag_result.get("llm_answer", "") or "Извините, не удалось получить ответ."
    
    try:
        user_message = Message(
            user_id=user.id,
            text=request.question,
            relevance=relevance,
            is_bot=0
        )
        db.add(user_message)
        
        # Сохраняем ответ бота
        bot_message = Message(
            user_id=user.id,
            text=bot_answer,
            relevance=None,
            is_bot=1
        )
        db.add(bot_message)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database error: {str(e)}")
        # Все равно возвращаем ответ, даже если не удалось сохранить
    
    return QueryResponse(
        question=request.question,
        answer=bot_answer,
        relevance=relevance
    )


@app.get("/users/{telegram_id}/onboarding", response_model=OnboardingStatusResponse)
def get_onboarding_status(telegram_id: int, db: Session = Depends(get_db)):
    """Получить статус onboarding пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Определяем текущий вопрос на основе заполненных полей
    current_question = None
    if not user.mouse_keyboard_skill:
        current_question = 1
    elif not user.programming_experience:
        current_question = 2
    elif not user.child_age:
        current_question = 3
    elif not user.child_name:
        current_question = 4
    
    return OnboardingStatusResponse(
        onboarding_completed=user.onboarding_completed == 1,
        current_question=current_question
    )


@app.get("/users/{telegram_id}/onboarding/data", response_model=OnboardingDataResponse)
def get_onboarding_data(telegram_id: int, db: Session = Depends(get_db)):
    """Получить извлеченные данные onboarding пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Формируем extracted данные из полей пользователя
    extracted = {
        "mouse_keyboard_skill": user.mouse_keyboard_skill,
        "programming_experience": user.programming_experience,
        "child_age": user.child_age,
        "child_name": user.child_name
    }
    
    # Определяем, нужны ли уточнения (если какое-то поле не заполнено)
    needs_clarification = not all([
        user.mouse_keyboard_skill,
        user.programming_experience,
        user.child_age,
        user.child_name
    ])
    
    # Если нужны уточнения, определяем какой вопрос следующий
    clarification_question = None
    if needs_clarification:
        if not user.mouse_keyboard_skill:
            clarification_question = "Насколько уверенно ребенок дружит с мышкой и клавиатурой?"
        elif not user.programming_experience:
            clarification_question = "Был ли уже опыт в программировании или робототехнике?"
        elif not user.child_age:
            clarification_question = "Сколько лет ребенку?"
        elif not user.child_name:
            clarification_question = "Как зовут ребенка?"
    
    return OnboardingDataResponse(
        extracted=extracted,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question
    )


@app.post("/users/{telegram_id}/onboarding/answer", response_model=OnboardingAnswerResponse)
async def process_onboarding_answer(telegram_id: int, request: OnboardingAnswerRequest, db: Session = Depends(get_db)):
    """Обработать ответ на вопрос onboarding"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Вопросы onboarding
    questions = {
        1: "Насколько уверенно ребенок дружит с мышкой и клавиатурой?",
        2: "Был ли уже опыт в программировании или робототехнике? (Если нет — так даже интереснее, мы любим открывать таланты!)",
        3: "Сколько лет ребенку? Мы подберем группу комфортную по возрасту",
        4: "Как зовут ребенка?"
    }
    
    question_text = questions.get(request.question_number)
    if not question_text:
        raise HTTPException(status_code=400, detail="Invalid question number")
    
    # Формируем контекст предыдущих ответов
    context = {}
    if user.mouse_keyboard_skill:
        context["mouse_keyboard_skill"] = user.mouse_keyboard_skill
    if user.programming_experience:
        context["programming_experience"] = user.programming_experience
    if user.child_age:
        context["child_age"] = user.child_age
    if user.child_name:
        context["child_name"] = user.child_name
    
    # Отправляем в LLM Service для извлечения данных
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LLM_SERVICE_URL}/extract_onboarding",
                json={
                    "question": question_text,
                    "answer": request.answer,
                    "context": context
                },
                timeout=30.0
            )
            response.raise_for_status()
            llm_result = response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Service error: {str(e)}")
    
    extracted = llm_result.get("extracted", {})
    needs_clarification = llm_result.get("needs_clarification", False)
    clarification_question = llm_result.get("clarification_question")
    
    # Если не нужны уточнения, сохраняем данные
    question_completed = False
    if not needs_clarification:
        # Сохраняем данные в зависимости от номера вопроса
        if request.question_number == 1:
            if extracted.get("mouse_keyboard_skill"):
                user.mouse_keyboard_skill = extracted["mouse_keyboard_skill"]
                question_completed = True
        elif request.question_number == 2:
            if extracted.get("programming_experience"):
                user.programming_experience = extracted["programming_experience"]
                question_completed = True
        elif request.question_number == 3:
            if extracted.get("child_age"):
                user.child_age = extracted["child_age"]
                question_completed = True
        elif request.question_number == 4:
            if extracted.get("child_name"):
                user.child_name = extracted["child_name"]
                question_completed = True
        
        if question_completed:
            # Обновляем onboarding_data
            onboarding_data = {
                "mouse_keyboard_skill": user.mouse_keyboard_skill,
                "programming_experience": user.programming_experience,
                "child_age": user.child_age,
                "child_name": user.child_name
            }
            user.onboarding_data = json.dumps(onboarding_data, ensure_ascii=False)
            db.commit()
    
    return OnboardingAnswerResponse(
        extracted=extracted,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        question_completed=question_completed
    )


@app.post("/users/{telegram_id}/onboarding/answer-all", response_model=OnboardingAnswerAllResponse)
async def process_onboarding_answer_all(telegram_id: int, request: OnboardingAnswerAllRequest, db: Session = Depends(get_db)):
    """Обработать ответ на все вопросы onboarding сразу"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Формируем контекст уже имеющихся данных
    context = {}
    if user.mouse_keyboard_skill:
        context["mouse_keyboard_skill"] = user.mouse_keyboard_skill
    if user.programming_experience:
        context["programming_experience"] = user.programming_experience
    if user.child_age:
        context["child_age"] = user.child_age
    if user.child_name:
        context["child_name"] = user.child_name
    
    # Отправляем в LLM Service для извлечения всех данных сразу
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LLM_SERVICE_URL}/extract_onboarding_all",
                json={
                    "question": "",  # Пустой вопрос, так как задаем все сразу
                    "answer": request.answer,
                    "context": context
                },
                timeout=30.0
            )
            response.raise_for_status()
            llm_result = response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Service error: {str(e)}")
    
    extracted = llm_result.get("extracted", {})
    needs_clarification = llm_result.get("needs_clarification", False)
    clarification_question = llm_result.get("clarification_question")
    
    # Сохраняем извлеченные данные
    # Обновляем только если новое значение не пустое и отличается от текущего
    if extracted.get("mouse_keyboard_skill"):
        user.mouse_keyboard_skill = extracted["mouse_keyboard_skill"]
    
    if extracted.get("programming_experience"):
        user.programming_experience = extracted["programming_experience"]
    
    # Для возраста - обновляем только если это действительно возраст (не оценка)
    if extracted.get("child_age"):
        # Проверяем, что это разумный возраст (от 3 до 18)
        age = extracted["child_age"]
        if isinstance(age, int) and 3 <= age <= 18:
            user.child_age = age
        elif isinstance(age, str):
            # Пытаемся извлечь число из строки
            try:
                age_num = int(age)
                if 3 <= age_num <= 18:
                    user.child_age = age_num
            except:
                pass
    
    if extracted.get("child_name"):
        user.child_name = extracted["child_name"]
    
    # Проверяем, все ли данные собраны
    all_filled = all([
        user.mouse_keyboard_skill,
        user.programming_experience,
        user.child_age,
        user.child_name
    ])
    
    if all_filled:
        user.onboarding_completed = 1
    
    # Обновляем onboarding_data
    onboarding_data = {
        "mouse_keyboard_skill": user.mouse_keyboard_skill,
        "programming_experience": user.programming_experience,
        "child_age": user.child_age,
        "child_name": user.child_name
    }
    user.onboarding_data = json.dumps(onboarding_data, ensure_ascii=False)
    db.commit()
    
    return OnboardingAnswerAllResponse(
        extracted=extracted,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        onboarding_completed=all_filled
    )


@app.post("/users/{telegram_id}/onboarding/complete")
def complete_onboarding(telegram_id: int, db: Session = Depends(get_db)):
    """Завершить onboarding"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем, что все поля заполнены
    if not all([user.mouse_keyboard_skill, user.programming_experience, user.child_age, user.child_name]):
        raise HTTPException(status_code=400, detail="Not all onboarding fields are filled")
    
    user.onboarding_completed = 1
    db.commit()
    
    return {"message": "Onboarding completed", "user_id": user.id}


def is_image_file(file_name: str) -> bool:
    """Проверка, является ли файл изображением"""
    if not file_name:
        return False
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    return any(file_name.lower().endswith(ext) for ext in image_extensions)


async def send_telegram_message(
    telegram_id: int, 
    text: str, 
    file_path: Optional[str] = None, 
    file_content: Optional[bytes] = None, 
    file_name: Optional[str] = None,
    files: Optional[List[tuple]] = None  # Список кортежей (file_name, file_content)
):
    """Отправить сообщение через Telegram Bot API с поддержкой фото и множественных файлов"""
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            # Если есть множественные файлы - отправляем только первое фото
            if files:
                print(f"DEBUG send_telegram_message: получено файлов: {len(files)}")
                # Находим первое валидное фото
                first_photo = None
                for idx, (fname, fcontent) in enumerate(files):
                    print(f"DEBUG send_telegram_message: файл {idx}: name={fname}, content_size={len(fcontent) if fcontent else 0}, is_image={is_image_file(fname) if fname else False}")
                    if fname and fcontent and is_image_file(fname):
                        first_photo = (fname, fcontent)
                        print(f"DEBUG send_telegram_message: найдено первое фото: {fname}")
                        break
                
                if first_photo:
                    fname, fcontent = first_photo
                    print(f"Отправка фото: {fname}, размер: {len(fcontent)} байт")
                    
                    # Формируем данные для отправки фото
                    # Используем правильный формат для httpx: (filename, content)
                    files_data = {"photo": (fname, fcontent)}
                    data = {"chat_id": telegram_id}  # chat_id может быть числом
                    
                    # Добавляем caption если есть текст
                    if text and text.strip():
                        data["caption"] = text
                        print(f"Текст добавлен как caption: {text[:50]}...")
                    
                    try:
                        response = await client.post(
                            f"{TELEGRAM_API_URL}/sendPhoto",
                            data=data,
                            files=files_data,
                            timeout=30.0
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        if not result.get("ok"):
                            error_msg = result.get("description", "Unknown error")
                            print(f"Telegram API вернул ошибку: {error_msg}")
                            raise HTTPException(status_code=500, detail=f"Telegram API error: {error_msg}")
                        
                        print(f"Фото {fname} успешно отправлено")
                        return result
                    except httpx.HTTPStatusError as e:
                        error_text = e.response.text if e.response else str(e)
                        print(f"Ошибка HTTP при отправке фото: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка отправки фото: {error_text}")
                    except Exception as e:
                        print(f"Ошибка при отправке фото: {e}")
                        import traceback
                        traceback.print_exc()
                        raise HTTPException(status_code=500, detail=f"Ошибка отправки фото: {str(e)}")
                else:
                    # Если нет фото, но есть файлы - отправляем текст отдельно
                    print("Фото не найдено в файлах, отправляем только текст")
                    if text and text.strip():
                        response = await client.post(
                            f"{TELEGRAM_API_URL}/sendMessage",
                            json={"chat_id": telegram_id, "text": text},
                            timeout=30.0
                        )
                        response.raise_for_status()
                        return response.json()
                    else:
                        raise HTTPException(status_code=400, detail="Нет фото для отправки и нет текста")
            
            # Один файл (старая логика для обратной совместимости)
            elif file_path or file_content:
                is_image = is_image_file(file_name or file_path or "")
                
                if file_content:
                    file_data = file_content
                    file_name_to_send = file_name or "photo" if is_image else "file"
                else:
                    # Если файл по пути
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    file_name_to_send = os.path.basename(file_path)
                
                print(f"Отправка файла: {file_name_to_send}, is_image={is_image}, размер: {len(file_data)} байт")
                
                if is_image:
                    # Отправка как фото
                    files_data = {"photo": (file_name_to_send, file_data)}
                    data = {"chat_id": telegram_id}
                    if text and text.strip():
                        data["caption"] = text
                        print(f"Текст добавлен как caption: {text[:50]}...")
                    
                    try:
                        response = await client.post(
                            f"{TELEGRAM_API_URL}/sendPhoto",
                            data=data,
                            files=files_data,
                            timeout=30.0
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        if not result.get("ok"):
                            error_msg = result.get("description", "Unknown error")
                            print(f"Telegram API вернул ошибку: {error_msg}")
                            raise HTTPException(status_code=500, detail=f"Telegram API error: {error_msg}")
                        
                        print(f"Фото {file_name_to_send} успешно отправлено")
                        return result
                    except httpx.HTTPStatusError as e:
                        error_text = e.response.text if e.response else str(e)
                        print(f"Ошибка HTTP при отправке фото: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка отправки фото: {error_text}")
                    except Exception as e:
                        print(f"Ошибка при отправке фото: {e}")
                        import traceback
                        traceback.print_exc()
                        raise HTTPException(status_code=500, detail=f"Ошибка отправки фото: {str(e)}")
                else:
                    # Отправка как документ
                    files_data = {"document": (file_name_to_send, file_data)}
                    data = {"chat_id": telegram_id}
                    if text and text.strip():
                        data["caption"] = text
                    
                    response = await client.post(
                        f"{TELEGRAM_API_URL}/sendDocument",
                        data=data,
                        files=files_data,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if not result.get("ok"):
                        error_msg = result.get("description", "Unknown error")
                        raise HTTPException(status_code=500, detail=f"Telegram API error: {error_msg}")
                    
                    return result
            else:
                # Отправка текста
                response = await client.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={"chat_id": telegram_id, "text": text},
                    timeout=30.0
                )
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"Telegram API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@app.post("/admin/send-message")
async def send_message_to_user(
    telegram_id: int = Form(...),
    text: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    current_user: AdminUser = Depends(require_role(["dev", "admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Отправить сообщение пользователю через Telegram с поддержкой множественных файлов"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем файлы из параметров функции
    files_list = []
    
    print(f"DEBUG send-message: files parameter type: {type(files)}, length: {len(files) if files else 0}")
    
    if files:
        for idx, file_item in enumerate(files):
            try:
                # Получаем имя файла
                filename = getattr(file_item, 'filename', None)
                if not filename:
                    print(f"DEBUG send-message: файл {idx} без имени, пропускаем")
                    continue
                
                print(f"DEBUG send-message: обработка файла {idx}: {filename}, type={type(file_item)}")
                
                # Читаем содержимое файла
                file_content = await file_item.read()
                if not file_content:
                    print(f"DEBUG send-message: файл {filename} пустой, пропускаем")
                    continue
                
                files_list.append((filename, file_content))
                print(f"DEBUG send-message: файл {filename} подготовлен, размер: {len(file_content)} байт")
            except Exception as e:
                print(f"DEBUG send-message: ошибка при обработке файла {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    print(f"DEBUG send-message: Итого подготовлено файлов: {len(files_list)}")
    
    # Отправляем через Telegram
    if files_list:
        telegram_result = await send_telegram_message(telegram_id, text, files=files_list)
    else:
        telegram_result = await send_telegram_message(telegram_id, text)
    
    # Сохраняем сообщение в БД
    bot_message = Message(
        user_id=user.id,
        text=text,
        relevance=None,
        is_bot=1
    )
    db.add(bot_message)
    db.commit()
    
    return {"message": "Message sent", "telegram_result": telegram_result}


@app.post("/admin/broadcast")
async def broadcast_message(
    telegram_ids: str = Form(...),
    text: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    current_user: AdminUser = Depends(require_role(["dev", "admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Массовая рассылка сообщений с поддержкой множественных файлов"""
    try:
        ids = json.loads(telegram_ids)
    except:
        raise HTTPException(status_code=400, detail="Invalid telegram_ids format")
    
    # Получаем файлы из параметров функции
    files_list = []
    
    print(f"DEBUG broadcast: files parameter type: {type(files)}, length: {len(files) if files else 0}")
    
    if files:
        for idx, file_item in enumerate(files):
            try:
                # Получаем имя файла
                filename = getattr(file_item, 'filename', None)
                if not filename:
                    print(f"DEBUG broadcast: файл {idx} без имени, пропускаем")
                    continue
                
                print(f"DEBUG broadcast: обработка файла {idx}: {filename}, type={type(file_item)}")
                
                # Читаем содержимое файла
                file_content = await file_item.read()
                if not file_content:
                    print(f"DEBUG broadcast: файл {filename} пустой, пропускаем")
                    continue
                
                files_list.append((filename, file_content))
                print(f"DEBUG broadcast: файл {filename} подготовлен, размер: {len(file_content)} байт")
            except Exception as e:
                print(f"DEBUG broadcast: ошибка при обработке файла {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    print(f"DEBUG broadcast: Итого подготовлено файлов: {len(files_list)}")
    
    results = []
    errors = []
    
    for telegram_id in ids:
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                errors.append({"telegram_id": telegram_id, "error": "User not found"})
                continue
            
            # Отправляем через Telegram
            print(f"DEBUG broadcast: Отправка сообщения пользователю {telegram_id}, файлов: {len(files_list)}")
            if files_list:
                telegram_result = await send_telegram_message(telegram_id, text, files=files_list)
            else:
                telegram_result = await send_telegram_message(telegram_id, text)
            
            # Сохраняем сообщение в БД
            bot_message = Message(
                user_id=user.id,
                text=text,
                relevance=None,
                is_bot=1
            )
            db.add(bot_message)
            results.append({"telegram_id": telegram_id, "status": "sent"})
        except Exception as e:
            errors.append({"telegram_id": telegram_id, "error": str(e)})
    
    db.commit()
    
    return {
        "sent": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
    }


@app.post("/admin/schedule-broadcast")
async def schedule_broadcast(
    request: StarletteRequest,
    current_user: AdminUser = Depends(require_role(["dev", "admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Запланированная рассылка с поддержкой множественных файлов"""
    # Получаем все данные из формы
    form = await request.form()
    
    telegram_ids = form.get("telegram_ids", "[]")
    text = form.get("text", "")
    scheduled_at = form.get("scheduled_at", "")
    
    try:
        ids = json.loads(telegram_ids)
        scheduled_datetime = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid format: {str(e)}")
    
    # Для запланированных рассылок сохраняем только первый файл (для упрощения)
    # В будущем можно расширить модель для хранения множественных файлов
    file_content = None
    file_name = None
    files_from_form = form.getlist("files")
    if files_from_form and len(files_from_form) > 0:
        first_file = files_from_form[0]
        if isinstance(first_file, UploadFile) and first_file.filename:
            file_content = await first_file.read()
            file_name = first_file.filename
    
    # Сохраняем в таблицу scheduled_broadcasts
    import base64
    broadcast = ScheduledBroadcast(
        telegram_ids=json.dumps(ids, ensure_ascii=False),
        text=text,
        scheduled_at=scheduled_datetime,
        file_name=file_name,
        file_content=base64.b64encode(file_content).decode('utf-8') if file_content else None,
        sent=0
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    
    return {
        "message": "Broadcast scheduled",
        "scheduled_at": scheduled_at,
        "recipients_count": len(ids),
        "id": broadcast.id
    }


async def process_scheduled_broadcasts():
    """Обработка запланированных рассылок"""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Получаем все неотправленные рассылки, время которых наступило
        broadcasts = db.query(ScheduledBroadcast).filter(
            ScheduledBroadcast.sent == 0,
            ScheduledBroadcast.scheduled_at <= now
        ).all()
        
        for broadcast in broadcasts:
            try:
                telegram_ids = json.loads(broadcast.telegram_ids)
                file_content = None
                if broadcast.file_content:
                    import base64
                    file_content = base64.b64decode(broadcast.file_content)
                
                # Отправляем рассылку
                for telegram_id in telegram_ids:
                    try:
                        await send_telegram_message(
                            telegram_id,
                            broadcast.text,
                            file_content=file_content,
                            file_name=broadcast.file_name
                        )
                        
                        # Сохраняем сообщение в БД
                        user = db.query(User).filter(User.telegram_id == telegram_id).first()
                        if user:
                            bot_message = Message(
                                user_id=user.id,
                                text=broadcast.text,
                                relevance=None,
                                is_bot=1
                            )
                            db.add(bot_message)
                            db.commit()  # Коммитим после каждого сообщения
                    except Exception as e:
                        print(f"Error sending to {telegram_id}: {e}")
                        db.rollback()
                
                # Помечаем как отправленную только после успешной отправки всем
                broadcast.sent = 1
                db.commit()
            except Exception as e:
                print(f"Error processing broadcast {broadcast.id}: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup():
    init_db()
    # Запускаем планировщик в фоне
    import asyncio
    import threading
    
    def run_scheduler():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            loop.run_until_complete(process_scheduled_broadcasts())
            import time
            time.sleep(60)  # Проверяем каждую минуту
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()


@app.delete("/users/{telegram_id}")
def delete_user(telegram_id: int, db: Session = Depends(get_db)):
    """Удалить пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Удаляем все сообщения пользователя
    db.query(Message).filter(Message.user_id == user.id).delete()
    
    # Удаляем пользователя
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted", "telegram_id": telegram_id}


# Эндпоинты аутентификации
@app.post("/auth/login", response_model=LoginResponse)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """Вход в систему"""
    user = db.query(AdminUser).filter(AdminUser.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Сохраняем в сессии
    request.session["username"] = user.username
    request.session["role"] = user.role
    
    return LoginResponse(
        username=user.username,
        role=user.role,
        message="Login successful"
    )


@app.post("/auth/logout")
def logout(request: Request):
    """Выход из системы"""
    request.session.clear()
    return {"message": "Logout successful"}


@app.get("/auth/me", response_model=CurrentUserResponse)
def get_current_user_info(current_user: AdminUser = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return CurrentUserResponse(
        username=current_user.username,
        role=current_user.role
    )


# CRUD эндпоинты для управления админ-пользователями (только dev и admin)
@app.get("/admin/users", response_model=List[AdminUserResponse])
def get_admin_users(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех админ-пользователей"""
    if current_user.role not in ["dev", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    users = db.query(AdminUser).all()
    return users


@app.post("/admin/users", response_model=AdminUserResponse)
def create_admin_user(
    user_data: AdminUserCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать нового админ-пользователя"""
    if current_user.role not in ["dev", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем, что роль валидна
    if user_data.role not in ["dev", "admin", "manager"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Проверяем, что пользователь с таким username не существует
    existing_user = db.query(AdminUser).filter(AdminUser.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Создаем нового пользователя
    password_hash = get_password_hash(user_data.password)
    new_user = AdminUser(
        username=user_data.username,
        password_hash=password_hash,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@app.put("/admin/users/{user_id}", response_model=AdminUserResponse)
def update_admin_user(
    user_id: int,
    user_data: AdminUserUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить админ-пользователя"""
    if current_user.role not in ["dev", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Обновляем поля
    if user_data.username is not None:
        # Проверяем, что новый username не занят
        existing_user = db.query(AdminUser).filter(
            AdminUser.username == user_data.username,
            AdminUser.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = user_data.username
    
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    
    if user_data.role is not None:
        if user_data.role not in ["dev", "admin", "manager"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = user_data.role
    
    db.commit()
    db.refresh(user)
    
    return user


@app.delete("/admin/users/{user_id}")
def delete_admin_user(
    user_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить админ-пользователя"""
    if current_user.role not in ["dev", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Нельзя удалить самого себя
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@app.get("/")
def root():
    return {"message": "Backend API"}

