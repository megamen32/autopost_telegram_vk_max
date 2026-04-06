from __future__ import annotations

import re


def canonicalize_telegram_chat_ref(value: str | int | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.startswith('-100') and s[4:].isdigit():
        return s[4:]
    if s.lstrip('-').isdigit():
        return s.lstrip('-')
    if s.startswith('@'):
        return s[1:].lower()
    m = re.match(r'https?://(?:t\.me|telegram\.me)/([A-Za-z0-9_]+)/?$', s)
    if m:
        return m.group(1).lower()
    if re.fullmatch(r'[A-Za-z0-9_]{5,}', s):
        return s.lower()
    return s.lower()
