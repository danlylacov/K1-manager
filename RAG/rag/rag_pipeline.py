from typing import Dict
import os
from RAG.rag.config import RAGConfig, DEFAULT_CONFIG
from RAG.rag.document_processor import document_to_markdown, split_document
from RAG.rag.embedding_service import EmbeddingService
from RAG.rag.vector_store import VectorStore
from RAG.rag.query_processor import QueryProcessor
from RAG.rag.reranker import Reranker


class RAGPipeline:
    """Главный класс RAG пайплайна"""
    
    def __init__(self, config: RAGConfig = None):
        if config is None:
            config = DEFAULT_CONFIG
        
        self.config = config
        self.embedding_service = EmbeddingService(config.embedding)

        # Используем переменную окружения или путь по умолчанию
        db_path = os.getenv('CHROMA_DB_PATH', '/app/data/chroma_db')
        
        self.vector_store = VectorStore(db_path=db_path, config=config.retrieval)
        self.reranker = Reranker(self.embedding_service) if config.retrieval.use_reranking else None
        self.query_processor = QueryProcessor(
            self.embedding_service,
            self.vector_store,
            self.reranker,
            config.retrieval
        )
    
    def ingest_document(self, document_path: str, replace_all: bool = True) -> int:
        """Загружает документ в векторную БД с оптимизацией памяти
        
        Args:
            document_path: Путь к документу
            replace_all: Если True, заменяет все документы. Если False, добавляет к существующим
        """
        import gc
        
        # 1. Конвертация в текст
        document = document_to_markdown(document_path)
        
        # 2. Разбиение на чанки с метаданными
        chunks = split_document(document, self.config.chunking)
        print(f"Документ разбит на {len(chunks)} чанков")
        
        # Очистка памяти после разбиения
        del document
        gc.collect()
        
        # 3. Создание эмбеддингов (уже оптимизировано в encode_batch)
        documents_text = [chunk["content"] for chunk in chunks]
        embeddings = self.embedding_service.encode_batch(documents_text)
        print(f"Создано {len(embeddings)} эмбеддингов")
        
        # 4. Загрузка в векторную БД
        if replace_all:
            count = self.vector_store.upload_documents(documents_text, embeddings, chunks, replace_all=True)
        else:
            count = self.vector_store.add_documents(documents_text, embeddings, chunks)
        print(f"Загружено {count} документов в векторную БД")
        
        # Финальная очистка памяти
        del documents_text, embeddings
        gc.collect()
        
        return count
    
    def update_document(self, document_path: str) -> int:
        """Обновляет документ: удаляет старый и добавляет новый"""
        from pathlib import Path
        doc_name = Path(document_path).name
        
        # Удаляем старый документ
        deleted = self.vector_store.delete_document_by_name(doc_name)
        print(f"Удалено старых чанков: {deleted}")
        
        # Добавляем новый
        return self.ingest_document(document_path, replace_all=False)
    
    def delete_document(self, document_name: str) -> int:
        """Удаляет документ по имени"""
        return self.vector_store.delete_document_by_name(document_name)
    
    def list_documents(self):
        """Возвращает список всех документов в базе"""
        return self.vector_store.list_documents()
    
    def query(
        self, 
        question: str, 
        n_results: int = None,
        return_full_context: bool = True
    ) -> Dict:
        """Выполняет запрос к RAG системе"""
        if n_results is None:
            n_results = self.config.retrieval.n_results
        
        # Поиск релевантных чанков
        results = self.query_processor.search(question, n_results=n_results)
        
        if not results:
            return {
                "question": question,
                "answer": "К сожалению, не найдено релевантной информации.",
                "sources": [],
                "similarity_scores": []
            }
        
        # Форматирование результатов
        sources = []
        similarities = []
        
        for i, result in enumerate(results):
            similarity = result.get("similarity", 1.0 / (1.0 + result["distance"]))
            sources.append({
                "content": result["document"],
                "metadata": result.get("metadata", {}),
                "similarity": similarity,
                "rank": i + 1
            })
            similarities.append(similarity)

        if return_full_context and len(sources) > 0:
            context_parts = [src["content"] for src in sources[:3]]
            answer = "\n\n".join(context_parts)
        else:
            answer = sources[0]["content"] if sources else ""
        
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "similarity_scores": similarities,
            "avg_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
            "num_results": len(results)
        }
    
    def format_response(self, result: Dict, show_sources: bool = True) -> str:
        """Форматирует ответ для пользователя"""
        output = f"Ответ LLM: {result['llm_answer']}\n\n"
        output += f"Вопрос: {result['question']}\n\n"
        output += f"Ответ:\n{result['answer']}\n\n"
        output += "-" * 80
        
        if show_sources and result['sources']:
            output += f"\n\nИсточники (релевантность: {result['avg_similarity']:.3f}):\n"
            for i, source in enumerate(result['sources'][:3], 1):
                output += f"\n{i}. Релевантность: {source['similarity']:.3f}\n"
                output += f"   {source['content'][:200]}...\n"
        
        return output



