from __future__ import annotations

import asyncio
import signal

import discord
from loguru import logger

from bot import ScribeBot
from config import get_settings
from worker import get_worker


def configure_logging(level: str) -> None:
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=level.upper(), backtrace=False, diagnose=False)


async def runner() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.guilds = True
    bot = ScribeBot(intents=intents, settings=settings)
    get_worker(bot)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows may not support all signals
            pass

    async with bot:
        start_task = asyncio.create_task(bot.start(settings.discord_token))
        await stop_event.wait()
        await bot.close()
        await start_task


def main() -> None:
    asyncio.run(runner())


if __name__ == "__main__":
    main()
