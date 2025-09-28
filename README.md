# Scribe

Scribe is a lightweight Discord slash-command bot designed for frictionless note taking, bookmarking, and reminders. It keeps configuration simple, runs fully asynchronously, and produces structured logs for reliable operations.

## Quickstart

1. Ensure Python 3.11 or newer is installed.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in the secrets.
5. Run the bot:
   ```bash
   python -m scribe.bot
   ```

Scribe reads configuration from environment variables (see below). The bot logs startup, command sync scope, and reminder dispatch events.

## Configuration

All configuration happens through environment variables, typically via an `.env` file:

- `DISCORD_TOKEN` (**required**) — Bot token from the Discord Developer Portal.
- `CLIENT_ID` — Application (client) ID for invite URLs.
- `GUILD_ID` — Guild ID for fast, guild-scoped command sync during development. Leave empty to sync globally.
- `LOG_LEVEL` — Logging level (`INFO`, `DEBUG`, etc.), default is `INFO`.
- `DB_PATH` — SQLite database path, default `./scribe.sqlite3`.
- `OWNER_IDS` — Comma-separated list of Discord user IDs with owner privileges (admin cog access).

Example invite URL (replace `CLIENT_ID`):
```
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot%20applications.commands&permissions=3072
```

Required bot permissions: Send Messages, Read Message History, Use Application Commands. Message content intent is **not** enabled by default; if you need transcript-style features later, enable it in the Discord Developer Portal and set `intents.message_content = True` in `scribe.bot`.

## Running

The entry point is `python -m scribe.bot`. On startup the bot:

1. Loads configuration.
2. Configures logging.
3. Runs database migrations.
4. Registers slash commands (guild-scoped if `GUILD_ID` is set, otherwise global).
5. Starts a background reminder dispatcher loop.

Use `/admin sync` to resync commands after code changes. Guild sync propagates instantly; global sync may take up to an hour to appear for all users.

## Commands

Utility:
- `/ping` — Latency check (ephemeral).
- `/about` — Bot metadata, uptime, versions (ephemeral).
- `/help` — Command overview embed (ephemeral).

Notes:
- `/note add content:<text>` — Store a note tied to your account and channel (ephemeral confirmation).
- `/note list [user] [limit]` — List recent notes for yourself or another user.
- `/note delete id:<int>` — Remove a note you own; admins with Manage Messages or owners may delete any.

Bookmarks:
- `/bookmark add message_link:<link> [note:<text>]` — Save a Discord message jump link with an optional label (ephemeral confirmation).
- `/bookmark list [limit]` — Show your saved bookmarks.
- `/bookmark remove id:<int>` — Delete one of your bookmarks.

Reminders:
- `/reminder create when:<time> message:<text>` — Schedule a reminder (minimum 10 seconds in the future).
- `/reminder list [user] [limit]` — View pending reminders (sent=0) sorted by due time.
- `/reminder cancel id:<int>` — Cancel a pending reminder you created; admins/owners can cancel any.

Admin:
- `/admin sync [scope]` — Resync commands (`guild` or `global`). Restricted to owners or members with Administrator permissions.

## Reminder Time Formats

Relative:
- `in 10m`, `in 2h`, `in 3d`
- `in 1h30m` (combinations of days, hours, minutes)

Absolute:
- `2024-05-01 14:30` (interpreted in the server’s local timezone, stored in UTC)
- `2024-05-01T14:30Z`
- `2024-05-01T14:30:00-0400` (offset with or without colon)

Ambiguous or past times are rejected with a helpful error. Stored timestamps use ISO 8601 in UTC.

## Testing

Install `pytest` (e.g., `pip install pytest`) and run:

```bash
python -m pytest
```

Unit tests cover the reminder time parser to ensure the accepted formats behave as expected.

## Troubleshooting

- **Commands missing**: Ensure the bot has `applications.commands` scope, then run `/admin sync`. Remember global commands can take up to an hour to propagate.
- **Missing permissions**: Verify the bot possesses Send Messages and Read Message History in the target channel.
- **Intents errors**: The bot uses default intents. If you later enable message content features, update the Discord Developer Portal and the code accordingly.
- **Database path issues**: Confirm the process can read/write the configured `DB_PATH`.

## Extending Scribe

Cogs live under `src/scribe/cogs`. To add a cog:

1. Create a new `Group`-based cog module.
2. Provide an async `setup(bot)` function that registers the group with `bot.tree`.
3. Import and call the setup function from `scribe.bot.ScribeBot.setup_hook`.

Slash commands defined with `discord.app_commands` slot neatly into the existing structure, and the database helper in `scribe.db` provides reusable CRUD functions for SQLite interactions.
