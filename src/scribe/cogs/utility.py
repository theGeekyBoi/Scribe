from __future__ import annotations

import platform
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands

from .. import __version__
from ..bot import ScribeBot


class UtilityGroup(app_commands.Group):
    def __init__(self, bot: ScribeBot) -> None:
        super().__init__(name="utility", description="Utility commands.")
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction[discord.Client]) -> None:
        latency_ms = round(self.bot.latency * 1000, 2) if self.bot.latency else "N/A"
        await interaction.response.send_message(f"Pong! 🏓 {latency_ms} ms", ephemeral=True)

    @app_commands.command(name="about", description="Show information about the bot.")
    async def about(self, interaction: discord.Interaction[discord.Client]) -> None:
        now = datetime.now(UTC)
        uptime = now - self.bot.start_time
        embed = discord.Embed(
            title="About Scribe",
            color=discord.Color.blurple(),
            description="Scribe is a note-taking, bookmarking, and reminder bot for Discord.",
        )
        embed.add_field(name="Version", value=__version__)
        embed.add_field(name="Uptime", value=_format_timedelta(uptime), inline=True)
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.set_footer(text="Built for reliability and clarity.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Show command reference.")
    async def help(self, interaction: discord.Interaction[discord.Client]) -> None:
        embed = discord.Embed(
            title="Scribe Command Reference",
            color=discord.Color.teal(),
        )
        embed.add_field(
            name="Utility",
            value="\n".join(["`/ping`", "`/about`", "`/help`"]),
            inline=False,
        )
        embed.add_field(
            name="Notes",
            value="\n".join(["`/note add`", "`/note list`", "`/note delete`"]),
            inline=False,
        )
        embed.add_field(
            name="Bookmarks",
            value="\n".join(["`/bookmark add`", "`/bookmark list`", "`/bookmark remove`"]),
            inline=False,
        )
        embed.add_field(
            name="Reminders",
            value="\n".join(["`/reminder create`", "`/reminder list`", "`/reminder cancel`"]),
            inline=False,
        )
        embed.add_field(
            name="Admin",
            value="`/admin sync` (owners or admins)",
            inline=False,
        )
        embed.set_footer(text="Use /admin sync guild to refresh commands instantly in a development server.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


def _format_timedelta(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not parts:
        parts.append(f"{seconds}s")
    if not parts:
        parts.append("0s")
    return " ".join(parts)


async def setup(bot: ScribeBot) -> None:
    group = UtilityGroup(bot)
    bot.tree.add_command(group.ping)
    bot.tree.add_command(group.about)
    bot.tree.add_command(group.help)
