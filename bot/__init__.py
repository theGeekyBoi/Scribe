from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import discord
from discord import app_commands
from loguru import logger

from .db.session import create_sessionmaker, init_db
from .exceptions import ConfigError, ScribeError
from .services.metrics import MetricsRegistry
from .services.translator.base import TranslatorRegistry

SetupFunc = Callable[["ScribeBot"], Awaitable[None]]


@dataclass(slots=True)
class BotContext:
    translator_registry: TranslatorRegistry
    metrics: MetricsRegistry


class ScribeBot(discord.Client):
    """Discord client implementation for Scribe."""

    def add_listener(self, func, name: str | None = None) -> None:
        super().add_listener(func, name)


    def __init__(self, *, intents: discord.Intents, settings: Any) -> None:
        super().__init__(intents=intents)
        if not settings.discord_token:
            raise ConfigError("Discord token missing")
        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self.metrics = MetricsRegistry()
        self.translators = TranslatorRegistry(settings)
        self._sessionmaker = create_sessionmaker(settings.database_path)
        self.context = BotContext(
            translator_registry=self.translators,
            metrics=self.metrics,
        )
        self.start_time = datetime.now(timezone.utc)
        self._command_synced = asyncio.Event()

    @property
    def sessionmaker(self):  # type: ignore[override]
        return self._sessionmaker

    async def setup_hook(self) -> None:
        await init_db(self._sessionmaker)
        await self._load_cogs()
        await self._sync_commands()
        self._command_synced.set()

    async def _load_cogs(self) -> None:
        for module_name in (
            "bot.cogs.user",
            "bot.cogs.admin",
            "bot.cogs.listeners",
        ):
            await self._import_and_setup(module_name)

    async def _import_and_setup(self, module_name: str) -> None:
        logger.debug("Loading cog module {}", module_name)
        module = importlib.import_module(module_name)
        if not hasattr(module, "setup"):
            raise ConfigError(f"Cog module {module_name} is missing setup()")
        setup_func: SetupFunc = getattr(module, "setup")
        await setup_func(self)

    async def _sync_commands(self) -> None:
        guild = None
        if self.settings.discord_guild_test_id:
            guild = discord.Object(id=self.settings.discord_guild_test_id)
        await self.tree.sync(guild=guild)
        if guild:
            logger.info("Synced commands to test guild {}", guild.id)
        else:
            logger.info("Synced commands globally (may take up to 1 hour)")

    async def on_ready(self) -> None:
        logger.info("Logged in as {} (id={})", self.user, getattr(self.user, "id", None))

    async def on_app_command_error(
        self, interaction: discord.Interaction[Any], error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, ScribeError):
            if interaction.response.is_done():
                await interaction.followup.send(str(error.original), ephemeral=True)
            else:
                await interaction.response.send_message(str(error.original), ephemeral=True)
            return
        logger.exception("Unhandled app command error: {}", error)
        if interaction.response.is_done():
            await interaction.followup.send("Sorry, something went wrong.", ephemeral=True)
        else:
            await interaction.response.send_message("Sorry, something went wrong.", ephemeral=True)
