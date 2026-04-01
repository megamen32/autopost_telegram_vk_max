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
- реальный `TelegramAdapter` на Telethon + заглушки `vk`, `max`

## Чего пока нет

- реальные интеграции с VK/MAX API
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


## Telegram через Telethon

В этой версии Telegram переведён с заглушки на реальный адаптер Telethon.
Поддерживается:

- авторизация через `TELEGRAM_STRING_SESSION`
- авторизация через `TELEGRAM_BOT_TOKEN`
- отправка текста
- отправка фото
- отправка видео
- приём новых сообщений через Telethon updates

### Переменные окружения

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_STRING_SESSION=
TELEGRAM_BOT_TOKEN=
TELEGRAM_SESSION_NAME=autopost_sync
TELEGRAM_RECEIVE_UPDATES=true
TELEGRAM_SEQUENTIAL_UPDATES=false
TELEGRAM_ALLOWED_SOURCE_CHAT_IDS=[]
```

Нужно задать `TELEGRAM_API_ID` и `TELEGRAM_API_HASH`, а затем либо `TELEGRAM_STRING_SESSION`, либо `TELEGRAM_BOT_TOKEN`.

### Замечания

- если Telegram не настроен, адаптер мягко отключается и приложение всё равно стартует;
- входящие сообщения принимаются не через HTTP webhook, а через Telethon updates;
- ручной `POST /webhooks/telegram` сохранён для тестов и отладки.


## VK callback configuration

Set `VK_TOKEN`, `VK_GROUP_ID`, and optionally `VK_CONFIRMATION_TOKEN` / `VK_SECRET`.
VK webhook endpoint: `/webhooks/vk`.
Supported incoming callback types in this build: `message_new`, `wall_post_new`, and `confirmation`.
Publishing currently supports text and photo uploads to community wall; video/audio/document media fall back to links where possible.


## MAX adapter

The project now includes a real MAX adapter based on the official MAX Bot API. It can receive `message_created` webhook updates, validate the `X-Max-Bot-Api-Secret` header, send text messages, and upload image/video/audio/file attachments through `/uploads` followed by `/messages`. MAX recommends webhook delivery for production, requires HTTPS on port 443, and supports up to 30 requests per second. If sending immediately after upload fails with `attachment.not.ready`, the adapter includes a short delay and can fall back to text with media links.


## Delivery queue and retry

This version includes a database-backed `delivery_jobs` queue and a background worker. Sync ingestion enqueues outgoing deliveries instead of sending media inline. The worker retries transient media failures such as MAX `attachment.not.ready`, rate limits, timeouts, and temporary upload processing with exponential backoff.


## Production queue

- PostgreSQL row locking via `FOR UPDATE SKIP LOCKED` when the dialect is PostgreSQL
- lease-based job acquisition with `lock_token` and `lock_expires_at`
- dead-letter state: `dead_letter`
- platform-specific retry classifiers for Telegram, VK, and MAX


## Queue heartbeat

For long media uploads, the worker now periodically extends the PostgreSQL lease while the job is still running. Configure it with `DELIVERY_JOB_HEARTBEAT_INTERVAL_SECONDS`.


## Single source of truth

Telegram, VK and MAX platform settings are stored only in the database and edited through the Web GUI.
Environment variables are reserved for infrastructure settings such as `DATABASE_URL`, `SECRETS_ENCRYPTION_KEY` and worker tuning.
