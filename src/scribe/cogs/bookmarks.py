from __future__ import annotations

import re
from datetime import UTC, datetime

import discord
from discord import app_commands

from .. import UserError
from ..bot import ScribeBot
from . import ensure_positive

MESSAGE_LINK_PATTERN = re.compile(
    r"^https://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(?P<guild>\d{17,20})/(?P<channel>\d{17,20})/(?P<message>\d{17,20})$"
)


def _shorten(text: str, limit: int = 120) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


class BookmarksGroup(app_commands.Group):
    def __init__(self, bot: ScribeBot) -> None:
        super().__init__(name="bookmark", description="Save and revisit important messages.")
        self.bot = bot

    @app_commands.describe(
        message_link="Discord message link to bookmark.",
        note="Optional label for the bookmark.",
    )
    async def add(
        self,
        interaction: discord.Interaction[discord.Client],
        message_link: str,
        note: str | None = None,
    ) -> None:
        if interaction.guild is None:
            raise UserError("Bookmarks must be created inside a server.")
        match = MESSAGE_LINK_PATTERN.match(message_link.strip())
        if not match:
            raise UserError("Message link must match https://discord.com/channels/<guild>/<channel>/<message>.")
        guild_id = int(match.group("guild"))
        if guild_id != interaction.guild.id:
            raise UserError("Message link must reference a message in this server.")
        if note and len(note) > 160:
            raise UserError("Bookmark note must be 160 characters or fewer.")

        bookmark_id = await self.bot.db.add_bookmark(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            message_link=message_link.strip(),
            note=note.strip() if note else None,
        )
        await interaction.response.send_message(
            f"Saved bookmark #{bookmark_id} → {message_link}",
            ephemeral=True,
        )

    @app_commands.describe(limit="Number of bookmarks to list (1-50).")
    async def list(
        self,
        interaction: discord.Interaction[discord.Client],
        limit: app_commands.Range[int, 1, 50] = 10,
    ) -> None:
        if interaction.guild is None:
            raise UserError("Bookmarks are only available inside servers.")
        bookmarks = await self.bot.db.list_bookmarks(
            guild_id=interaction.guild.id, user_id=interaction.user.id, limit=limit
        )
        if not bookmarks:
            await interaction.response.send_message("You have no bookmarks yet.", ephemeral=True)
            return

        lines: list[str] = []
        for bookmark in bookmarks:
            created = datetime.fromisoformat(bookmark["created_at"])
            note = f" — {_shorten(bookmark['note'])}" if bookmark["note"] else ""
            lines.append(
                f"**#{bookmark['id']}** {bookmark['message_link']}{note}\n"
                f"↳ {discord.utils.format_dt(created, style='f')} ({discord.utils.format_dt(created, style='R')})"
            )
        embed = discord.Embed(
            title=f"Bookmarks for {interaction.user.display_name}",
            description="\n\n".join(lines),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.describe(id="Identifier of the bookmark to remove.")
    async def remove(self, interaction: discord.Interaction[discord.Client], id: int) -> None:
        ensure_positive(id, "Bookmark ID")
        bookmark = await self.bot.db.fetch_bookmark(id)
        if bookmark is None:
            raise UserError("That bookmark does not exist.")
        if bookmark["guild_id"] != getattr(interaction.guild, "id", None):
            raise UserError("You can only remove bookmarks from this server.")
        if bookmark["user_id"] != interaction.user.id and not self.bot.is_owner_id(interaction.user.id):
            raise UserError("You can only remove your own bookmarks.")

        await self.bot.db.delete_bookmark(id)
        await interaction.response.send_message(f"Removed bookmark #{id}.", ephemeral=True)


async def setup(bot: ScribeBot) -> None:
    bot.tree.add_command(BookmarksGroup(bot))
