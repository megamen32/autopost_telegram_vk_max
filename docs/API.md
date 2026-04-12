# API Reference

Complete reference for AutoPost Sync REST API endpoints.

## Base URL

```
http://localhost:8000  (development)
https://autopost.example.com  (production)
```

## Authentication

Current version has **no authentication layer**. In production, add middleware (JWT, API keys, etc.).

## Interactive Documentation

Visit **http://localhost:8000/docs** for Swagger UI with live testing.

---

## Adapter Instances

Manage platform adapter configurations.

### List Adapter Instances

```
GET /api/adapter-instances
```

**Response:**
```json
[
  {
    "id": "telegram-main",
    "adapter_key": "telegram",
    "display_name": "Telegram Main",
    "enabled": true,
    "status": "running",
    "connected": true,
    "created_at": "2026-04-12T10:00:00Z",
    "updated_at": "2026-04-12T14:30:00Z"
  }
]
```

### Get Adapter Instance

```
GET /api/adapter-instances/{instance_id}
```

**Response:**
```json
{
  "id": "telegram-main",
  "adapter_key": "telegram",
  "display_name": "Telegram Main",
  "enabled": true,
  "status": "running",
  "config": {
    "api_id": 1234567,
    "receive_updates": true,
    "allowed_source_chat_ids": []
  },
  "secrets": {}  // encrypted, not returned
}
```

### Create Adapter Instance

```
POST /api/adapter-instances
Content-Type: application/json
```

**Request:**
```json
{
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
}
```

**Response:** 201 Created
```json
{
  "id": "telegram-main",
  "adapter_key": "telegram",
  "display_name": "Telegram Main",
  "enabled": true,
  "status": "disabled",
  "created_at": "2026-04-12T14:30:00Z"
}
```

### Update Adapter Instance

```
PUT /api/adapter-instances/{instance_id}
Content-Type: application/json
```

**Request:**
```json
{
  "display_name": "Telegram Updated",
  "enabled": true,
  "config": {
    "api_id": 1234567,
    "receive_updates": false
  },
  "secrets": {
    "api_hash": "new_api_hash"
  }
}
```

**Response:** 200 OK

### Delete Adapter Instance

```
DELETE /api/adapter-instances/{instance_id}
```

**Response:** 204 No Content

### Restart Adapter Instance

```
POST /api/adapter-instances/{instance_id}/restart
```

**Response:** 200 OK
```json
{
  "id": "telegram-main",
  "status": "running",
  "message": "Adapter restarted successfully"
}
```

---

## Sync Rules

Define transformations between source and target platforms.

### List Sync Rules

```
GET /api/sync-rules
```

**Response:**
```json
[
  {
    "id": 1,
    "source_platform": "telegram",
    "target_platform": "vk",
    "enabled": true,
    "content_policy": {
      "allow_text": true,
      "allow_images": true,
      "allow_video": true,
      "max_images": 10
    },
    "copy_text_template": "{text}\n#crosspost",
    "created_at": "2026-04-12T10:00:00Z"
  }
]
```

### Create Sync Rule

```
POST /api/sync-rules
Content-Type: application/json
```

**Request:**
```json
{
  "source_platform": "telegram",
  "target_platform": "vk",
  "enabled": true,
  "content_policy": {
    "allow_text": true,
    "allow_images": true,
    "allow_video": true,
    "allow_documents": false,
    "max_images": 10
  },
  "copy_text_template": "{text}\n#crosspost"
}
```

**Response:** 201 Created

### Update Sync Rule

```
PUT /api/sync-rules/{rule_id}
```

### Delete Sync Rule

```
DELETE /api/sync-rules/{rule_id}
```

---

## Routes

Map specific source chats to target chats.

### List Routes

```
GET /api/routes
```

**Response:**
```json
[
  {
    "id": 1,
    "source_adapter_instance_id": "telegram-main",
    "source_chat_id": "123456789",
    "target_adapter_instance_id": "vk-prod",
    "target_chat_id": "237416141",
    "enabled": true,
    "created_at": "2026-04-12T10:00:00Z"
  }
]
```

### Create Route

```
POST /api/routes
Content-Type: application/json
```

**Request:**
```json
{
  "source_adapter_instance_id": "telegram-main",
  "source_chat_id": "123456789",
  "target_adapter_instance_id": "vk-prod",
  "target_chat_id": "237416141",
  "enabled": true
}
```

**Response:** 201 Created

### Update Route

```
PUT /api/routes/{route_id}
```

### Delete Route

```
DELETE /api/routes/{route_id}
```

---

## Delivery Jobs

Monitor and manage the delivery queue.

### List Delivery Jobs

```
GET /api/delivery-jobs
```

**Query parameters:**
- `status=pending` — Filter by status (pending, acquired, completed, failed)
- `limit=100` — Results per page
- `offset=0` — Pagination offset

**Response:**
```json
{
  "total": 150,
  "limit": 100,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "status": "pending",
      "source_post_id": "telegram:123:999",
      "target_adapter_instance_id": "vk-prod",
      "target_chat_id": "237416141",
      "attempt_count": 0,
      "next_retry_at": "2026-04-12T14:35:00Z",
      "error_message": null,
      "result_post_id": null,
      "created_at": "2026-04-12T14:30:00Z"
    }
  ]
}
```

### Get Delivery Job

```
GET /api/delivery-jobs/{job_id}
```

### Retry Failed Job

```
POST /api/delivery-jobs/{job_id}/retry
```

**Response:** 200 OK
```json
{
  "id": 1,
  "status": "pending",
  "next_retry_at": "2026-04-12T14:35:00Z"
}
```

