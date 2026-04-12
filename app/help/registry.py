from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class HelpEntry:
    id: str
    title: str
    summary: str
    body_markdown: str
    adapter_key: str | None = None
    field_key: str | None = None
    tags: list[str] = field(default_factory=list)
    order: int = 100

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "body_markdown": self.body_markdown,
            "adapter_key": self.adapter_key,
            "field_key": self.field_key,
            "tags": self.tags,
            "order": self.order,
        }


COMMON_HELP: list[HelpEntry] = [
    HelpEntry(
        id="route.source_chat",
        title="Что вводить в поле источника маршрута",
        summary="Можно указать chat id, @username или ссылку. Для Telegram лучше всего работает числовой chat id.",
        body_markdown=(
            "### Что можно вводить\n"
            "- числовой `chat id`\n"
            "- `@username`\n"
            "- ссылку вида `https://t.me/name`\n\n"
            "### Что надёжнее всего\n"
            "Для Telegram самый надёжный вариант — числовой chat id.\n\n"
            "### Почему\n"
            "Username и ссылки требуют дополнительного резолва через адаптер. В bot mode Telegram это может работать не для всех каналов и чатов."
        ),
        tags=["routes", "telegram"],
        order=10,
    ),
    HelpEntry(
        id="route.target_chat",
        title="Что вводить в поле назначения маршрута",
        summary="Можно указать chat id, @username или ссылку. Для отправки в Telegram лучше всего работает числовой chat id.",
        body_markdown=(
            "### Что можно вводить\n"
            "- числовой `chat id`\n"
            "- `@username`\n"
            "- ссылку вида `https://t.me/name`\n\n"
            "### Практический совет\n"
            "Если тестируешь echo-бота в Telegram, указывай свой числовой user/chat id."
        ),
        tags=["routes", "telegram"],
        order=11,
    ),
    HelpEntry(
        id="route.enabled",
        title="Что значит «Маршрут включён»",
        summary="Если маршрут выключен, он не создаёт jobs и не участвует в синхронизации.",
        body_markdown=(
            "### Включён\n"
            "Маршрут участвует в синхронизации и может создавать delivery jobs.\n\n"
            "### Выключен\n"
            "Маршрут сохранён, но не используется. Это удобно, если хочешь временно остановить синхронизацию без удаления настроек."
        ),
        tags=["routes"],
        order=12,
    ),
]


class HelpRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, HelpEntry] = {entry.id: entry for entry in COMMON_HELP}

    def register_many(self, entries: Iterable[HelpEntry]) -> None:
        for entry in entries:
            self._entries[entry.id] = entry

    def list_entries(self) -> list[HelpEntry]:
        return sorted(self._entries.values(), key=lambda item: (item.order, item.title))

    def get(self, entry_id: str) -> HelpEntry | None:
        return self._entries.get(entry_id)
