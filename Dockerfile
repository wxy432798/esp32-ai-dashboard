FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY . .

EXPOSE 8787

CMD ["python3", "server/backend.py", "--host", "0.0.0.0", "--port", "8787", "--refresh", "300"]
