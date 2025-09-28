from __future__ import annotations

from typing import Any, Awaitable, Callable

import discord
from discord import app_commands

from .. import UserError


def owner_or_admin_check() -> Callable[[discord.Interaction[Any]], Awaitable[bool]]:
    async def predicate(interaction: discord.Interaction[Any]) -> bool:
        client = interaction.client
        if isinstance(client, discord.Client):
            bot = client
        else:
            raise RuntimeError("Interaction client is unavailable.")

        is_owner = hasattr(bot, "is_owner_id") and bot.is_owner_id(interaction.user.id)  # type: ignore[attr-defined]
        if is_owner:
            return True

        if interaction.guild and isinstance(interaction.user, discord.Member):
            if interaction.user.guild_permissions.administrator:
                return True

        raise app_commands.CheckFailure("Administrator permission or bot ownership required.")

    return predicate


def ensure_positive(identifier: int, label: str) -> None:
    if identifier <= 0:
        raise UserError(f"{label} must be a positive integer.")
