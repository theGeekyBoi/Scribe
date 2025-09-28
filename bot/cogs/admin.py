from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from bot import ScribeBot
from bot.db import crud
from bot.db.models import GlossaryEntry
from bot.services.langid import validate_language_code

from .user import scribe_group


def guild_admin_check(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.manage_guild:  # type: ignore[union-attr]
        return True
    raise app_commands.CheckFailure("Manage Guild permission required.")


admin_group = app_commands.Group(name="admin", description="Administrative commands")
channel_group = app_commands.Group(name="channel", description="Channel configuration")
admin_group.add_command(channel_group)


def _render_glossary(entries: list[GlossaryEntry]) -> str:
    if not entries:
        return "(empty)"
    return "\n".join(
        f"• `{entry.term}` → `{entry.translation}`" + (f" _(ctx: {entry.context})_" if entry.context else "")
        for entry in entries
    )


@admin_group.command(name="set-guild-default", description="Set the guild default language")
@app_commands.describe(lang="ISO language code (en, es, fr, ...)")
@app_commands.check(guild_admin_check)
async def set_guild_default(interaction: discord.Interaction[ScribeBot], lang: str) -> None:
    lang = lang.lower()
    if not validate_language_code(lang):
        await interaction.response.send_message("Unsupported language code", ephemeral=True)
        return
    async with interaction.client.sessionmaker() as session:
        await crud.update_guild_settings(session, interaction.guild_id, default_lang=lang)
    await interaction.response.send_message(f"Guild default language set to `{lang}`.", ephemeral=True)


@channel_group.command(name="enable", description="Enable Scribe in this channel")
@app_commands.check(guild_admin_check)
async def channel_enable(interaction: discord.Interaction[ScribeBot]) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only text channels are supported.", ephemeral=True)
        return
    async with interaction.client.sessionmaker() as session:
        await crud.upsert_channel_override(session, guild_id=interaction.guild_id, channel_id=channel.id, enabled=True)
    await interaction.response.send_message("Channel enabled for Scribe translations.", ephemeral=True)


@channel_group.command(name="disable", description="Disable Scribe in this channel")
@app_commands.check(guild_admin_check)
async def channel_disable(interaction: discord.Interaction[ScribeBot]) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only text channels are supported.", ephemeral=True)
        return
    async with interaction.client.sessionmaker() as session:
        await crud.upsert_channel_override(session, guild_id=interaction.guild_id, channel_id=channel.id, enabled=False)
    await interaction.response.send_message("Channel disabled for Scribe translations.", ephemeral=True)


@channel_group.command(name="mode", description="Set translation mode for this channel")
@app_commands.describe(mode="on_demand, threaded, dm_mirror, inline_auto")
@app_commands.check(guild_admin_check)
async def channel_mode(interaction: discord.Interaction[ScribeBot], mode: str) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only text channels are supported.", ephemeral=True)
        return
    async with interaction.client.sessionmaker() as session:
        await crud.upsert_channel_override(session, guild_id=interaction.guild_id, channel_id=channel.id, mode=mode)
    await interaction.response.send_message(f"Channel mode set to `{mode}`.", ephemeral=True)


@channel_group.command(name="target-langs", description="Manage inline target languages")
@app_commands.describe(action="add/remove/list", lang="Language code when adding/removing")
@app_commands.choices(action=[
    app_commands.Choice(name="Add", value="add"),
    app_commands.Choice(name="Remove", value="remove"),
    app_commands.Choice(name="List", value="list"),
])
@app_commands.check(guild_admin_check)
async def channel_target_langs(
    interaction: discord.Interaction[ScribeBot],
    action: app_commands.Choice[str],
    lang: Optional[str] = None,
) -> None:
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Only text channels are supported.", ephemeral=True)
        return
    async with interaction.client.sessionmaker() as session:
        langs = await crud.get_channel_target_langs(session, channel.id)
        if action.value == "list":
            await interaction.response.send_message(
                "Configured target languages: " + (", ".join(langs) if langs else "(none)"),
                ephemeral=True,
            )
            return
        if not lang:
            await interaction.response.send_message("Provide a language code.", ephemeral=True)
            return
        lang = lang.lower()
        if not validate_language_code(lang):
            await interaction.response.send_message("Unsupported language code", ephemeral=True)
            return
        if action.value == "add":
            if lang not in langs:
                langs.append(lang)
        elif action.value == "remove":
            langs = [l for l in langs if l != lang]
        await crud.upsert_channel_override(
            session,
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            target_langs=langs,
        )
    await interaction.response.send_message(
        "Configured target languages: " + (", ".join(langs) if langs else "(none)"),
        ephemeral=True,
    )


@admin_group.command(name="provider", description="Set translation provider preference")
@app_commands.describe(provider="google, deepl, openai")
@app_commands.check(guild_admin_check)
async def provider_set(interaction: discord.Interaction[ScribeBot], provider: str) -> None:
    provider = provider.lower()
    async with interaction.client.sessionmaker() as session:
        await crud.update_guild_settings(session, interaction.guild_id, provider=provider)
    await interaction.response.send_message(f"Preferred provider set to `{provider}`.", ephemeral=True)


@admin_group.command(name="glossary-add", description="Add a glossary entry")
@app_commands.describe(term="Source term", translation="Desired translation", context="Optional context", priority="Lower values run first")
@app_commands.check(guild_admin_check)
async def glossary_add(
    interaction: discord.Interaction[ScribeBot],
    term: str,
    translation: str,
    context: Optional[str] = None,
    priority: Optional[int] = 100,
) -> None:
    async with interaction.client.sessionmaker() as session:
        entry = await crud.upsert_glossary_entry(
            session,
            interaction.guild_id,
            term.strip(),
            translation.strip(),
            context=context,
            priority=priority or 100,
        )
        entries = await crud.list_glossary_entries(session, interaction.guild_id)
    await interaction.response.send_message(
        f"Saved glossary entry `{entry.term}`.\n{_render_glossary(list(entries))}",
        ephemeral=True,
    )


@admin_group.command(name="glossary-remove", description="Remove a glossary entry")
@app_commands.describe(term="Glossary term")
@app_commands.check(guild_admin_check)
async def glossary_remove(interaction: discord.Interaction[ScribeBot], term: str) -> None:
    async with interaction.client.sessionmaker() as session:
        removed = await crud.remove_glossary_entry(session, interaction.guild_id, term)
    if removed:
        await interaction.response.send_message(f"Removed `{term}` from the glossary.", ephemeral=True)
    else:
        await interaction.response.send_message(f"No glossary entry found for `{term}`.", ephemeral=True)


@admin_group.command(name="glossary-list", description="List glossary entries")
@app_commands.check(guild_admin_check)
async def glossary_list(interaction: discord.Interaction[ScribeBot]) -> None:
    async with interaction.client.sessionmaker() as session:
        entries = await crud.list_glossary_entries(session, interaction.guild_id)
    await interaction.response.send_message(_render_glossary(list(entries)), ephemeral=True)


@admin_group.command(name="stats", description="Show guild usage stats")
@app_commands.check(guild_admin_check)
async def stats(interaction: discord.Interaction[ScribeBot]) -> None:
    async with interaction.client.sessionmaker() as session:
        usage = await crud.get_usage_for_period(session, interaction.guild_id, days=7)
    if not usage:
        await interaction.response.send_message("No usage recorded yet.", ephemeral=True)
        return
    lines = ["Last 7 days usage:"]
    for record in usage:
        lines.append(
            f"• {record.day}: {record.char_count} chars, ${record.cost_estimate_usd:.4f}"
        )
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@admin_group.command(name="health", description="Bot status overview")
@app_commands.check(guild_admin_check)
async def health(interaction: discord.Interaction[ScribeBot]) -> None:
    uptime = discord.utils.utcnow() - interaction.client.start_time
    await interaction.response.send_message(
        f"✅ Scribe online. Uptime: {uptime}. Translators configured: {len(interaction.client.translators._ordered)}",
        ephemeral=True,
    )


async def setup(bot: ScribeBot) -> None:
    scribe_group.add_command(admin_group)
