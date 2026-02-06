from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from RAG.rag.config import EmbeddingConfig
import gc
import os

class EmbeddingService:
    """Сервис для создания эмбеддингов"""
    
    def __init__(self, config: EmbeddingConfig = None):
        if config is None:
            from RAG.rag.config import DEFAULT_CONFIG
            config = DEFAULT_CONFIG.embedding
        
        self.config = config
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Ленивая загрузка модели с оптимизацией для CPU"""
        if self._model is None:
            os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
            os.environ['HF_HUB_DISABLE_EXPERIMENTAL_WARNING'] = '1'
            os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
            os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

            # Определяем путь к кэшу моделей из переменной окружения
            cache_dir = os.getenv('HF_HOME', '/app/data/models')
            
            print(f"Загрузка модели {self.config.model_name}...")
            print(f"Используется кэш: {cache_dir}")
            self._model = SentenceTransformer(
                self.config.model_name,
                device="cpu",
                cache_folder=cache_dir
            )


            try:
                from pathlib import Path
                cache_dir = os.getenv('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
                model_cache = Path(cache_dir) / "hub" / f"models--{self.config.model_name.replace('/', '--')}"
                
                if model_cache.exists():
                    deleted_count = 0
                    # Удаляем ONNX файлы
                    for onnx_file in model_cache.rglob("*.onnx"):
                        try:
                            onnx_file.unlink()
                            deleted_count += 1
                        except:
                            pass
                    # Удаляем OpenVINO файлы
                    for openvino_file in model_cache.rglob("*openvino*"):
                        try:
                            if openvino_file.is_file():
                                openvino_file.unlink()
                                deleted_count += 1
                        except:
                            pass
                    # Удаляем quantized файлы
                    for quant_file in model_cache.rglob("*quantized*"):
                        try:
                            if quant_file.is_file():
                                quant_file.unlink()
                                deleted_count += 1
                        except:
                            pass
                    if deleted_count > 0:
                        print(f"Удалено {deleted_count} оптимизированных файлов (ONNX/OpenVINO) из кэша")
            except Exception as cleanup_error:
                print(f"Не удалось очистить оптимизированные файлы: {cleanup_error}")
            
            # Оптимизация модели для CPU
            if hasattr(self._model, 'eval'):
                self._model.eval()
        return self._model
    
    def encode(
        self, 
        texts: List[str], 
        normalize: bool = None,
        batch_size: int = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """Создает эмбеддинги для списка текстов"""
        if normalize is None:
            normalize = self.config.normalize_embeddings
        if batch_size is None:
            batch_size = self.config.batch_size
        
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_query(self, query: str) -> np.ndarray:
        """Создает эмбеддинг для запроса"""
        return self.encode([query], show_progress=False)[0]
    
    def encode_batch(self, texts: List[str], batch_size: int = None) -> np.ndarray:
        """Создает эмбеддинги батчами для больших объемов данных с оптимизацией памяти"""
        if batch_size is None:
            batch_size = self.config.batch_size
        
        # Уменьшаем batch_size если тексты очень длинные
        avg_length = sum(len(t) for t in texts[:min(10, len(texts))]) / min(10, len(texts))
        if avg_length > 1000:
            batch_size = max(4, batch_size // 2)
        
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch, show_progress=False)
            all_embeddings.append(batch_embeddings)

            # Более агрессивная очистка памяти для ограниченных ресурсов
            if i % (batch_size * 2) == 0:
                gc.collect()
        
        result = np.vstack(all_embeddings) if len(all_embeddings) > 1 else all_embeddings[0]
        # Финальная очистка
        del all_embeddings
        gc.collect()
        return result
    
    def clear_cache(self):
        """Очищает кэш модели"""
        if self._model is not None:
            del self._model
            self._model = None
        gc.collect()

