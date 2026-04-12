# VK Adapter

> **VK (VKontakte) adapter** for posting to communities, handling incoming events, and media uploads. Supports both OAuth user authentication and community tokens.

## Features

- 🔐 **VK ID OAuth 2.0** — Official VK ID PKCE authentication with automatic token refresh
- 📸 **Media Support** — Photos, videos, documents, and multi-media posts
- 🔄 **Bidirectional** — Both incoming Callback API webhooks and long polling; outgoing posts
- 🌐 **API Version Agnostic** — Configurable VK API version (default: 5.199)
- 💾 **Token Encryption** — Secrets stored encrypted at rest in database
- 🔁 **Automatic Token Refresh** — Refresh tokens handled transparently during publishing
- 🌉 **Browser Fallback** — Optional Chrome DevTools Protocol fallback for automation scenarios

## Setup

### 1. Create VK App (Community Tokens)

For incoming events and legacy community operations:

1. Go to [VK Developers](https://vk.com/dev)
2. Create a new **Standalone** application
3. Copy the **App ID** to use as `token` later (via Callback API configuration)
4. Enable required API methods in app permissions

### 2. Enable VK ID (User Authentication)

For publishing media and posts as a user:

1. Go to [VK ID Workplace](https://id.vk.com)
2. Create or select your application
3. Copy the **Client ID** → save as `vk_id_client_id` in adapter config
4. Configure redirect URI: `https://your-domain/auth/vk/callback` (or local `http://127.0.0.1:8000/auth/vk/callback`)
5. Enable **User API** access with `offline` scope

### 3. Configure Adapter Instance

Via the Web UI or API, set up your VK adapter:

```json
{
  "display_name": "VK main",
  "group_id": 237416141,
  "vk_id_client_id": "1234567890",
  "receive_updates": true,
  "receive_mode": "long_poll",
  "api_version": "5.199"
}
```

**Secrets** (encrypted in DB):
- `user_access_token_for_media` — Primary token from VK ID OAuth
- `vk_oauth_refresh_token` — Refresh token for auto-renewal
- `vk_oauth_device_id` — Device ID for PKCE flow
- `token` — (optional) Community token for Callback API

### 4. Start OAuth Flow

Click **"Authenticate with VK"** in Web UI:

1. Browser opens VK ID login
2. User grants permission (posts, media uploads, offline access)
3. Server exchanges code for `access_token` + `refresh_token`
4. Tokens stored encrypted in database

## Publishing

### Text Post

```python
from app.domain.models import UnifiedPost
from app.domain.enums import Platform

post = UnifiedPost(
    source_platform=Platform.TELEGRAM,
    source_adapter_id="telegram-main",
    source_chat_id="123",
    source_message_id="456",
    text="Hello VK!",
    media=[]
)

# Publish to group 237416141
post_id = await vk_adapter.publish_post("237416141", post)
# => "789_1234" (wall post ID)
```

### Photo Post

```python
from app.domain.models import MediaItem
from app.domain.enums import ContentType

post = UnifiedPost(
    source_platform=Platform.TELEGRAM,
    source_adapter_id="telegram-main",
    source_chat_id="123",
    source_message_id="456",
    text="Photo from Telegram",
    media=[
        MediaItem(
            type=ContentType.IMAGE,
            file_id="/path/to/photo.jpg",  # local file or URL
            mime_type="image/jpeg"
        )
    ]
)

post_id = await vk_adapter.publish_post("237416141", post)
```

### Video Post

```python
MediaItem(
    type=ContentType.VIDEO,
    file_id="/path/to/video.mp4",
    mime_type="video/mp4",
    filename="my_video.mp4"
)
```

## Receiving Events

### Long Polling

Default mode. Adapter polls VK Callback API for new events:

```json
{
  "receive_updates": true,
  "receive_mode": "long_poll",
  "allowed_source_chat_ids": ["100", "-237416141"]
}
```

Events arrive via:
- `message_new` — Private messages
- `wall_post_new` — New wall posts in community

### Webhook / Callback API

For production, use VK's official webhook delivery:

1. **Set Callback API server address** in VK Community settings:
   - Admin → Settings → Callback API
   - Server address: `https://your-domain/webhooks/vk-main`
   - API version: `5.199`

2. **Set Callback API settings** in adapter config:
   ```json
   {
     "receive_mode": "webhook",
     "token": "your_community_token"
   }
   ```

3. The `POST /webhooks/vk-main` endpoint automatically:
   - Verifies signature via `secret`
   - Routes events to `on_post` callback
   - Returns confirmation token to VK

## Token Lifecycle

### First Authentication

1. User clicks **"Authenticate with VK"**
2. VK ID OAuth flow (PKCE, no code verifier exposed)
3. Server receives:
   - `access_token` — expires in ~24h
   - `refresh_token` — lifetime token
   - `expires_at` — expiration timestamp
4. Both tokens encrypted and stored in DB

### Auto-Refresh

Before publishing, if token is expired or will expire in <5 minutes:

```python
refreshed = await adapter._refresh_user_token_if_needed()
# If true: new access_token stored, adapter.user_access_token_for_media updated
```

This is **automatic** during `publish_post()`.

### Manual Refresh

If needed:

```python
await adapter._refresh_user_token_if_needed()
```

## Media Upload Pipeline

### Photos

1. `photos.getWallUploadServer()` → get upload endpoint
2. Upload file via HTTP POST to VK's upload server
3. `photos.saveWallPhoto()` → convert upload to photo object
4. Attach to `wall.post()` as `attachments`

### Videos

1. `video.save()` → reserve video slot and get upload endpoint
2. Upload file via HTTP POST
3. Attach to `wall.post()` as `attachments`

### Documents

1. `docs.getWallUploadServer()` → get upload endpoint
2. Upload file
3. `docs.save()` → convert to document object
4. Attach to `wall.post()`

## Error Handling

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid user_id` | User token expired, not refreshed | Token likely expired; re-authenticate |
| `Photo upload server error` | Temporary VK issue | Retry with backoff |
| `Method is unavailable for this profile type` | Using wrong token type | Ensure VK ID user token, not group token |
| `Access token invalid or expired` | Token not refreshed before use | Check `vk_oauth_token_expires_at` |

### Debugging

Enable debug logging:

```json
{
  "log_level": "DEBUG"
}
```

View adapter logs:

```bash
curl http://localhost:8000/api/debug/adapter-logs?instance_id=vk-main
```

## Advanced Configuration

### Browser Fallback (Local Development)

For local automation without exposing VK API tokens, use Chrome DevTools Protocol:

1. Start Chrome with remote debugging:
   ```bash
   open -na "Google Chrome" --args --remote-debugging-port=9222
   ```

2. Log in to VK in that Chrome instance

3. Point adapter to CDP:
   ```json
   {
     "vk_browser_cdp_url": "http://127.0.0.1:9222"
   }
   ```

4. Adapter publishes via browser automation (slower, but no API tokens)

**Note:** This is a development-only fallback. Production should use official VK ID OAuth.

### Custom API Version

```json
{
  "api_version": "5.200"
}
```

## Testing

```bash
# Unit tests
pytest tests/unit/test_vk_adapter.py -v

# Integration test (requires database + VK config)
python test_vk_photo_post.py
```

## Troubleshooting

### "Security Error" during OAuth

**Cause:** Using VK ID app with old `oauth.vk.com` endpoint.

**Fix:** Ensure you're using official VK ID at `https://id.vk.com/oauth/authorize` (not `oauth.vk.com`).

### "Method is unavailable"

**Cause:** Using a VK ID identity token instead of a VK API user token.

**Fix:** VK ID tokens are for identity only. Use the official VK OAuth flow at `/api/auth/vk/start` to get a proper API token.

### Token not refreshing

**Cause:** `refresh_token` missing or expired (>6 months).

**Fix:** Re-authenticate via `/api/auth/vk/start` to get a new refresh token.

### Photo upload fails

**Cause:** Token doesn't have media permissions.

**Fix:** Re-authenticate with offline scope and media permissions enabled.

## API Reference

### `publish_post(chat_id, post) → str`

Publish a UnifiedPost to a wall or community. Returns post ID.

### `_refresh_user_token_if_needed() → bool`

Refresh access token if expired or expiring soon. Returns True if refreshed.

### `parse_incoming_event(payload) → UnifiedPost | None`

Parse a VK webhook payload into UnifiedPost.

## See Also

- [Main README](../../README.md)
- [VK API Docs](https://dev.vk.com/ru)
- [VK ID OAuth Docs](https://id.vk.ru)
- Telegram adapter: [../telegram/README.md](../telegram/README.md)
- MAX adapter: [../max/README.md](../max/README.md)
