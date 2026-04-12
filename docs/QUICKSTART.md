# Quick Start Guide

Get up and running with AutoPost Sync in 5 minutes.

## Prerequisites

- Python 3.11+ 
- PostgreSQL (or Docker)
- Git

## Install & Run (5 minutes)

### 1. Clone & Setup (2 min)

```bash
git clone https://github.com/yourusername/autopost_sync.git
cd autopost_sync
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Start Database (1 min)

```bash
docker compose up -d db
sleep 2  # wait for database
```

### 3. Configure & Run (2 min)

```bash
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Open browser: **http://127.0.0.1:8000/docs**

## Configure Your First Adapter (2 min)

### Option A: Via Web UI

1. Open http://127.0.0.1:8000/docs
2. Expand `POST /api/adapter-instances`
3. Click "Try it out"
4. Copy this JSON and paste:

```json
{
  "adapter_key": "telegram",
  "display_name": "My Telegram",
  "config": {
    "api_id": 12345678,
    "receive_updates": true
  },
  "secrets": {
    "api_hash": "your_api_hash_here",
    "bot_token": "your_bot_token_here"
  }
}
```

5. Click "Execute"
6. Wait for success (201 response)

### Option B: Via curl

```bash
curl -X POST http://localhost:8000/api/adapter-instances \
  -H 'Content-Type: application/json' \
  -d '{
    "adapter_key": "telegram",
    "display_name": "My Telegram",
    "config": {"api_id": 12345678, "receive_updates": true},
    "secrets": {"api_hash": "your_api_hash", "bot_token": "your_bot_token"}
  }'
```

## Where to Get Credentials

### Telegram

1. Go to https://my.telegram.org/apps
2. Create an app
3. Copy **API ID** and **API Hash**
4. (Optional) For bot: create bot at @BotFather, copy token

### VK

1. Go to https://vk.com/dev (create app)
2. Copy **App ID** as group token
3. (Optional) For user posting: go to https://id.vk.com, create/select app, copy **Client ID**

### MAX

1. Go to https://max.im and create bot
2. Copy bot **Token** (starts with `bot_`)

## Create a Sync Rule (1 min)

Send a message from Telegram to VK:

```bash
# Create rule
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
    "copy_text_template": "{text}\n#crosspost"
  }'

# Create route
curl -X POST http://localhost:8000/api/routes \
  -H 'Content-Type: application/json' \
  -d '{
    "source_adapter_instance_id": "my-telegram",
    "source_chat_id": "your_channel_id",
    "target_adapter_instance_id": "my-vk",
    "target_chat_id": "vk_group_id",
    "enabled": true
  }'
```

## Test It

```bash
# Send test message
curl -X POST http://localhost:8000/webhooks/my-telegram \
  -H 'Content-Type: application/json' \
  -d '{
    "chat_id": "your_channel_id",
    "message_id": "1",
    "text": "Hello from Telegram!",
    "media": []
  }'

# Check if it worked
curl http://localhost:8000/api/delivery-jobs
```

Look for status "completed" with result_post_id.

## Next Steps

- **Add more adapters** — Follow same pattern for VK, MAX
- **Explore API docs** — http://localhost:8000/docs
- **Read full docs** — See [docs/README.md](./README.md)
- **Production setup** — See [INSTALLATION.md](./INSTALLATION.md)
- **Troubleshooting** — See adapter-specific READMEs

## Common Commands

```bash
# Start app
uvicorn app.main:app --reload

# Start background worker (in another terminal)
python -m app.workers.delivery_worker

# Run tests
pytest tests/ -v

# Format code
black . && isort .

# Database migrations
alembic upgrade head
alembic downgrade -1

# List adapters
curl http://localhost:8000/api/adapter-instances | jq .

# Check job queue
curl http://localhost:8000/api/debug/delivery-jobs | jq .
```

## Troubleshooting

### "Could not connect to database"
```bash
# Check if PostgreSQL is running
docker compose ps db
docker compose logs db
```

### "Module not found: uvicorn"
```bash
# Activate venv
source .venv/bin/activate
pip install -e .
```

### "Port 8000 already in use"
```bash
# Use different port
uvicorn app.main:app --port 8001
```

### "SECRETS_ENCRYPTION_KEY not set"
```bash
# Generate and add to .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Chat IDs

How to find chat IDs:

**Telegram:**
- Channel: positive number (e.g., `123456789`)
- Group: negative number (e.g., `-987654321`)
- Direct: positive number

**VK:**
- Group: positive number without minus (e.g., `237416141`)
- Chat: positive number (e.g., `2000000123`)

**MAX:**
- Usually starts with `chat_` (e.g., `chat_123`)

## API Quick Reference

```bash
# List adapters
GET /api/adapter-instances

# Create adapter
POST /api/adapter-instances

# Create sync rule
POST /api/sync-rules

# Create route
POST /api/routes

# Check delivery jobs
GET /api/delivery-jobs

# Send webhook
POST /webhooks/{adapter_instance_id}

# Interactive docs
GET /docs
```

## Need Help?

- Read full documentation: [docs/README.md](./README.md)
- Check adapter setup: [Telegram](../app/adapters/telegram/README.md), [VK](../app/adapters/vk/README.md), [MAX](../app/adapters/max/README.md)
- Report issue on GitHub
- Check logs: `docker compose logs -f app`

Happy syncing! 🚀
