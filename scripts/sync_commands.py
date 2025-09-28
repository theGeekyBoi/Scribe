from __future__ import annotations

import asyncio

import discord

from bot import ScribeBot
from config import get_settings


async def main() -> None:
    settings = get_settings()
    intents = discord.Intents.none()
    bot = ScribeBot(intents=intents, settings=settings)
    async with bot:
        await bot.login(settings.discord_token)
        await bot.setup_hook()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
