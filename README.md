# AutoPost Sync

> **Автоматически копируй посты между Telegram, VK и MAX через удобный интерфейс**

![GitHub License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)

[🇷🇺 Русский](#русский) | [🇬🇧 English](#english)

---

## 🇷🇺 Русский

### 💡 Что это?

**AutoPost Sync** — это приложение для автоматической синхронизации постов между социальными платформами.

**Примеры использования:**

📱 **Для контент-мейкеров:**
- Опубликовал пост в Telegram → он сам появится в VK и MAX
- Экономишь время на ручное копирование постов
- Один контент — все платформы сразу

📊 **Для сообществ:**
- Синхронизируй новости с основного канала на все соцсети
- Управляй всеми платформами с одного места
- Не пропусти ничего

🤖 **Для ботов:**
- Настрой бота один раз
- Он будет автоматически публиковать везде
- Никакого кода не нужно писать

### 🎯 Как это работает?

```
┌─────────────────┐
│  Твой пост в    │
│   Telegram      │
└────────┬────────┘
         │
    ↓ (автоматически)
         │
    ┌────▼────────────────────┐
    │  AutoPost настроил      │
    │  "Копировать в VK, MAX" │
    └────┬────────────────────┘
         │
    ├─→ VK группа
    ├─→ MAX чат
    └─→ Другие платформы
```

### ✨ Основные преимущества

✅ **Просто в использовании** — интуитивный веб-интерфейс, без команд  
✅ **Все платформы** — Telegram, VK, MAX в одном месте  
✅ **Автоматизация** — один раз настроил, потом работает само  
✅ **Медиа поддержка** — фото, видео, документы копируются автоматически  
✅ **Умная защита** — не создаёт дубли, блокирует циклы  
✅ **Безопасно** — все токены зашифрованы в базе  

### 🚀 Быстрый старт (2 команды)

```bash
# 1. Скачай проект
git clone https://github.com/yourusername/autopost_sync.git && cd autopost_sync

# 2. Запусти (Docker автоматически скачает всё нужное)
docker compose up
```

Готово! Открой в браузере: **http://localhost:8000**

### 📋 Настройка (3 шага в интерфейсе)

#### Шаг 1️⃣ Добавь Telegram

Открой http://localhost:8000 → кнопка "➕ Добавить адаптер" → выбери "Telegram"

В форме заполни:
- **Display Name:** "Мой Telegram" (просто имя для себя)
- **API ID:** твой номер
- **API Hash:** скопируй из кабинета
- **Bot Token:** (опционально) если хочешь бота

Где взять данные:
1. Перейди https://my.telegram.org/apps
2. Создай приложение
3. Скопируй **API ID** и **API Hash** в поле
4. (Опционально) Для бота добавь токен от @BotFather

#### Шаг 2️⃣ Добавь VK

Открой http://localhost:8000 → кнопка "➕ Добавить адаптер" → выбери "VK"

В форме заполни:
- **Display Name:** "Моя VK" (имя для себя)
- **VK Group ID:** ID твоей группы
- **VK ID Client ID:** для OAuth входа

Где взять данные:
1. Перейди https://vk.com/dev
2. Создай приложение
3. Скопируй ID приложения

#### Шаг 3️⃣ Создай синхронизацию

Открой http://localhost:8000 → кнопка "➕ Новое правило синхронизации"

Выбери:
- **Откуда:** Telegram (выбери инстанс "Мой Telegram")
- **Куда:** VK (выбери инстанс "Моя VK")
- **Контент:** поставь галочки что нужно:
  - ✅ Текст (всегда копируется)
  - ✅ Фото (загружаются в VK)
  - ✅ Видео (загружаются в VK)

Нажми **"Сохранить"** → готово!

Теперь все посты из Telegram будут автоматически публиковаться в VK! 🎉

### ⚠️ Важные ограничения платформ

**Telegram:**
- ✅ Полная поддержка
- Нужно API ID и API Hash (берётся в кабинете разработчика)

**VK:**
- ✅ Полная поддержка
- Нужна обычная ссылка на группу/сообщество
- Токен берётся из кабинета разработчика

**MAX:**
- ⚠️ **Важно:** Доступно только для юридических лиц (ИП, ООО и т.д.)
- Требуется быть резидентом РФ
- Нужно пройти верификацию в [dev.max.ru](https://dev.max.ru/docs/chatbots/bots-coding/prepare)
- Подробнее: https://dev.max.ru/docs/chatbots/bots-coding/prepare

### ❓ Частые вопросы

**Нужно ли мне быть программистом?**
Нет! Весь интерфейс — веб-приложение с кнопками и формами. Никакого кода писать не нужно.

**Что если я что-то неправильно настроил?**
Можешь всегда переделать в интерфейсе. Все настройки хранятся в базе и легко редактируются.

**Где мои токены и пароли?**
Все токены зашифрованы в базе данных. Никто их не видит и не сохраняет.

**Что будет если выключить сервер?**
Когда ты его снова включишь, он продолжит с того же места. Никакие посты не потеряются.

**Это бесплатно?**
Да, это Open Source проект под лицензией MIT.

### 📚 Полная документация

Нужна помощь? Смотри подробные гайды:

- 🚀 [Детальный гайд по установке](docs/INSTALLATION.md) — для разных ОС и серверов
- 🔌 [Гайд для каждой платформы](docs/README.md) — специфика Telegram, VK, MAX
- ❓ [FAQ и примеры](docs/README.md) — ответы на частые вопросы
- 👨‍💻 [Для разработчиков](docs/ARCHITECTURE.md) — как работает изнутри

Для расширенной настройки каждой платформы:
- [Telegram](app/adapters/telegram/README.md)
- [VK](app/adapters/vk/README.md)
- [MAX](app/adapters/max/README.md)

### 💻 Требования к серверу

- **Минимум:** 2GB RAM, 10GB дискового пространства
- **ОС:** Linux, macOS или Windows с Docker
- **Браузер:** Chrome, Firefox, Safari, Edge (любой современный)

### 📄 Лицензия

MIT License — используй как хочешь, даже в коммерческих целях.

---

## 🇬🇧 English

### 💡 What is this?

**AutoPost Sync** is an app for automatic synchronization of posts between social media platforms.

**Use cases:**

📱 **For content creators:**
- Post once in Telegram → it appears automatically in VK and MAX
- Save time on manual copying
- One content → all platforms at once

📊 **For communities:**
- Sync news from main channel to all social media
- Manage all platforms from one place
- Never miss anything

🤖 **For bots:**
- Set up bot once
- It will automatically publish everywhere
- No coding needed

### 🎯 How it works?

```
┌─────────────────┐
│  Your post in   │
│   Telegram      │
└────────┬────────┘
         │
    ↓ (automatically)
         │
    ┌────▼────────────────────┐
    │  AutoPost configured    │
    │  "Copy to VK, MAX"      │
    └────┬────────────────────┘
         │
    ├─→ VK group
    ├─→ MAX chat
    └─→ Other platforms
```

### ✨ Key Features

✅ **Easy to use** — web interface with buttons and forms, no commands  
✅ **All platforms** — Telegram, VK, MAX in one place  
✅ **Automation** — set once, it works by itself  
✅ **Media support** — photos, videos, documents copy automatically  
✅ **Smart protection** — no duplicates, blocks loops  
✅ **Secure** — all tokens encrypted in database  

### 🚀 Quick Start (2 commands)

```bash
# 1. Download the project
git clone https://github.com/yourusername/autopost_sync.git && cd autopost_sync

# 2. Run (Docker automatically downloads everything needed)
docker compose up
```

Done! Open in browser: **http://localhost:8000**

### 📋 Setup (3 steps in interface)

#### Step 1️⃣ Add Telegram

Open http://localhost:8000 → click "➕ Add adapter" → select "Telegram"

Fill in the form:
- **Display Name:** "My Telegram" (name for yourself)
- **API ID:** your number
- **API Hash:** copy from developer cabinet
- **Bot Token:** (optional) if you want a bot

Get credentials:
1. Go to https://my.telegram.org/apps
2. Create an app
3. Copy **API ID** and **API Hash**
4. (Optional) Add bot token from @BotFather

#### Step 2️⃣ Add VK

Open http://localhost:8000 → click "➕ Add adapter" → select "VK"

Fill in the form:
- **Display Name:** "My VK" (name for yourself)
- **VK Group ID:** your group ID
- **VK ID Client ID:** for OAuth login

Get credentials:
1. Go to https://vk.com/dev
2. Create an app
3. Copy App ID

#### Step 3️⃣ Create Sync Rule

Open http://localhost:8000 → click "➕ New sync rule"

Select:
- **From:** Telegram (select "My Telegram")
- **To:** VK (select "My VK")
- **Content:** check what you need:
  - ✅ Text (always copied)
  - ✅ Photos (uploaded to VK)
  - ✅ Videos (uploaded to VK)

Click **"Save"** → done!

Now all posts from Telegram automatically publish to VK! 🎉

### ⚠️ Platform Limitations

**Telegram:**
- ✅ Full support
- Need API ID and API Hash (from developer cabinet)

**VK:**
- ✅ Full support
- Need regular link to group/community
- Token from developer cabinet

**MAX:**
- ⚠️ **Important:** Available only for legal entities (LLC, self-employed, etc.)
- Must be a resident of Russia
- Verification required at [dev.max.ru](https://dev.max.ru/docs/chatbots/bots-coding/prepare)
- Details: https://dev.max.ru/docs/chatbots/bots-coding/prepare

### ❓ FAQ

**Do I need to be a programmer?**
No! The entire interface is a web app with buttons and forms. No coding required.

**What if I configure something wrong?**
You can always change it in the interface. All settings are stored in database and easily editable.

**Where are my tokens and passwords?**
All tokens are encrypted in the database. No one sees or stores them.

**What happens if I turn off the server?**
When you turn it back on, it continues from where it left off. No posts are lost.

**Is this free?**
Yes, it's an Open Source project under MIT license.

### 📚 Full Documentation

Need help? Check detailed guides:

- 🚀 [Detailed installation guide](docs/INSTALLATION.md) — for different OS and servers
- 🔌 [Guide for each platform](docs/README.md) — specifics for Telegram, VK, MAX
- ❓ [FAQ and examples](docs/README.md) — answers to common questions
- 👨‍💻 [For developers](docs/ARCHITECTURE.md) — how it works inside

For platform-specific setup:
- [Telegram](app/adapters/telegram/README.md)
- [VK](app/adapters/vk/README.md)
- [MAX](app/adapters/max/README.md)

### 💻 Server Requirements

- **Minimum:** 2GB RAM, 10GB disk space
- **OS:** Linux, macOS or Windows with Docker
- **Browser:** Chrome, Firefox, Safari, Edge (any modern)

### 📄 License

MIT License — use however you want, even commercially.
