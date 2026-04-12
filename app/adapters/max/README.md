# MAX Adapter

> **MAX adapter** for messaging and collaboration. Publish text, images, videos, and documents. Receive incoming messages via long polling or webhooks.

## Features

- 💬 **Text & Rich Media** — Text, images, videos, audio, files
- 🔄 **Bidirectional** — Both sending and receiving messages
- 🔁 **Long Polling** — Default mode, no HTTPS required (local development friendly)
- 🌐 **Webhooks** — Production-ready Callback API
- 🔐 **Token Encryption** — Secrets encrypted at rest
- ⚙️ **Official SDK** — Uses maxapi/max-botapi-python when available, falls back to raw HTTP

## Setup

### 1. Get MAX Bot Token

1. Go to [MAX Bot Developer Dashboard](https://max.im)
2. Create a new bot
3. Copy the **Token** (starts with `bot_`)

### 2. Configure Adapter Instance

Via Web UI or API:

```json
{
  "display_name": "MAX main",
  "receive_updates": true,
  "receive_mode": "long_poll",
  "prefer_official_sdk": true
}
```

**Secrets** (encrypted in DB):
- `token` — Bot token from MAX dashboard (required)
- `secret` — Webhook signature secret (only for webhook mode)

### 3. Start Receiving Messages

For local development, long polling requires no additional setup:

```json
{
  "receive_updates": true,
  "receive_mode": "long_poll",
  "long_poll_timeout_seconds": 30,
  "long_poll_limit": 100
}
```

For production, use webhooks (requires public HTTPS):

```json
{
  "receive_updates": true,
  "receive_mode": "webhook",
  "webhook_url": "https://your-domain/webhooks/max-main"
}
```

## Publishing

### Text Message

```python
from app.domain.models import UnifiedPost
from app.domain.enums import Platform

post = UnifiedPost(
    source_platform=Platform.TELEGRAM,
    source_adapter_id="telegram-main",
    source_chat_id="123",
    source_message_id="456",
    text="Hello MAX!",
    media=[]
)

# Send to chat
message_id = await max_adapter.publish_post("chat_123", post)
```

### Image Message

```python
from app.domain.models import MediaItem
from app.domain.enums import ContentType

post = UnifiedPost(
    ...
    text="Photo from Telegram",
    media=[
        MediaItem(
            type=ContentType.IMAGE,
            file_id="/path/to/image.jpg",
            mime_type="image/jpeg"
        )
    ]
)

message_id = await max_adapter.publish_post("chat_123", post)
```

### Multiple Media

```python
MediaItem(
    type=ContentType.IMAGE,
    file_id="/path/to/photo1.jpg"
),
MediaItem(
    type=ContentType.IMAGE,
    file_id="/path/to/photo2.jpg"
),
MediaItem(
    type=ContentType.VIDEO,
    file_id="/path/to/video.mp4"
)
```

### Documents

```python
MediaItem(
    type=ContentType.DOCUMENT,
    file_id="/path/to/file.pdf",
    mime_type="application/pdf",
    filename="my_document.pdf"
)
```

## Receiving Messages

### Long Polling (Recommended for Local)

Default mode. Adapter periodically polls MAX for new events:

```json
{
  "receive_updates": true,
  "receive_mode": "long_poll",
  "long_poll_timeout_seconds": 30,
  "long_poll_limit": 100,
  "allowed_source_chat_ids": ["chat_123", "chat_456"]
}
```

**Advantages:**
- Works behind NAT and firewalls
- No HTTPS required
- Perfect for development

**Disadvantages:**
- Slight delay (up to `long_poll_timeout_seconds`)
- Polling cost on API

### Webhooks (Production)

For production deployment with guaranteed HTTPS:

1. **Configure MAX webhooks** in bot dashboard:
   - Webhook URL: `https://your-domain/webhooks/max-main`
   - Event types: `message_created` (and others)

2. **Set in adapter config:**
   ```json
   {
     "receive_mode": "webhook",
     "webhook_url": "https://your-domain/webhooks/max-main",
     "secret": "your_webhook_secret"
   }
   ```

3. **Endpoint automatically:**
   - Verifies signature via `X-Max-Bot-Api-Secret` header
   - Routes events to `on_post` callback
   - Returns 200 OK to MAX

## Configuration

### Simple Settings

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `display_name` | str | — | Human-readable name |
| `token` | str (secret) | — | Bot token (required) |
| `receive_updates` | bool | true | Listen for incoming messages |
| `receive_mode` | choice | `long_poll` | `long_poll` or `webhook` |

### Advanced Settings

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `webhook_url` | str | — | HTTPS endpoint for webhooks |
| `secret` | str (secret) | — | Webhook signature verification |
| `update_types` | list | `["message_created"]` | Event types to subscribe to |
| `allowed_source_chat_ids` | list | `[]` | Restrict incoming to these chats |
| `prefer_official_sdk` | bool | true | Try official SDK first |
| `long_poll_timeout_seconds` | int | 30 | How long to hold poll request |
| `long_poll_limit` | int | 100 | Max events per poll request |
| `log_level` | choice | `INFO` | Verbosity: `ERROR`, `WARNING`, `INFO`, `DEBUG` |

## Incoming Event Format

When a MAX message arrives, it's converted to `UnifiedPost`:

```python
UnifiedPost(
    source_platform=Platform.MAX,
    source_adapter_id="max-main",
    source_chat_id="chat_123",
    source_message_id="msg_456",
    text="Message text",
    media=[
        MediaItem(
            type=ContentType.IMAGE,
            url="https://api.max.im/files/...",
            filename="photo.jpg",
            mime_type="image/jpeg"
        )
    ],
    is_repost=False,
)
```

This can be routed to other platforms via sync rules.

## Error Handling

### Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid token` | Token is wrong or expired | Get new token from MAX dashboard |
| `Chat not found` | Chat ID doesn't exist | Verify chat ID in MAX UI |
| `File too large` | Media exceeds MAX's size limit | Check MAX file size limits |
| `Webhook signature invalid` | Secret doesn't match | Verify webhook secret in config |
| `Connection timeout` | MAX API unreachable | Check network; try retry with backoff |

### Debugging

Enable debug logging:

```json
{
  "log_level": "DEBUG"
}
```

View logs:

```bash
curl http://localhost:8000/api/debug/adapter-logs?instance_id=max-main
```

## Official SDK vs HTTP API

By default, `prefer_official_sdk: true`:

1. Try to use official MAX SDK (`maxapi` or `max-botapi-python`)
2. If method not in SDK, fall back to raw HTTP API
3. Covers all MAX methods eventually

If you want to use only HTTP API:

```json
{
  "prefer_official_sdk": false
}
```

## Testing

```bash
# Unit tests
pytest tests/unit/test_max_adapter.py -v

# Integration test (requires MAX token)
python -c "
import asyncio
from app.adapters.max.adapter import MaxAdapter

async def test():
    adapter = MaxAdapter(
        instance_id='test',
        token='bot_...',
    )
    await adapter.startup()
    await adapter.publish_post('chat_id', UnifiedPost(...))

asyncio.run(test())
"
```

## Advanced

### Switching Between Long Polling and Webhooks

At runtime:

1. Update `receive_mode` in adapter config
2. Restart adapter (or use `/api/admin/adapters/{instance_id}/restart`)
3. Adapter automatically switches polling → webhook or vice versa

No data loss; messages queue in MAX until received.

### Custom Event Types

By default, only `message_created` is subscribed. To listen to other event types:

```json
{
  "update_types": ["message_created", "message_edited", "message_deleted"]
}
```

Check MAX documentation for available event types.

### Batch Updates in Long Polling

Each poll request returns up to `long_poll_limit` events (default 100). To tune:

```json
{
  "long_poll_timeout_seconds": 60,  // Hold request longer
  "long_poll_limit": 200             // Get more events per request
}
```

Trade-off: higher limit = larger payloads; higher timeout = more latency.

## Troubleshooting

### "Invalid token"

**Cause:** Token expired or wrong.

**Fix:**
1. Go to MAX dashboard
2. Regenerate bot token
3. Update adapter config

### "Chat not found"

**Cause:** Chat ID is wrong.

**Fix:**
1. Open the chat in MAX UI
2. Look for chat ID in chat info
3. Verify format (typically `chat_` prefix)

### "Webhook signature verification failed"

**Cause:** Secret in config doesn't match MAX dashboard.

**Fix:**
1. Copy webhook secret from MAX dashboard
2. Paste into adapter `secret` field
3. Restart adapter

### Long polling is slow

**Cause:** `long_poll_timeout_seconds` is set too high.

**Fix:** Lower it:

```json
{
  "long_poll_timeout_seconds": 10  // Poll more frequently
}
```

Or switch to webhooks for real-time.

### "Method not supported by SDK"

**Cause:** Official MAX SDK doesn't support the method yet.

**Fix:** Already handled! Adapter falls back to raw HTTP API automatically.

## See Also

- [Main README](../../README.md)
- [MAX API Documentation](https://max.im/api)
- [MAX Bot API SDK](https://github.com/maxim-top/max-botapi-python)
- Telegram adapter: [../telegram/README.md](../telegram/README.md)
- VK adapter: [../vk/README.md](../vk/README.md)
