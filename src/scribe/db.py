from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncIterator

import aiosqlite


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Database:
    """Async SQLite helper providing migrations and CRUD helpers."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            await self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        await self.connect()
        if self._conn is None:
            raise RuntimeError("Database connection is not available.")
        yield self._conn

    async def migrate(self) -> None:
        async with self.connection() as conn:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    author_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_notes_guild_channel ON notes (guild_id, channel_id);
                CREATE INDEX IF NOT EXISTS idx_notes_author ON notes (author_id);

                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message_link TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_bookmarks_guild_user ON bookmarks (guild_id, user_id);

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_reminders_sent_due ON reminders (sent, due_at);
                CREATE INDEX IF NOT EXISTS idx_reminders_guild_user ON reminders (guild_id, user_id);
                """
            )
            await conn.commit()

    async def add_note(self, guild_id: int, channel_id: int, author_id: int, content: str) -> int:
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO notes (guild_id, channel_id, author_id, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, channel_id, author_id, content, _utcnow_iso()),
            )
            await conn.commit()
            return cursor.lastrowid

    async def list_notes(
        self, guild_id: int, author_id: int | None, limit: int
    ) -> list[dict[str, Any]]:
        query = """
            SELECT id, guild_id, channel_id, author_id, content, created_at
            FROM notes
            WHERE guild_id = ?
        """
        params: list[Any] = [guild_id]
        if author_id is not None:
            query += " AND author_id = ?"
            params.append(author_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        async with self.connection() as conn:
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetch_note(self, note_id: int) -> dict[str, Any] | None:
        async with self.connection() as conn:
            async with conn.execute(
                """
                SELECT id, guild_id, channel_id, author_id, content, created_at
                FROM notes
                WHERE id = ?
                """,
                (note_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete_note(self, note_id: int) -> None:
        async with self.connection() as conn:
            await conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            await conn.commit()

    async def add_bookmark(
        self, guild_id: int, user_id: int, message_link: str, note: str | None
    ) -> int:
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO bookmarks (guild_id, user_id, message_link, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, user_id, message_link, note, _utcnow_iso()),
            )
            await conn.commit()
            return cursor.lastrowid

    async def list_bookmarks(self, guild_id: int, user_id: int, limit: int) -> list[dict[str, Any]]:
        async with self.connection() as conn:
            async with conn.execute(
                """
                SELECT id, guild_id, user_id, message_link, note, created_at
                FROM bookmarks
                WHERE guild_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (guild_id, user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetch_bookmark(self, bookmark_id: int) -> dict[str, Any] | None:
        async with self.connection() as conn:
            async with conn.execute(
                """
                SELECT id, guild_id, user_id, message_link, note, created_at
                FROM bookmarks
                WHERE id = ?
                """,
                (bookmark_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete_bookmark(self, bookmark_id: int) -> None:
        async with self.connection() as conn:
            await conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            await conn.commit()

    async def add_reminder(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        message: str,
        due_at: datetime,
    ) -> int:
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO reminders (guild_id, channel_id, user_id, message, due_at, created_at, sent)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    guild_id,
                    channel_id,
                    user_id,
                    message,
                    due_at.astimezone(UTC).replace(microsecond=0).isoformat(),
                    _utcnow_iso(),
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def list_reminders(
        self, guild_id: int, user_id: int | None, limit: int
    ) -> list[dict[str, Any]]:
        query = """
            SELECT id, guild_id, channel_id, user_id, message, due_at, created_at, sent
            FROM reminders
            WHERE guild_id = ? AND sent = 0
        """
        params: list[Any] = [guild_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY due_at ASC LIMIT ?"
        params.append(limit)
        async with self.connection() as conn:
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetch_reminder(self, reminder_id: int) -> dict[str, Any] | None:
        async with self.connection() as conn:
            async with conn.execute(
                """
                SELECT id, guild_id, channel_id, user_id, message, due_at, created_at, sent
                FROM reminders
                WHERE id = ?
                """,
                (reminder_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete_reminder(self, reminder_id: int) -> None:
        async with self.connection() as conn:
            await conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            await conn.commit()

    async def get_due_reminders(self, now: datetime) -> list[dict[str, Any]]:
        async with self.connection() as conn:
            async with conn.execute(
                """
                SELECT id, guild_id, channel_id, user_id, message, due_at, created_at, sent
                FROM reminders
                WHERE sent = 0 AND due_at <= ?
                ORDER BY due_at ASC
                """,
                (now.astimezone(UTC).isoformat(),),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def mark_reminder_sent(self, reminder_id: int) -> None:
        async with self.connection() as conn:
            await conn.execute(
                "UPDATE reminders SET sent = 1 WHERE id = ?",
                (reminder_id,),
            )
            await conn.commit()
