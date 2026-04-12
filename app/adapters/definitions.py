from __future__ import annotations

from app.adapters.max.definition import MAX_DEFINITION
from app.adapters.schema import AdapterDefinition, AdapterSettingField, when_true
from app.adapters.telegram.adapter import TelegramAdapter
from app.adapters.vk.adapter import VkAdapter
from app.domain.enums import Platform
from app.help.registry import HelpEntry, HelpRegistry


TELEGRAM_HELP = [
    HelpEntry(
        id="telegram.api_id",
        title="Где взять Telegram API ID",
        summary="API ID создаётся в кабинете Telegram API на my.telegram.org/apps.",
        body_markdown=(
            "### Где взять\n"
            "1. Открой `https://my.telegram.org/apps`.\n"
            "2. Войди в свой Telegram-аккаунт.\n"
            "3. Создай приложение Telegram API.\n"
            "4. Скопируй `api_id`.\n\n"
            "### Важно\n"
            "Для Telethon `api_id` обязателен даже если ты используешь `bot token`."
        ),
        adapter_key="telegram",
        field_key="api_id",
        tags=["telegram", "auth"],
        order=20,
    ),
    HelpEntry(
        id="telegram.api_hash",
        title="Где взять Telegram API Hash",
        summary="API Hash лежит там же, где и API ID: на my.telegram.org/apps.",
        body_markdown=(
            "### Где взять\n"
            "1. Открой `https://my.telegram.org/apps`.\n"
            "2. Найди созданное приложение Telegram API.\n"
            "3. Скопируй `api_hash`.\n\n"
            "### Важно\n"
            "Это секрет. Не показывай его публично и не коммить в репозиторий."
        ),
        adapter_key="telegram",
        field_key="api_hash",
        tags=["telegram", "auth", "secret"],
        order=21,
    ),
    HelpEntry(
        id="telegram.bot_token",
        title="Где взять Telegram Bot Token",
        summary="Bot token выдаёт BotFather после создания бота.",
        body_markdown=(
            "### Где взять\n"
            "1. Открой `@BotFather`.\n"
            "2. Создай бота или выбери существующего.\n"
            "3. Скопируй токен.\n\n"
            "### Важно\n"
            "Даже с `bot token` Telethon всё равно требует `api_id` и `api_hash`."
        ),
        adapter_key="telegram",
        field_key="bot_token",
        tags=["telegram", "bot"],
        order=22,
    ),
]

VK_HELP = [
    HelpEntry(
        id="vk.group_id",
        title="Где взять VK Group ID",
        summary="Открой своё сообщество VK и возьми число из ссылки вида vk.com/club123456.",
        body_markdown=(
            "### Где взять\n"
            "Если ссылка на сообщество выглядит как `vk.com/club237416141`, то `VK Group ID` = `237416141`.\n\n"
            "### Что вводить\n"
            "В это поле вводится число **без знака минус**.\n\n"
            "### Важно\n"
            "В некоторых методах VK `owner_id` для сообщества будет использоваться со знаком минус: `-237416141`."
        ),
        adapter_key="vk",
        field_key="group_id",
        tags=["vk"],
        order=30,
    ),
    HelpEntry(
        id="vk.client_id",
        title="Где взять VK ID Client ID",
        summary="Client ID берётся в кабинете приложения VK ID.",
        body_markdown=(
            "### Где взять\n"
            "1. Открой кабинет VK ID для своего приложения.\n"
            "2. Выбери нужное приложение.\n"
            "3. Открой параметры приложения.\n"
            "4. Скопируй `client_id`.\n\n"
            "### Для чего нужен\n"
            "Нужен для кнопки `Войти с VK` и OAuth-подключения пользователя."
        ),
        adapter_key="vk",
        field_key="vk_id_client_id",
        tags=["vk", "oauth"],
        order=31,
    ),
    HelpEntry(
        id="vk.oauth",
        title="Как работает вход с VK",
        summary="Кнопка «Войти с VK» запускает официальный VK ID OAuth и сохраняет пользовательский access token для публикации wall/photos/video.",
        body_markdown=(
            "### Что происходит\n"
            "- открывается VK ID OAuth\n"
            "- пользователь подтверждает вход\n"
            "- сервис сохраняет пользовательский access token и refresh token\n\n"
            "### Зачем это нужно\n"
            "Для публикации постов с фото и видео официальный пользовательский token надёжнее, чем token сообщества."
        ),
        adapter_key="vk",
        tags=["vk", "oauth"],
        order=32,
    ),
    HelpEntry(
        id="vk.browser_cdp",
        title="Как включить browser fallback для VK",
        summary="Это отдельный opt-in fallback, а не основной путь. Основной сценарий для open-source сборки должен идти через официальный VK OAuth/API.",
        body_markdown=(
            "### Когда это нужно\n"
            "Только если официальный VK OAuth/API не даёт рабочий токен для `wall.post` и загрузки фото.\n\n"
            "### Что сделать\n"
            "1. Установи optional dependency: `pip install .[vk-browser]`.\n"
            "2. Запусти Chrome с remote debugging, например: `open -na \"Google Chrome\" --args --remote-debugging-port=9222`.\n"
            "3. Войди в нужный VK-аккаунт в этом окне Chrome.\n"
            "4. Укажи в настройках инстанса `VK Browser CDP URL`, например `http://127.0.0.1:9222`.\n\n"
            "### Ограничение\n"
            "Это experimental fallback для локального запуска на машине пользователя. По умолчанию open-source сценарий должен опираться на официальные API VK."
        ),
        adapter_key="vk",
        field_key="vk_browser_cdp_url",
        tags=["vk", "browser", "fallback"],
        order=33,
    ),
]


