from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import discord
from loguru import logger

from bot.db import crud
from bot.db.models import TargetKindEnum
from bot.services.formatting import sanitize_for_webhook, stitch_translation
from bot.services.glossary import apply_glossary, compile_glossary
from bot.services.spans import extract_spans, reinsert_spans
from bot.services.translator.base import TranslationPayload
from bot.services.webhooks import WebhookManager


@dataclass(slots=True)
class TranslationJob:
    message_id: int
    guild_id: int
    channel_id: int
    author_id: int
    author_name: str
    author_avatar: Optional[str]
    content: str
    source_lang: str
    target_lang: str
    target_kind: TargetKindEnum
    reference_url: Optional[str]


class TranslationWorker:
    def __init__(self, bot: "ScribeBot") -> None:
        self.bot = bot
        self.queue: "asyncio.Queue[TranslationJob]" = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._webhooks = WebhookManager()
        self._thread_cache: dict[int, int] = {}

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="scribe-worker")

    async def enqueue(self, job: TranslationJob) -> None:
        await self.queue.put(job)

    async def _run(self) -> None:
        while True:
            job = await self.queue.get()
            try:
                await self._process(job)
            except Exception:
                logger.exception("Failed processing translation job %s", job)
            finally:
                self.queue.task_done()

    async def _process(self, job: TranslationJob) -> None:
        async with self.bot.sessionmaker() as session:
            glossary_entries = await crud.list_glossary_entries(session, job.guild_id)
        spans_text, spans = extract_spans(job.content)
        payload = TranslationPayload(
            text=spans_text,
            source_lang=job.source_lang,
            target_lang=job.target_lang,
            glossary=[(entry.term, entry.translation) for entry in glossary_entries] or None,
        )
        outcome = await self.bot.translators.translate(payload)
        translated = outcome.text
        if glossary_entries:
            compiled = compile_glossary(glossary_entries)
            translated = apply_glossary(translated, compiled)
        translated = reinsert_spans(translated, spans, job.content)
        translated = stitch_translation(job.reference_url, translated)
        message = await self._dispatch(job, translated)
        if message:
            async with self.bot.sessionmaker() as session:
                await crud.register_message_map(
                    session,
                    guild_id=job.guild_id,
                    channel_id=job.channel_id,
                    original_msg_id=job.message_id,
                    translated_msg_id=message.id,
                    dst_lang=job.target_lang,
                    target_kind=job.target_kind,
                )

    async def _dispatch(self, job: TranslationJob, text: str) -> Optional[discord.Message]:
        channel = self.bot.get_channel(job.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(job.channel_id)
            except discord.HTTPException:
                logger.warning("Unable to resolve channel %s", job.channel_id)
                return None
        if job.target_kind == TargetKindEnum.inline and isinstance(channel, discord.TextChannel):
            content = sanitize_for_webhook(text)
            return await self._webhooks.send(
                channel,
                username=f"{job.author_name} ↳ {job.target_lang.upper()}",
                avatar_url=job.author_avatar,
                content=content,
            )
        if job.target_kind == TargetKindEnum.threaded and isinstance(channel, discord.TextChannel):
            thread = await self._ensure_thread(channel)
            return await thread.send(text)
        if job.target_kind == TargetKindEnum.dm:
            user = self.bot.get_user(job.author_id) or await self.bot.fetch_user(job.author_id)
            return await user.send(text)
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            return await channel.send(text)
        return None

    async def _ensure_thread(self, channel: discord.TextChannel) -> discord.Thread:
        cached = self._thread_cache.get(channel.id)
        if cached:
            thread = channel.get_thread(cached)
            if thread:
                return thread
        thread_name = "🌐-translations"
        for thread in channel.threads:
            if thread.name == thread_name:
                self._thread_cache[channel.id] = thread.id
                return thread
        thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
        self._thread_cache[channel.id] = thread.id
        return thread


_worker_instance: Optional[TranslationWorker] = None


def get_worker(bot: "ScribeBot") -> TranslationWorker:
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = TranslationWorker(bot)
        _worker_instance.start()
    return _worker_instance
