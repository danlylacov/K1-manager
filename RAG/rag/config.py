from dataclasses import dataclass
from typing import List

@dataclass
class ChunkingConfig:
    """Конфигурация разбиения текста на чанки"""
    chunk_size: int = 500
    chunk_overlap: int = 100
    separators: List[str] = None
    
    def __post_init__(self):
        if self.separators is None:
            self.separators = ["\n\n", "\n", ". ", " ", ""]

@dataclass
class EmbeddingConfig:
    """Конфигурация модели эмбеддингов"""
    # Используем более легкую модель без ONNX версий для экономии места
    # all-MiniLM-L6-v2: ~80MB, быстрая, без ONNX оптимизаций
    # paraphrase-multilingual-mpnet-base-v2: ~420MB, лучше качество, но есть ONNX версии
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    normalize_embeddings: bool = True
    batch_size: int = 8  # Уменьшено с 32 для экономии памяти (2GB RAM)

@dataclass
class RetrievalConfig:
    """Конфигурация поиска"""
    n_results: int = 3
    use_reranking: bool = True
    rerank_top_k: int = 5  # Сколько результатов re-rank
    use_multi_query: bool = True
    min_similarity_threshold: float = 0.3  # Минимальный порог релевантности

@dataclass
class RAGConfig:
    """Общая конфигурация RAG системы"""
    chunking: ChunkingConfig = None
    embedding: EmbeddingConfig = None
    retrieval: RetrievalConfig = None
    
    def __post_init__(self):
        if self.chunking is None:
            self.chunking = ChunkingConfig()
        if self.embedding is None:
            self.embedding = EmbeddingConfig()
        if self.retrieval is None:
            self.retrieval = RetrievalConfig()


DEFAULT_CONFIG = RAGConfig()

