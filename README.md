# autopost_sync alpha

Альфа-версия сервиса синхронизации постов между платформами через единый внутренний формат `UnifiedPost`.

## Что есть в этой версии

- FastAPI webhook endpoint: `POST /webhooks/{platform}`
- единый доменный формат сообщений
- матрица синхронизации через `SyncRule`
- маршруты между конкретными каналами через `Route`
- фильтры по типам контента: текст, изображения, видео, аудио, документы, репосты
- защита от дублей
- защита от циклов через trace/path
- in-memory репозитории для быстрого старта
- заглушки адаптеров `telegram`, `vk`, `max`
- CRUD API для правил и маршрутов

## Чего пока нет

- реальные интеграции с Telegram/VK/MAX API
- постоянное хранилище PostgreSQL
- очередь задач
- синхронизация edit/delete
- полноценная работа с файлами и загрузкой медиа
- аутентификация вебхуков

## Быстрый запуск

```bash
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

## Структура

См. код в `app/`.

## Дальше

1. заменить in-memory репозитории на PostgreSQL;
2. реализовать реальные клиенты платформ;
3. добавить очередь доставки и retry;
4. добавить edit/delete sync;
5. добавить UI для матрицы и маршрутов.
