from __future__ import annotations

from bot.services.langid import detect_language, mostly_matches_language, validate_language_code


def test_detect_language_simple() -> None:
    result = detect_language("hola, cómo estás")
    assert result.language == "es"
    assert result.confidence > 0.5


def test_mostly_matches_language_threshold() -> None:
    assert mostly_matches_language("bonjour", "fr")
    assert not mostly_matches_language("hello bonjour", "fr", threshold=0.9)


def test_validate_language_code() -> None:
    assert validate_language_code("en")
    assert not validate_language_code("xx")

