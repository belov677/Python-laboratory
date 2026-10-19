#!/usr/bin/env bash
# Локальный прогон этапов .github/workflows/lab21-ci.yml; ошибка этапа останавливает pipeline.
cd "$(dirname "$0")"
set -a; source ./.env; set +a
export COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}

stage() {
  local name=$1; shift; local t=$SECONDS
  echo; echo "▶ STAGE: $name"
  if "$@"; then echo "✔ $name — успешно ($((SECONDS - t)) с)"; else echo "✘ $name — ОШИБКА, pipeline остановлен"; exit 1; fi
}
install()  { pip install -q -r requirements-dev.txt 2>&1 | grep -vi warning || true; }
lint()     { ruff check . && ruff format --check .; }
tests()    { python3 -m pytest -q -p no:logging --cov --cov-report=term --cov-fail-under=85 2>&1 | grep -E "TOTAL|Required|passed|failed|FAILED"; return "${PIPESTATUS[0]}"; }
migrations() {
  local url=$TEST_DATABASE_URL
  PGPASSWORD=$POSTGRES_PASSWORD psql -q -h localhost -U logistics_app -d logistics_final_test \
      -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null
  DATABASE_URL=$url alembic -q upgrade head && DATABASE_URL=$url alembic check && DATABASE_URL=$url alembic -q downgrade base
}
build()    { docker compose build 2>&1 | grep -E "Built|ERROR"; return "${PIPESTATUS[0]}"; }
smoke()    { docker compose up -d --wait 2>&1 | tail -1 && docker compose ps --format "table {{.Service}}\t{{.Status}}" && python3 scripts/smoke_test.py; }

stage "Install" install
stage "Lint (ruff + bandit)" lint
stage "Tests + coverage ≥ 85%" tests
stage "Migrations (alembic upgrade/check/downgrade)" migrations
stage "Docker build" build
stage "Smoke test (docker compose)" smoke
echo; echo "PIPELINE: SUCCESS"
