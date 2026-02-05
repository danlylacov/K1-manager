from typing import List, Dict
from RAG.rag.embedding_service import EmbeddingService
from RAG.rag.vector_store import VectorStore
from RAG.rag.reranker import Reranker
from RAG.rag.config import RetrievalConfig


class QueryProcessor:
    """Обработка запросов с использованием лучших практик RAG"""
    
    def __init__(
        self, 
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        reranker: Reranker = None,
        config: RetrievalConfig = None
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.reranker = reranker
        if config is None:
            from RAG.rag.config import DEFAULT_CONFIG
            config = DEFAULT_CONFIG.retrieval
        self.config = config
    
    def generate_query_variations(self, query: str, max_variations: int = 3) -> List[str]:
        """Генерирует варианты запроса для multi-query подхода"""
        variations = [query]
        
        words = query.split()
        if len(words) > 3:
            # Извлекаем ключевые слова (убираем стоп-слова)
            stop_words = {'что', 'какие', 'какое', 'как', 'где', 'когда', 'сколько', 'есть', 'ли'}
            key_words = [w for w in words if w.lower() not in stop_words]
            
            if len(key_words) >= 2:
                variations.append(' '.join(key_words[-3:]))
            
            if len(key_words) >= 3:
                variations.append(' '.join([key_words[0]] + key_words[-2:]))
        
        # Убираем дубликаты и ограничиваем количество
        unique_variations = []
        seen = set()
        for var in variations:
            var_lower = var.lower()
            if var_lower not in seen and len(var) > 3:
                unique_variations.append(var)
                seen.add(var_lower)
        
        return unique_variations[:max_variations]
    
    def multi_query_search(self, query: str, n_results: int = None) -> List[Dict]:
        """Multi-query поиск: объединяет результаты от разных вариантов запроса"""
        if n_results is None:
            n_results = self.config.n_results
        
        if not self.config.use_multi_query:
            query_embedding = self.embedding_service.encode_query(query)
            results = self.vector_store.search(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results
            )
            return self._format_search_results(results)
        
        # Multi-query поиск
        query_variations = self.generate_query_variations(query)
        all_results = []
        seen_docs = set()
        
        # Ищем по каждому варианту запроса
        for variation in query_variations:
            query_embedding = self.embedding_service.encode_query(variation)
            var_results = self.vector_store.search(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results * 2  # Берем больше для объединения
            )
            
            # Добавляем результаты, избегая дубликатов
            for i, doc in enumerate(var_results["documents"][0]):
                doc_hash = hash(doc[:100])
                if doc_hash not in seen_docs:
                    all_results.append({
                        "document": doc,
                        "metadata": var_results["metadatas"][0][i],
                        "distance": var_results["distances"][0][i],
                        "query_variation": variation,
                    })
                    seen_docs.add(doc_hash)
        
        # Re-ranking для объединения результатов
        if self.reranker and len(all_results) > 1:
            documents = [r["document"] for r in all_results]
            distances = [r["distance"] for r in all_results]
            
            reranked = self.reranker.rerank(
                query,
                documents,
                distances,
                top_k=n_results
            )
            
            # Обновляем результаты с новыми similarity
            for i, rerank_result in enumerate(reranked):
                orig_result = all_results[rerank_result["rank"]]
                orig_result["similarity"] = rerank_result["similarity"]
                orig_result["reranked"] = True
            all_results.sort(key=lambda x: x.get("similarity", 1.0 / (1.0 + x["distance"])), reverse=True)
        else:
            all_results.sort(key=lambda x: x["distance"])

        return all_results[:n_results]
    
    def _format_search_results(self, results: Dict) -> List[Dict]:
        """Форматирует результаты поиска"""
        formatted = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            similarity = 1.0 / (1.0 + distance)
            formatted.append({
                "document": doc,
                "metadata": metadata,
                "distance": distance,
                "similarity": similarity,
            })
        return formatted
    
    def search(self, query: str, n_results: int = None, use_reranking: bool = None) -> List[Dict]:
        """Основной метод поиска"""
        if n_results is None:
            n_results = self.config.n_results
        if use_reranking is None:
            use_reranking = self.config.use_reranking
        
        # Multi-query поиск
        results = self.multi_query_search(query, n_results * 2 if use_reranking else n_results)
        
        # Дополнительный re-ranking если включен
        if use_reranking and self.reranker and len(results) > 1:
            documents = [r["document"] for r in results]
            distances = [r["distance"] for r in results]
            
            reranked = self.reranker.rerank(
                query,
                documents,
                distances,
                top_k=self.config.rerank_top_k
            )

            reranked_map = {r["rank"]: r for r in reranked}
            for i, result in enumerate(results):
                if i in reranked_map:
                    result["similarity"] = reranked_map[i]["similarity"]
                    result["reranked"] = True
            
            # Пересортируем
            results.sort(key=lambda x: x.get("similarity", 1.0 / (1.0 + x["distance"])), reverse=True)
        
        # Фильтрация по порогу релевантности
        filtered_results = []
        for result in results:
            similarity = result.get("similarity", 1.0 / (1.0 + result["distance"]))
            if similarity >= self.config.min_similarity_threshold:
                filtered_results.append(result)
        
        return filtered_results[:n_results]

