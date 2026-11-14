FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8004

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

RUN useradd --create-home --uid 1000 app
USER app

EXPOSE 8004
CMD ["sh", "-c", "uvicorn main:app --host \"$HOST\" --port \"$PORT\""]
