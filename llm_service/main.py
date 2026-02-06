#!/usr/bin/env python3
"""
LLM Service - отдельный сервис для работы с LLM
"""

import os
import json
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from llm_service.llm_provider import LLMProvider
from llm_service.schemas import (
    ProcessRequest, ProcessResponse,
    OnboardingExtractRequest, OnboardingExtractResponse, ExtractedData
)
from typing import Optional, Dict, Any

app = FastAPI(title="LLM Service", description="Сервис для работы с LLM")

# Определяем путь к промптам относительно файла main.py
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(filename: str) -> str:
    """Загрузить промпт из файла"""
    prompt_path = PROMPTS_DIR / filename
    with open(prompt_path, 'r', encoding='utf-8') as file:
        return file.read()


def get_extract_system_prompt() -> str:
    """Получить системный промпт для извлечения данных onboarding"""
    return load_prompt("extract_system_prompt.txt")


def parse_json_response(text: str) -> dict:
    """Парсинг JSON из ответа LLM"""
    # Пытаемся найти JSON в тексте
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Если не нашли, пытаемся распарсить весь текст
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Не удалось распарсить JSON из ответа: {text[:200]}")


@app.post("/process", response_model=ProcessResponse)
async def process(request: ProcessRequest):
    """Обработка текста через LLM с системным промптом"""
    try:
        llm = LLMProvider(system_prompt=request.system_prompt)
        response = llm.process_prompt(request.user_prompt)
        return ProcessResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка LLM: {str(e)}")


@app.post("/extract_onboarding", response_model=OnboardingExtractResponse)
async def extract_onboarding(request: OnboardingExtractRequest):
    """Извлечение структурированных данных из ответа пользователя"""
    try:
        # Загружаем промпты из файлов
        system_prompt = get_extract_system_prompt()
        user_prompt_template = load_prompt("extract_onboarding_user_prompt.txt")
        
        # Формируем user prompt
        context_str = json.dumps(request.context, ensure_ascii=False) if request.context else "нет"
        
        user_prompt = user_prompt_template.format(
            question=request.question,
            answer=request.answer,
            context=context_str
        )
        
        llm = LLMProvider(system_prompt=system_prompt)
        response = llm.process_prompt(user_prompt)
        
        # Парсим JSON из ответа
        parsed = parse_json_response(response)
        
        # Валидируем и создаем ответ
        extracted = ExtractedData(
            mouse_keyboard_skill=parsed.get("extracted", {}).get("mouse_keyboard_skill"),
            programming_experience=parsed.get("extracted", {}).get("programming_experience"),
            child_age=parsed.get("extracted", {}).get("child_age"),
            child_name=parsed.get("extracted", {}).get("child_name")
        )
        
        return OnboardingExtractResponse(
            extracted=extracted,
            needs_clarification=parsed.get("needs_clarification", False),
            clarification_question=parsed.get("clarification_question")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка извлечения данных: {str(e)}")


@app.post("/extract_onboarding_all", response_model=OnboardingExtractResponse)
async def extract_onboarding_all(request: OnboardingExtractRequest):
    """Извлечение всех данных onboarding из одного ответа"""
    try:
        # Загружаем промпты из файлов
        system_prompt = get_extract_system_prompt()
        user_prompt_template = load_prompt("extract_onboarding_all_user_prompt.txt")
        
        # Формируем user prompt
        context_str = json.dumps(request.context, ensure_ascii=False) if request.context else "нет"
        
        user_prompt = user_prompt_template.format(
            answer=request.answer,
            context=context_str
        )
        
        llm = LLMProvider(system_prompt=system_prompt)
        response = llm.process_prompt(user_prompt)
        
        # Парсим JSON из ответа
        parsed = parse_json_response(response)
        
        extracted_dict = parsed.get("extracted", {})
        
        # Объединяем с контекстом - ПРИОРИТЕТ контексту (уже сохраненным данным)
        # Используем данные из контекста, если они есть, иначе используем новые
        if request.context:
            # Для каждого поля: если есть в контексте - используем контекст, иначе новое значение
            extracted_dict["mouse_keyboard_skill"] = request.context.get("mouse_keyboard_skill") or extracted_dict.get("mouse_keyboard_skill")
            extracted_dict["programming_experience"] = request.context.get("programming_experience") or extracted_dict.get("programming_experience")
            extracted_dict["child_age"] = request.context.get("child_age") or extracted_dict.get("child_age")
            extracted_dict["child_name"] = request.context.get("child_name") or extracted_dict.get("child_name")
        
        # Валидируем и создаем ответ
        extracted = ExtractedData(
            mouse_keyboard_skill=extracted_dict.get("mouse_keyboard_skill"),
            programming_experience=extracted_dict.get("programming_experience"),
            child_age=extracted_dict.get("child_age"),
            child_name=extracted_dict.get("child_name")
        )
        
        # Определяем, нужны ли уточнения (только для полей, которых нет)
        needs_clarification = False
        clarification_question = None
        
        missing_fields = []
        if not extracted.mouse_keyboard_skill:
            missing_fields.append("mouse_keyboard_skill")
        if not extracted.programming_experience:
            missing_fields.append("programming_experience")
        if not extracted.child_age:
            missing_fields.append("child_age")
        if not extracted.child_name:
            missing_fields.append("child_name")
        
        if missing_fields:
            needs_clarification = True
            # Используем вопрос от LLM, если он есть, иначе формируем свой
            clarification_question = parsed.get("clarification_question")
            if not clarification_question:
                # Формируем вопрос для самого важного недостающего поля
                # Приоритет: имя → возраст → навыки → опыт
                if "child_name" in missing_fields:
                    clarification_question = "Как зовут ребенка?"
                elif "child_age" in missing_fields:
                    clarification_question = "Сколько лет ребенку?"
                elif "mouse_keyboard_skill" in missing_fields:
                    clarification_question = "Насколько уверенно ребенок дружит с мышкой и клавиатурой?"
                elif "programming_experience" in missing_fields:
                    clarification_question = "Был ли уже опыт в программировании или робототехнике?"
        else:
            # Все данные есть, но используем вопрос от LLM, если он есть (может быть null)
            clarification_question = parsed.get("clarification_question")
        
        return OnboardingExtractResponse(
            extracted=extracted,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка извлечения данных: {str(e)}")


@app.get("/")
def root():
    return {"message": "LLM Service", "endpoints": ["POST /process", "POST /extract_onboarding"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

