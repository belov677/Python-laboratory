# syntax=docker/dockerfile:1
# Один образ для API и фонового worker (разные команды запуска в docker-compose.yml).

FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/src
WORKDIR /srv
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --no-cache-dir --no-index /wheels/* \
    && useradd --create-home --uid 10001 app
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://localhost:8000/health', timeout=3).status != 200)"]
ENTRYPOINT ["entrypoint.sh"]
CMD ["api"]