### Cancel Job

```
POST /api/delivery-jobs/{job_id}/cancel
```

**Response:** 200 OK

---

## Message Links

Track message routing and deduplication.

### List Message Links

```
GET /api/message-links
```

**Query parameters:**
- `source_platform=telegram`
- `source_chat_id=123456789`
- `source_message_id=999`

**Response:**
```json
[
  {
    "id": 1,
    "source_platform": "telegram",
    "source_chat_id": "123456789",
    "source_message_id": "999",
    "target_platform": "vk",
    "target_chat_id": "237416141",
    "target_message_id": "789_1234",
    "is_repost": false,
    "created_at": "2026-04-12T14:30:00Z"
  }
]
```

---

## Webhooks

Receive incoming messages from platforms.

### Telegram Webhook

```
POST /webhooks/{adapter_instance_id}
Content-Type: application/json
```

**Request (Telethon event):**
```json
{
  "chat_id": "123456789",
  "message_id": "999",
  "text": "Hello from Telegram",
  "media": [
    {
      "type": "image",
      "url": "https://example.com/photo.jpg",
      "filename": "photo.jpg",
      "mime_type": "image/jpeg"
    }
  ]
}
```

**Response:** 200 OK

### VK Webhook

```
POST /webhooks/{adapter_instance_id}
Content-Type: application/json
```

**Request (VK Callback API):**
```json
{
  "type": "message_new",
  "object": {
    "message": {
      "id": 123,
      "peer_id": 100,
      "text": "Hello from VK"
    }
  },
  "group_id": 237416141
}
```

**Response:** 200 OK + confirmation token if first request from VK

### MAX Webhook

```
POST /webhooks/{adapter_instance_id}
Content-Type: application/json
X-Max-Bot-Api-Secret: signature
```

**Request:**
```json
{
  "event": "message.created",
  "data": {
    "message": {
      "id": "msg_123",
      "chat_id": "chat_456",
      "text": "Hello from MAX"
    }
  }
}
```

**Response:** 200 OK

---

## Authentication Endpoints

### Start Telegram OAuth

```
GET /api/auth/telegram/start
```

**Response:** 301 Redirect to Telegram OAuth

### Start VK OAuth (VK ID)

```
GET /api/auth/vk/start
```

**Query parameters:**
- `redirect_uri` — Where to redirect after auth (optional)

**Response:** 301 Redirect to VK ID login

### VK OAuth Callback

```
GET /auth/vk/callback
```

**Query parameters:**
- `code` — Auth code from VK
- `state` — State token for CSRF protection

**Response:** 200 OK with token details
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": 1681234567,
  "adapter_instance_id": "vk-main"
}
```

### Start VK Group Token Auth

```
GET /api/auth/vk/groups-auth-start
```

**Response:** 301 Redirect to VK classic OAuth

---

## Debug Endpoints

### Debug: Delivery Job Queue Status

```
GET /api/debug/delivery-jobs
```

**Response:**
```json
{
  "total_jobs": 150,
  "pending_jobs": 45,
  "acquired_jobs": 3,
  "failed_jobs": 12,
  "completed_jobs": 90,
  "oldest_pending_job_age_seconds": 3600,
  "average_processing_time_seconds": 2.5
}
```

### Debug: Adapter Logs

```
GET /api/debug/adapter-logs
```

**Query parameters:**
- `instance_id=telegram-main`
- `level=DEBUG`
- `limit=100`

**Response:**
```json
[
  {
    "timestamp": "2026-04-12T14:30:00Z",
    "level": "INFO",
    "message": "Adapter started",
    "context": {
      "instance_id": "telegram-main",
      "adapter_key": "telegram"
    }
  }
]
```

### Debug: Database Status

```
GET /api/debug/db-status
```

**Response:**
```json
{
  "connected": true,
  "pool_size": 10,
  "active_connections": 3,
  "last_query_time_ms": 12.5
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request body"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 409 Conflict

```json
{
  "detail": "Route already exists for this source/target pair"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Unexpected server error",
  "request_id": "req_abc123"
}
```

---

## Rate Limiting

Current version has **no rate limiting**. Implement in production:

- API endpoints: 100 req/min per IP
- Webhook endpoints: No limit (trust platform signatures)
- OAuth endpoints: 10 req/min per IP

---

## Examples

### Example: Create Telegram → VK Sync

```bash
# 1. Create Telegram adapter
curl -X POST http://localhost:8000/api/adapter-instances \
  -H 'Content-Type: application/json' \
  -d '{
    "adapter_key": "telegram",
    "display_name": "Telegram",
    "config": {"api_id": 12345, "receive_updates": true},
    "secrets": {"api_hash": "...", "bot_token": "..."}
  }'

# 2. Create VK adapter
curl -X POST http://localhost:8000/api/adapter-instances \
  -H 'Content-Type: application/json' \
  -d '{
    "adapter_key": "vk",
    "display_name": "VK",
    "config": {"group_id": 237416141, "receive_updates": false},
    "secrets": {"token": "..."}
  }'

# 3. Create sync rule
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

# 4. Create route
curl -X POST http://localhost:8000/api/routes \
  -H 'Content-Type: application/json' \
  -d '{
    "source_adapter_instance_id": "telegram-main",
    "source_chat_id": "123456789",
    "target_adapter_instance_id": "vk-prod",
    "target_chat_id": "237416141",
    "enabled": true
  }'
```

---

## See Also

- [Installation Guide](./INSTALLATION.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Contributing Guide](./CONTRIBUTING.md)
- Interactive docs: **http://localhost:8000/docs**
