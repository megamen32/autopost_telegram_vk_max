from __future__ import annotations

from app.adapters.max.definition import MAX_DEFINITION
from app.adapters.schema import AdapterDefinition, AdapterSettingField, when_all, when_eq, when_true
from app.adapters.telegram.adapter import TelegramAdapter
from app.adapters.vk.adapter import VkAdapter
from app.domain.enums import Platform


def _telegram_factory(instance_id: str, config: dict[str, any], secrets: dict[str, any]) -> TelegramAdapter:
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
        log_level=(config.get("log_level") or "INFO"),
    )


TELEGRAM_DEFINITION = AdapterDefinition(
    adapter_key="telegram",
    platform=Platform.TELEGRAM.value,
    title="Telegram",
    description="Telethon adapter. По умолчанию работает через long polling / live updates Telethon. Для Telegram сейчас нет отдельного webhook-режима внутри сервиса — входящие события идут через сам клиент Telethon.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True, False, "Человеческое имя инстанса в интерфейсе и логах.", "Telegram main"),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, "Позволяет временно выключить инстанс без удаления настроек.", default=True),
        AdapterSettingField("bot_token", "Bot token", "str", "simple", False, True, "Токен Telegram-бота. Для bot-режима он обязателен, но Telethon всё равно требует api_id и api_hash."),
        AdapterSettingField("receive_updates", "Принимать входящие сообщения", "bool", "simple", False, False, "Если выключить, инстанс будет только отправлять сообщения, без чтения входящих событий.", default=True),
        AdapterSettingField("api_id", "API ID", "int", "advanced", False, False, "API ID приложения Telegram. Нужен и для bot token, и для user session режима."),
        AdapterSettingField("api_hash", "API Hash", "str", "advanced", False, True, "API Hash приложения Telegram. Хранится как секрет."),
        AdapterSettingField("string_session", "String session", "str", "advanced", False, True, "Сессия Telethon для userbot-режима. Используй вместо bot token, если нужен доступ как у пользовательского аккаунта."),
        AdapterSettingField("session_name", "Session name", "str", "advanced", False, False, "Имя локального session-файла, если не используется string session.", "autopost_sync"),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced", False, False, "Если список не пустой, входящие обновления принимаются только из указанных чатов/каналов.", visible_when=when_true("receive_updates")),
        AdapterSettingField("sequential_updates", "Sequential updates", "bool", "advanced", False, False, "Обрабатывать входящие обновления строго последовательно. Полезно для отладки, но снижает throughput.", default=False, visible_when=when_true("receive_updates")),
        AdapterSettingField("check_all_chats", "Проверять все чаты", "bool", "advanced", False, False, "Заготовка под более строгую фильтрацию источников. Пока обычно не требуется.", default=False, visible_when=when_true("receive_updates")),
AdapterSettingField("log_level", "Уровень логов адаптера", "choice", "advanced", False, False, "Сколько логов и диагностики сохранять для этого адаптера.", options=[{"value": "ERROR", "label": "ERROR"}, {"value": "WARNING", "label": "WARNING"}, {"value": "INFO", "label": "INFO"}, {"value": "DEBUG", "label": "DEBUG"}], default="INFO"),
    ],
    factory=_telegram_factory,
)


def _vk_factory(instance_id: str, config: dict[str, any], secrets: dict[str, any]) -> VkAdapter:
    return VkAdapter(
        instance_id=instance_id,
        token=secrets.get("token"),
        group_id=config.get("group_id"),
        api_version=config.get("api_version") or "5.199",
        confirmation_token=secrets.get("confirmation_token"),
        secret=secrets.get("secret"),
        receive_updates=bool(config.get("receive_updates", True)),
        receive_mode=config.get("receive_mode") or "long_poll",
        allowed_source_chat_ids=config.get("allowed_source_chat_ids") or [],
        long_poll_wait_seconds=int(config.get("long_poll_wait_seconds") or 25),
        log_level=(config.get("log_level") or "INFO"),
    )


VK_DEFINITION = AdapterDefinition(
    adapter_key="vk",
    platform=Platform.VK.value,
    title="VK",
    description="VK adapter. По умолчанию включён long polling. Для production можно переключить на Callback API webhook, если нужен входящий HTTPS endpoint от VK.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True, False, "Человеческое имя инстанса в интерфейсе и логах.", "VK main"),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, "Позволяет временно выключить инстанс без удаления настроек.", default=True),
        AdapterSettingField("group_id", "Group ID", "int", "simple", True, False, "ID сообщества VK, от имени которого публикуются посты и принимаются входящие события."),
        AdapterSettingField("token", "Token", "str", "simple", True, True, "Сервисный токен сообщества с правами на публикацию и получение событий."),
        AdapterSettingField("receive_updates", "Принимать входящие события", "bool", "simple", False, False, "Если выключить, инстанс будет только отправлять посты, без чтения входящих событий.", default=True),
        AdapterSettingField("receive_mode", "Режим получения событий", "choice", "simple", False, False, "Long polling удобен по умолчанию. Webhook нужен, если хочешь принимать события через Callback API VK на свой HTTP endpoint.", options=[{"value": "long_poll", "label": "Long polling"}, {"value": "webhook", "label": "Webhook / Callback API"}], default="long_poll", visible_when=when_true("receive_updates")),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced", False, False, "Если список не пустой, входящие обновления принимаются только из указанных peer_id / owner_id.", visible_when=when_true("receive_updates")),
        AdapterSettingField("api_version", "API version", "str", "advanced", False, False, "Версия VK API. Обычно достаточно дефолта.", default="5.199"),
        AdapterSettingField("confirmation_token", "Confirmation token", "str", "advanced", False, True, "Нужен только для webhook-режима Callback API, когда VK присылает событие confirmation.", visible_when=when_all(when_true("receive_updates"), when_eq("receive_mode", "webhook"))),
        AdapterSettingField("secret", "Webhook secret", "str", "advanced", False, True, "Секрет Callback API. Проверяется только в webhook-режиме.", visible_when=when_all(when_true("receive_updates"), when_eq("receive_mode", "webhook"))),
        AdapterSettingField("long_poll_wait_seconds", "Long poll wait, сек", "int", "advanced", False, False, "Сколько секунд держать одно long poll соединение с VK открытым.", default=25, visible_when=when_all(when_true("receive_updates"), when_eq("receive_mode", "long_poll"))),
    ],
    factory=_vk_factory,
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

    def create_adapter(self, adapter_key: str, instance_id: str, config: dict[str, any], secrets: dict[str, any]):
        return self.get(adapter_key).factory(instance_id, config, secrets)
