FROM python:3.11-slim

WORKDIR /app

COPY llm_service/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY llm_service/ ./llm_service/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "llm_service.main:app", "--host", "0.0.0.0", "--port", "8002"]

