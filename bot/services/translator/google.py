from __future__ import annotations

import json
from pathlib import Path

import httpx

from config import ScribeSettings
from bot.exceptions import ProviderError

from .base import TranslationOutcome, TranslationPayload, Translator


class GoogleTranslator(Translator):
    name = "google"

    def __init__(self, settings: ScribeSettings) -> None:
        super().__init__(settings)
        self._project_id = settings.provider.google_project_id
        self._credentials_path = settings.provider.google_credentials
        if not self._project_id or not self._credentials_path:
            raise ProviderError("Google Cloud credentials not configured")
        creds_path = Path(self._credentials_path)
        if not creds_path.exists():
            raise ProviderError("Google credentials file missing")
        creds = json.loads(creds_path.read_text(encoding="utf-8"))
        self._access_token = creds.get("token")
        if not self._access_token:
            raise ProviderError("Google credentials missing token field")
        self._client = httpx.AsyncClient(timeout=20.0)

    async def translate(self, payload: TranslationPayload) -> TranslationOutcome:
        url = (
            f"https://translation.googleapis.com/v3/projects/{self._project_id}:translateText"
        )
        body = {
            "contents": [payload.text],
            "mimeType": "text/plain",
            "targetLanguageCode": payload.target_lang,
        }
        if payload.source_lang:
            body["sourceLanguageCode"] = payload.source_lang
        response = await self._client.post(
            url,
            headers={"Authorization": f"Bearer {self._access_token}"},
            json=body,
        )
        if response.status_code >= 400:
            raise ProviderError(f"Google Translate API error {response.status_code}: {response.text}")
        data = response.json()
        translated = data["translations"][0]["translatedText"]
        return TranslationOutcome(text=translated, provider=self.name, latency=0.0, char_count=len(payload.text))
