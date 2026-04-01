# 🚀 AutoPost Sync — кросспостинг между Telegram, VK и MAX

**AutoPost Sync** — это self-hosted сервис для автоматического кросспостинга между платформами, типа https://crosslybot.ru/:

* Telegram (через Telethon)
* VK (через vkbottle)
* MAX (через официальный API)

Поддерживает:

* матрицу синхронизации (любая платформа → любая)
* фильтрацию контента (текст, фото, видео, аудио, репосты)
* очередь доставки с retry и backoff
* обработку больших медиа
* Web GUI для управления
* хранение настроек в БД (единый источник истины)

---

# 🔥 Основные возможности

### 📡 Кросспостинг

* Telegram → VK / MAX
* VK → Telegram / MAX
* MAX → Telegram / VK

### 🧠 Гибкая логика

* матрица синхронизации
* правила по типу контента
* режимы обработки репостов

### ⚙️ Надёжность

* очередь задач на PostgreSQL
* retry policy (rate limit, timeout, media not ready)
* heartbeat для долгих upload-задач
* dead-letter очередь

### 🌐 Web интерфейс

* настройка платформ
* управление маршрутами
* просмотр очереди
* статусы постов

### 🔐 Безопасность

* все токены шифруются в БД
* ключ хранится в `.env`

---

# 📦 Установка

## 1. Клонировать проект

```bash
git clone https://github.com/your-repo/autopost-sync.git
cd autopost-sync
```

---

## 2. Установить зависимости

```bash
pip install -e .
```

---

## 3. Настроить `.env`

Создать файл:

```bash
cp .env.example .env
```

Минимально:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/autopost
SECRETS_ENCRYPTION_KEY=your-super-secret-key
APP_BASE_URL=http://localhost:8000
```

---

## 4. Запустить PostgreSQL

Через docker:

```bash
docker compose up -d db
```

---

## 5. Применить миграции

```bash
alembic upgrade head
```

---

## 6. Запустить приложение

```bash
uvicorn app.main:app --reload
```

---

## 7. Открыть Web GUI

👉 [http://localhost:8000](http://localhost:8000)

---

# ⚙️ Настройка платформ

Теперь **ВСЕ настройки делаются через Web GUI**, а не через `.env`.

## Telegram

Нужно:

* `api_id`
* `api_hash`
* либо `string_session`
* либо `bot_token`

## VK

Нужно:

* `group_id`
* `token`
* `confirmation_token`
* `secret`

## MAX

Нужно:

* `token`
* `webhook_url`
* `secret`

---

# 🔁 Как работает синхронизация

## 1. Приходит событие

* Telegram (Telethon)
* VK (Callback API)
* MAX (Webhook)

## 2. Преобразуется в UnifiedPost

## 3. Routing Engine:

* смотрит матрицу
* находит маршруты

## 4. Применяются правила:

* фильтрация контента
* обработка репостов

## 5. Пост попадает в очередь

## 6. Worker:

* берёт задачу (`SKIP LOCKED`)
* отправляет
* делает retry при ошибке

---

# 🧩 Структура проекта

```text
app/
├── adapters/        # Telegram / VK / MAX
├── services/        # бизнес-логика
├── repositories/    # работа с БД
├── api/             # REST API
├── workers/         # очередь и обработка
├── domain/          # модели
├── webui/           # frontend
```

---

# 🗄️ База данных

Основные таблицы:

* `platform_settings` — настройки платформ
* `routes` — маршруты каналов
* `sync_rules` — матрица синхронизации
* `delivery_jobs` — очередь задач
* `message_links` — связи сообщений
* `processed_events` — дедупликация

---

# 🧠 Очередь и retry

Используется PostgreSQL:

* `FOR UPDATE SKIP LOCKED`
* lease-модель
* heartbeat
* exponential backoff

Ошибки:

* `429 / rate limit`
* `attachment.not.ready`
* network timeout

---

# 🖥️ Web GUI

Разделы:

* **Overview** — статистика
* **Matrix** — правила платформ
* **Routes** — маршруты
* **Jobs** — очередь
* **Platform Settings** — настройки API

---

# 🔐 Безопасность

* токены шифруются через `Fernet`
* ключ хранится в `.env`
* секреты не возвращаются в UI

---

# ⚠️ Важно

* `.env` больше НЕ используется для платформ
* все настройки — только в БД
* после изменения настроек нужен restart

---

# 🧪 Тесты

```bash
pytest
```

---

# 🧭 Roadmap

* runtime reload без рестарта
* distributed workers
* media cache
* аналитика постов
* multi-user UI

---

# 💡 Использование

Примеры:

### Telegram → VK

* добавляешь маршрут
* включаешь правило
* пост автоматически дублируется

### VK → Telegram

* настраиваешь callback
* добавляешь маршрут
* всё работает

---

# 📌 Для кого это

* владельцы Telegram-каналов
* SMM
* медиа
* разработчики
* автоматизация контента

---

# 🏁 Итог

Это не “бот”, а **инфраструктура кросспостинга уровня сервиса**:

* расширяемая
* надёжная
* self-hosted
* без SaaS ограничений
