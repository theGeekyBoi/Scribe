from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional

import discord
from loguru import logger


@dataclass
class WebhookEntry:
    webhook: discord.Webhook
    lock: asyncio.Lock


class WebhookManager:
    def __init__(self) -> None:
        self._cache: Dict[int, WebhookEntry] = {}

    async def ensure_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        entry = self._cache.get(channel.id)
        if entry:
            return entry.webhook
        lock = asyncio.Lock()
        self._cache[channel.id] = WebhookEntry(webhook=None, lock=lock)  # type: ignore[arg-type]
        async with lock:
            webhook = await self._create_webhook(channel)
            self._cache[channel.id] = WebhookEntry(webhook=webhook, lock=lock)
            return webhook

    async def _create_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        try:
            for webhook in await channel.webhooks():
                if webhook.name == "Scribe Inline" and webhook.user == channel.guild.me:
                    return webhook
            return await channel.create_webhook(name="Scribe Inline")
        except discord.Forbidden:
            logger.warning("Missing webhook permissions in channel {}", channel.id)
            raise

    async def send(
        self,
        channel: discord.TextChannel,
        *,
        username: str,
        avatar_url: Optional[str],
        content: str,
    ) -> Optional[discord.Message]:
        webhook = await self.ensure_webhook(channel)
        return await webhook.send(
            content=content,
            username=username,
            avatar_url=avatar_url,
            wait=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
