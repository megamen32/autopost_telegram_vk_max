# autopost_sync beta

Beta-версия сервиса синхронизации постов между платформами через единый внутренний формат `UnifiedPost`.

## Что появилось по сравнению с alpha

- PostgreSQL-ready хранилище через `SQLAlchemy Async`
- env-конфигурация через `pydantic-settings`
- таблицы `sync_rules`, `routes`, `processed_events`, `message_links`
- Alembic-конфигурация и первая миграция
- `docker-compose.yml` для локального PostgreSQL
- API теперь работает поверх постоянного хранилища, а не in-memory

## Что есть в этой версии

- FastAPI webhook endpoint: `POST /webhooks/{platform}`
- единый доменный формат сообщений
- матрица синхронизации через `SyncRule`
- маршруты между конкретными каналами через `Route`
- фильтры по типам контента: текст, изображения, видео, аудио, документы, репосты
- защита от дублей
- защита от циклов через trace/path
- CRUD API для правил и маршрутов
- заглушки адаптеров `telegram`, `vk`, `max`

## Чего пока нет

- реальные интеграции с Telegram/VK/MAX API
- очередь задач и retry
- синхронизация edit/delete
- полноценная загрузка медиа в целевые платформы
- аутентификация вебхуков
- UI

## Быстрый запуск через PostgreSQL

```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

## Быстрый запуск без Alembic

Если `AUTO_CREATE_TABLES=true`, приложение само создаст таблицы при старте:

```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

## Примеры

### Создать правило TG -> VK

```bash
curl -X POST http://127.0.0.1:8000/rules \
  -H 'Content-Type: application/json' \
  -d '{
    "source_platform": "telegram",
    "target_platform": "vk",
    "enabled": true,
    "content_policy": {
      "allow_text": true,
      "allow_images": true,
      "allow_video": true,
      "allow_audio": false,
      "allow_documents": false,
      "allow_reposts": false,
      "max_images": null,
      "max_video_size_mb": null,
      "max_audio_size_mb": null,
      "drop_unsupported_media": true
    },
    "repost_mode": "ignore",
    "copy_text_template": "{text}"
  }'
```

### Создать маршрут TG channel -> VK group

```bash
curl -X POST http://127.0.0.1:8000/routes \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "route-1",
    "source_platform": "telegram",
    "source_chat_id": "tg-channel-1",
    "target_platform": "vk",
    "target_chat_id": "vk-group-1",
    "enabled": true
  }'
```

### Послать тестовый webhook

```bash
curl -X POST http://127.0.0.1:8000/webhooks/telegram \
  -H 'Content-Type: application/json' \
  -d '{
    "chat_id": "tg-channel-1",
    "message_id": "100",
    "text": "Привет из Telegram",
    "media": [
      {"type": "image", "url": "https://example.com/image.jpg"}
    ],
    "is_repost": false
  }'
```

### Проверить созданные связи сообщений

```bash
curl http://127.0.0.1:8000/debug/message-links
```

## Следующие шаги для gamma

1. реальные publisher/client слои для Telegram, VK и MAX;
2. retry-очередь и rate limiting;
3. синхронизация edit/delete;
4. хранение токенов/аккаунтов платформ;
5. UI для матрицы и маршрутов.
