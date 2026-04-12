# Architecture Overview

AutoPost Sync is built on **pluggable adapter architecture** with a clean separation of concerns: domain models, adapters, repositories, services, and workers.

## High-Level Flow

```
User Message (Telegram, VK, MAX)
    ↓
Adapter.parse_incoming_event() → UnifiedPost
    ↓
Sync Rules & Routes (router logic)
    ↓
Delivery Queue (async job store)
    ↓
Background Worker
    ↓
Target Adapter.publish_post()
    ↓
Target Platform API
```

## Core Layers

### 1. Domain Layer (`app/domain/`)

**Responsibility:** Define core business entities. Platform-agnostic.

#### `models.py`

**UnifiedPost** — Normalized message format:
- `source_platform` — Where message came from
- `source_adapter_id` — Which adapter instance
- `source_chat_id` — Chat/channel/group ID
- `source_message_id` — Message ID
- `text` — Message body
- `media` — List of MediaItem (photos, videos, docs, etc.)
- `is_repost` — Is this a repost?
- `original_platform` — If repost, original source
- `trace` — MessageTrace for anti-loop detection

**MediaItem** — File metadata:
- `type` — ContentType (IMAGE, VIDEO, AUDIO, DOCUMENT)
- `url` — Remote URL (if already uploaded)
- `file_id` — Local file path or remote ID
- `mime_type` — MIME type
- `filename` — Filename

**MessageTrace** — Anti-loop tracking:
- `visited_platforms` — Set of platforms message has been through
- `visited_adapters` — Set of adapter instances
- `original_message_id` — Root message ID for deduplication

#### `enums.py`

- `Platform` — TELEGRAM, VK, MAX
- `ContentType` — IMAGE, VIDEO, AUDIO, DOCUMENT, TEXT

### 2. Adapter Layer (`app/adapters/`)

**Responsibility:** Implement platform-specific logic.

#### Base Class (`base.py`)

**BaseAdapter** — Abstract interface all adapters implement:

```python
class BaseAdapter(ABC):
    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Is this adapter ready to use?"""

    async def startup(self, on_post: Callable) -> None:
        """Start listening for incoming messages."""

    async def shutdown(self) -> None:
        """Stop and clean up."""

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        """Convert platform event to UnifiedPost."""

    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        """Publish to platform. Return post ID."""
```

**Status Tracking:**
- `_status` — One of: `disabled`, `starting`, `running`, `shutdown`, `startup_failed`
- `_connected` — Is adapter currently connected?
- `_status_updated_at` — Last status change timestamp

#### Adapter Instances

Each adapter can have **multiple instances**. Example:
- `telegram-main` — Primary Telegram userbot
- `telegram-bot` — Secondary Telegram bot
- `vk-prod` — Production VK community
- `vk-test` — Test VK community

**Instance Configuration** stored in DB:
- `id` — Instance ID (e.g., "telegram-main")
- `adapter_key` — Platform key ("telegram", "vk", "max")
- `enabled` — Is this instance active?
- `display_name` — Human-readable name
- `config` — JSON config dict
- `secrets` — Encrypted secrets dict

### 3. Database Layer (`app/db/`)

**ORM:** SQLAlchemy async with asyncpg driver

#### Core Tables

**adapter_instances**
- `id` — Instance ID
- `adapter_key` — Platform type
- `enabled` — Is active
- `display_name` — UI name
- `config` — Platform-specific config (JSON)
- `secrets` — Encrypted secrets (JSON)
- `status` — Current status
- `created_at`, `updated_at` — Timestamps

**sync_rules**
- `id` — Rule ID
- `source_platform` — Source platform
- `target_platform` — Target platform
- `enabled` — Is active
- `content_policy` — What media types to allow
- `copy_text_template` — Template for text transformation
- `created_at`, `updated_at` — Timestamps

**routes**
- `id` — Route ID
- `source_adapter_instance_id` — Source adapter
- `source_chat_id` — Source chat
- `target_adapter_instance_id` — Target adapter
- `target_chat_id` — Target chat
- `enabled` — Is active
- `created_at`, `updated_at` — Timestamps

