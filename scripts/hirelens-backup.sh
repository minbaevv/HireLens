#!/usr/bin/env bash
# HireLens: ежедневный бэкап базы данных и загруженных файлов.
#
# Что делает:
#   1. Снимает дамп PostgreSQL (pg_dump) и жмёт его gzip.
#   2. Архивирует том с загрузками (фото, резюме, видео интервью, логотипы).
#   3. Удаляет копии старше RETENTION_DAYS дней.
#   4. Пишет журнал в $BACKUP_DIR/backup.log.
#
# Установка описана в scripts/BACKUP-README.md

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/HireLens}"
BACKUP_DIR="${BACKUP_DIR:-/root/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_USER="${DB_USER:-ai_hr_user}"
DB_NAME="${DB_NAME:-ai_hr_db}"

STAMP="$(date +%Y%m%d_%H%M)"
LOG="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

fail() {
	log "ОШИБКА: $*"
	exit 1
}

cd "$PROJECT_DIR" || fail "нет каталога проекта $PROJECT_DIR"

log "=== старт бэкапа ==="

# ---------- 1. База данных ----------
DB_FILE="$BACKUP_DIR/db_${STAMP}.sql.gz"
if docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" 2>>"$LOG" | gzip -9 > "$DB_FILE"; then
	DB_SIZE=$(stat -c %s "$DB_FILE")
	# пустой или подозрительно маленький дамп считаем провалом
	if [ "$DB_SIZE" -lt 1024 ]; then
		rm -f "$DB_FILE"
		fail "дамп базы получился меньше 1 КБ — бэкап не сохранён"
	fi
	log "база: $(basename "$DB_FILE") ($(numfmt --to=iec "$DB_SIZE" 2>/dev/null || echo "$DB_SIZE B"))"
else
	rm -f "$DB_FILE"
	fail "pg_dump не отработал"
fi

# ---------- 2. Загруженные файлы ----------
# Имя тома определяем автоматически: у compose оно вида <проект>_backend_uploads
VOLUME="$(docker volume ls --quiet | grep -m1 'backend_uploads' || true)"
[ -n "$VOLUME" ] || fail "не найден том backend_uploads"

FILES_FILE="$BACKUP_DIR/uploads_${STAMP}.tar.gz"
if docker run --rm \
	-v "$VOLUME":/src:ro \
	-v "$BACKUP_DIR":/dst \
	alpine:3.20 \
	tar czf "/dst/$(basename "$FILES_FILE")" -C /src . 2>>"$LOG"; then
	FILES_SIZE=$(stat -c %s "$FILES_FILE")
	FILES_COUNT=$(tar tzf "$FILES_FILE" | grep -c -v '/$' || true)
	log "файлы: $(basename "$FILES_FILE") ($(numfmt --to=iec "$FILES_SIZE" 2>/dev/null || echo "$FILES_SIZE B"), файлов: $FILES_COUNT, том: $VOLUME)"
else
	rm -f "$FILES_FILE"
	fail "не удалось заархивировать том $VOLUME"
fi

# ---------- 3. Чистка старых копий ----------
DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db_*.sql.gz' -o -name 'uploads_*.tar.gz' \) -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
log "удалено старых копий: $DELETED (хранение $RETENTION_DAYS дн.)"

# ---------- 4. Итог ----------
TOTAL=$(du -sh "$BACKUP_DIR" | cut -f1)
FREE=$(df -h "$BACKUP_DIR" | awk 'NR==2 {print $4}')
log "готово. занято бэкапами: $TOTAL, свободно на диске: $FREE"
log "=== конец бэкапа ==="
