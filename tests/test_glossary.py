from __future__ import annotations

from types import SimpleNamespace

from bot.services.glossary import apply_glossary, compile_glossary


def make_entry(term: str, translation: str, priority: int = 100) -> SimpleNamespace:
    return SimpleNamespace(term=term, translation=translation, context=None, priority=priority)


def test_apply_glossary_basic() -> None:
    entries = [make_entry("API", "Interfaz"), make_entry("Bot", "Robot", priority=50)]
    compiled = compile_glossary(entries)
    result = apply_glossary("The API bot is here", compiled)
    assert "Interfaz" in result
    assert "Robot" in result


def test_apply_glossary_priority() -> None:
    entries = [make_entry("app", "aplicación", priority=10), make_entry("application", "solicitud", priority=200)]
    compiled = compile_glossary(entries)
    result = apply_glossary("the application", compiled)
    assert "solicitud" in result

