# Installation & Setup Guide

Detailed step-by-step instructions for setting up AutoPost Sync on your machine or server.

## Prerequisites

- **Python 3.11+** — Latest stable recommended
- **PostgreSQL 12+** — Can use SQLite for local development
- **Docker & Docker Compose** (optional) — For containerized database
- **Git** — For cloning the repository

## Option 1: Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/autopost_sync.git
cd autopost_sync
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python3.11 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Base installation
pip install -e .

# Optional: VK browser fallback (Playwright)
pip install -e ".[vk-browser]"

# Optional: Development tools
pip install -e ".[dev]"
```

### Step 4: Set Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your editor
```

**Key variables to set:**

```env
# Database (local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autopost_sync

# Encryption key (generate a random 32+ char string)
SECRETS_ENCRYPTION_KEY=your-very-long-random-string-min-32-chars

# App settings
APP_HOST=127.0.0.1
APP_PORT=8000
APP_BASE_URL=http://127.0.0.1:8000

# Optional: Logging
LOG_LEVEL=INFO
DEBUG=false
```

### Step 5: Start PostgreSQL

#### Option A: Docker Compose (Recommended)

```bash
# Start database in background
docker compose up -d db

# Verify it's running
docker compose ps db
```

#### Option B: Local PostgreSQL

```bash
# If you have PostgreSQL installed locally
postgres -D /usr/local/var/postgres

# Or via Homebrew on macOS
brew services start postgresql@16
```

### Step 6: Initialize Database

```bash
# Run migrations
alembic upgrade head

# Alternative: enable auto-create in .env
# AUTO_CREATE_TABLES=true
# Then just start the app, tables are created automatically
```

### Step 7: Run the Server

```bash
# Terminal 1: Start FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Start delivery worker (in another terminal, same venv)
python -m app.workers.delivery_worker
```

Open browser: **http://127.0.0.1:8000/docs** — Interactive API

### Step 8: Configure First Adapter

Via Web UI (FastAPI /docs) or curl:

```bash
# Create Telegram adapter instance
curl -X POST http://localhost:8000/api/adapter-instances \
  -H 'Content-Type: application/json' \
  -d '{
    "adapter_key": "telegram",
    "display_name": "Telegram Main",
    "config": {
      "api_id": 1234567,
      "receive_updates": true
    },
    "secrets": {
      "api_hash": "your_api_hash",
      "bot_token": "your_bot_token"
    }
  }'
```

## Option 2: Docker Deployment

### Using Docker Compose

```bash
# Clone repo
git clone https://github.com/yourusername/autopost_sync.git
cd autopost_sync

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Build and start all services
docker compose up -d

# Check logs
docker compose logs -f app
```

**docker-compose.yml includes:**
- `db` — PostgreSQL 16
- `app` — FastAPI + Uvicorn (add this to your compose file)
- `worker` — Delivery worker (add this to your compose file)

### Creating docker-compose.yml with App

Add to your `docker-compose.yml`:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/autopost_sync
      SECRETS_ENCRYPTION_KEY: ${SECRETS_ENCRYPTION_KEY}
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  worker:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/autopost_sync
      SECRETS_ENCRYPTION_KEY: ${SECRETS_ENCRYPTION_KEY}
    depends_on:
      db:
        condition: service_healthy
    command: python -m app.workers.delivery_worker
```

Also create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install Python dependencies
RUN pip install -e .

# Run migrations and app
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Option 3: Production Deployment (systemd)

### Prepare Server

```bash
# SSH into server
ssh user@your-server.com

# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create app user
sudo useradd -m -s /bin/bash autopost

# Clone repository
sudo -u autopost git clone https://github.com/yourusername/autopost_sync.git /opt/autopost
cd /opt/autopost
```

### Setup Venv & Dependencies

```bash
sudo -u autopost python3.11 -m venv /opt/autopost/.venv
sudo -u autopost /opt/autopost/.venv/bin/pip install -e .
```

### Configure Environment

```bash
# Create .env in app directory
sudo nano /opt/autopost/.env

# Set restrictive permissions
sudo chown autopost:autopost /opt/autopost/.env
sudo chmod 600 /opt/autopost/.env
```

### Create systemd Services

**File: `/etc/systemd/system/autopost-app.service`**

```ini
[Unit]
Description=AutoPost Sync FastAPI Server
After=network.target postgresql.service

