from __future__ import annotations

from typing import Optional

import discord
from loguru import logger

from bot import ScribeBot
from bot.db import crud
from bot.db.models import TargetKindEnum
from bot.services.langid import detect_language
from config import ScribeSettings
from worker import TranslationJob, get_worker


async def _resolve_mode(
    bot: ScribeBot,
    message: discord.Message,
) -> tuple[str, list[str]]:
    async with bot.sessionmaker() as session:
        override = await crud.get_channel_override(session, message.channel.id)
        guild_settings = await crud.get_or_create_guild(session, message.guild.id)
    mode = override.mode if override and override.mode else guild_settings.default_mode
    langs = []
    if override and override.target_langs:
        langs = override.target_langs.split(",")
    if not langs and guild_settings.default_lang:
        langs = [guild_settings.default_lang]
    if not langs:
        langs = [bot.settings.default_guild_lang]
    if mode == "inline_auto":
        max_langs = bot.settings.inline_auto_max_langs
        langs = langs[:max_langs]
    return mode, langs


async def handle_message(bot: ScribeBot, message: discord.Message) -> None:
    if message.author.bot or message.guild is None:
        return
    if not message.content:
        return
    mode, langs = await _resolve_mode(bot, message)
    detection = detect_language(message.content)
    worker = get_worker(bot)
    for lang in langs:
        if lang == detection.language:
            continue
        target_kind = TargetKindEnum.threaded
        if mode == "inline_auto":
            target_kind = TargetKindEnum.inline
        elif mode == "dm_mirror":
            target_kind = TargetKindEnum.dm
        job = TranslationJob(
            message_id=message.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            author_id=message.author.id,
            author_name=message.author.display_name,
            author_avatar=message.author.display_avatar.url if message.author.display_avatar else None,
            content=message.content,
            source_lang=detection.language,
            target_lang=lang,
            target_kind=target_kind,
            reference_url=message.jump_url,
        )
        await worker.enqueue(job)


async def handle_edit(bot: ScribeBot, before: discord.Message, after: discord.Message) -> None:
    await handle_message(bot, after)


async def handle_delete(bot: ScribeBot, message: discord.Message) -> None:
    if message.guild is None:
        return
    async with bot.sessionmaker() as session:
        mappings = await crud.fetch_message_mappings(session, original_msg_id=message.id)
        for mapping in mappings:
            channel = bot.get_channel(mapping.channel_id)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(mapping.channel_id)
                except discord.HTTPException:
                    logger.warning("Unable to fetch channel %s for deletion", mapping.channel_id)
                    continue
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    msg = await channel.fetch_message(mapping.translated_msg_id)
                    await msg.delete()
                except discord.HTTPException:
                    logger.debug("Translated message already deleted")
        for mapping in mappings:
            await crud.delete_message_mapping(session, mapping.id)


async def setup(bot: ScribeBot) -> None:
    async def on_message(message: discord.Message) -> None:
        await handle_message(bot, message)

    async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
        await handle_edit(bot, before, after)

    async def on_message_delete(message: discord.Message) -> None:
        await handle_delete(bot, message)

    bot.add_listener(on_message, "on_message")
    bot.add_listener(on_message_edit, "on_message_edit")
    bot.add_listener(on_message_delete, "on_message_delete")

