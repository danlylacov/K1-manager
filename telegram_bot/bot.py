import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8001")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class UserStates(StatesGroup):
    waiting_for_phone = State()
    onboarding_initial = State()  # Ожидание ответа на все вопросы сразу
    onboarding_clarification = State()  # Уточнение от LLM


def get_main_keyboard():
    """Клавиатура с основными кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Записаться на занятие", request_contact=True)]
        ],
        resize_keyboard=True
    )
    return keyboard


async def register_user(telegram_id: int, username: str = None):
    """Регистрация пользователя в backend"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_API_URL}/users",
                json={
                    "telegram_id": telegram_id,
                    "username": username
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Ошибка регистрации пользователя: {e}")
            return False


async def save_message(telegram_id: int, text: str, is_bot: int = 0, relevance: float = None):
    """Сохранить сообщение в БД"""
    async with httpx.AsyncClient() as client:
        try:
            # Сначала получаем user_id
            user_response = await client.get(f"{BACKEND_API_URL}/users/{telegram_id}")
            if user_response.status_code != 200:
                return False
            
            user_data = user_response.json()
            
            # Сохраняем сообщение
            message_data = {
                "user_id": user_data["id"],
                "text": text,
                "is_bot": is_bot,
                "relevance": relevance
            }
            
            response = await client.post(
                f"{BACKEND_API_URL}/messages",
                json=message_data
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Ошибка сохранения сообщения: {e}")
            return False


async def get_onboarding_status(telegram_id: int):
    """Получить статус onboarding"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_API_URL}/users/{telegram_id}/onboarding")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Ошибка получения статуса onboarding: {e}")
            return None


ONBOARDING_QUESTIONS_TEXT = """Расскажите, пожалуйста, о вашем ребенке:
1. Насколько уверенно ребенок дружит с мышкой и клавиатурой?
2. Был ли уже опыт в программировании или робототехнике? (Если нет — так даже интереснее, мы любим открывать таланты!)
3. Сколько лет ребенку? Мы подберем группу комфортную по возрасту
4. Как зовут ребенка?

Можете ответить на все вопросы сразу в свободной форме."""


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await register_user(message.from_user.id, message.from_user.username)
    
    # Сохраняем команду /start в БД
    await save_message(message.from_user.id, "/start", is_bot=0)
    
    # Проверяем статус onboarding
    onboarding_status = await get_onboarding_status(message.from_user.id)
    
    if onboarding_status and not onboarding_status.get("onboarding_completed"):
        # Начинаем onboarding - задаем все вопросы сразу
        await start_onboarding(message, state)
    else:
        # Onboarding завершен, показываем обычное меню
        welcome_text = (
            "Привет! Я бот для работы с базой знаний.\n\n"
            "Вы можете задать любой вопрос о нашей школе!"
        )
        await message.answer(welcome_text, reply_markup=get_main_keyboard())
        # Сохраняем приветственное сообщение бота
        await save_message(message.from_user.id, welcome_text, is_bot=1)


async def start_onboarding(message: types.Message, state: FSMContext):
    """Начать onboarding - задать все вопросы сразу"""
    await state.set_state(UserStates.onboarding_initial)
    await message.answer(ONBOARDING_QUESTIONS_TEXT)
    # Сохраняем вопросы бота
    await save_message(message.from_user.id, ONBOARDING_QUESTIONS_TEXT, is_bot=1)


async def process_question(message: types.Message):
    """Обработка вопроса пользователя"""
    question = message.text
    
    # Сохраняем вопрос пользователя (он будет сохранен в backend при обработке запроса, но сохраним и здесь для надежности)
    # await save_message(message.from_user.id, question, is_bot=0)
    
    # Отправляем индикатор "печатает..."
    bot_message = await message.answer("печатает...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_API_URL}/query",
                json={
                    "telegram_id": message.from_user.id,
                    "question": question
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            answer = result.get("answer", "Извините, произошла ошибка.")
            
            # Удаляем сообщение "печатает..." и отправляем ответ
            await bot_message.delete()
            await message.answer(answer, reply_markup=get_main_keyboard())
            # Сообщение бота уже сохранено в backend при обработке запроса
        except Exception as e:
            # Удаляем сообщение "печатает..." и отправляем ошибку
            await bot_message.delete()
            error_text = "Извините, произошла ошибка при обработке вопроса. Попробуйте позже."
            await message.answer(error_text, reply_markup=get_main_keyboard())
            await save_message(message.from_user.id, error_text, is_bot=1)
            print(f"Ошибка запроса к backend: {e}")


@dp.message(lambda message: message.text == "Записаться на занятие")
async def register_handler(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Записаться на занятие'"""
    # Сохраняем сообщение пользователя
    await save_message(message.from_user.id, message.text, is_bot=0)
    
    await state.set_state(UserStates.waiting_for_phone)
    phone_request_text = "Пожалуйста, поделитесь контактом, нажав кнопку ниже:"
    await message.answer(phone_request_text, reply_markup=get_main_keyboard())
    # Сохраняем запрос бота
    await save_message(message.from_user.id, phone_request_text, is_bot=1)


@dp.message(lambda message: message.contact is not None)
async def process_contact(message: types.Message, state: FSMContext):
    """Обработка контакта пользователя"""
    contact = message.contact
    phone = contact.phone_number
    
    # Сохраняем сообщение с контактом
    contact_text = f"Контакт: {phone}"
    await save_message(message.from_user.id, contact_text, is_bot=0)
    
    # Убеждаемся, что телефон начинается с +
    if not phone.startswith('+'):
        phone = '+' + phone
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{BACKEND_API_URL}/users/{message.from_user.id}",
                json={"phone": phone}
            )
            response.raise_for_status()
            
            phone_saved_text = f"Спасибо! Ваш телефон {phone} записан. Мы свяжемся с вами в ближайшее время."
            await message.answer(phone_saved_text, reply_markup=get_main_keyboard())
            # Сохраняем сообщение бота
            await save_message(message.from_user.id, phone_saved_text, is_bot=1)
        except Exception as e:
            error_text = "Извините, произошла ошибка при сохранении телефона. Попробуйте позже."
            await message.answer(error_text, reply_markup=get_main_keyboard())
            await save_message(message.from_user.id, error_text, is_bot=1)
            print(f"Ошибка обновления телефона: {e}")
            import traceback
            traceback.print_exc()
    
    await state.clear()


@dp.message(UserStates.waiting_for_phone)
async def process_phone_waiting(message: types.Message):
    """Обработка сообщений в состоянии ожидания контакта"""
    # Сохраняем сообщение пользователя
    if message.text:
        await save_message(message.from_user.id, message.text, is_bot=0)
    
    phone_wait_text = "Пожалуйста, поделитесь контактом, нажав кнопку 'Записаться на занятие'."
    await message.answer(phone_wait_text, reply_markup=get_main_keyboard())
    # Сохраняем ответ бота
    await save_message(message.from_user.id, phone_wait_text, is_bot=1)


async def process_onboarding_answer(message: types.Message, state: FSMContext):
    """Обработать ответ на все вопросы onboarding сразу"""
    answer = message.text
    
    # Сохраняем ответ пользователя
    await save_message(message.from_user.id, answer, is_bot=0)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_API_URL}/users/{message.from_user.id}/onboarding/answer-all",
                json={
                    "answer": answer
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            needs_clarification = result.get("needs_clarification", False)
            clarification_question = result.get("clarification_question")
            onboarding_completed = result.get("onboarding_completed", False)
            
            if onboarding_completed:
                # Все данные собраны, завершаем onboarding
                await complete_onboarding(message, state)
            elif needs_clarification and clarification_question:
                # Нужно уточнение
                await state.set_state(UserStates.onboarding_clarification)
                await message.answer(clarification_question)
                # Сохраняем уточняющий вопрос бота
                await save_message(message.from_user.id, clarification_question, is_bot=1)
            else:
                retry_text = "Попробуйте ответить еще раз."
                await message.answer(retry_text)
                await save_message(message.from_user.id, retry_text, is_bot=1)
                
        except Exception as e:
            error_text = "Извините, произошла ошибка. Попробуйте ответить еще раз."
            await message.answer(error_text)
            await save_message(message.from_user.id, error_text, is_bot=1)
            print(f"Ошибка обработки ответа onboarding: {e}")


async def complete_onboarding(message: types.Message, state: FSMContext):
    """Завершить onboarding"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_API_URL}/users/{message.from_user.id}/onboarding/complete"
            )
            response.raise_for_status()
            
            await state.clear()
            completion_text = (
                "Спасибо! Мы получили всю необходимую информацию.\n\n"
                "Теперь вы можете задавать вопросы о нашей школе!"
            )
            await message.answer(completion_text, reply_markup=get_main_keyboard())
            # Сохраняем сообщение о завершении onboarding
            await save_message(message.from_user.id, completion_text, is_bot=1)
        except Exception as e:
            error_text = "Извините, произошла ошибка при завершении регистрации."
            await message.answer(error_text)
            await save_message(message.from_user.id, error_text, is_bot=1)
            print(f"Ошибка завершения onboarding: {e}")


# Обработчики для onboarding
@dp.message(UserStates.onboarding_initial)
async def handle_onboarding_initial(message: types.Message, state: FSMContext):
    """Обработка начального ответа на все вопросы"""
    await process_onboarding_answer(message, state)


@dp.message(UserStates.onboarding_clarification)
async def handle_onboarding_clarification(message: types.Message, state: FSMContext):
    """Обработка уточняющего ответа"""
    await process_onboarding_answer(message, state)


@dp.message()
async def handle_message(message: types.Message, state: FSMContext):
    """Обработчик всех остальных сообщений"""
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    
    # Если в состоянии onboarding или ожидания телефона - не обрабатываем здесь
    if current_state in [UserStates.waiting_for_phone, 
                         UserStates.onboarding_initial,
                         UserStates.onboarding_clarification]:
        return
    
    # Проверяем, завершен ли onboarding
    onboarding_status = await get_onboarding_status(message.from_user.id)
    if onboarding_status and not onboarding_status.get("onboarding_completed"):
        # Onboarding не завершен, начинаем снова
        await start_onboarding(message, state)
        return
    
    # Onboarding завершен, обрабатываем как обычный вопрос
    await process_question(message)


async def main():
    """Запуск бота"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