**delivery_jobs**
- `id` — Job ID
- `status` — One of: pending, acquired, completed, failed
- `source_post_id` — Source UnifiedPost reference
- `target_adapter_instance_id` — Where to send
- `target_chat_id` — Destination chat
- `post_data` — Full UnifiedPost JSON
- `attempt_count` — How many times tried
- `next_retry_at` — When to retry
- `acquired_by_worker` — Which worker holds lease
- `lease_expires_at` — Lease expiration
- `error_message` — Last error if failed
- `result_post_id` — Result if success
- `created_at`, `updated_at` — Timestamps

**message_links**
- `id` — Link ID
- `source_platform` — Original platform
- `source_chat_id` — Original chat
- `source_message_id` — Original message
- `target_platform` — Where it was posted
- `target_chat_id` — Where it was posted
- `target_message_id` — Result post ID
- `is_repost` — Was this a repost?
- `created_at` — When created

### 4. Repository Layer (`app/repositories/`)

**Responsibility:** Data access abstraction. Database-agnostic interfaces.

**Repositories:**
- `AdapterInstancesRepo` — CRUD operations on adapter_instances
- `SyncRulesRepo` — CRUD operations on sync_rules
- `RoutesRepo` — CRUD operations on routes
- `DeliveryJobsRepo` — Job lease, acquire, mark done, retry logic
- `MessageLinksRepo` — Deduplication queries

**Key Pattern:** Repository methods handle encryption/decryption of secrets:

```python
instance = await repo.get("telegram-main", include_secrets=True)
# Secrets automatically decrypted via SecretBox
```

### 5. Service Layer (`app/services/`)

**Responsibility:** Business logic and orchestration.

**Services:**
- `SyncService` — Apply sync rules (filtering, text template)
- `RoutingService` — Match incoming messages to routes
- `MediaService` — Download, convert, upload media files
- `OAuthService` — Handle platform-specific auth flows (Telegram, VK, MAX)

### 6. Worker Layer (`app/workers/`)

**Responsibility:** Async job processing and retries.

**DeliveryWorker:**
1. Poll `delivery_jobs` table for pending jobs
2. Acquire job with lease (to avoid duplicate processing)
3. Call target adapter's `publish_post()`
4. On success: mark as completed, store result post ID
5. On failure: calculate next retry time with exponential backoff
6. On max attempts: mark as failed, log error

**Lease-Based Concurrency:**
- Multiple workers can run safely
- Each job has `acquired_by_worker` ID + `lease_expires_at`
- Worker extends lease via heartbeat to avoid timeout
- On worker crash, job auto-released after lease expires

### 7. API Layer (`app/api/`)

**Framework:** FastAPI

**Endpoint Groups:**

- `GET /docs` — Interactive API documentation
- `POST /webhooks/{adapter_instance_id}` — Webhook receivers for each adapter
- `POST /api/adapter-instances` — Create/list adapter instances
- `PUT /api/adapter-instances/{id}` — Update instance config/secrets
- `DELETE /api/adapter-instances/{id}` — Delete instance
- `POST /api/sync-rules` — Create/list sync rules
- `POST /api/routes` — Create/list routes
- `GET /api/debug/delivery-jobs` — View job queue status
- `POST /auth/vk/start` — Start VK OAuth flow
- `GET /auth/vk/callback` — VK OAuth callback
- `POST /auth/vk/groups-auth-start` — VK group token auth
- (similar for Telegram, MAX)

## Message Flow Example

### Scenario: Telegram → VK Sync

```
1. User sends message to Telegram channel
   
2. TelegramAdapter receives via Telethon event handler
   → Calls on_post(UnifiedPost)

3. Router matches route: telegram-main:123456 → vk-prod:237416141
   
4. SyncService applies rule:
   - Filter: allow images, videos, documents
   - Template: append "#crosspost" to text

5. Create delivery job:
   INSERT delivery_job(
     source_post_id,
     target_adapter_instance_id='vk-prod',
     target_chat_id='237416141',
     post_data=<serialized UnifiedPost>,
     status='pending'
   )

6. Background worker picks up job:
   - Acquires with lease
   - Downloads media files (if needed)
   - Calls VkAdapter.publish_post('237416141', post)
   - VkAdapter uploads photos to VK
   - Returns post_id
   
7. Mark job as completed:
   UPDATE delivery_job SET
     status='completed',
     result_post_id='789_1234'

8. Store message link:
   INSERT message_link(
     source_platform='telegram',
     source_chat_id='123456',
     source_message_id='999',
     target_platform='vk',
     target_chat_id='237416141',
     target_message_id='789_1234'
   )

9. Future: if someone reposts from VK, anti-loop detection
   checks message_links table → prevents infinite loop
```

