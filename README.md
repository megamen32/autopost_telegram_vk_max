# AutoPost Sync

> **Синхронизируй посты между Telegram, VK и MAX одной командой**

[🇷🇺 Русский](#русский) | [🇬🇧 English](#english)

---

## 🇷🇺 Русский

### Что это?

**AutoPost Sync** — это сервис, который автоматически копирует посты между платформами:

- Напишешь пост в **Telegram** → он появится в **VK**
- Отправишь сообщение в **VK** → оно попадёт в **MAX**
- И всё в обе стороны одновременно

### Как это работает?

```
Telegram канал
    ↓
Правило: "Копировать в VK"
    ↓
Маршрут: "Этот канал → ту группу VK"
    ↓
VK группа (пост готов)
```

### Основные возможности

✅ **Поддерживаемые платформы:**
- Telegram (текст, фото, видео, документы)
- VK (посты, фото, видео)
- MAX (сообщения, медиа)

✅ **Основной функционал:**
- Автоматическая синхронизация постов
- Поддержка медиа (фото, видео, документы)
- Защита от дублей и циклов
- Задачи с автоматическими повторами
- Шифрование токенов в базе

✅ **Разработка:**
- REST API
- PostgreSQL хранилище
- Фоновый воркер для отправки
- Логирование и мониторинг

### Быстрый старт (5 минут)

```bash
# 1. Установи зависимости
git clone https://github.com/yourusername/autopost_sync.git
cd autopost_sync
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Запусти базу
docker compose up -d db

# 3. Инициализируй БД
alembic upgrade head

# 4. Запусти сервер
uvicorn app.main:app --reload
```

Готово! Открой http://127.0.0.1:8000/docs

### Настройка первого адаптера

```bash
# Telegram
curl -X POST http://localhost:8000/api/adapter-instances \
  -H 'Content-Type: application/json' \
  -d '{
    "adapter_key": "telegram",
    "display_name": "Мой Telegram",
    "config": {"api_id": 12345678, "receive_updates": true},
    "secrets": {"api_hash": "your_hash", "bot_token": "your_token"}
  }'
```

### Где взять учётные данные?

**Telegram:**
- Перейди на https://my.telegram.org/apps
- Создай приложение
- Скопируй API ID и API Hash

**VK:**
- Перейди на https://vk.com/dev
- Создай приложение
- Скопируй ID приложения

**MAX:**
- Перейди на https://max.im
- Создай бота
- Скопируй токен бота

### Примеры использования

**Создать синхронизацию Telegram → VK:**

```bash
# 1. Создай правило
curl -X POST http://localhost:8000/api/sync-rules \
  -H 'Content-Type: application/json' \
  -d '{
    "source_platform": "telegram",
    "target_platform": "vk",
    "enabled": true,
    "content_policy": {
      "allow_text": true,
      "allow_images": true,
      "allow_video": true
    },
    "copy_text_template": "{text}"
  }'

# 2. Создай маршрут (привяжи конкретный канал к конкретной группе)
curl -X POST http://localhost:8000/api/routes \
  -H 'Content-Type: application/json' \
  -d '{
    "source_adapter_instance_id": "telegram-main",
    "source_chat_id": "123456789",
    "target_adapter_instance_id": "vk-main",
    "target_chat_id": "237416141",
    "enabled": true
  }'
```

Готово! Теперь все посты из Telegram-канала будут автоматически публиковаться в VK-группе.

### Структура проекта

```
autopost_sync/
├── app/
│   ├── adapters/           # Интеграции с платформами
│   │   ├── telegram/       # Telegram (Telethon)
│   │   ├── vk/             # VK (VK API)
│   │   └── max/            # MAX (MAX Bot API)
│   ├── api/                # REST API endpoints
│   ├── db/                 # Модели базы данных
│   ├── domain/             # Доменные модели
│   ├── repositories/       # Работа с БД
│   ├── services/           # Бизнес-логика
│   └── workers/            # Фоновые задачи
├── docs/                   # Подробная документация
├── tests/                  # Тесты
└── docker-compose.yml      # PostgreSQL для разработки
```

### Полная документация

- 📖 [Установка и настройка](docs/INSTALLATION.md)
- 🏗️ [Архитектура системы](docs/ARCHITECTURE.md)
- 🔌 [Как работают адаптеры](docs/CONTRIBUTING.md#adding-a-new-adapter)
- 📡 [REST API справочник](docs/API.md)
- 🚀 [Быстрый старт](docs/QUICKSTART.md)
- 💡 [FAQ и примеры](docs/README.md)

Для расширенной настройки каждой платформы смотри:
- [Telegram адаптер](app/adapters/telegram/README.md)
- [VK адаптер](app/adapters/vk/README.md)
- [MAX адаптер](app/adapters/max/README.md)

### Требования

- Python 3.11+
- PostgreSQL 12+
- Docker (опционально)

### Лицензия

MIT License

---

## 🇬🇧 English

### What is this?

**AutoPost Sync** is a service that automatically copies posts between platforms:

- Write a post in **Telegram** → it appears in **VK**
- Send a message in **VK** → it goes to **MAX**
- Works in both directions simultaneously

### How it works

```
Telegram channel
    ↓
Rule: "Copy to VK"
    ↓
Route: "This channel → that VK group"
    ↓
VK group (post ready)
```

### Key Features

✅ **Supported platforms:**
- Telegram (text, photos, videos, documents)
- VK (posts, photos, videos)
- MAX (messages, media)

✅ **Core functionality:**
- Automatic post synchronization
- Media support (photos, videos, documents)
- Duplicate and loop protection
- Automatic retry with backoff
- Encrypted token storage

✅ **For developers:**
- REST API
- PostgreSQL storage
- Background worker
- Logging and monitoring

### Quick Start (5 minutes)

```bash
# 1. Install dependencies
git clone https://github.com/yourusername/autopost_sync.git
cd autopost_sync
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Start database
docker compose up -d db

# 3. Initialize database
alembic upgrade head

# 4. Start server
uvicorn app.main:app --reload
```

Done! Open http://127.0.0.1:8000/docs

### Configure First Adapter

```bash
# Telegram
curl -X POST http://localhost:8000/api/adapter-instances \
  -H 'Content-Type: application/json' \
  -d '{
    "adapter_key": "telegram",
    "display_name": "My Telegram",
    "config": {"api_id": 12345678, "receive_updates": true},
    "secrets": {"api_hash": "your_hash", "bot_token": "your_token"}
  }'
```

### Where to get credentials?

**Telegram:**
- Go to https://my.telegram.org/apps
- Create an app
- Copy API ID and API Hash

**VK:**
- Go to https://vk.com/dev
- Create an app
- Copy App ID

**MAX:**
- Go to https://max.im
- Create a bot
- Copy bot token

### Usage Examples

**Sync Telegram → VK:**

```bash
# 1. Create sync rule
curl -X POST http://localhost:8000/api/sync-rules \
  -H 'Content-Type: application/json' \
  -d '{
    "source_platform": "telegram",
    "target_platform": "vk",
    "enabled": true,
    "content_policy": {
      "allow_text": true,
      "allow_images": true,
      "allow_video": true
    },
    "copy_text_template": "{text}"
  }'

# 2. Create route (bind specific channel to group)
curl -X POST http://localhost:8000/api/routes \
  -H 'Content-Type: application/json' \
  -d '{
    "source_adapter_instance_id": "telegram-main",
    "source_chat_id": "123456789",
    "target_adapter_instance_id": "vk-main",
    "target_chat_id": "237416141",
    "enabled": true
  }'
```

Done! All posts from Telegram channel will be automatically published to VK group.

### Project Structure

```
autopost_sync/
├── app/
│   ├── adapters/           # Platform integrations
│   │   ├── telegram/       # Telegram (Telethon)
│   │   ├── vk/             # VK (VK API)
│   │   └── max/            # MAX (MAX Bot API)
│   ├── api/                # REST API endpoints
│   ├── db/                 # Database models
│   ├── domain/             # Domain models
│   ├── repositories/       # Database access
│   ├── services/           # Business logic
│   └── workers/            # Background jobs
├── docs/                   # Detailed documentation
├── tests/                  # Tests
└── docker-compose.yml      # PostgreSQL for development
```

### Full Documentation

- 📖 [Installation & Setup](docs/INSTALLATION.md)
- 🏗️ [System Architecture](docs/ARCHITECTURE.md)
- 🔌 [How Adapters Work](docs/CONTRIBUTING.md#adding-a-new-adapter)
- 📡 [REST API Reference](docs/API.md)
- 🚀 [Quick Start](docs/QUICKSTART.md)
- 💡 [FAQ & Examples](docs/README.md)

For platform-specific setup:
- [Telegram Adapter](app/adapters/telegram/README.md)
- [VK Adapter](app/adapters/vk/README.md)
- [MAX Adapter](app/adapters/max/README.md)

### Requirements

- Python 3.11+
- PostgreSQL 12+
- Docker (optional)

### License

MIT License
