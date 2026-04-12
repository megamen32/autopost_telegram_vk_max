from __future__ import annotations

import asyncio

import pytest

from app.adapters.telegram.adapter import TelegramAdapter
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost


class _FakeResult:
    def __init__(self, message_id: int) -> None:
        self.id = message_id


class _FakeTelegramClient:
    def __init__(self) -> None:
        self.send_message_calls: list[dict] = []
        self.send_file_calls: list[dict] = []

    async def send_message(self, *, entity, message: str):
        self.send_message_calls.append({"entity": entity, "message": message})
        return _FakeResult(101)

    async def send_file(self, *, entity, file, caption: str, force_document: bool, supports_streaming: bool):
        self.send_file_calls.append(
            {
                "entity": entity,
                "file": file,
                "caption": caption,
                "force_document": force_document,
                "supports_streaming": supports_streaming,
            }
        )
        return _FakeResult(202)


def _make_adapter() -> TelegramAdapter:
    return TelegramAdapter(
        instance_id="tg-instance",
        api_id=123456,
        api_hash="api-hash",
        string_session="string-session",
        receive_updates=False,
    )


async def _fake_get_client(self, required: bool = False):
    return self._fake_client


def test_telegram_publish_text_only_uses_send_message(monkeypatch):
    adapter = _make_adapter()
    client = _FakeTelegramClient()
    adapter._fake_client = client
    monkeypatch.setattr(TelegramAdapter, "_get_client", _fake_get_client)

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-source",
        source_chat_id="1001",
        source_message_id="42",
        text="Hello from Telegram",
        media=[],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="7508316104", post=post))

    assert post_id == "101"
    assert client.send_message_calls == [{"entity": 7508316104, "message": "Hello from Telegram"}]
    assert client.send_file_calls == []


@pytest.mark.parametrize(
    "content_type,filename,mime_type,expected_force_document,expected_supports_streaming",
    [
        (ContentType.IMAGE, "image.jpg", "image/jpeg", False, False),
        (ContentType.DOCUMENT, "report.pdf", "application/pdf", True, False),
        (ContentType.AUDIO, "song.mp3", "audio/mpeg", False, False),
        (ContentType.VIDEO, "video.mp4", "video/mp4", False, True),
    ],
)
def test_telegram_publish_media_uses_local_file_and_type_flags(
    monkeypatch,
    tmp_path,
    content_type,
    filename,
    mime_type,
    expected_force_document,
    expected_supports_streaming,
):
    adapter = _make_adapter()
    client = _FakeTelegramClient()
    adapter._fake_client = client
    monkeypatch.setattr(TelegramAdapter, "_get_client", _fake_get_client)

    local_file = tmp_path / filename
    local_file.write_bytes(b"payload-bytes")

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="tg-source",
        source_chat_id="1001",
        source_message_id="42",
        text="Media caption",
        media=[
            MediaItem(
                type=content_type,
                file_id="https://t.me/channel/123",
                url=str(local_file),
                mime_type=mime_type,
                filename=filename,
            )
        ],
    )

    post_id = asyncio.run(adapter.publish_post(chat_id="7508316104", post=post))

    assert post_id == "202"
    assert client.send_message_calls == []
    assert client.send_file_calls == [
        {
            "entity": 7508316104,
            "file": str(local_file),
            "caption": "Media caption",
            "force_document": expected_force_document,
            "supports_streaming": expected_supports_streaming,
        }
    ]
