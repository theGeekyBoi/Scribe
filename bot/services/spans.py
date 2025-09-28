from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable, List, Tuple

from bot.exceptions import SpanParsingError


class SpanType(Enum):
    CODE_BLOCK = auto()
    INLINE_CODE = auto()
    SPOILER = auto()
    BLOCK_QUOTE = auto()
    MENTION = auto()
    LINK = auto()
    CUSTOM_EMOJI = auto()
    TIMESTAMP = auto()


@dataclass(slots=True)
class Span:
    type: SpanType
    start: int
    end: int
    placeholder: str
    original: str


CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
SPOILER_PATTERN = re.compile(r"\|\|.*?\|\|", re.DOTALL)
BLOCK_QUOTE_PATTERN = re.compile(r"(^|\n)>[^\n]*", re.MULTILINE)
MENTION_PATTERN = re.compile(r"<(@[!&]?|#)\d+>")
CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:[\w~]+:\d+>")
TIMESTAMP_PATTERN = re.compile(r"<t:\d+(?::[tTdDfFR])?>")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\([^\)\s]+\)")
URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)

PLACEHOLDER_TEMPLATE = "⟦SP{index}⟧"


def extract_spans(raw: str) -> tuple[str, list[Span]]:
    spans: List[Span] = []
    taken: List[Tuple[int, int]] = []

    def register(match: re.Match[str], span_type: SpanType) -> None:
        start, end = match.span()
        if start == end:
            return
        for existing_start, existing_end in taken:
            if start < existing_end and end > existing_start:
                return
        placeholder = PLACEHOLDER_TEMPLATE.format(index=len(spans))
        spans.append(Span(span_type, start, end, placeholder, raw[start:end]))
        taken.append((start, end))

    for pattern, span_type in (
        (CODE_BLOCK_PATTERN, SpanType.CODE_BLOCK),
        (SPOILER_PATTERN, SpanType.SPOILER),
        (BLOCK_QUOTE_PATTERN, SpanType.BLOCK_QUOTE),
        (INLINE_CODE_PATTERN, SpanType.INLINE_CODE),
        (MARKDOWN_LINK_PATTERN, SpanType.LINK),
        (URL_PATTERN, SpanType.LINK),
        (MENTION_PATTERN, SpanType.MENTION),
        (CUSTOM_EMOJI_PATTERN, SpanType.CUSTOM_EMOJI),
        (TIMESTAMP_PATTERN, SpanType.TIMESTAMP),
    ):
        for match in pattern.finditer(raw):
            register(match, span_type)

    spans.sort(key=lambda span: span.start)
    builder: list[str] = []
    cursor = 0
    for span in spans:
        builder.append(raw[cursor:span.start])
        builder.append(span.placeholder)
        cursor = span.end
    builder.append(raw[cursor:])
    transformed = "".join(builder)
    return transformed, spans


def reinsert_spans(translated_text: str, spans: Iterable[Span], original_raw: str) -> str:
    result = translated_text
    for span in spans:
        if span.placeholder not in result:
            raise SpanParsingError(f"Missing placeholder {span.placeholder}")
        result = result.replace(span.placeholder, span.original)
    return result
