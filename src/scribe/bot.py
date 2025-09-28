from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Sequence

import discord
from discord import app_commands

from . import UserError, __version__
from .db import Database
from .logging_config import configure_logging
from .settings import Settings


class ScribeBot(discord.Client):
    """Discord Client subclass managing the application command tree."""

    def __init__(self, settings: Settings, database: Database) -> None:
        intents = discord.Intents.default()
        # Enable below after granting the Message Content intent in the Developer Portal.
        # intents.message_content = True
        super().__init__(intents=intents)
        self.settings = settings
        self.db = database
        self.tree = app_commands.CommandTree(self)
        self.log = logging.getLogger("scribe.bot")
        self.start_time = datetime.now(UTC)
        self._reminder_task: asyncio.Task[None] | None = None

    def is_owner_id(self, user_id: int) -> bool:
        return user_id in self.settings.owner_ids

    async def setup_hook(self) -> None:
        from .cogs import admin, bookmarks, notes, reminders, utility

        await self.db.connect()
        await self.db.migrate()

        await utility.setup(self)
        await notes.setup(self)
        await bookmarks.setup(self)
        await reminders.setup(self)
        await admin.setup(self)

        default_scope = "guild" if self.settings.guild_id else "global"
        synced = await self.sync_application_commands(scope=default_scope)
        self.log.info(
            "Command tree synced",
            extra={"scope": default_scope, "count": len(synced)},
        )

        self._reminder_task = asyncio.create_task(
            self._reminder_dispatch_loop(), name="scribe-reminder-dispatcher"
        )

    async def on_ready(self) -> None:
        self.log.info(
            "Logged in as %s (id=%s)",
            self.user,
            self.user.id if self.user else None,
            extra={"guilds": len(self.guilds)},
        )

    async def on_app_command_completion(
        self, interaction: discord.Interaction[Any], command: app_commands.Command[Any, ..., Any]
    ) -> None:
        self.log.info(
            "Command completed",
            extra={
                "command": command.qualified_name,
                "guild_id": interaction.guild_id,
                "channel_id": getattr(interaction.channel, "id", None),
                "user_id": interaction.user.id if interaction.user else None,
            },
        )

    async def on_app_command_error(
        self, interaction: discord.Interaction[Any], error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandInvokeError) and error.original:
            original = error.original
        else:
            original = error

        if isinstance(original, UserError):
            await self._send_ephemeral(interaction, str(original))
            return

        if isinstance(original, app_commands.CheckFailure):
            await self._send_ephemeral(interaction, "You do not have permission to use this command.")
            return

        self.log.exception(
            "Unhandled command error",
            exc_info=original,
            extra={
                "guild_id": interaction.guild_id,
                "channel_id": getattr(interaction.channel, "id", None),
                "user_id": interaction.user.id if interaction.user else None,
            },
        )
        await self._send_ephemeral(interaction, "Sorry, something went wrong.")

    async def _send_ephemeral(self, interaction: discord.Interaction[Any], message: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def sync_application_commands(
        self, scope: str | None = None, guild_id: int | None = None
    ) -> Sequence[app_commands.AppCommand]:
        target = scope or ("guild" if (guild_id or self.settings.guild_id) else "global")
        if target == "guild":
            effective_guild = guild_id or self.settings.guild_id
            if not effective_guild:
                raise UserError("No guild configured for guild-scoped sync.")
            guild_obj = discord.Object(id=effective_guild)
            synced = await self.tree.sync(guild=guild_obj)
            self.log.info(
                "Synced commands to guild",
                extra={"guild_id": effective_guild, "count": len(synced)},
            )
            return synced
        synced = await self.tree.sync()
        self.log.info("Synced commands globally", extra={"count": len(synced)})
        return synced

    async def close(self) -> None:
        if self._reminder_task:
            self._reminder_task.cancel()
            try:
                await self._reminder_task
            except asyncio.CancelledError:
                pass
        await self.db.close()
        await super().close()

    async def _reminder_dispatch_loop(self) -> None:
        try:
            while not self.is_closed():
                await self._dispatch_due_reminders()
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.log.debug("Reminder dispatcher cancelled")
            raise
        except Exception:
            self.log.exception("Reminder dispatcher crashed; restarting in 10 seconds")
            await asyncio.sleep(10)
            self._reminder_task = asyncio.create_task(
                self._reminder_dispatch_loop(), name="scribe-reminder-dispatcher"
            )

    async def _dispatch_due_reminders(self) -> None:
        now = datetime.now(UTC)
        due = await self.db.get_due_reminders(now)
        if not due:
            return
        self.log.info("Dispatching reminders", extra={"count": len(due)})
        for reminder in due:
            channel = self.get_channel(reminder["channel_id"])
            if channel is None:
                try:
                    channel = await self.fetch_channel(reminder["channel_id"])
                except discord.HTTPException:
                    channel = None
            if not channel or not hasattr(channel, "send"):
                self.log.warning(
                    "Unable to resolve channel for reminder",
                    extra={"reminder_id": reminder["id"], "channel_id": reminder["channel_id"]},
                )
                await self.db.mark_reminder_sent(reminder["id"])
                continue

            due_at = datetime.fromisoformat(reminder["due_at"])
            content = (
                f"<@{reminder['user_id']}> ⏰ Reminder: {reminder['message']}\n"
                f"(Scheduled for {discord.utils.format_dt(due_at, style='f')} | "
                f"{discord.utils.format_dt(due_at, style='R')})"
            )
            try:
                await channel.send(content)
                await self.db.mark_reminder_sent(reminder["id"])
                self.log.info(
                    "Reminder dispatched",
                    extra={
                        "reminder_id": reminder["id"],
                        "guild_id": reminder["guild_id"],
                        "channel_id": reminder["channel_id"],
                        "user_id": reminder["user_id"],
                    },
                )
            except discord.HTTPException as exc:
                self.log.exception(
                    "Failed to send reminder",
                    exc_info=exc,
                    extra={
                        "reminder_id": reminder["id"],
                        "guild_id": reminder["guild_id"],
                        "channel_id": reminder["channel_id"],
                    },
                )
                # Mark as sent to prevent repeated failures; operators can recreate if needed.
                await self.db.mark_reminder_sent(reminder["id"])


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    db = Database(settings.db_path)
    bot = ScribeBot(settings=settings, database=db)
    bot.log.info("Starting Scribe v%s", __version__)
    bot.run(settings.token)


if __name__ == "__main__":
    main()
