from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


def _parse_optional_int(raw: str | None) -> int | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError as exc:
        raise ValueError(f"Expected a positive integer, got {raw!r}") from exc


def _parse_owner_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    owners: set[int] = set()
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            owner_id = int(piece)
            if owner_id <= 0:
                raise ValueError
            owners.add(owner_id)
        except ValueError as exc:
            raise ValueError(f"Invalid OWNER_IDS entry: {piece!r}") from exc
    return owners


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration derived from environment variables."""

    token: str
    client_id: int | None
    guild_id: int | None
    log_level: str
    db_path: str
    owner_ids: set[int]

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required to start the bot.")
        client_id = _parse_optional_int(os.getenv("CLIENT_ID"))
        guild_id = _parse_optional_int(os.getenv("GUILD_ID"))
        log_level = (os.getenv("LOG_LEVEL") or "INFO").upper()
        db_path = os.getenv("DB_PATH") or "./scribe.sqlite3"
        owner_ids = _parse_owner_ids(os.getenv("OWNER_IDS"))
        return cls(
            token=token,
            client_id=client_id,
            guild_id=guild_id,
            log_level=log_level,
            db_path=db_path,
            owner_ids=owner_ids,
        )
