from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from app.help.registry import HelpEntry


@dataclass(slots=True)
class VisibilityRule:
    field: str | None = None
    eq: Any | None = None
    ne: Any | None = None
    in_: list[Any] | None = None
    not_in: list[Any] | None = None
    is_true: bool | None = None
    is_false: bool | None = None
    is_none: bool | None = None
    is_not_none: bool | None = None
    all: list["VisibilityRule"] | None = None
    any: list["VisibilityRule"] | None = None


@dataclass(slots=True)
class AdapterSettingField:
    name: str
    label: str
    field_type: str
    scope: str = "simple"
    required: bool = False
    secret: bool = False
    help_text: str | None = None
    help_entry_id: str | None = None
    placeholder: str | None = None
    options: list[dict[str, str]] = field(default_factory=list)
    default: Any = None
    visible_when: VisibilityRule | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data.get("visible_when") is not None:
            data["visible_when"] = _normalize_visibility_dict(data["visible_when"])
        return data


@dataclass(slots=True)
class AdapterDefinition:
    adapter_key: str
    platform: str
    title: str
    description: str
    fields: list[AdapterSettingField]
    help_entries: list[HelpEntry] = field(default_factory=list)
    factory: Callable[[str, dict[str, Any], dict[str, Any]], Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_key": self.adapter_key,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "fields": [field.to_dict() for field in self.fields],
            "help_entries": [entry.to_dict() for entry in self.help_entries],
        }


def _normalize_visibility_dict(node: Any) -> Any:
    if isinstance(node, dict):
        result = {}
        for key, value in node.items():
            if key == "in_":
                result["in"] = _normalize_visibility_dict(value)
            else:
                result[key] = _normalize_visibility_dict(value)
        return result
    if isinstance(node, list):
        return [_normalize_visibility_dict(item) for item in node]
    return node


def when_eq(field: str, value: Any) -> VisibilityRule:
    return VisibilityRule(field=field, eq=value)


def when_ne(field: str, value: Any) -> VisibilityRule:
    return VisibilityRule(field=field, ne=value)


def when_true(field: str) -> VisibilityRule:
    return VisibilityRule(field=field, is_true=True)


def when_false(field: str) -> VisibilityRule:
    return VisibilityRule(field=field, is_false=True)


def when_none(field: str) -> VisibilityRule:
    return VisibilityRule(field=field, is_none=True)


def when_not_none(field: str) -> VisibilityRule:
    return VisibilityRule(field=field, is_not_none=True)


def when_all(*rules: VisibilityRule) -> VisibilityRule:
    return VisibilityRule(all=list(rules))


def when_any(*rules: VisibilityRule) -> VisibilityRule:
    return VisibilityRule(any=list(rules))
