from __future__ import annotations

import httpx

from config import ScribeSettings
from bot.exceptions import ProviderError

from .base import TranslationOutcome, TranslationPayload, Translator


class DeepLTranslator(Translator):
    name = "deepl"
    supports_glossary = True

    def __init__(self, settings: ScribeSettings) -> None:
        super().__init__(settings)
        self._api_key = settings.provider.deepl_api_key
        if not self._api_key:
            raise ProviderError("DEEPL_API_KEY not configured")
        self._client = httpx.AsyncClient(timeout=20.0)

    async def translate(self, payload: TranslationPayload) -> TranslationOutcome:
        params = {
            "text": payload.text,
            "target_lang": payload.target_lang.upper(),
        }
        if payload.source_lang:
            params["source_lang"] = payload.source_lang.upper()
        response = await self._client.post(
            "https://api-free.deepl.com/v2/translate",
            data=params,
            headers={"Authorization": f"DeepL-Auth-Key {self._api_key}"},
        )
        if response.status_code >= 400:
            raise ProviderError(f"DeepL returned {response.status_code}: {response.text}")
        data = response.json()
        translated = data["translations"][0]["text"]
        return TranslationOutcome(text=translated, provider=self.name, latency=0.0, char_count=len(payload.text))
