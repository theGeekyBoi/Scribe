from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    ChannelOverride,
    GuildSettings,
    GlossaryEntry,
    MessageMap,
    TargetKindEnum,
    UsageStats,
    UserSettings,
)


async def get_or_create_user(session: AsyncSession, user_id: int) -> UserSettings:
    result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = UserSettings(user_id=user_id)
        session.add(user)
        await session.flush()
    return user


async def set_user_language(session: AsyncSession, user_id: int, lang: str | None) -> UserSettings:
    user = await get_or_create_user(session, user_id)
    user.preferred_lang = lang
    user.updated_at = datetime.utcnow()
    await session.commit()
    return user


async def set_user_dm_mirror(session: AsyncSession, user_id: int, enabled: bool) -> UserSettings:
    user = await get_or_create_user(session, user_id)
    user.dm_mirror_enabled = enabled
    user.updated_at = datetime.utcnow()
    await session.commit()
    return user


async def forget_user(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(UserSettings).where(UserSettings.user_id == user_id))
    await session.commit()


async def get_or_create_guild(session: AsyncSession, guild_id: int) -> GuildSettings:
    result = await session.execute(select(GuildSettings).where(GuildSettings.guild_id == guild_id))
    guild = result.scalar_one_or_none()
    if guild is None:
        guild = GuildSettings(guild_id=guild_id)
        session.add(guild)
        await session.flush()
    return guild


async def update_guild_settings(
    session: AsyncSession,
    guild_id: int,
    **kwargs,
) -> GuildSettings:
    guild = await get_or_create_guild(session, guild_id)
    for key, value in kwargs.items():
        if hasattr(guild, key) and value is not None:
            setattr(guild, key, value)
    guild.updated_at = datetime.utcnow()
    await session.commit()
    return guild


async def get_channel_override(session: AsyncSession, channel_id: int) -> ChannelOverride | None:
    result = await session.execute(select(ChannelOverride).where(ChannelOverride.channel_id == channel_id))
    return result.scalar_one_or_none()


async def upsert_channel_override(
    session: AsyncSession,
    *,
    guild_id: int,
    channel_id: int,
    enabled: bool | None = None,
    mode: str | None = None,
    target_langs: list[str] | None = None,
) -> ChannelOverride:
    override = await get_channel_override(session, channel_id)
    if override is None:
        override = ChannelOverride(guild_id=guild_id, channel_id=channel_id)
        session.add(override)
    if enabled is not None:
        override.enabled = enabled
    if mode is not None:
        override.mode = mode
    if target_langs is not None:
        override.target_langs = ",".join(sorted(set(target_langs))) if target_langs else None
    override.updated_at = datetime.utcnow()
    await session.commit()
    return override


async def get_channel_target_langs(session: AsyncSession, channel_id: int) -> list[str]:
    override = await get_channel_override(session, channel_id)
    if override and override.target_langs:
        return [lang for lang in override.target_langs.split(",") if lang]
    return []


async def register_message_map(
    session: AsyncSession,
    *,
    guild_id: int,
    channel_id: int,
    original_msg_id: int,
    translated_msg_id: int,
    dst_lang: str,
    target_kind: TargetKindEnum,
) -> MessageMap:
    mapping = MessageMap(
        guild_id=guild_id,
        channel_id=channel_id,
        original_msg_id=original_msg_id,
        translated_msg_id=translated_msg_id,
        dst_lang=dst_lang,
        target_kind=target_kind,
    )
    session.add(mapping)
    await session.commit()
    return mapping


async def fetch_message_mappings(
    session: AsyncSession,
    *,
    original_msg_id: int,
) -> Sequence[MessageMap]:
    result = await session.execute(
        select(MessageMap).where(MessageMap.original_msg_id == original_msg_id)
    )
    return result.scalars().all()


async def delete_message_mapping(session: AsyncSession, mapping_id: int) -> None:
    await session.execute(delete(MessageMap).where(MessageMap.id == mapping_id))
    await session.commit()


async def upsert_glossary_entry(
    session: AsyncSession,
    guild_id: int,
    term: str,
    translation: str,
    *,
    context: str | None = None,
    priority: int = 100,
) -> GlossaryEntry:
    entry = await session.get(GlossaryEntry, {"guild_id": guild_id, "term": term})
    if entry is None:
        entry = GlossaryEntry(
            guild_id=guild_id,
            term=term,
            translation=translation,
            context=context,
            priority=priority,
        )
        session.add(entry)
    else:
        entry.translation = translation
        entry.context = context
        entry.priority = priority
    await session.commit()
    return entry


async def remove_glossary_entry(session: AsyncSession, guild_id: int, term: str) -> bool:
    result = await session.execute(
        delete(GlossaryEntry).where(
            GlossaryEntry.guild_id == guild_id,
            GlossaryEntry.term == term,
        )
    )
    await session.commit()
    return result.rowcount > 0  # type: ignore[return-value]


async def list_glossary_entries(session: AsyncSession, guild_id: int) -> Sequence[GlossaryEntry]:
    result = await session.execute(
        select(GlossaryEntry).where(GlossaryEntry.guild_id == guild_id).order_by(GlossaryEntry.priority)
    )
    return result.scalars().all()


async def increment_usage(
    session: AsyncSession,
    guild_id: int,
    *,
    characters: int,
    cost: float,
) -> UsageStats:
    today = date.today()
    result = await session.execute(
        select(UsageStats).where(UsageStats.guild_id == guild_id, UsageStats.day == today)
    )
    stats = result.scalar_one_or_none()
    if stats is None:
        stats = UsageStats(guild_id=guild_id, day=today, char_count=0, cost_estimate_usd=0)
        session.add(stats)
    stats.char_count += characters
    stats.cost_estimate_usd += cost
    await session.commit()
    return stats


async def get_usage_for_period(
    session: AsyncSession,
    guild_id: int,
    days: int = 7,
) -> Sequence[UsageStats]:
    earliest = date.today().fromordinal(date.today().toordinal() - days + 1)
    result = await session.execute(
        select(UsageStats)
        .where(UsageStats.guild_id == guild_id, UsageStats.day >= earliest)
        .order_by(UsageStats.day)
    )
    return result.scalars().all()
