import os
import logging
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProvider:
    def __init__(self, system_prompt: str = None):
        credentials = os.getenv('GIGACHAT_CREDENTIALS', '')
        if not credentials:
            raise ValueError("GIGACHAT_CREDENTIALS не установлен")
        
        self.giga = GigaChat(
            credentials=credentials,
            verify_ssl_certs=False,
        )
        self.system_prompt = system_prompt

    def process_prompt(self, user_prompt: str) -> str:
        """Обработка промпта через LLM"""
        messages_list = []
        if self.system_prompt:
            messages_list.append(Messages(role=MessagesRole('system'), content=self.system_prompt))
        messages_list.append(Messages(role=MessagesRole('user'), content=user_prompt))
        chat_request = Chat(messages=messages_list)
        
        try:
            prompt = self.giga.chat(chat_request)
            response_content = prompt.choices[0].message.content
            return response_content
        except Exception as e:
            logger.error(f"Ошибка при обработке промпта: {e}")
            raise

