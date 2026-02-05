from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
import httpx
import os
import json
from typing import List, Optional
from datetime import datetime

from backend.database import get_db, init_db
from backend.models import User, Message, ScheduledBroadcast
from backend.schemas import (
    UserCreate, UserUpdate, UserResponse,
    MessageCreate, MessageResponse,
    QueryRequest, QueryResponse,
    OnboardingStatusResponse, OnboardingAnswerRequest, OnboardingAnswerResponse,
    OnboardingAnswerAllRequest, OnboardingAnswerAllResponse,
    OnboardingDataResponse
)

app = FastAPI(title="Backend API", description="API для управления пользователями и сообщениями")

RAG_API_URL = os.getenv("RAG_API_URL", "http://rag-api:8000")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8002")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None


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
    
    # Запрос к RAG API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{RAG_API_URL}/query",
                json={"question": request.question},
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


async def send_telegram_message(telegram_id: int, text: str, file_path: Optional[str] = None, file_content: Optional[bytes] = None, file_name: Optional[str] = None):
    """Отправить сообщение через Telegram Bot API"""
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            if file_path or file_content:
                # Отправка файла
                if file_content:
                    files = {"document": (file_name or "file", file_content)}
                    data = {"chat_id": telegram_id, "caption": text}
                    response = await client.post(
                        f"{TELEGRAM_API_URL}/sendDocument",
                        data=data,
                        files=files,
                        timeout=30.0
                    )
                else:
                    # Если файл по пути
                    with open(file_path, "rb") as f:
                        files = {"document": (os.path.basename(file_path), f.read())}
                        data = {"chat_id": telegram_id, "caption": text}
                        response = await client.post(
                            f"{TELEGRAM_API_URL}/sendDocument",
                            data=data,
                            files=files,
                            timeout=30.0
                        )
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
    text: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Отправить сообщение пользователю через Telegram"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    file_content = None
    file_name = None
    if file:
        file_content = await file.read()
        file_name = file.filename
    
    # Отправляем через Telegram
    telegram_result = await send_telegram_message(telegram_id, text, file_content=file_content, file_name=file_name)
    
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
    telegram_ids: str = Form(...),  # JSON string
    text: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Массовая рассылка сообщений"""
    try:
        ids = json.loads(telegram_ids)
    except:
        raise HTTPException(status_code=400, detail="Invalid telegram_ids format")
    
    file_content = None
    file_name = None
    if file:
        file_content = await file.read()
        file_name = file.filename
    
    results = []
    errors = []
    
    for telegram_id in ids:
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                errors.append({"telegram_id": telegram_id, "error": "User not found"})
                continue
            
            # Отправляем через Telegram
            telegram_result = await send_telegram_message(telegram_id, text, file_content=file_content, file_name=file_name)
            
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
    telegram_ids: str = Form(...),
    text: str = Form(...),
    scheduled_at: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Запланированная рассылка"""
    try:
        ids = json.loads(telegram_ids)
        scheduled_datetime = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid format: {str(e)}")
    
    file_content = None
    file_name = None
    if file:
        file_content = await file.read()
        file_name = file.filename
    
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


@app.get("/")
def root():
    return {"message": "Backend API"}

