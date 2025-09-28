from __future__ import annotations

from typing import Optional


class ScribeError(Exception):
    """Base exception for Scribe-specific errors."""

    def __init__(self, message: str, *, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.detail = detail


class ConfigError(ScribeError):
    """Raised when configuration is invalid or incomplete."""


class ProviderError(ScribeError):
    """Raised when a translation provider fails permanently."""


class RateLimitError(ScribeError):
    """Raised when an operation exceeds the configured rate limit."""


class GlossaryError(ScribeError):
    """Issues while applying glossary replacements."""


class TranslationError(ScribeError):
    """Raised for transient translation failures eligible for retry."""


class SpanParsingError(ScribeError):
    """Raised when span extraction encounters an unrecoverable state."""
