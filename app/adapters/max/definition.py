from __future__ import annotations

from app.adapters.schema import AdapterDefinition, AdapterSettingField
from app.adapters.max.adapter import MaxAdapter
from app.domain.enums import Platform


def create_max_adapter(instance_id: str, config: dict, secrets: dict):
    return MaxAdapter(
        instance_id=instance_id,
        token=secrets.get("token"),
        webhook_url=config.get("webhook_url"),
        secret=secrets.get("secret"),
        receive_updates=bool(config.get("receive_updates", True)),
        update_types=config.get("update_types") or ["message_created"],
        allowed_source_chat_ids=config.get("allowed_source_chat_ids") or [],
        prefer_official_sdk=bool(config.get("prefer_official_sdk", True)),
    )


MAX_DEFINITION = AdapterDefinition(
    adapter_key="max",
    platform=Platform.MAX.value,
    title="MAX",
    description="MAX adapter. В simple-режиме обычно нужен только токен. По умолчанию используется официальный maxapi/max-botapi-python как транспортный слой, с fallback на прямой HTTP API.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, default=True),
        AdapterSettingField("token", "Token", "str", "simple", True, True),
        AdapterSettingField("receive_updates", "Принимать входящие события", "bool", "simple", False, False, default=True),
        AdapterSettingField("prefer_official_sdk", "Предпочитать официальный SDK transport", "bool", "advanced", False, False, default=True),
        AdapterSettingField("webhook_url", "Webhook URL", "str", "advanced"),
        AdapterSettingField("update_types", "Типы обновлений", "list_str", "advanced"),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced"),
        AdapterSettingField("secret", "Webhook secret", "str", "advanced", False, True),
    ],
    factory=create_max_adapter,
)
