import os
import time
from pathlib import Path

from fastapi.testclient import TestClient


def test_smoke(tmp_path: Path):
    db_path = tmp_path / 'test.db'
    os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{db_path}'
    os.environ['AUTO_CREATE_TABLES'] = 'true'

    from app.main import app

    with TestClient(app) as client:
        health = client.get('/health')
        assert health.status_code == 200
        assert health.json()['ok'] is True

        rule_resp = client.post(
            '/rules',
            json={
                'source_platform': 'telegram',
                'target_platform': 'vk',
                'enabled': True,
                'content_policy': {
                    'allow_text': True,
                    'allow_images': True,
                    'allow_video': True,
                    'allow_audio': False,
                    'allow_documents': False,
                    'allow_reposts': False,
                    'max_images': None,
                    'max_video_size_mb': None,
                    'max_audio_size_mb': None,
                    'drop_unsupported_media': True,
                },
                'repost_mode': 'ignore',
                'copy_text_template': '{text}',
            },
        )
        assert rule_resp.status_code == 200

        route_resp = client.post(
            '/routes',
            json={
                'id': 'route-1',
                'source_platform': 'telegram',
                'source_chat_id': 'tg-1',
                'target_platform': 'vk',
                'target_chat_id': 'vk-1',
                'enabled': True,
            },
        )
        assert route_resp.status_code == 200

        webhook_resp = client.post(
            '/webhooks/telegram',
            json={
                'chat_id': 'tg-1',
                'message_id': '42',
                'text': 'hello',
                'media': [{'type': 'image', 'url': 'https://example.com/a.jpg'}],
                'is_repost': False,
            },
        )
        assert webhook_resp.status_code == 200

        links = []
        deadline = time.time() + 2.0
        while time.time() < deadline:
            links_resp = client.get('/debug/message-links')
            assert links_resp.status_code == 200
            links = links_resp.json()
            if links:
                break
            time.sleep(0.1)

        assert len(links) == 1
        assert links[0]['target_platform'] == 'vk'
