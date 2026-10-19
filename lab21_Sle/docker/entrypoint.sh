#!/bin/sh
# api: миграции БД и запуск веб-сервера; worker: обработчик событий.
set -e
case "$1" in
  api)
    alembic upgrade head
    exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000 --proxy-headers ;;
  worker)
    exec python -m app.worker ;;
  *)
    exec "$@" ;;
esac
