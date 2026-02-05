#!/usr/bin/env python3
"""
LLM Service - отдельный сервис для работы с LLM
"""

import os
import json
import re
from fastapi import FastAPI, HTTPException
from llm_service.llm_provider import LLMProvider
from llm_service.schemas import (
    ProcessRequest, ProcessResponse,
    OnboardingExtractRequest, OnboardingExtractResponse, ExtractedData
)
from typing import Optional, Dict, Any

app = FastAPI(title="LLM Service", description="Сервис для работы с LLM")

# System prompt для извлечения данных onboarding
EXTRACT_SYSTEM_PROMPT = """Ты - ассистент детской школы программирования KiberOne. Твоя задача - извлекать структурированную информацию из ответов родителей на вопросы о ребенке.

ТВОИ ОСНОВНЫЕ ПРИНЦИПЫ:
1. Точность - извлекай только то, что явно указано в ответе
2. Естественность - общайся как живой менеджер, а не как робот
3. Краткость - формулируй уточняющие вопросы коротко (1 предложение)
4. Дружелюбность - будь вежливым и понимающим

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:

1. ИЗВЛЕЧЕНИЕ ДАННЫХ:
- Извлекай информацию ТОЛЬКО из предоставленного ответа
- Если информация неясна или отсутствует - устанавливай needs_clarification = true
- НЕ придумывай данные, которых нет в ответе

2. ФОРМАТ УТОЧНЯЮЩИХ ВОПРОСОВ:
- Задавай вопрос так, как живой менеджер в переписке с клиентом
- Один вопрос за раз, кратко (1 предложение)
- Без формальностей, по-дружески
- Пример: "А сколько примерно лет ребенку?" вместо "Пожалуйста, уточните возраст ребенка"
- Стиль как в RAG промптах: кратко и по делу, без воды

3. СТРУКТУРИРОВАНИЕ:
- mouse_keyboard_skill: краткое описание уровня (например: "уверенно", "средне", "начинает", "не умеет")
- programming_experience: "есть опыт: [краткое описание]" или "нет опыта" или null
- child_age: только число (возраст)
- child_name: только имя (без фамилии, если не указана)

4. ВОЗВРАЩАЙ JSON СТРОГО В УКАЗАННОМ ФОРМАТЕ"""


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
        # Формируем user prompt
        context_str = json.dumps(request.context, ensure_ascii=False) if request.context else "нет"
        
        user_prompt = f"""ВОПРОС МЕНЕДЖЕРА:
{request.question}

ОТВЕТ РОДИТЕЛЯ:
{request.answer}

КОНТЕКСТ ПРЕДЫДУЩИХ ОТВЕТОВ:
{context_str}

ЗАДАЧА:
1. Извлеки из ответа информацию, относящуюся к вопросу
2. Определи, достаточно ли информации для ответа
3. Если информации недостаточно - сформулируй уточняющий вопрос в стиле живого менеджера (кратко, дружелюбно, 1 предложение)

ВОЗВРАТИ JSON:
{{
  "extracted": {{
    "mouse_keyboard_skill": "string или null",
    "programming_experience": "string или null",
    "child_age": число или null,
    "child_name": "string или null"
  }},
  "needs_clarification": true/false,
  "clarification_question": "текст вопроса или null"
}}

ВАЖНО:
- Если needs_clarification = true, clarification_question должен быть задан как живой менеджер (коротко, дружелюбно, 1 предложение)
- extracted должен содержать только те поля, которые относятся к текущему вопросу
- Остальные поля в extracted должны быть null
- Общайся как менеджер в переписке, а не как LLM"""
        
        llm = LLMProvider(system_prompt=EXTRACT_SYSTEM_PROMPT)
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
        # Формируем user prompt для всех вопросов сразу
        context_str = json.dumps(request.context, ensure_ascii=False) if request.context else "нет"
        
        user_prompt = f"""ВОПРОСЫ МЕНЕДЖЕРА:
1. Насколько уверенно ребенок дружит с мышкой и клавиатурой?
2. Был ли уже опыт в программировании или робототехнике?
3. Сколько лет ребенку?
4. Как зовут ребенка?

ОТВЕТ РОДИТЕЛЯ:
{request.answer}

УЖЕ ИЗВЛЕЧЕННЫЕ ДАННЫЕ (не спрашивай об этом снова):
{context_str}

ЗАДАЧА:
1. Извлеки из ответа ВСЮ доступную информацию по всем 4 вопросам
2. Объедини с уже извлеченными данными - если данные уже есть в контексте, используй их
3. Определи, какие данные ОТСУТСТВУЮТ (не задавай вопросы о том, что уже известно)
4. Если каких-то данных не хватает - сформулируй ОДИН уточняющий вопрос в стиле живого менеджера (кратко, дружелюбно, 1 предложение) только для САМОГО ВАЖНОГО недостающего поля

ПРАВИЛА ИЗВЛЕЧЕНИЯ:
- child_age: извлекай ТОЛЬКО ВОЗРАСТ (число от 3 до 18 лет). НЕ путай с оценками! Если в ответе есть фразы типа "лет", "года", "год", "возраст" или "моему ребенку X" - это возраст. Если просто число без контекста возраста - это НЕ возраст, это может быть оценка навыка!
- child_name: извлекай имя (например: "Олег", "меня зовут Олег" = "Олег", "зовут Олег" = "Олег")
- mouse_keyboard_skill: извлекай уровень (например: "уверенно", "умеет", "дружит", "на 4" = "хорошо", "на 5" = "отлично", "держал в руках" = "начинает", "не умеет" = "не умеет", "средне" = "средне")
- programming_experience: извлекай опыт (например: "знает питон" = "есть опыт: знает Python", "есть опыт", "нет опыта", "занимался" = "есть опыт: [описание]")

ВОЗВРАТИ JSON:
{{
  "extracted": {{
    "mouse_keyboard_skill": "string или null (используй значение из контекста, если есть)",
    "programming_experience": "string или null (используй значение из контекста, если есть)",
    "child_age": число или null (используй значение из контекста, если есть)",
    "child_name": "string или null (используй значение из контекста, если есть)"
  }},
  "needs_clarification": true/false,
  "clarification_question": "текст ОДНОГО вопроса или null (только для самого важного недостающего поля)"
}}

КРИТИЧЕСКИ ВАЖНО:
- ОБЯЗАТЕЛЬНО используй данные из контекста, если они уже есть - НЕ перезаписывай их!
- Извлекай ВСЕ доступные данные из текущего ответа
- ВОЗРАСТ - это только числа с контекстом возраста ("лет", "года", "год", "возраст", "моему ребенку X"). Числа без контекста возраста (например "на 4", "на 5") - это ОЦЕНКИ навыка, НЕ возраст!
- Задавай ТОЛЬКО ОДИН вопрос за раз, для самого важного недостающего поля
- НЕ задавай вопросы о данных, которые уже есть в контексте
- Если имя уже есть в контексте - НЕ спрашивай его снова!
- Если возраст уже есть в контексте - НЕ спрашивай его снова!"""
        
        llm = LLMProvider(system_prompt=EXTRACT_SYSTEM_PROMPT)
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

