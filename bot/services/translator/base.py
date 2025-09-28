from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from loguru import logger

from config import ProviderName, ScribeSettings
from bot.exceptions import ProviderError, TranslationError


@dataclass(slots=True)
class TranslationPayload:
    text: str
    source_lang: str
    target_lang: str
    glossary: list[tuple[str, str]] | None = None
    timeout: float = 15.0


@dataclass(slots=True)
class TranslationOutcome:
    text: str
    provider: ProviderName
    latency: float
    char_count: int


class Translator(ABC):
    name: ProviderName
    supports_glossary: bool = False

    def __init__(self, settings: ScribeSettings) -> None:
        self.settings = settings

    @abstractmethod
    async def translate(self, payload: TranslationPayload) -> TranslationOutcome:
        raise NotImplementedError


class TranslatorRegistry:
    """Manages configured translators and provides fallback behaviour."""

    def __init__(self, settings: ScribeSettings) -> None:
        self._settings = settings
        self._translators: dict[ProviderName, Translator] = {}
        self._ordered: list[ProviderName] = []
        self._lock = asyncio.Lock()
        self._instantiate(settings)

    def _instantiate(self, settings: ScribeSettings) -> None:
        from .deepl import DeepLTranslator
        from .google import GoogleTranslator
        from .openai import OpenAITranslator

        mapping: dict[ProviderName, type[Translator]] = {
            "openai": OpenAITranslator,
            "deepl": DeepLTranslator,
            "google": GoogleTranslator,
        }
        for provider in settings.provider.ordered():
            cls = mapping.get(provider)
            if not cls:
                continue
            try:
                translator = cls(settings)
            except ProviderError as exc:
                logger.warning("Skipping provider {}: {}", provider, exc)
                continue
            self._translators[provider] = translator
            self._ordered.append(provider)
        if not self._ordered:
            logger.warning("No translators configured; falling back to echo translator")

    async def translate(self, payload: TranslationPayload) -> TranslationOutcome:
        if not self._ordered:
            return TranslationOutcome(
                text=payload.text,
                provider="echo",  # type: ignore[arg-type]
                latency=0.0,
                char_count=len(payload.text),
            )
        async with self._lock:
            for provider_name in self._ordered:
                translator = self._translators[provider_name]
                try:
                    start = time.perf_counter()
                    outcome = await translator.translate(payload)
                    outcome.latency = time.perf_counter() - start
                    outcome.char_count = len(payload.text)
                    return outcome
                except ProviderError as exc:
                    logger.warning("Provider {} failed: {}", provider_name, exc)
                    continue
                except TranslationError as exc:
                    logger.warning("Transient failure from {}: {}", provider_name, exc)
                    continue
        logger.error("All translators failed; returning original text")
        return TranslationOutcome(
            text=payload.text,
            provider=self._ordered[-1],
            latency=0.0,
            char_count=len(payload.text),
        )