# factories

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
    description="Telethon adapter. Входящие события идут через live updates Telethon.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True, False, "Человеческое имя инстанса в интерфейсе и логах.", None, "Telegram main"),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, "Позволяет временно выключить инстанс без удаления настроек.", None, default=True),
        AdapterSettingField("api_id", "Telegram API ID", "int", "simple", True, False, "Обязательное поле. Берётся в кабинете Telegram API.", "telegram.api_id"),
        AdapterSettingField("api_hash", "Telegram API Hash", "str", "simple", True, True, "Обязательное поле. Берётся там же, где API ID.", "telegram.api_hash"),
        AdapterSettingField("bot_token", "Bot token", "str", "simple", False, True, "Токен от @BotFather для bot mode.", "telegram.bot_token"),
        AdapterSettingField("receive_updates", "Принимать входящие сообщения", "bool", "simple", False, False, "Если выключить, инстанс будет только отправлять сообщения.", None, default=True),
        AdapterSettingField("string_session", "String session", "str", "advanced", False, True, "Сессия Telethon для userbot-режима.", None),
        AdapterSettingField("session_name", "Session name", "str", "advanced", False, False, "Имя локального session-файла, если не используется string session.", None, "autopost_sync"),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced", False, False, "Если список не пустой, входящие обновления принимаются только из указанных чатов/каналов.", None, visible_when=when_true("receive_updates")),
        AdapterSettingField("sequential_updates", "Sequential updates", "bool", "advanced", False, False, "Полезно для отладки, но снижает throughput.", None, default=False, visible_when=when_true("receive_updates")),
        AdapterSettingField("check_all_chats", "Проверять все чаты", "bool", "advanced", False, False, "Дополнительная фильтрация источников.", None, default=False, visible_when=when_true("receive_updates")),
        AdapterSettingField("log_level", "Уровень логов адаптера", "choice", "advanced", False, False, "Сколько логов и диагностики сохранять для этого адаптера.", None, options=[{"value": "ERROR", "label": "ERROR"}, {"value": "WARNING", "label": "WARNING"}, {"value": "INFO", "label": "INFO"}, {"value": "DEBUG", "label": "DEBUG"}], default="INFO"),
    ],
    help_entries=TELEGRAM_HELP,
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
        user_access_token_for_media=secrets.get("user_access_token_for_media"),
        vk_id_client_id=config.get("vk_id_client_id"),
        vk_oauth_refresh_token=secrets.get("vk_oauth_refresh_token"),
        vk_oauth_device_id=secrets.get("vk_oauth_device_id"),
        vk_oauth_token_expires_at=config.get("vk_oauth_token_expires_at") or secrets.get("vk_oauth_token_expires_at"),
        browser_cdp_url=config.get("vk_browser_cdp_url"),
        log_level=(config.get("log_level") or "INFO"),
    )


