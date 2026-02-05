import os
import logging
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from dotenv import load_dotenv

load_dotenv()


class LLMProvider:
    def __init__(self, system_prompt: str = None):
        self.giga = GigaChat(
            credentials=os.getenv('GIGACHAT_CREDENTIALS', ''),
            verify_ssl_certs=False,
        )
        self.system_prompt = system_prompt

    def proces_prompt(self, user_prompt: str) -> str:
        messages_list = []
        if self.system_prompt:
            messages_list.append(Messages(role=MessagesRole('system'), content=self.system_prompt))
        messages_list.append(Messages(role=MessagesRole('user'), content=user_prompt))
        chat_request = Chat(messages=messages_list)
        prompt = self.giga.chat(chat_request)
        response_content = prompt.choices[0].message.content
        return response_content