[Service]
Type=notify
User=autopost
WorkingDirectory=/opt/autopost
EnvironmentFile=/opt/autopost/.env
ExecStart=/opt/autopost/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**File: `/etc/systemd/system/autopost-worker.service`**

```ini
[Unit]
Description=AutoPost Sync Delivery Worker
After=network.target postgresql.service autopost-app.service

[Service]
Type=simple
User=autopost
WorkingDirectory=/opt/autopost
EnvironmentFile=/opt/autopost/.env
ExecStart=/opt/autopost/.venv/bin/python -m app.workers.delivery_worker
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable autopost-app autopost-worker
sudo systemctl start autopost-app autopost-worker

# Check status
sudo systemctl status autopost-app
sudo systemctl status autopost-worker

# View logs
sudo journalctl -u autopost-app -f
```

### Configure Reverse Proxy (Nginx)

```nginx
upstream autopost_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name autopost.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name autopost.example.com;

    ssl_certificate /etc/letsencrypt/live/autopost.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/autopost.example.com/privkey.pem;

    client_max_body_size 100M;

    location / {
        proxy_pass http://autopost_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /webhooks/ {
        proxy_pass http://autopost_app/webhooks/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL Certificates (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d autopost.example.com

# Auto-renewal (runs daily)
sudo certbot renew --dry-run
```

## Database Migrations

### Creating Migrations After Schema Changes

```bash
# With venv activated
alembic revision --autogenerate -m "Add new field to adapter_instances"

# Review the generated migration
nano alembic/versions/xxx_add_new_field.py

# Apply migration
alembic upgrade head
```

### Downgrading

```bash
# Go back one revision
alembic downgrade -1

# Go to specific revision
alembic downgrade abc123def456
```

## Testing Setup

### Run Tests Locally

```bash
# Unit tests (no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires live DB + adapters)
pytest tests/integration/ -v -m integration

# Specific test file
pytest tests/unit/test_vk_adapter.py -v

# With coverage
pytest --cov=app tests/
```

### Database for Tests

Tests can use:
1. Real PostgreSQL — set `TEST_DATABASE_URL` env var
2. SQLite in-memory — automatic fallback
3. SQLite file-based — `TEST_DATABASE_URL=sqlite+aiosqlite:///test.db`

## Troubleshooting

### "Could not connect to database"

**Cause:** PostgreSQL not running or wrong credentials

**Solution:**
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# If using Docker, check:
docker compose ps db
docker compose logs db

# Test connection
psql -h localhost -U postgres -d autopost_sync
```

### "ModuleNotFoundError: No module named 'uvicorn'"

**Cause:** Dependencies not installed in venv

**Solution:**
```bash
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### "SSL certificate verify failed"

**Cause:** Platform APIs use SSL; missing certificates

**Solution (macOS):**
```bash
# Install certificates
/Applications/Python\ 3.11/Install\ Certificates.command
```

### "Address already in use: 127.0.0.1:8000"

**Cause:** Port 8000 in use by another process

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <pid>

# Or use different port
uvicorn app.main:app --port 8001
```

### "SECRETS_ENCRYPTION_KEY not set"

**Cause:** Missing env variable

**Solution:**
```bash
# Generate random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
echo "SECRETS_ENCRYPTION_KEY=<generated-key>" >> .env
```

## Next Steps

1. **Set up first adapter** — Follow adapter-specific README
2. **Create sync rule** — Define source/target platform pair
3. **Create route** — Map source chat to target chat
4. **Test publishing** — Send message, verify delivery
5. **Enable webhooks** — For production reliability
6. **Monitor logs** — Check `/api/debug/delivery-jobs` for queue status

## See Also

- [Architecture Overview](./ARCHITECTURE.md)
- [API Reference](./API.md)
- [Contributing Guide](./CONTRIBUTING.md)
- [Telegram Adapter Setup](../app/adapters/telegram/README.md#setup)
- [VK Adapter Setup](../app/adapters/vk/README.md#setup)
- [MAX Adapter Setup](../app/adapters/max/README.md#setup)
