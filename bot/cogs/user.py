from __future__ import annotations

import re
from typing import Optional

import discord
from discord import app_commands

from bot import ScribeBot
from bot.db import crud
from bot.db.models import GlossaryEntry
from bot.exceptions import ConfigError
from bot.services.formatting import stitch_translation
from bot.services.glossary import apply_glossary, compile_glossary
from bot.services.langid import detect_language, validate_language_code
from bot.services.spans import extract_spans, reinsert_spans
from bot.services.translator.base import TranslationPayload

MESSAGE_LINK_RE = re.compile(
    r"https://discord.com/channels/(?P<guild>\d+)/(?P<channel>\d+)/(?P<message>\d+)"
)


class TranslateToggleView(discord.ui.View):
    def __init__(self, *, original: str, translated: str, language: str) -> None:
        super().__init__(timeout=None)
        self._original = original
        self._translated = translated
        self._language = language
        self._showing_original = False

    @discord.ui.button(label="Show original", custom_id="scribe:show-original", style=discord.ButtonStyle.secondary)
    async def show_original(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        if self._showing_original:
            await interaction.response.defer()
            return
        await interaction.response.edit_message(content=self._original)
        self._showing_original = True

    @discord.ui.button(label="Show translation", custom_id="scribe:show-translation", style=discord.ButtonStyle.primary)
    async def show_translation(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:  # type: ignore[override]
        if not self._showing_original:
            await interaction.response.defer()
            return
        await interaction.response.edit_message(content=self._translated)
        self._showing_original = False


scribe_group = app_commands.Group(name="scribe", description="Scribe translation utilities")


@scribe_group.command(name="set-language", description="Set your preferred translation language")
@app_commands.describe(lang="ISO language code (e.g. en, es, fr)")
async def set_language(interaction: discord.Interaction[ScribeBot], lang: str) -> None:
    lang = lang.lower()
    if not validate_language_code(lang):
        await interaction.response.send_message(
            "Unsupported language code. Supported examples: en, es, fr, de, ja, ko, zh, ru, pt",
            ephemeral=True,
        )
        return
    async with interaction.client.sessionmaker() as session:
        await crud.set_user_language(session, interaction.user.id, lang)
    await interaction.response.send_message(f"Saved your preferred language as `{lang}`.", ephemeral=True)


async def _resolve_message(
    interaction: discord.Interaction[ScribeBot], message_link: str
) -> Optional[discord.Message]:
    match = MESSAGE_LINK_RE.match(message_link)
    if not match:
        await interaction.response.send_message("Message link must be a Discord message URL.", ephemeral=True)
        return None
    guild_id = int(match.group("guild"))
    channel_id = int(match.group("channel"))
    message_id = int(match.group("message"))
    if interaction.guild_id != guild_id:
        await interaction.response.send_message("Message must belong to this guild.", ephemeral=True)
        return None
    channel = interaction.client.get_channel(channel_id)
    if channel is None:
        channel = await interaction.client.fetch_channel(channel_id)
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Unsupported channel type.", ephemeral=True)
        return None
    try:
        return await channel.fetch_message(message_id)
    except discord.HTTPException:
        await interaction.response.send_message("Could not fetch that message.", ephemeral=True)
        return None


@scribe_group.command(name="translate", description="Translate a message")
@app_commands.describe(message="Message link to translate", to="Target language (defaults to your preference)")
async def translate_command(
    interaction: discord.Interaction[ScribeBot],
    message: Optional[str] = None,
    to: Optional[str] = None,
) -> None:
    await interaction.response.defer(ephemeral=True)
    target_lang = to.lower() if to else None
    async with interaction.client.sessionmaker() as session:
        user_settings = await crud.get_or_create_user(session, interaction.user.id)
        glossary_entries = await crud.list_glossary_entries(session, interaction.guild_id or 0)
    if not target_lang:
        target_lang = user_settings.preferred_lang or interaction.client.settings.default_guild_lang
    if not validate_language_code(target_lang):
        raise ConfigError("Target language is not supported")
    target_message: Optional[discord.Message] = None
    if message:
        target_message = await _resolve_message(interaction, message)
        if target_message is None:
            return
    else:
        await interaction.followup.send("Please provide a message link to translate.", ephemeral=True)
        return
    spans_text, spans = extract_spans(target_message.content)
    detection = detect_language(spans_text)
    payload = TranslationPayload(
        text=spans_text,
        source_lang=detection.language,
        target_lang=target_lang,
        glossary=[(entry.term, entry.translation) for entry in glossary_entries] or None,
    )
    outcome = await interaction.client.translators.translate(payload)
    translated = outcome.text
    if glossary_entries:
        compiled = compile_glossary(glossary_entries)
        translated = apply_glossary(translated, compiled)
    translated = reinsert_spans(translated, spans, target_message.content)
    link = target_message.jump_url
    final_content = stitch_translation(link, translated)
    view = TranslateToggleView(original=target_message.content, translated=final_content, language=target_lang)
    await interaction.followup.send(final_content, ephemeral=True, view=view)


@scribe_group.command(name="opt-in-dm", description="Enable DM translation mirror")
async def opt_in_dm(interaction: discord.Interaction[ScribeBot]) -> None:
    async with interaction.client.sessionmaker() as session:
        await crud.set_user_dm_mirror(session, interaction.user.id, True)
    await interaction.response.send_message("DM mirror enabled. We'll translate channels you can see.", ephemeral=True)


@scribe_group.command(name="opt-out-dm", description="Disable DM translation mirror")
async def opt_out_dm(interaction: discord.Interaction[ScribeBot]) -> None:
    async with interaction.client.sessionmaker() as session:
        await crud.set_user_dm_mirror(session, interaction.user.id, False)
    await interaction.response.send_message("DM mirror disabled.", ephemeral=True)


@scribe_group.command(name="forgetme", description="Erase stored preferences about you")
async def forget_me(interaction: discord.Interaction[ScribeBot]) -> None:
    async with interaction.client.sessionmaker() as session:
        await crud.forget_user(session, interaction.user.id)
    await interaction.response.send_message("All stored data about you has been deleted.", ephemeral=True)


async def setup(bot: ScribeBot) -> None:
    bot.tree.add_command(scribe_group)
