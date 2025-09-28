from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord import app_commands

from .. import UserError
from ..bot import ScribeBot
from . import ensure_positive


def _shorten(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _local_timezone() -> datetime.tzinfo:
    tz = datetime.now().astimezone().tzinfo
    return tz or UTC


def _format_timestamp(value: str) -> tuple[str, str]:
    dt = datetime.fromisoformat(value)
    local_dt = dt.astimezone(_local_timezone())
    absolute = local_dt.strftime("%Y-%m-%d %H:%M %Z")
    relative = discord.utils.format_dt(dt, style="R")
    return absolute, relative


class NotesGroup(app_commands.Group):
    def __init__(self, bot: ScribeBot) -> None:
        super().__init__(name="note", description="Capture and manage notes.")
        self.bot = bot

    @app_commands.describe(content="Text you want to store as a note.")
    async def add(self, interaction: discord.Interaction[discord.Client], content: str) -> None:
        if not content.strip():
            raise UserError("Note content cannot be empty.")
        if len(content) > 2000:
            raise UserError("Note content must be 2000 characters or fewer.")

        if interaction.guild is None or interaction.channel is None:
            raise UserError("Notes can only be used inside servers.")
        note_id = await self.bot.db.add_note(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            author_id=interaction.user.id,
            content=content.strip(),
        )
        now = datetime.now(UTC)
        await interaction.response.send_message(
            f"Saved note #{note_id} at {discord.utils.format_dt(now, style='f')} (UTC).",
            ephemeral=True,
        )

    @app_commands.describe(
        user="User whose notes to view (default: yourself).",
        limit="Number of notes to return (1-50).",
    )
    async def list(
        self,
        interaction: discord.Interaction[discord.Client],
        user: discord.User | None = None,
        limit: app_commands.Range[int, 1, 50] = 10,
    ) -> None:
        if interaction.guild is None:
            raise UserError("Notes can only be used in servers.")
        target = user or interaction.user
        notes = await self.bot.db.list_notes(
            guild_id=interaction.guild.id,
            author_id=target.id,
            limit=limit,
        )
        if not notes:
            await interaction.response.send_message("No notes found.", ephemeral=True)
            return

        title_user = target.mention
        lines: list[str] = []
        for note in notes:
            absolute, relative = _format_timestamp(note["created_at"])
            lines.append(
                f"**#{note['id']}** • {_shorten(note['content'])}\n"
                f"↳ {absolute} ({relative})"
            )
        embed = discord.Embed(
            title=f"Notes for {title_user}",
            description="\n\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.describe(id="Identifier of the note to remove.")
    async def delete(self, interaction: discord.Interaction[discord.Client], id: int) -> None:
        ensure_positive(id, "Note ID")
        note = await self.bot.db.fetch_note(id)
        if note is None:
            raise UserError("That note does not exist.")
        if interaction.guild is None or note["guild_id"] != interaction.guild.id:
            raise UserError("You can only delete notes from this server.")

        is_owner = self.bot.is_owner_id(interaction.user.id)
        has_manage = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_messages

        if note["author_id"] != interaction.user.id and not (is_owner or has_manage):
            raise UserError("You can only delete your own notes unless you have Manage Messages permission.")

        await self.bot.db.delete_note(id)
        await interaction.response.send_message(f"Deleted note #{id}.", ephemeral=True)


async def setup(bot: ScribeBot) -> None:
    bot.tree.add_command(NotesGroup(bot))
