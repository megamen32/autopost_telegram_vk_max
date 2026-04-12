from __future__ import annotations

import asyncio

from app.adapters.vk.browser_publisher import VkBrowserPublisher
from app.domain.enums import ContentType
from app.domain.models import MediaItem


def test_vk_browser_publisher_prepares_video_audio_and_documents(tmp_path):
    video_path = tmp_path / "video.mp4"
    audio_path = tmp_path / "song.mp3"
    doc_path = tmp_path / "report.pdf"
    video_path.write_bytes(b"video-bytes")
    audio_path.write_bytes(b"audio-bytes")
    doc_path.write_bytes(b"doc-bytes")

    publisher = VkBrowserPublisher(cdp_url="http://127.0.0.1:9222", group_id=12345)

    files = asyncio.run(
        publisher._prepare_files(
            media=[
                MediaItem(type=ContentType.VIDEO, url=str(video_path), mime_type="video/mp4", filename="video.mp4"),
                MediaItem(type=ContentType.AUDIO, url=str(audio_path), mime_type="audio/mpeg", filename="song.mp3"),
                MediaItem(type=ContentType.DOCUMENT, url=str(doc_path), mime_type="application/pdf", filename="report.pdf"),
            ],
            temp_dir=tmp_path,
        )
    )

    assert files == [video_path, audio_path, doc_path]
