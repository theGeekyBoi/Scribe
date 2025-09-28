from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["openai", "deepl", "google"]
SUPPORTED_PROVIDERS = {"openai", "deepl", "google"}


class ProviderConfig(BaseModel):
    name: ProviderName = Field(default="openai")
    fallbacks: List[ProviderName] = Field(default_factory=list)
    openai_api_key: str | None = None
    deepl_api_key: str | None = None
    google_project_id: str | None = None
    google_credentials: str | None = None

    @field_validator("name")
    @classmethod
    def validate_provider(cls, value: str) -> ProviderName:
        value_lower = value.lower()
        if value_lower not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported translator provider: {value}")
        return value_lower  # type: ignore[return-value]

    @field_validator("fallbacks", mode="after")
    @classmethod
    def dedupe_fallbacks(cls, value: List[ProviderName]) -> List[ProviderName]:
        seen: set[str] = set()
        ordered: List[ProviderName] = []
        for item in value:
            item_lower = item.lower()
            if item_lower in seen or item_lower == "":
                continue
            if item_lower not in SUPPORTED_PROVIDERS:
                logger.warning("Ignoring unsupported fallback provider '{}'.", item)
                continue
            ordered.append(item_lower)  # type: ignore[arg-type]
            seen.add(item_lower)
        return ordered

    def ordered(self) -> List[ProviderName]:
        base: List[ProviderName] = [self.name]
        for fallback in self.fallbacks:
            if fallback not in base:
                base.append(fallback)
        return base


class ScribeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    discord_token: str = Field(alias="DISCORD_TOKEN")
    discord_client_id: int | None = Field(default=None, alias="DISCORD_CLIENT_ID")
    discord_guild_test_id: int | None = Field(default=None, alias="DISCORD_GUILD_TEST_ID")
    discord_public_key: str | None = Field(default=None, alias="DISCORD_PUBLIC_KEY")

    default_guild_lang: str = Field(default="en", alias="DEFAULT_GUILD_LANG")
    default_mode: str = Field(default="on_demand", alias="DEFAULT_MODE")
    inline_auto_max_langs: int = Field(default=1, alias="INLINE_AUTO_MAX_LANGS")
    retention_hours: int = Field(default=72, alias="RETENTION_HOURS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_path: str = Field(default="data/scribe.db", alias="DATABASE_PATH")

    translator_provider: ProviderName = Field(default="openai", alias="TRANSLATOR_PROVIDER")
    translator_fallbacks: str | None = Field(default=None, alias="TRANSLATOR_FALLBACKS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    deepl_api_key: str | None = Field(default=None, alias="DEEPL_API_KEY")
    google_project_id: str | None = Field(default=None, alias="GOOGLE_PROJECT_ID")
    google_credentials: str | None = Field(default=None, alias="GOOGLE_APPLICATION_CREDENTIALS")

    provider: ProviderConfig = Field(default_factory=ProviderConfig)

    worker_mode: bool = Field(default=False, alias="SCRIBE_WORKER_MODE")
    healthcheck_host: str = Field(default="127.0.0.1", alias="HEALTHCHECK_HOST")
    healthcheck_port: int = Field(default=8080, alias="HEALTHCHECK_PORT")

    @model_validator(mode="after")
    def _build_provider(self) -> "ScribeSettings":
        fallbacks_list: List[ProviderName] = []
        if self.translator_fallbacks:
            candidates = [item.strip() for item in self.translator_fallbacks.split(",") if item.strip()]
            for item in candidates:
                lowered = item.lower()
                if lowered in SUPPORTED_PROVIDERS:
                    fallbacks_list.append(lowered)  # type: ignore[arg-type]
                else:
                    logger.warning("Ignoring unsupported fallback provider '{}'.", item)
        self.provider = ProviderConfig(
            name=self.translator_provider,
            fallbacks=fallbacks_list,
            openai_api_key=self.openai_api_key,
            deepl_api_key=self.deepl_api_key,
            google_project_id=self.google_project_id,
            google_credentials=self.google_credentials,
        )
        return self

    @property
    def TRANSLATOR_PROVIDER(self) -> ProviderName:
        return self.provider.name

    @property
    def TRANSLATOR_FALLBACKS(self) -> List[ProviderName]:
        return self.provider.fallbacks


@lru_cache
def get_settings() -> ScribeSettings:
    try:
        return ScribeSettings()
    except ValidationError as exc:
        logger.error("Configuration validation failed: {}", exc)
        raise



