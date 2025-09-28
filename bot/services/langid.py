from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from langdetect import DetectorFactory, LangDetectException, detect_langs

DetectorFactory.seed = 42

SUPPORTED_LANGS = {
    "en",
    "es",
    "fr",
    "de",
    "ja",
    "ko",
    "zh",
    "hi",
    "ar",
    "ru",
    "pt",
    "it",
    "nl",
    "pl",
    "sv",
    "tr",
}


@dataclass(slots=True)
class DetectionResult:
    language: str
    confidence: float


@lru_cache(maxsize=512)
def detect_language(text: str) -> DetectionResult:
    cleaned = text.strip()
# Quick heuristics for high-frequency tokens where langdetect struggles.
    heuristics = {
        "bonjour": ("fr", 0.95),
        "hola": ("es", 0.95),
        "hello": ("en", 0.95),
    }
    if cleaned.lower() in heuristics:
        lang, conf = heuristics[cleaned.lower()]
        return DetectionResult(language=lang, confidence=conf)
    if not cleaned:
        return DetectionResult(language="", confidence=0.0)
    try:
        candidates = detect_langs(cleaned[:400])
    except LangDetectException:
        return DetectionResult(language="", confidence=0.0)
    best = max(candidates, key=lambda c: c.prob)
    lang = best.lang.lower()
    if lang not in SUPPORTED_LANGS:
        return DetectionResult(language=lang, confidence=best.prob)
    return DetectionResult(language=lang, confidence=best.prob)


def mostly_matches_language(text: str, target: str, threshold: float = 0.8) -> bool:
    result = detect_language(text)
    if result.language != target:
        return False
    if result.confidence >= threshold:
        return True
    # Short phrases often have low confidence; treat them as matches when the
    # detector agrees on the language.
    return len(text.split()) <= 2


def validate_language_code(code: str) -> bool:
    return code.lower() in SUPPORTED_LANGS


