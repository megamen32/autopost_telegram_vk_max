from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from app.adapters.max.adapter import MaxAdapter
from app.adapters.telegram.adapter import TelegramAdapter
from app.adapters.vk.adapter import VkAdapter
from app.domain.enums import Platform


@dataclass(slots=True)
class AdapterSettingField:
    name: str
    label: str
    field_type: str
    scope: str = "simple"
    required: bool = False
    secret: bool = False
    help_text: str | None = None
    placeholder: str | None = None
    options: list[dict[str, str]] = field(default_factory=list)
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AdapterDefinition:
    adapter_key: str
    platform: str
    title: str
    description: str
    fields: list[AdapterSettingField]
    factory: Callable[[str, dict[str, Any], dict[str, Any]], Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_key": self.adapter_key,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "fields": [field.to_dict() for field in self.fields],
        }


def _telegram_factory(instance_id: str, config: dict[str, Any], secrets: dict[str, Any]) -> TelegramAdapter:
    return TelegramAdapter(
        instance_id=instance_id,
        api_id=config.get("api_id"),
        api_hash=secrets.get("api_hash"),
        string_session=secrets.get("string_session"),
        bot_token=secrets.get("bot_token"),
        session_name=config.get("session_name") or f"autopost_sync_{instance_id}",
        receive_updates=bool(config.get("receive_updates", True)),
        sequential_updates=bool(config.get("sequential_updates", False)),
        allowed_source_chat_ids=config.get("allowed_source_chat_ids") or [],
        check_all_chats=bool(config.get("check_all_chats", False)),
    )


TELEGRAM_DEFINITION = AdapterDefinition(
    adapter_key="telegram",
    platform=Platform.TELEGRAM.value,
    title="Telegram",
    description="Telethon adapter. В simple-режиме обычно хватает bot token. В advanced можно включить user session и доп. флаги.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True, False, "Как этот инстанс показывать в UI", "Telegram main"),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, default=True),
        AdapterSettingField("api_id", "API ID", "int", "advanced", False, False),
        AdapterSettingField("api_hash", "API Hash", "str", "advanced", False, True),
        AdapterSettingField("bot_token", "Bot token", "str", "simple", False, True),
        AdapterSettingField("string_session", "String session", "str", "advanced", False, True),
        AdapterSettingField("session_name", "Session name", "str", "advanced", False, False, placeholder="autopost_sync"),
        AdapterSettingField("receive_updates", "Принимать входящие сообщения", "bool", "simple", False, False, default=True),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced"),
        AdapterSettingField("sequential_updates", "Sequential updates", "bool", "advanced", False, False, default=False),
        AdapterSettingField("check_all_chats", "Проверять все чаты", "bool", "advanced", False, False, default=False),
    ],
    factory=_telegram_factory,
)


def _vk_factory(instance_id: str, config: dict[str, Any], secrets: dict[str, Any]) -> VkAdapter:
    return VkAdapter(
        instance_id=instance_id,
        token=secrets.get("token"),
        group_id=config.get("group_id"),
        api_version=config.get("api_version") or "5.199",
        confirmation_token=secrets.get("confirmation_token"),
        secret=secrets.get("secret"),
        receive_updates=bool(config.get("receive_updates", True)),
        allowed_source_chat_ids=config.get("allowed_source_chat_ids") or [],
    )


VK_DEFINITION = AdapterDefinition(
    adapter_key="vk",
    platform=Platform.VK.value,
    title="VK",
    description="VK Callback API adapter. В simple-режиме нужен только токен и id группы.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, default=True),
        AdapterSettingField("group_id", "Group ID", "int", "simple", True),
        AdapterSettingField("token", "Token", "str", "simple", True, True),
        AdapterSettingField("receive_updates", "Принимать входящие события", "bool", "simple", False, False, default=True),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced"),
        AdapterSettingField("api_version", "API version", "str", "advanced", False, False, default="5.199"),
        AdapterSettingField("confirmation_token", "Confirmation token", "str", "advanced", False, True),
        AdapterSettingField("secret", "Webhook secret", "str", "advanced", False, True),
    ],
    factory=_vk_factory,
)


def _max_factory(instance_id: str, config: dict[str, Any], secrets: dict[str, Any]) -> MaxAdapter:
    return MaxAdapter(
        instance_id=instance_id,
        token=secrets.get("token"),
        webhook_url=config.get("webhook_url"),
        secret=secrets.get("secret"),
        receive_updates=bool(config.get("receive_updates", True)),
        update_types=config.get("update_types") or ["message_created"],
        allowed_source_chat_ids=config.get("allowed_source_chat_ids") or [],
    )


MAX_DEFINITION = AdapterDefinition(
    adapter_key="max",
    platform=Platform.MAX.value,
    title="MAX",
    description="MAX Bot API adapter. В simple-режиме обычно нужен только токен.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, default=True),
        AdapterSettingField("token", "Token", "str", "simple", True, True),
        AdapterSettingField("receive_updates", "Принимать входящие события", "bool", "simple", False, False, default=True),
        AdapterSettingField("webhook_url", "Webhook URL", "str", "advanced"),
        AdapterSettingField("update_types", "Типы обновлений", "list_str", "advanced"),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced"),
        AdapterSettingField("secret", "Webhook secret", "str", "advanced", False, True),
    ],
    factory=_max_factory,
)


class AdapterDefinitionRegistry:
    def __init__(self) -> None:
        self._defs = {
            TELEGRAM_DEFINITION.adapter_key: TELEGRAM_DEFINITION,
            VK_DEFINITION.adapter_key: VK_DEFINITION,
            MAX_DEFINITION.adapter_key: MAX_DEFINITION,
        }

    def list_definitions(self) -> list[AdapterDefinition]:
        return list(self._defs.values())

    def get(self, adapter_key: str) -> AdapterDefinition:
        return self._defs[adapter_key]

    def create_adapter(self, adapter_key: str, instance_id: str, config: dict[str, Any], secrets: dict[str, Any]):
        return self.get(adapter_key).factory(instance_id, config, secrets)
