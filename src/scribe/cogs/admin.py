from __future__ import annotations

import discord
from discord import app_commands

from .. import UserError
from ..bot import ScribeBot
from . import owner_or_admin_check, ensure_positive


class AdminGroup(app_commands.Group):
    def __init__(self, bot: ScribeBot) -> None:
        super().__init__(name="admin", description="Administrative utilities.")
        self.bot = bot

    @app_commands.describe(scope="Sync globally or to the current guild.")
    @app_commands.choices(
        scope=[
            app_commands.Choice(name="Guild", value="guild"),
            app_commands.Choice(name="Global", value="global"),
        ]
    )
    @app_commands.check(owner_or_admin_check())
    async def sync(
        self,
        interaction: discord.Interaction[discord.Client],
        scope: app_commands.Choice[str] | None = None,
    ) -> None:
        target_scope = scope.value if scope else None
        guild_id = interaction.guild_id if target_scope == "guild" else None
        if target_scope == "guild":
            if guild_id is None:
                guild_id = self.bot.settings.guild_id
            if guild_id is None:
                raise UserError("No guild available for guild-scoped sync.")
            ensure_positive(guild_id, "Guild ID")
        synced = await self.bot.sync_application_commands(scope=target_scope, guild_id=guild_id)
        message = f"Synced {len(synced)} commands ({target_scope or 'auto'})."
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: ScribeBot) -> None:
    bot.tree.add_command(AdminGroup(bot))
