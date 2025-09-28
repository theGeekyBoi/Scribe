from __future__ import annotations

import re
from typing import Iterable

MENTION_PATTERN = re.compile(r"@")


def sanitize_for_webhook(content: str) -> str:
    """Insert zero-width characters to avoid accidental pings when using webhooks."""
    return MENTION_PATTERN.sub("@\u200b", content)


def stitch_translation(original_link: str | None, translated_text: str) -> str:
    if original_link:
        return f"[↩ Original]({original_link})\n{translated_text}"
    return translated_text


def clamp_lines(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
