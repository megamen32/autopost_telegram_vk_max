"""
Test: load VK adapter from DB, refresh token if needed, post photo to group.

Usage:
    python test_vk_photo_post.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from io import BytesIO

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.adapters.vk.adapter import VkAdapter
from app.adapters.vk.client import VkClient
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost


VK_GROUP_ID = 237416141
INSTANCE_ID = "vk-vk4"


def generate_test_image() -> bytes:
    """Generate a simple PNG test image (red square 200x200)."""
    try:
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(255, 50, 50))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        pass

    import struct
    import zlib

    width, height = 200, 200
    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00"
        raw_data += b"\xff\x32\x32" * width

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressed = zlib.compress(raw_data)

    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr_data)
    png += png_chunk(b"IDAT", compressed)
    png += png_chunk(b"IEND", b"")
    return png


async def load_adapter_from_db() -> VkAdapter:
    """Load VK adapter instance from DB with decrypted secrets."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings
    from app.repositories.adapter_instances_repo import AdapterInstancesRepo
    from app.utils.crypto import SecretBox
    from app.adapters.definitions import VK_DEFINITION

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        repo = AdapterInstancesRepo(session, SecretBox(settings.secrets_encryption_key))
        instance = await repo.get(INSTANCE_ID, include_secrets=True)

    await engine.dispose()

    if not instance:
        raise RuntimeError(f"Instance {INSTANCE_ID} not found in DB")

    config = instance.get("config") or {}
    secrets = instance.get("secrets") or {}

    print(f"Loaded instance: {instance['id']}")
    print(f"  display_name: {instance['display_name']}")
    print(f"  group_id: {config.get('group_id')}")
    print(f"  vk_id_client_id: {config.get('vk_id_client_id')}")
    print(f"  vk_oauth_token_expires_at: {config.get('vk_oauth_token_expires_at')}")
    print(f"  has user_access_token: {'user_access_token_for_media' in secrets and bool(secrets['user_access_token_for_media'])}")
    print(f"  has refresh_token: {'vk_oauth_refresh_token' in secrets and bool(secrets['vk_oauth_refresh_token'])}")
    print(f"  has device_id: {'vk_oauth_device_id' in secrets and bool(secrets['vk_oauth_device_id'])}")
    print(f"  has group_token: {'token' in secrets and bool(secrets['token'])}")

    # Check token expiry
    expires_at = config.get("vk_oauth_token_expires_at")
    if expires_at:
        now = int(time.time())
        diff = int(expires_at) - now
        if diff > 0:
            print(f"  token expires in: {diff}s ({diff//3600}h {(diff%3600)//60}m)")
        else:
            print(f"  token EXPIRED {-diff}s ago")

    # Create adapter using factory pattern
    adapter = VkAdapter(
        instance_id=instance["id"],
        token=secrets.get("token"),
        group_id=config.get("group_id"),
        user_access_token_for_media=secrets.get("user_access_token_for_media"),
        vk_id_client_id=config.get("vk_id_client_id"),
        vk_oauth_refresh_token=secrets.get("vk_oauth_refresh_token"),
        vk_oauth_device_id=secrets.get("vk_oauth_device_id"),
        vk_oauth_token_expires_at=config.get("vk_oauth_token_expires_at"),
        log_level="DEBUG",
    )
    return adapter


async def main():
    print("=" * 60)
    print("VK Photo Post Test (via adapter from DB)")
    print("=" * 60)

    # Load adapter
    adapter = await load_adapter_from_db()
    print(f"\nAdapter enabled: {adapter.enabled}")
    print(f"Can refresh: {adapter._can_refresh_user_token()}")

    # Try refresh first
    if adapter._can_refresh_user_token():
        print("\nRefreshing user token...")
        try:
            refreshed = await adapter._refresh_user_token_if_needed()
            print(f"  Refreshed: {refreshed}")
            if adapter.user_access_token_for_media:
                print(f"  New token: {adapter.user_access_token_for_media[:30]}...")
        except Exception as exc:
            print(f"  Refresh failed: {exc}")
            print("  Will try with existing token...")

    # Save test image to temp file
    image_data = generate_test_image()
    tmp_path = "/tmp/test_vk_image.png"
    with open(tmp_path, "wb") as f:
        f.write(image_data)
    print(f"\nTest image saved: {tmp_path} ({len(image_data)} bytes)")

    # Create UnifiedPost with a photo
    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_adapter_id="test",
        source_chat_id="test",
        source_message_id="test",
        text=f"Test post with photo from autopost_sync @ {time.strftime('%Y-%m-%d %H:%M:%S')}",
        media=[
            MediaItem(
                type=ContentType.IMAGE,
                url=None,
                file_id=tmp_path,  # local file path
                mime_type="image/png",
                filename="test_image.png",
            )
        ],
    )

    # Publish
    chat_id = str(VK_GROUP_ID)
    print(f"\nPublishing to group {chat_id}...")
    try:
        post_id = await adapter.publish_post(chat_id, post)
        print(f"\n{'='*60}")
        print(f"SUCCESS! Post ID: {post_id}")
        print(f"URL: https://vk.com/wall-{VK_GROUP_ID}_{post_id}")
        print(f"{'='*60}")
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        import traceback
        traceback.print_exc()

        # If we have a user token, try raw API call for diagnostics
        if adapter.user_access_token_for_media:
            print("\n--- Diagnostic: trying raw API call ---")
            client = VkClient(adapter.user_access_token_for_media, api_version="5.199")
            try:
                result = await client.call_method("users.get", {})
                print(f"  users.get OK: {result}")
            except Exception as e2:
                print(f"  users.get failed: {e2}")

            try:
                result = await client.call_method("groups.getById", {"group_id": VK_GROUP_ID})
                print(f"  groups.getById OK: {result}")
            except Exception as e2:
                print(f"  groups.getById failed: {e2}")


if __name__ == "__main__":
    asyncio.run(main())
