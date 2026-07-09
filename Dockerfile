FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CHROMIUM_BIN=/usr/bin/chromium

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-noto \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8787

CMD ["python3", "server/backend.py", "--host", "0.0.0.0", "--port", "8787", "--refresh", "300"]
