from pathlib import Path
from typing import Dict, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from RAG.rag.config import ChunkingConfig
from markitdown import MarkItDown

md_converter = MarkItDown()


def document_to_markdown(document_path: str) -> Dict[str, str]:
    """Конвертирует документ в markdown текст"""
    try:
        result = md_converter.convert(document_path)
        content = result.text_content
    except Exception as e:
        raise ValueError(f"Ошибка при чтении документа {document_path}: {e}")

    return {
        'source': document_path,
        'content': content
    }


def split_document(document: Dict[str, str], config: ChunkingConfig = None) -> List[Dict[str, str]]:
    """Разбивает документ на чанки с метаданными"""
    if config is None:
        from RAG.rag.config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.chunking

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=config.separators,
        length_function=len,
    )

    doc_chunks = text_splitter.split_text(document["content"])

    chunks = []
    for i, chunk_text in enumerate(doc_chunks):
        chunk = {
            "content": chunk_text,
            "source": document["source"],
            "chunk_id": i,
            "metadata": {
                "chunk_index": i,
                "total_chunks": len(doc_chunks),
                "document_name": Path(document["source"]).name,
                "chunk_length": len(chunk_text),
            }
        }
        chunks.append(chunk)

    return chunks