## Encryption Strategy

**At Rest:** Secrets encrypted in database using AES-256-GCM via `cryptography` library.

**Key:** `SECRETS_ENCRYPTION_KEY` (minimum 32 characters) from environment.

**Implementation:** `app/utils/crypto.py` / `SecretBox` class:

```python
secret_box = SecretBox(key=os.getenv("SECRETS_ENCRYPTION_KEY"))

# Encrypt on store
encrypted = secret_box.encrypt({"token": "secret"})

# Decrypt on load
decrypted = secret_box.decrypt(encrypted)
```

**Lifecycle:**
1. Adapter config/secrets passed to adapter constructor
2. Adapter holds them in memory (never re-encrypted)
3. On shutdown: memory cleared
4. On worker publish: fetched from repo (auto-decrypted) → passed to adapter → used once → not stored in logs

## Error Handling & Retry

### Job Failure Scenarios

1. **Transient Error** (429 rate limit, timeout)
   - Retry with exponential backoff
   - Next attempt: `now + 2^attempt_count * base_seconds`
   - Cap at `max_seconds` (default 300s)

2. **Permanent Error** (invalid token, chat not found)
   - Max 5 attempts (config: `delivery_max_attempts`)
   - After max attempts: mark failed, alert operator

3. **Worker Crash**
   - Job lease expires
   - Next worker picks it up
   - Automatic recovery

### Logging

All adapters log via Python `logging` module:
- Level: ERROR, WARNING, INFO, DEBUG
- Output: stdout (captured by Docker/systemd)
- Context: instance_id, adapter_key in each log entry

## Scalability Considerations

### Horizontal Scaling

**Multiple Workers:**
- Each worker instance gets its own `DELIVERY_WORKER_INSTANCE_ID`
- Lease-based job stealing prevents duplicates
- Safe to run 1, 5, 100 workers concurrently

**Configuration:**
```env
DELIVERY_WORKER_POLL_INTERVAL_SECONDS=1.0
DELIVERY_WORKER_BATCH_SIZE=10
DELIVERY_JOB_LEASE_SECONDS=300
DELIVERY_JOB_HEARTBEAT_INTERVAL_SECONDS=30
```

### Database Performance

- Indexes on `delivery_jobs(status, next_retry_at)` for fast polling
- Indexes on `routes(source_adapter_instance_id, source_chat_id)` for fast routing
- `message_links` compound index for dedup lookups
- Async queries via SQLAlchemy + asyncpg (non-blocking)

### Media Handling

- Files downloaded to temp directory during publish
- Cleaned up after upload
- No permanent local storage of user media
- Streaming upload where supported by platform API

## Security Considerations

### Input Validation

- `UnifiedPost` is DTO (data transfer object) — immutable after creation
- Sync rules validate media types before processing
- Text templates use simple string interpolation (no code injection)

### Token Safety

- Never logged or printed
- Encrypted at rest
- In-memory only during active use
- Separate encryption keys per environment

### Access Control

- No authentication layer yet (local deployment assumption)
- If exposed to internet: add auth middleware
- Webhook signatures verified (adapter-specific)

### Message Content

- No filtering, validation, or scanning of message content
- Adapters pass through as-is (respecting platform content policies)
- No sensitive data storage (only message IDs and metadata)

## Future Enhancements

1. **Web UI Dashboard** — Visual route builder, job monitoring
2. **Plugin System** — Third-party adapters without code changes
3. **GraphQL API** — Alternative to REST
4. **Media Preprocessing** — Resize, format conversion
5. **Scheduled Posting** — Publish at specific times
6. **Analytics Dashboard** — Message counts, routing statistics
7. **Message Editing** — Synchronize edits across platforms
8. **Audit Logs** — Who changed what and when
