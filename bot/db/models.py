from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, Integer, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata_obj = MetaData()


class Base(DeclarativeBase):
    metadata = metadata_obj


class TargetKindEnum(str, Enum):
    threaded = "threaded"
    inline = "inline"
    dm = "dm"


class UserSettings(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preferred_lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    dm_mirror_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GuildSettings(Base):
    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    default_lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    default_mode: Mapped[str] = mapped_column(String(32), default="on_demand")
    inline_auto_max_langs: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cost_cap_usd: Mapped[float | None] = mapped_column(Integer, nullable=True)
    retention_hours: Mapped[int] = mapped_column(Integer, default=72)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelOverride(Base):
    __tablename__ = "channel_overrides"

    channel_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_langs: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageMap(Base):
    __tablename__ = "message_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    original_msg_id: Mapped[int] = mapped_column(Integer, nullable=False)
    translated_msg_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dst_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    target_kind: Mapped[TargetKindEnum] = mapped_column(SAEnum(TargetKindEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GlossaryEntry(Base):
    __tablename__ = "glossary"

    guild_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(128), primary_key=True)
    translation: Mapped[str] = mapped_column(String(256))
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)


class UsageStats(Base):
    __tablename__ = "usage"

    guild_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[datetime] = mapped_column(Date, primary_key=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0)

