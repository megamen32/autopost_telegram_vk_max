# Telegram Adapter

> **Telegram adapter** powered by Telethon. Receive messages from channels and chats; post text, photos, videos, documents, and more.

## Features

- 📱 **Telethon Client** — Full Telegram client library support
- 🤖 **Bot & User Modes** — Use a bot token OR Telegram user account (string session)
- 📨 **Incoming Messages** — Real-time message updates via Telethon event handlers
- 📸 **Rich Media** — Text, photos, videos, audio, documents, forwarded messages
- 🔄 **Forwarding** — Repost messages while preserving media and formatting
- 🎯 **Source Filtering** — Restrict incoming updates to specific chats
- 🛡️ **Session Persistence** — String session stored encrypted in database

## Setup

### 1. Create Telegram Application

Get your API credentials:

1. Go to [Telegram API Development Tools](https://my.telegram.org/apps)
2. Log in with your Telegram account
3. Click **"Create new application"**
4. Fill in app details (name, platform, etc.)
5. Copy **API ID** and **API Hash**

### 2. Get Bot Token (Optional)

If using bot mode instead of user mode:

1. Open [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot`
3. Choose a name and username
4. Copy the token: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 3. Configure Adapter Instance

Via Web UI or API:

```json
{
  "display_name": "Telegram main",
  "api_id": 1234567890,
  "receive_updates": true,
  "allowed_source_chat_ids": ["123456789", "-1001234567890"]
}
```

**Secrets** (encrypted in DB):
- `api_hash` — From my.telegram.org (required)
- `bot_token` — From @BotFather (optional; use for bot mode)
- `string_session` — User account session (optional; use for userbot mode)

### 4. Authenticate

#### Option A: Bot Mode (Recommended)

Easiest: just provide `bot_token` from @BotFather. No user login needed.

```json
{
  "api_id": 1234567890,
  "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
}
```

Limitations:
- Can only send to chats where the bot is a member
- Cannot access private messages (only groups/channels)
- Cannot edit messages

#### Option B: User Mode (Full Access)

For full access (private messages, editing, etc.), use a Telegram account:

1. Adapter starts with `api_id` + `api_hash` (no `bot_token`)
2. Telethon initiates login flow:
   - Asks for phone number
   - Sends code to Telegram app
   - User enters code
3. Session string stored as `string_session` secret

```json
{
  "api_id": 1234567890,
  "string_session": "1234567890abc123..."  // from first login
}
```

**Important:** String session is sensitive. It's encrypted at rest, but represents full account access.

## Publishing

### Text Message

```python
from app.domain.models import UnifiedPost
from app.domain.enums import Platform

post = UnifiedPost(
    source_platform=Platform.VK,
    source_adapter_id="vk-main",
    source_chat_id="100",
    source_message_id="200",
    text="Hello Telegram!",
    media=[]
)

# Send to channel by ID
message_id = await telegram_adapter.publish_post("-1001234567890", post)
```

### Photo Message

```python
from app.domain.models import MediaItem
from app.domain.enums import ContentType

post = UnifiedPost(
    ...
    text="Photo from VK",
    media=[
        MediaItem(
            type=ContentType.IMAGE,
            file_id="/path/to/photo.jpg",
            mime_type="image/jpeg"
        )
    ]
)

message_id = await telegram_adapter.publish_post("chat_id", post)
```

### Video / Audio / Document

```python
MediaItem(
    type=ContentType.VIDEO,
    file_id="/path/to/video.mp4",
    mime_type="video/mp4",
    filename="my_video.mp4"
)

MediaItem(
    type=ContentType.AUDIO,
    file_id="/path/to/song.mp3",
    mime_type="audio/mpeg"
)

MediaItem(
    type=ContentType.DOCUMENT,
    file_id="/path/to/file.pdf",
    mime_type="application/pdf"
)
```

## Receiving Messages

### Real-time Updates

Telethon receives messages in real time via event handlers:

```json
{
  "receive_updates": true,
  "allowed_source_chat_ids": ["-1001234567890", "123456789"]
}
```

The adapter listens for:
- **NewMessage** — Text, photos, forwarded messages, etc.
- **Edits** — Message edits (if configured)

### Source Filtering

Only accept messages from specific chats:

```json
{
  "allowed_source_chat_ids": [
    "123456789",           // Private chat
    "-1001234567890",      // Supergroup/channel (negative)
    "100"                  // Basic group
  ]
}
```

If `allowed_source_chat_ids` is empty, all chats are accepted (if `check_all_chats` is true).

### Chat ID Format

- **Private chat:** Positive ID (e.g., `123456789`)
- **Channel/supergroup:** Negative ID (e.g., `-1001234567890`)
- **Basic group:** ID with prefix (e.g., `-100123456789`)

## Configuration

### Simple Settings

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `display_name` | str | — | Human-readable name in UI |
| `api_id` | int | — | From my.telegram.org (required) |
| `receive_updates` | bool | true | Listen for incoming messages |

### Advanced Settings

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `bot_token` | str (secret) | — | Token from @BotFather (optional) |
| `string_session` | str (secret) | — | User session string (optional) |
| `session_name` | str | `autopost_sync_{instance_id}` | Local session file name |
| `sequential_updates` | bool | false | Process updates one-at-a-time (debug mode) |
| `allowed_source_chat_ids` | list | `[]` | Restrict incoming to these chats |
| `check_all_chats` | bool | false | Extra filtering for source selection |
| `log_level` | choice | `INFO` | Verbosity: `ERROR`, `WARNING`, `INFO`, `DEBUG` |

## Error Handling

### Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `SessionPasswordNeeded` | Account has 2FA enabled | Provide password during login |
| `PhoneNumberInvalid` | Wrong phone format | Use international format: `+1234567890` |
| `ApiIdInvalid` | Wrong API ID | Double-check at my.telegram.org |
| `Bot token is invalid` | Expired or incorrect token | Get new token from @BotFather |
| `Cannot send messages to this chat` | Bot not member or lacks permissions | Add bot to chat; grant message permission |

### Debugging

Enable debug output:

```json
{
  "log_level": "DEBUG"
}
```

View logs:

```bash
curl http://localhost:8000/api/debug/adapter-logs?instance_id=telegram-main
```

## Incoming Event Format

When a Telegram message arrives, it's converted to `UnifiedPost`:

```python
UnifiedPost(
    source_platform=Platform.TELEGRAM,
    source_adapter_id="telegram-main",
    source_chat_id="-1001234567890",
    source_message_id="123",
    text="Message text",
    media=[
        MediaItem(
            type=ContentType.IMAGE,
            url="https://example.com/photo.jpg",
            filename="photo.jpg",
            mime_type="image/jpeg"
        )
    ],
    is_repost=False,
)
```

This can then be routed to other platforms via sync rules.

## Testing

```bash
# Unit tests
pytest tests/unit/test_telegram_adapter.py -v

# Manual test: send message to your channel
python -c "
import asyncio
from app.adapters.telegram.adapter import TelegramAdapter

async def test():
    adapter = TelegramAdapter(
        instance_id='test',
        api_id=1234567890,
        bot_token='...',
    )
    await adapter.startup()
    await adapter.publish_post('your_channel_id', UnifiedPost(...))

asyncio.run(test())
"
```

## Advanced

### Sequential vs Parallel Updates

By default, updates are processed in parallel (faster):

```json
{
  "sequential_updates": false
}
```

For debugging race conditions or message ordering issues:

```json
{
  "sequential_updates": true
}
```

### Session String Storage

A string session encodes the Telethon client state. It's encrypted before storage:

```python
# First login (interactive)
# => string_session generated and stored

# Subsequent startups
# => string_session loaded from DB, decrypted, used
```

No login flow needed after first setup.

### File Download

Large media files are downloaded on-demand during publishing:

```python
# Telegram → Download → temporary /tmp/file.mp4
# → Upload to target platform
```

File size limits depend on target platform.

## Troubleshooting

### "Session file was not found"

**Cause:** Using user mode without string session.

**Fix:** Provide string session from a previous login, or use bot token mode.

### "The session file is corrupted"

**Cause:** String session decryption failed.

**Fix:**
1. Check `SECRETS_ENCRYPTION_KEY` is consistent
2. Re-authenticate to generate new session

### "Too many requests (429)"

**Cause:** Sending too many messages to Telegram.

**Fix:** Enable delivery queue with backoff:

```json
{
  "delivery_max_attempts": 5,
  "delivery_retry_base_seconds": 10
}
```

### "Cannot upload file to Telegram"

**Cause:** File too large or unsupported format.

**Fix:** Check Telegram's file size limits:
- Photos: < 5 MB
- Videos: < 2 GB (for regular chat), 4 GB (for premium)
- Documents: < 2 GB

## See Also

- [Main README](../../README.md)
- [Telethon Documentation](https://docs.telethon.dev)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- VK adapter: [../vk/README.md](../vk/README.md)
- MAX adapter: [../max/README.md](../max/README.md)
