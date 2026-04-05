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
        receive_mode=config.get("receive_mode") or "long_poll",
        receive_updates=bool(config.get("receive_updates", True)),
        update_types=config.get("update_types") or ["message_created"],
        allowed_source_chat_ids=config.get("allowed_source_chat_ids") or [],
        prefer_official_sdk=bool(config.get("prefer_official_sdk", True)),
        long_poll_timeout_seconds=int(config.get("long_poll_timeout_seconds") or 30),
        long_poll_limit=int(config.get("long_poll_limit") or 100),
    )


MAX_DEFINITION = AdapterDefinition(
    adapter_key="max",
    platform=Platform.MAX.value,
    title="MAX",
    description="MAX adapter. По умолчанию включён long polling. Для production MAX рекомендует webhook, но для локального запуска long polling удобнее и не требует внешнего HTTPS endpoint.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True, False, "Человеческое имя инстанса в интерфейсе и логах.", "MAX main"),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, "Позволяет временно выключить инстанс без удаления настроек.", default=True),
        AdapterSettingField("token", "Token", "str", "simple", True, True, "Токен бота MAX. Обязателен для отправки сообщений и получения входящих событий."),
        AdapterSettingField("receive_updates", "Принимать входящие события", "bool", "simple", False, False, "Если выключить, инстанс будет только отправлять сообщения, без приёма входящих обновлений.", default=True),
        AdapterSettingField("receive_mode", "Режим получения событий", "choice", "simple", False, False, "Long polling удобен по умолчанию. Webhook нужен, если бот работает за публичным HTTPS endpoint.", options=[{"value": "long_poll", "label": "Long polling"}, {"value": "webhook", "label": "Webhook"}], default="long_poll"),
        AdapterSettingField("prefer_official_sdk", "Предпочитать официальный SDK transport", "bool", "advanced", False, False, "Сначала пробовать maxapi/max-botapi-python, а если метод не покрыт — падать обратно на прямой HTTP API.", default=True),
        AdapterSettingField("webhook_url", "Webhook URL", "str", "advanced", False, False, "Нужен только если выбран webhook-режим. Должен быть публичный HTTPS URL этого инстанса."),
        AdapterSettingField("secret", "Webhook secret", "str", "advanced", False, True, "Секрет для проверки заголовка X-Max-Bot-Api-Secret. Используется только в webhook-режиме."),
        AdapterSettingField("update_types", "Типы обновлений", "list_str", "advanced", False, False, "Какие типы событий получать. Обычно достаточно message_created."),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced", False, False, "Если список не пустой, входящие обновления принимаются только из указанных чатов."),
        AdapterSettingField("long_poll_timeout_seconds", "Long poll timeout, сек", "int", "advanced", False, False, "Сколько секунд держать один запрос /updates открытым в режиме long polling.", default=30),
        AdapterSettingField("long_poll_limit", "Long poll batch size", "int", "advanced", False, False, "Сколько событий максимум забирать за один long poll запрос.", default=100),
    ],
    factory=create_max_adapter,
)
