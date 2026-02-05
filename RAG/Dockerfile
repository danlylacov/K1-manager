# Multi-stage build для уменьшения размера образа
FROM python:3.11-slim as builder

# Устанавливаем только необходимые инструменты для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements
COPY RAG/requirements.txt .

# Устанавливаем зависимости (включая CPU версию PyTorch)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Финальный образ без build-essential
FROM python:3.11-slim

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения
COPY RAG/ ./RAG/

# Создаем директории для данных
RUN mkdir -p /app/data/chroma_db /app/data/models /tmp

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/data/models \
    CHROMA_DB_PATH=/app/data/chroma_db \
    TRANSFORMERS_OFFLINE=0 \
    HF_HUB_DISABLE_EXPERIMENTAL_WARNING=1 \
    ONNXRUNTIME_DISABLE_OPTIMIZATION=1

# Порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "RAG.api.rag_api:app", "--host", "0.0.0.0", "--port", "8000"]

