from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


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
