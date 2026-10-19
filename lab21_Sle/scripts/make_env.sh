#!/usr/bin/env bash
# Создаёт .env со случайными секретами (CI и первый запуск).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { echo ".env уже существует"; exit 0; }
cp .env.example .env
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 16)/" .env
sed -i "s/^RABBITMQ_PASSWORD=.*/RABBITMQ_PASSWORD=$(openssl rand -hex 16)/" .env
sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 32)/" .env
sed -i "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=Adm$(openssl rand -hex 6)/" .env
echo ".env создан (пароль диспетчера: $(grep ^ADMIN_PASSWORD .env | cut -d= -f2))"
