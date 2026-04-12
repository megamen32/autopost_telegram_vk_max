import os

import pytest

from app.adapters.vk.adapter import VkAdapter
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost


LIVE_VK_GROUP_ID = os.getenv("LIVE_VK_GROUP_ID")
LIVE_VK_TOKEN = os.getenv("LIVE_VK_TOKEN")
LIVE_VK_IMAGE_URL = os.getenv("LIVE_VK_IMAGE_URL")
LIVE_VK_CHAT_ID = os.getenv("LIVE_VK_CHAT_ID")
RUN_LIVE_VK_TESTS = os.getenv("RUN_LIVE_VK_TESTS") == "true"


@pytest.mark.skipif(
    not RUN_LIVE_VK_TESTS or not LIVE_VK_GROUP_ID or not LIVE_VK_TOKEN or not LIVE_VK_IMAGE_URL or not LIVE_VK_CHAT_ID,
    reason="live VK env vars are not set",
)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_vk_publish_photo() -> None:
    adapter = VkAdapter(
        instance_id="vk-live-test",
        token=LIVE_VK_TOKEN,
        group_id=int(LIVE_VK_GROUP_ID),
    )

    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="telegram-live-test",
        source_chat_id="telegram-live-chat",
        source_message_id="telegram-live-message",
        text="Live integration test from Telegram photo to VK wall photo",
        media=[
            MediaItem(
                type=ContentType.IMAGE,
                url=LIVE_VK_IMAGE_URL,
                mime_type="image/jpeg",
                filename="live-vk-photo.jpg",
            )
        ],
    )

    post_id = await adapter.publish_post(chat_id=LIVE_VK_CHAT_ID, post=post)
    assert str(post_id).isdigit()
