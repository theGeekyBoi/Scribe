from __future__ import annotations

import pytest

from bot.exceptions import SpanParsingError
from bot.services import spans


def test_extract_and_reinsert_code_block() -> None:
    raw = "Here is code:\n```python\nprint(1)\n```\nend"
    transformed, extracted = spans.extract_spans(raw)
    assert "```python" not in transformed
    rebuilt = spans.reinsert_spans(transformed, extracted, raw)
    assert rebuilt == raw


def test_inline_code_and_mentions() -> None:
    raw = "Use `pip install` and ping <@123>."
    transformed, extracted = spans.extract_spans(raw)
    assert "`pip install`" not in transformed
    assert "<@123>" not in transformed
    rebuilt = spans.reinsert_spans(transformed, extracted, raw)
    assert rebuilt == raw


def test_spoilers_and_links() -> None:
    raw = "Spoiler ||secret|| and link https://example.com/page"
    transformed, extracted = spans.extract_spans(raw)
    assert "secret" not in transformed
    assert "https://" not in transformed
    rebuilt = spans.reinsert_spans(transformed + " translation", extracted, raw)
    assert "||secret||" in rebuilt


def test_block_quotes() -> None:
    raw = "> quoted text\nNext line"
    transformed, extracted = spans.extract_spans(raw)
    assert transformed.count(spans.PLACEHOLDER_TEMPLATE.format(index=0)) == 1
    rebuilt = spans.reinsert_spans(transformed, extracted, raw)
    assert rebuilt.startswith("> quoted text")


def test_missing_placeholder_raises() -> None:
    raw = "`code`"
    transformed, extracted = spans.extract_spans(raw)
    with pytest.raises(SpanParsingError):
        spans.reinsert_spans(transformed.replace("⟦SP0⟧", ""), extracted, raw)
