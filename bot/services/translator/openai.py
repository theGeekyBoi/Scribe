from __future__ import annotations

import httpx

from config import ScribeSettings
from bot.exceptions import ProviderError

from .base import TranslationOutcome, TranslationPayload, Translator


class OpenAITranslator(Translator):
    name = "openai"

    def __init__(self, settings: ScribeSettings) -> None:
        super().__init__(settings)
        self._api_key = settings.provider.openai_api_key
        if not self._api_key:
            raise ProviderError("OPENAI_API_KEY not configured")
        self._model = getattr(settings, "openai_model", "gpt-4o-mini")
        self._client = httpx.AsyncClient(timeout=20.0)

    async def translate(self, payload: TranslationPayload) -> TranslationOutcome:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a translation engine. Translate the user content preserving Markdown formatting and code." ,
                },
                {
                    "role": "user",
                    "content": payload.text,
                },
            ],
            "temperature": 0,
        }
        response = await self._client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
        if response.status_code >= 400:
            raise ProviderError(f"OpenAI returned {response.status_code}: {response.text}")
        data = response.json()
        translated = data["choices"][0]["message"]["content"].strip()
        return TranslationOutcome(text=translated, provider=self.name, latency=0.0, char_count=len(payload.text))
