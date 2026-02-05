from typing import List, Dict
import numpy as np


class Reranker:
    """Класс для re-ranking результатов поиска"""

    def __init__(self, embedding_service):
        self.embedding_service = embedding_service

    def rerank(
            self,
            query: str,
            documents: List[str],
            distances: List[float],
            top_k: int = None
    ) -> List[Dict]:
        """Переранжирует результаты по косинусному сходству"""
        if not documents:
            return []

        # Кодируем запрос и документы
        query_embedding = self.embedding_service.encode_query(query)
        doc_embeddings = self.embedding_service.encode(documents)

        # Преобразуем в numpy если нужно
        if not isinstance(query_embedding, np.ndarray):
            query_embedding = np.array(query_embedding)
        if not isinstance(doc_embeddings, np.ndarray):
            doc_embeddings = np.array(doc_embeddings)

        # Вычисляем косинусное сходство (используем numpy напрямую)
        # Нормализуем для косинусного сходства
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        doc_norms = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=1, keepdims=True) + 1e-8)
        similarities = np.dot(query_norm, doc_norms.T)

        if similarities.ndim > 1:
            similarities = similarities.flatten()

        # Создаем список результатов с пересчитанными similarity
        results = []
        for i, (doc, orig_distance, similarity) in enumerate(zip(documents, distances, similarities)):
            results.append({
                "document": doc,
                "original_distance": orig_distance,
                "similarity": float(similarity),
                "rank": i,
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Возвращаем топ результатов
        if top_k:
            results = results[:top_k]

        return results
