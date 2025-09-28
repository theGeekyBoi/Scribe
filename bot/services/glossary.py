from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from bot.db.models import GlossaryEntry


@dataclass(slots=True)
class CompiledGlossary:
    pattern: re.Pattern[str]
    replacement: str
    term: str


def compile_glossary(entries: Iterable[GlossaryEntry]) -> list[CompiledGlossary]:
    compiled: list[CompiledGlossary] = []
    for entry in sorted(entries, key=lambda e: e.priority):
        escaped = re.escape(entry.term)
        pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        compiled.append(CompiledGlossary(pattern=pattern, replacement=entry.translation, term=entry.term))
    return compiled


def apply_glossary(text: str, compiled: Iterable[CompiledGlossary]) -> str:
    result = text
    for item in compiled:
        result = item.pattern.sub(item.replacement, result)
    return result
