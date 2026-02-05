#!/usr/bin/env python3
"""
Простой FastAPI сервис для работы с RAG системой
"""

import os
import warnings
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel


os.environ['ANONYMIZED_TELEMETRY'] = 'False'
warnings.filterwarnings('ignore', category=UserWarning)

sys_path = str(Path(__file__).parent)
import sys
sys.path.insert(0, sys_path)

from RAG.rag.rag_pipeline import RAGPipeline
from RAG.llm_provider.llm_provider import LLMProvider

app = FastAPI(title="RAG API", description="API для работы с RAG системой")


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    avg_similirity: float
    llm_answer: Optional[str] = None


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Выполнить запрос к RAG системе"""
    pipeline = RAGPipeline()
    result = pipeline.query(request.question)
    
    if not result.get("sources"):
        return QueryResponse(
            question=request.question,
            avg_similirity=0.0,
            llm_answer="Извините, я не обладаю такой информацией! Все детали вы можете уточнить у менеджера!"
        )


    try:
        # Определяем путь к промптам относительно файла API
        prompts_dir = Path(__file__).parent / "prompts"
        system_prompt_path = prompts_dir / "system_prompt.txt"
        user_prompt_path = prompts_dir / "user_prompt.txt"
        
        with open(system_prompt_path, 'r', encoding='utf-8') as file:
            system_prompt = file.read()

        with open(user_prompt_path, 'r', encoding='utf-8') as file:
            user_prompt = file.read()
            user_prompt = user_prompt.format(answer=result['answer'], question=request.question)
            print(user_prompt)

        llm = LLMProvider(system_prompt)
        llm_answer = llm.proces_prompt(user_prompt)
        
        if not llm_answer or not llm_answer.strip():
            llm_answer = "Извините, не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Ошибка LLM: {error_details}")
        llm_answer = "Извините, произошла ошибка при обработке запроса. Попробуйте позже."

    print(result)
    if result['avg_similarity'] < 0.3:
        return QueryResponse(
            question=request.question,
            avg_similirity=result['avg_similarity'],
            llm_answer="Извините, я не обладаю такой информацией! Все детали вы можете уточнить у менеджера!"
        )
    
    return QueryResponse(
        question=request.question,
        avg_similirity=result['avg_similarity'],
        llm_answer=llm_answer
    )


@app.post("/documents")
async def upload_document(file: UploadFile = File(...), replace_all: bool = True):
    """Загрузить документ"""
    # Сохраняем файл временно
    temp_path = Path(f"/tmp/{file.filename}")
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        pipeline = RAGPipeline()
        count = pipeline.ingest_document(str(temp_path), replace_all=replace_all)
        
        return {"message": "Документ загружен", "filename": file.filename, "chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.get("/documents")
async def list_documents():
    """Список всех документов"""
    try:
        pipeline = RAGPipeline()
        doc_names = pipeline.list_documents()
        vector_store = pipeline.vector_store
        
        # Получаем количество чанков для каждого документа
        documents = []
        for doc_name in doc_names:
            chunks = vector_store.get_document_chunks(doc_name)
            documents.append({
                "document": doc_name,
                "chunks": len(chunks)
            })
        
        stats = vector_store.get_collection_stats()
        return {
            "documents": documents,
            "total_documents": len(documents),
            "total_chunks": stats["count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.put("/documents/{document_name}")
async def update_document(document_name: str, file: UploadFile = File(...)):
    """Обновить документ"""
    temp_path = Path(f"/tmp/{file.filename}")
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        pipeline = RAGPipeline()
        deleted = pipeline.delete_document(document_name)
        count = pipeline.ingest_document(str(temp_path), replace_all=False)
        
        return {
            "message": "Документ обновлен",
            "deleted_chunks": deleted,
            "new_chunks": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.delete("/documents/{document_name}")
async def delete_document(document_name: str):
    """Удалить документ"""
    try:
        pipeline = RAGPipeline()
        count = pipeline.delete_document(document_name)
        return {
            "message": "Документ удален",
            "deleted_chunks": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")


@app.get("/")
async def root():
    """Информация об API"""
    return {
        "message": "RAG API",
        "endpoints": {
            "POST /query": "Выполнить запрос",
            "POST /documents": "Загрузить документ",
            "GET /documents": "Список документов",
            "PUT /documents/{name}": "Обновить документ",
            "DELETE /documents/{name}": "Удалить документ"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

