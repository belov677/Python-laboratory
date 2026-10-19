# syntax=docker/dockerfile:1
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
# Необязательный секрет ca_bundle нужен только за прокси с собственным CA (учебная среда);
# в обычной среде он не передаётся, и pip использует системные сертификаты.
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip install --no-cache-dir aiogram "SQLAlchemy[asyncio]" aiosqlite redis
COPY bot ./bot
CMD ["python", "-m", "bot.main"]
