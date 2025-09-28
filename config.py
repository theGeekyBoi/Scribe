from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["openai", "deepl", "google"]


class ProviderConfig(BaseModel):
    name: ProviderName = Field(alias="TRANSLATOR_PROVIDER")
    fallbacks: list[ProviderName] = Field(default_factory=list, alias="TRANSLATOR_FALLBACKS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    deepl_api_key: str | None = Field(default=None, alias="DEEPL_API_KEY")
    google_project_id: str | None = Field(default=None, alias="GOOGLE_PROJECT_ID")
    google_credentials: str | None = Field(default=None, alias="GOOGLE_APPLICATION_CREDENTIALS")

    def ordered(self) -> list[ProviderName]:
        seen: set[ProviderName] = set()
        order: list[ProviderName] = []
        for provider in [self.name, *self.fallbacks]:
            if provider in seen:
                continue
            order.append(provider)
            seen.add(provider)
        return order


class ScribeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    discord_token: str = Field(alias="DISCORD_TOKEN")
    discord_client_id: int | None = Field(default=None, alias="DISCORD_CLIENT_ID")
    discord_guild_test_id: int | None = Field(default=None, alias="DISCORD_GUILD_TEST_ID")

    default_guild_lang: str = Field(default="en", alias="DEFAULT_GUILD_LANG")
    default_mode: str = Field(default="on_demand", alias="DEFAULT_MODE")
    inline_auto_max_langs: int = Field(default=1, alias="INLINE_AUTO_MAX_LANGS")
    retention_hours: int = Field(default=72, alias="RETENTION_HOURS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_path: str = Field(default="data/scribe.db", alias="DATABASE_PATH")

    provider: ProviderConfig = Field(default_factory=ProviderConfig)

    worker_mode: bool = Field(default=False, alias="SCRIBE_WORKER_MODE")
    healthcheck_host: str = Field(default="127.0.0.1", alias="HEALTHCHECK_HOST")
    healthcheck_port: int = Field(default=8080, alias="HEALTHCHECK_PORT")


@lru_cache
def get_settings() -> ScribeSettings:
    return ScribeSettings()
