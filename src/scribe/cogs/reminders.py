from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands

from .. import UserError
from ..bot import ScribeBot
from . import ensure_positive

RELATIVE_PATTERN = re.compile(r"^in\s+(?P<delta>.+)$", re.IGNORECASE)
RELATIVE_COMPONENT = re.compile(r"(\d+)([dhm])", re.IGNORECASE)
ISO_PATTERN = re.compile(
    r"""
    ^
    (?P<date>\d{4}-\d{2}-\d{2})
    [T\s]
    (?P<time>\d{2}:\d{2}(?::\d{2})?)
    (?P<tz>Z|[+-]\d{2}:?\d{2})?
    $
    """,
    re.VERBOSE,
)


def parse_time_spec(spec: str, now: datetime | None = None) -> datetime:
    """Parse absolute or relative time expressions into a UTC datetime."""
    if not spec:
        raise UserError("Time specification cannot be empty.")
    current = now or datetime.now(UTC)
    spec = spec.strip()

    match = RELATIVE_PATTERN.match(spec)
    if match:
        delta_spec = match.group("delta")
        if not delta_spec:
            raise UserError("Relative time must include a duration, e.g. `in 10m`.")
        compact = delta_spec.replace(" ", "")
        idx = 0
        total = timedelta()
        for comp in RELATIVE_COMPONENT.finditer(compact):
            if comp.start() != idx:
                raise UserError("Could not parse that relative time expression.")
            idx = comp.end()
            amount = int(comp.group(1))
            unit = comp.group(2).lower()
            if amount <= 0:
                raise UserError("Relative time values must be positive.")
            if unit == "d":
                total += timedelta(days=amount)
            elif unit == "h":
                total += timedelta(hours=amount)
            elif unit == "m":
                total += timedelta(minutes=amount)
        if idx != len(compact) or total == timedelta():
            raise UserError("Could not parse that relative time expression.")
        return current + total

    iso_match = ISO_PATTERN.match(spec)
    if iso_match:
        tz_part = iso_match.group("tz")
        date_part = iso_match.group("date")
        time_part = iso_match.group("time")
        cleaned = f"{date_part}T{time_part}"
        if tz_part:
            if tz_part.upper() == "Z":
                cleaned += "+00:00"
            elif ":" not in tz_part:
                cleaned += tz_part[:-2] + ":" + tz_part[-2:]
            else:
                cleaned += tz_part
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo or UTC
            dt = dt.replace(tzinfo=local_tz)
        return dt.astimezone(UTC)

    try:
        local_tz = datetime.now().astimezone().tzinfo or UTC
        dt = datetime.strptime(spec, "%Y-%m-%d %H:%M").replace(tzinfo=local_tz)
        return dt.astimezone(UTC)
    except ValueError:
        pass

    raise UserError(
        "Unrecognized time format. Examples: `in 10m`, `2024-05-01 14:30`, or `2024-05-01T14:30Z`."
    )


def humanize_timedelta(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "now"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append("less than a minute")
    return " ".join(parts)


class RemindersGroup(app_commands.Group):
    def __init__(self, bot: ScribeBot) -> None:
        super().__init__(name="reminder", description="Schedule and manage reminders.")
        self.bot = bot

    @app_commands.describe(
        when="When the reminder should trigger (relative or absolute time).",
        message="Reminder text to send.",
    )
    async def create(
        self,
        interaction: discord.Interaction[discord.Client],
        when: str,
        message: str,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            raise UserError("Reminders must be created inside a server channel.")
        if not message.strip():
            raise UserError("Reminder message cannot be empty.")
        if len(message) > 512:
            raise UserError("Reminder message must be 512 characters or fewer.")

        due_at = parse_time_spec(when)
        now = datetime.now(UTC)
        if due_at <= now + timedelta(seconds=10):
            raise UserError("Reminders must be scheduled at least 10 seconds in the future.")

        reminder_id = await self.bot.db.add_reminder(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            user_id=interaction.user.id,
            message=message.strip(),
            due_at=due_at,
        )
        human = humanize_timedelta(due_at - now)
        await interaction.response.send_message(
            f"Reminder #{reminder_id} set for {discord.utils.format_dt(due_at, style='f')} "
            f"({discord.utils.format_dt(due_at, style='R')} — {human}).",
            ephemeral=True,
        )

    @app_commands.describe(
        user="Filter by user (default: yourself).",
        limit="Number of reminders to return (1-50).",
    )
    async def list(
        self,
        interaction: discord.Interaction[discord.Client],
        user: discord.User | None = None,
        limit: app_commands.Range[int, 1, 50] = 10,
    ) -> None:
        if interaction.guild is None:
            raise UserError("Reminders are only available in servers.")
        target_user_id = user.id if user else interaction.user.id
        reminders = await self.bot.db.list_reminders(
            guild_id=interaction.guild.id, user_id=target_user_id, limit=limit
        )
        if not reminders:
            await interaction.response.send_message("No pending reminders.", ephemeral=True)
            return

        lines: list[str] = []
        for reminder in reminders:
            due_at = datetime.fromisoformat(reminder["due_at"])
            lines.append(
                f"**#{reminder['id']}** • {discord.utils.escape_markdown(reminder['message'])}\n"
                f"↳ {discord.utils.format_dt(due_at, style='f')} ({discord.utils.format_dt(due_at, style='R')})"
            )
        embed = discord.Embed(
            title=f"Pending reminders for {user.mention if user else interaction.user.mention}",
            description="\n\n".join(lines),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.describe(id="Identifier of the reminder to cancel.")
    async def cancel(self, interaction: discord.Interaction[discord.Client], id: int) -> None:
        ensure_positive(id, "Reminder ID")
        reminder = await self.bot.db.fetch_reminder(id)
        if reminder is None:
            raise UserError("That reminder does not exist.")
        if interaction.guild is None or reminder["guild_id"] != interaction.guild.id:
            raise UserError("You may only cancel reminders from this server.")
        if reminder["sent"]:
            raise UserError("That reminder has already been sent and cannot be cancelled.")

        is_owner = self.bot.is_owner_id(interaction.user.id)
        is_creator = reminder["user_id"] == interaction.user.id
        has_admin = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator

        if not (is_creator or is_owner or has_admin):
            raise UserError("You can only cancel your own reminders unless you are an admin or owner.")

        await self.bot.db.delete_reminder(id)
        await interaction.response.send_message(f"Cancelled reminder #{id}.", ephemeral=True)


async def setup(bot: ScribeBot) -> None:
    bot.tree.add_command(RemindersGroup(bot))
