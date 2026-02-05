FROM python:3.11-slim

WORKDIR /app

COPY telegram_bot/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY telegram_bot/ ./telegram_bot/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["python", "telegram_bot/bot.py"]

