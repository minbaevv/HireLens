#!/usr/bin/env bash
# HireLens: закрытие брошенных интервью.
# Запускается из cron каждые 15 минут.
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/HireLens}"

cd "$PROJECT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] проверка брошенных интервью"

if ! docker compose ps --status running --services 2>/dev/null | grep -qx backend; then
	echo "бэкенд не запущен — пропускаем прогон"
	exit 0
fi

docker compose exec -T backend python -m app.scripts.close_abandoned_interviews
