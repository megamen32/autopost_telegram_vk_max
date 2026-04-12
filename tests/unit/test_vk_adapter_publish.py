import asyncio

from app.adapters.vk import adapter as vk_adapter_module
from app.adapters.vk.adapter import VkAdapter
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost


def test_vk_adapter_posts_telegram_image_to_vk(monkeypatch):
    class FakeClient:
        def __init__(self, token: str, api_version: str = "5.199") -> None:
            self.token = token
            self.api_version = api_version

        async def call_method(self, method: str, params: dict):
            if method == "photos.getWallUploadServer":
                return {"upload_url": "https://upload.vk.com/photo"}
            if method == "photos.saveWallPhoto":
                return [{"owner_id": -12345, "id": 67890}]
            if method == "wall.post":
                return {"post_id": 100}
            raise AssertionError(f"Unexpected method: {method}")

        async def download_bytes(self, url: str) -> bytes:
            return b"image-bytes"

        async def upload_file(self, upload_url: str, *, form_field: str, filename: str, content: bytes, content_type: str | None):
            return {"photo": "photo_data", "server": "server", "hash": "hash"}

    monkeypatch.setattr(vk_adapter_module, "VkClient", FakeClient)

    adapter = VkAdapter(
        instance_id="vk-instance",
        token="group-token",
        group_id=12345,
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="Привет, это изображение из Telegram",
        media=[
            MediaItem(
                type=ContentType.IMAGE,
                url="https://example.com/image.jpg",
                mime_type="image/jpeg",
                filename="image.jpg",
            )
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert post_id == "100"


def test_vk_adapter_falls_back_to_second_media_token(monkeypatch):
    created_tokens: list[str] = []

    class FakeClient:
        def __init__(self, token: str, api_version: str = "5.199") -> None:
            self.token = token
            self.api_version = api_version
            created_tokens.append(token)

        async def call_method(self, method: str, params: dict):
            if method == "photos.getWallUploadServer":
                return {"upload_url": "https://upload.vk.com/photo"}
            if method == "photos.saveWallPhoto":
                return [{"owner_id": -12345, "id": 67890}]
            if method == "wall.post":
                return {"post_id": 100}
            raise AssertionError(f"Unexpected method: {method}")

        async def download_bytes(self, url: str) -> bytes:
            return b"image-bytes"

        async def upload_file(self, upload_url: str, *, form_field: str, filename: str, content: bytes, content_type: str | None):
            return {"photo": "photo_data", "server": "server", "hash": "hash"}

    monkeypatch.setattr(vk_adapter_module, "VkClient", FakeClient)

    adapter = VkAdapter(
        instance_id="vk-instance",
        token="group-token",
        user_access_token_for_media="user-token",
        group_id=12345,
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="Привет, это изображение из Telegram",
        media=[
            MediaItem(
                type=ContentType.IMAGE,
                url="https://example.com/image.jpg",
                mime_type="image/jpeg",
                filename="image.jpg",
            )
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert post_id == "100"
    assert created_tokens == ["user-token", "user-token"]


def test_vk_adapter_refreshes_expired_user_token_before_publish(monkeypatch):
    created_tokens: list[str] = []
    refresh_calls: list[dict] = []

    class FakeClient:
        def __init__(self, token: str, api_version: str = "5.199") -> None:
            self.token = token
            self.api_version = api_version
            created_tokens.append(token)

        async def call_method(self, method: str, params: dict):
            if method == "photos.getWallUploadServer":
                return {"upload_url": "https://upload.vk.com/photo"}
            if method == "photos.saveWallPhoto":
                return [{"owner_id": -12345, "id": 67890}]
            if method == "wall.post":
                return {"post_id": 101}
            raise AssertionError(f"Unexpected method: {method}")

        async def download_bytes(self, url: str) -> bytes:
            return b"image-bytes"

        async def upload_file(self, upload_url: str, *, form_field: str, filename: str, content: bytes, content_type: str | None):
            return {"photo": "photo_data", "server": "server", "hash": "hash"}

    async def fake_refresh_access_token(*, client_id: str, refresh_token: str, device_id: str, scope=None, state=None):
        refresh_calls.append(
            {
                "client_id": client_id,
                "refresh_token": refresh_token,
                "device_id": device_id,
            }
        )
        return {
            "access_token": "refreshed-user-token",
            "refresh_token": "refreshed-refresh-token",
            "expires_in": 3600,
        }

    monkeypatch.setattr(vk_adapter_module, "VkClient", FakeClient)
    monkeypatch.setattr(vk_adapter_module, "refresh_access_token", fake_refresh_access_token)

    adapter = VkAdapter(
        instance_id="vk-instance",
        token="group-token",
        user_access_token_for_media="expired-user-token",
        vk_id_client_id="client-123",
        vk_oauth_refresh_token="refresh-123",
        vk_oauth_device_id="device-123",
        vk_oauth_token_expires_at=1,
        group_id=12345,
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="Привет, это изображение из Telegram",
        media=[
            MediaItem(
                type=ContentType.IMAGE,
                url="https://example.com/image.jpg",
                mime_type="image/jpeg",
                filename="image.jpg",
            )
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert post_id == "101"
    assert refresh_calls == [
        {
            "client_id": "client-123",
            "refresh_token": "refresh-123",
            "device_id": "device-123",
        }
    ]
    assert adapter.user_access_token_for_media == "refreshed-user-token"
    assert adapter.vk_oauth_refresh_token == "refreshed-refresh-token"
    assert created_tokens == ["refreshed-user-token", "refreshed-user-token"]


def test_vk_adapter_switches_to_browser_fallback_when_api_publish_fails(monkeypatch):
    class FakeClient:
        def __init__(self, token: str, api_version: str = "5.199") -> None:
            self.token = token
            self.api_version = api_version

        async def call_method(self, method: str, params: dict):
            if method == "photos.getWallUploadServer":
                raise RuntimeError("Access denied: no access to call this method")
            raise AssertionError(f"Unexpected method: {method}")

    class FakeBrowserPublisher:
        def __init__(self, *, cdp_url: str, group_id: int, timeout_ms: int = 120000) -> None:
            assert cdp_url == "http://127.0.0.1:9222"
            assert group_id == 12345

        async def publish_post(self, *, text: str, media: list[MediaItem]) -> str:
            assert text == "Browser fallback text"
            assert len(media) == 1
            assert media[0].type == ContentType.IMAGE
            return "777"

    monkeypatch.setattr(vk_adapter_module, "VkClient", FakeClient)
    monkeypatch.setattr(vk_adapter_module, "VkBrowserPublisher", FakeBrowserPublisher)

    adapter = VkAdapter(
        instance_id="vk-instance",
        token="group-token",
        group_id=12345,
        browser_cdp_url="http://127.0.0.1:9222",
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="Browser fallback text",
        media=[
            MediaItem(
                type=ContentType.IMAGE,
                url="https://example.com/image.jpg",
                mime_type="image/jpeg",
                filename="image.jpg",
            )
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert post_id == "777"


def test_vk_adapter_can_publish_via_browser_without_api_tokens(monkeypatch):
    class FakeBrowserPublisher:
        def __init__(self, *, cdp_url: str, group_id: int, timeout_ms: int = 120000) -> None:
            assert cdp_url == "http://127.0.0.1:9222"
            assert group_id == 12345

        async def publish_post(self, *, text: str, media: list[MediaItem]) -> str:
            assert text == "Text only browser post"
            assert media == []
            return "888"

    monkeypatch.setattr(vk_adapter_module, "VkBrowserPublisher", FakeBrowserPublisher)

    adapter = VkAdapter(
        instance_id="vk-instance",
        group_id=12345,
        browser_cdp_url="http://127.0.0.1:9222",
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="Text only browser post",
        media=[],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert adapter.enabled is True
    assert post_id == "888"


def test_vk_adapter_uploads_video_document_and_audio_via_api(monkeypatch):
    calls: list[tuple] = []

    class FakeClient:
        def __init__(self, token: str, api_version: str = "5.199") -> None:
            self.token = token
            self.api_version = api_version

        async def call_method(self, method: str, params: dict):
            calls.append(("call_method", method, params))
            if method == "video.save":
                assert params["group_id"] == 12345
                assert params["wallpost"] == 1
                return {"upload_url": "https://upload.vk.com/video", "owner_id": -12345, "video_id": 701}
            if method == "docs.getWallUploadServer":
                assert params == {"group_id": 12345}
                return {"upload_url": "https://upload.vk.com/doc"}
            if method == "docs.save":
                assert params == {"file": "doc-file-token"}
                return [{"owner_id": -12345, "id": 702}]
            if method == "audio.getUploadServer":
                assert params == {}
                return {"upload_url": "https://upload.vk.com/audio"}
            if method == "audio.save":
                assert params == {"server": "11", "audio": "audio-token", "hash": "audio-hash"}
                return [{"owner_id": -12345, "id": 703}]
            if method == "wall.post":
                assert params["attachments"] == "video-12345_701,doc-12345_702,audio-12345_703"
                assert params["message"] == "Mixed media"
                return {"post_id": 200}
            raise AssertionError(f"Unexpected method: {method}")

        async def download_bytes(self, url: str) -> bytes:
            calls.append(("download_bytes", url))
            return f"bytes-for:{url}".encode()

        async def upload_file(self, upload_url: str, *, form_field: str, filename: str, content: bytes, content_type: str | None):
            calls.append(("upload_file", upload_url, form_field, filename, content_type))
            if "video" in upload_url:
                return {"owner_id": -12345, "video_id": 701}
            if "doc" in upload_url:
                return {"file": "doc-file-token"}
            if "audio" in upload_url:
                return {"server": "11", "audio": "audio-token", "hash": "audio-hash"}
            raise AssertionError(f"Unexpected upload url: {upload_url}")

    monkeypatch.setattr(vk_adapter_module, "VkClient", FakeClient)

    adapter = VkAdapter(
        instance_id="vk-instance",
        token="group-token",
        group_id=12345,
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="Mixed media",
        media=[
            MediaItem(
                type=ContentType.VIDEO,
                url="https://example.com/video.mp4",
                mime_type="video/mp4",
                filename="video.mp4",
            ),
            MediaItem(
                type=ContentType.DOCUMENT,
                url="https://example.com/report.pdf",
                mime_type="application/pdf",
                filename="report.pdf",
            ),
            MediaItem(
                type=ContentType.AUDIO,
                url="https://example.com/song.mp3",
                mime_type="audio/mpeg",
                filename="song.mp3",
            ),
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert post_id == "200"
    assert ("call_method", "video.save", {"group_id": 12345, "name": "video.mp4", "wallpost": 1}) in calls
    assert ("call_method", "docs.getWallUploadServer", {"group_id": 12345}) in calls
    assert ("call_method", "audio.getUploadServer", {}) in calls


def test_vk_adapter_switches_to_browser_fallback_for_media_only_post(monkeypatch):
    class FakeClient:
        def __init__(self, token: str, api_version: str = "5.199") -> None:
            self.token = token
            self.api_version = api_version

        async def call_method(self, method: str, params: dict):
            if method == "video.save":
                raise RuntimeError("Access denied")
            raise AssertionError(f"Unexpected method: {method}")

    class FakeBrowserPublisher:
        def __init__(self, *, cdp_url: str, group_id: int, timeout_ms: int = 120000) -> None:
            assert cdp_url == "http://127.0.0.1:9222"
            assert group_id == 12345

        async def publish_post(self, *, text: str, media: list[MediaItem]) -> str:
            assert text == ""
            assert [item.type for item in media] == [ContentType.VIDEO, ContentType.DOCUMENT, ContentType.AUDIO]
            return "909"

    monkeypatch.setattr(vk_adapter_module, "VkClient", FakeClient)
    monkeypatch.setattr(vk_adapter_module, "VkBrowserPublisher", FakeBrowserPublisher)

    adapter = VkAdapter(
        instance_id="vk-instance",
        token="group-token",
        group_id=12345,
        browser_cdp_url="http://127.0.0.1:9222",
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-instance",
        source_chat_id="1001",
        source_message_id="42",
        text="",
        media=[
            MediaItem(
                type=ContentType.VIDEO,
                url="https://example.com/video.mp4",
                mime_type="video/mp4",
                filename="video.mp4",
            ),
            MediaItem(
                type=ContentType.DOCUMENT,
                url="https://example.com/report.pdf",
                mime_type="application/pdf",
                filename="report.pdf",
            ),
            MediaItem(
                type=ContentType.AUDIO,
                url="https://example.com/song.mp3",
                mime_type="audio/mpeg",
                filename="song.mp3",
            ),
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="-12345", post=post))

    assert post_id == "909"
