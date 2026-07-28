# Бэкапы HireLens

Скрипт `hirelens-backup.sh` ежедневно сохраняет базу данных и все загруженные файлы
(фото кандидатов, резюме, видео интервью, логотипы, квитанции).

Копии лежат в `/root/backups`, хранятся 7 дней, старые удаляются автоматически.

## Установка (один раз)

```bash
cd /root/HireLens
chmod +x scripts/hirelens-backup.sh
```

Пробный запуск вручную:

```bash
/root/HireLens/scripts/hirelens-backup.sh
```

Должен появиться вывод со строками «база: ...» и «файлы: ...».

## Автозапуск каждую ночь в 03:30

```bash
crontab -e
```

Добавить строку:

```
30 3 * * * /root/HireLens/scripts/hirelens-backup.sh >> /root/backups/cron.log 2>&1
```

Проверить, что задание встало:

```bash
crontab -l
```

## Проверка, что бэкапы идут

```bash
ls -lh /root/backups
tail -20 /root/backups/backup.log
```

В каталоге должны накапливаться пары файлов `db_<дата>.sql.gz` и `uploads_<дата>.tar.gz`.

## Восстановление

### База данных

ВНИМАНИЕ: перезапишет текущие данные. Сначала сделайте свежий бэкап.

```bash
cd /root/HireLens
gunzip -c /root/backups/db_20260728_0330.sql.gz | docker compose exec -T db psql -U ai_hr_user -d ai_hr_db
```

### Файлы

```bash
cd /root/HireLens
VOLUME=$(docker volume ls --quiet | grep -m1 backend_uploads)
docker run --rm -v "$VOLUME":/dst -v /root/backups:/src:ro alpine:3.20 \
  tar xzf /src/uploads_20260728_0330.tar.gz -C /dst
docker compose restart backend
```

### Восстановить один файл

Посмотреть содержимое архива:

```bash
tar tzf /root/backups/uploads_20260728_0330.tar.gz | grep photos
```

Извлечь конкретный файл во временную папку:

```bash
tar xzf /root/backups/uploads_20260728_0330.tar.gz -C /tmp ./photos/93_ee91b5495e7f0529.png
```

## Важно

Копии лежат на том же сервере, что и боевые данные. Это спасает от ошибочного
удаления, сбоя миграции или потери файла, но не спасёт, если умрёт сам сервер.
Следующий шаг надёжности — копирование архивов во внешнее хранилище.