VK_DEFINITION = AdapterDefinition(
    adapter_key="vk",
    platform=Platform.VK.value,
    title="VK",
    description="VK adapter. Основной официальный путь для публикации: VK ID user token. Group token остаётся вторичным режимом для входящих событий и legacy-кейсов.",
    fields=[
        AdapterSettingField("display_name", "Название инстанса", "str", "simple", True, False, "Человеческое имя инстанса в интерфейсе и логах.", None, "VK main"),
        AdapterSettingField("enabled", "Включен", "bool", "simple", False, False, "Позволяет временно выключить инстанс без удаления настроек.", None, default=True),
        AdapterSettingField("group_id", "VK Group ID", "int", "simple", True, False, "ID сообщества VK, без знака минус.", "vk.group_id"),
        AdapterSettingField("vk_id_client_id", "VK ID Client ID", "str", "simple", True, False, "Client ID из кабинета VK ID для кнопки «Войти с VK».", "vk.client_id"),
        AdapterSettingField("receive_updates", "Принимать входящие события из VK", "bool", "simple", False, False, "Для простого Telegram -> VK можно оставить выключенным.", None, default=False),
        AdapterSettingField("receive_mode", "Режим получения событий", "choice", "simple", False, False, "Long polling удобен по умолчанию, webhook нужен для Callback API.", None, options=[{"value": "long_poll", "label": "Long polling"}, {"value": "webhook", "label": "Webhook / Callback API"}], default="long_poll", visible_when=when_true("receive_updates")),
        AdapterSettingField("allowed_source_chat_ids", "Разрешённые source chat id", "list_str", "advanced", False, False, "Если список не пустой, входящие обновления принимаются только из указанных peer_id / owner_id.", None, visible_when=when_true("receive_updates")),
        AdapterSettingField("api_version", "API version", "str", "advanced", False, False, "Версия VK API.", None, default="5.199"),
        AdapterSettingField("token", "Токен сообщества VK", "str", "advanced", False, True, "Нужен в основном для входящих событий VK и некоторых методов сообщества.", None),
        AdapterSettingField("user_access_token_for_media", "VK user access token", "str", "advanced", False, True, "Основной пользовательский токен VK ID для публикации постов и загрузки медиа.", "vk.oauth"),
        AdapterSettingField("vk_browser_cdp_url", "VK Browser CDP URL", "str", "advanced", False, False, "Experimental opt-in fallback для локальной публикации через уже авторизованный Chrome. Пример: http://127.0.0.1:9222", "vk.browser_cdp", "http://127.0.0.1:9222"),
        AdapterSettingField("log_level", "Уровень логов адаптера", "choice", "advanced", False, False, "Сколько логов и диагностики сохранять для этого адаптера.", None, options=[{"value": "ERROR", "label": "ERROR"}, {"value": "WARNING", "label": "WARNING"}, {"value": "INFO", "label": "INFO"}, {"value": "DEBUG", "label": "DEBUG"}], default="INFO"),
    ],
    help_entries=VK_HELP,
    factory=_vk_factory,
)


class AdapterDefinitionRegistry:
    def __init__(self) -> None:
        self._defs = {
            TELEGRAM_DEFINITION.adapter_key: TELEGRAM_DEFINITION,
            VK_DEFINITION.adapter_key: VK_DEFINITION,
            MAX_DEFINITION.adapter_key: MAX_DEFINITION,
        }
        self.help_registry = HelpRegistry()
        for definition in self._defs.values():
            self.help_registry.register_many(definition.help_entries)

    def list_definitions(self) -> list[AdapterDefinition]:
        return list(self._defs.values())

    def list_help_entries(self):
        return self.help_registry.list_entries()

    def get(self, adapter_key: str) -> AdapterDefinition:
        return self._defs[adapter_key]

    def create_adapter(self, adapter_key: str, instance_id: str, config: dict[str, any], secrets: dict[str, any]):
        return self.get(adapter_key).factory(instance_id, config, secrets)
