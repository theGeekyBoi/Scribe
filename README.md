# Scribe — Real-Time Translation Bot for Discord

> *“A real-time translation bot that makes multilingual servers seamless. Users choose their preferred language, and Scribe translates messages while preserving mentions, formatting, and context. Supports per-channel settings, opt-ins, and multiple translation providers.”*

Scribe empowers diverse Discord communities by translating conversations in real time while meticulously preserving Markdown formatting, mentions, code blocks, spoilers, emojis, and links. Members set a preferred language and Scribe delivers translations through on-demand interactions, threaded discussion hubs, direct-message mirrors, and tightly controlled inline auto-posts. By removing language barriers without erasing tone or nuance, Scribe helps moderators and community builders create inclusive, multicultural spaces where everyone can participate.

---

## ✨ Features

- **Inclusive multilingual chat** – members choose a preferred language (ISO-639-1) and receive translations that respect cultural nuance and context.
- **Multiple delivery modes**
  - **On-demand**: Slash commands or buttons provide quick, ephemeral translations.
  - **Threaded hubs**: Per-channel translation threads (e.g., `#🌐-translations`) keep cross-language conversations organized.
  - **DM mirror**: Opt-in flow streams translated messages privately to the user.
  - **Inline auto mode**: Webhook-powered inline translations (max N target languages) mimic the original author without triggering pings.
- **Format-preserving pipeline** – code fences, inline code, spoilers, block quotes, mentions, links, timestamps, and emojis remain intact.
- **Edit & delete sync** – translated posts update or disappear alongside the source message.
- **Pluggable translation providers** – Google Cloud Translate v3, DeepL, and OpenAI (gpt-4o-mini). Seamlessly configure primaries and fallbacks via environment variables.
- **Guild glossaries** – map domain-specific terminology to precise translations.
- **Smart language detection** – span-aware detection with heuristics prevents redundant translations when text already matches the target language.
- **Usage observability** – track character counts, estimated provider cost, and latency percentiles per guild.
- **Resilience & privacy** – async token buckets, deduplication, exponential backoff, configurable content retention (default 72h), and `/scribe forgetme` for user data erasure.
- **Testing & tooling** – pytest coverage for span parsing, glossary logic, and language detection; Makefile workflows; Dockerized dev environment.

---

## 📸 Screenshots & Demos *(placeholders)*

| Scenario | Description | Media |
| --- | --- | --- |
| On-demand translation | Ephemeral translation with “Show original” and “Improve translation” buttons. | _GIF placeholder_ |
| Threaded hub | Auto-generated translation thread showing bilingual conversation. | _PNG placeholder_ |
| Inline auto mode | French webhook translation mirroring original author. | _GIF placeholder_ |
| DM mirror | Private feed translating a busy announcements channel. | _GIF placeholder_ |

---

## 🚀 Quickstart

> ℹ️ Scribe targets **Python 3.11+** and uses **discord.py 2.x** with slash commands. Install requirements and run via virtualenv or Docker.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -e .[dev]
cp .env.example .env
# Fill .env with Discord + provider credentials
python main.py
```

### Required Discord Setup

1. **Create a Discord application** in the [Developer Portal](https://discord.com/developers/applications).
2. Enable **Privileged Gateway Intents**:
   - Server Members
   - Message Content (needed for translation context)
3. Under **OAuth2 → URL Generator**, pick scopes `bot` and `applications.commands`.
4. Permissions:
   - Send Messages
   - Manage Webhooks
   - Read Message History
   - Manage Threads (for threaded mode)
5. Invite using the template (replace `<CLIENT_ID>`):
   ```
   https://discord.com/oauth2/authorize?client_id=<CLIENT_ID>&scope=bot%20applications.commands&permissions=268823688
   ```

### Environment Variables

See [`.env.example`](.env.example) for the full list. Core settings:

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Bot token from the Developer Portal. |
| `DISCORD_CLIENT_ID` | Application client ID (used for command sync scripts). |
| `TRANSLATOR_PROVIDER` | Primary provider (`openai`, `deepl`, or `google`). |
| `TRANSLATOR_FALLBACKS` | Comma-separated fallback providers. |
| `RETENTION_HOURS` | Translation cache retention (default 72h). |
| `DEFAULT_GUILD_LANG` | Default fallback language for guilds. |

Provider credentials:
- **OpenAI**: `OPENAI_API_KEY`
- **DeepL**: `DEEPL_API_KEY`
- **Google**: `GOOGLE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` (JSON file path)

---

## 🛠 Project Layout

```
scribe/
├── bot/
│   ├── cogs/
│   │   ├── admin.py
│   │   ├── listeners.py
│   │   └── user.py
│   ├── db/
│   │   ├── crud.py
│   │   ├── models.py
│   │   └── session.py
│   ├── services/
│   │   ├── formatting.py
│   │   ├── glossary.py
│   │   ├── langid.py
│   │   ├── metrics.py
│   │   ├── ratelimit.py
│   │   ├── spans.py
│   │   ├── translator/
│   │   │   ├── base.py
│   │   │   ├── deepl.py
│   │   │   ├── google.py
│   │   │   └── openai.py
│   │   └── webhooks.py
│   ├── exceptions.py
│   └── __init__.py
├── config.py
├── main.py
├── worker.py
├── scripts/
│   └── sync_commands.py
├── tests/
│   ├── test_glossary.py
│   ├── test_langid.py
│   └── test_spans.py
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── README.md
├── pyproject.toml
└── .env.example
```

---

## ⚙️ Modes & Workflows

### Slash Commands (grouped under `/scribe`)

| Command | Description |
| --- | --- |
| `/scribe set-language <lang>` | Set the invoking user’s preferred ISO language code. |
| `/scribe translate [message] [to]` | Translate a referenced message (reply or link). |
| `/scribe opt-in-dm` / `/scribe opt-out-dm` | Start or stop the DM translation mirror. |
| `/scribe forgetme` | Delete the user’s preferences and DM state. |

Admin-only (Manage Guild):
- `/scribe set-guild-default <lang>`
- `/scribe channel enable|disable`
- `/scribe channel mode <on_demand|threaded|dm_mirror|inline_auto>`
- `/scribe channel target-langs add|remove|list`
- `/scribe provider set <google|deepl|openai>`
- `/scribe costcap set <usd>`
- `/scribe glossary add|remove|list`
- `/scribe stats`
- `/scribe health`

### Translation Modes

| Mode | Description | Best for |
| --- | --- | --- |
| On-demand | Ephemeral translations via slash commands or persistent buttons. | Casual, low-volume chats |
| Threaded | Dedicated translation thread per channel; edits & deletes stay in sync. | Busy cross-language channels |
| DM Mirror | Opt-in personal feed in the user’s preferred language. | High-signal announcements |
| Inline Auto | Webhook posts translation inline (limited target languages) without triggering pings. | Public, high-visibility channels |

---

## 🌐 Providers

Scribe wraps each provider behind a `Translator` interface with token-bucket rate limiting, de-duplication, and fallback retries:

- **OpenAI** (default) — `gpt-4o-mini` (configurable).
- **DeepL** — uses glossaries when available, otherwise applies Scribe’s post-processing glossary step.
- **Google Cloud Translate** — uses Adaptive Translation if configured.

Configure priorities via `TRANSLATOR_PROVIDER` and `TRANSLATOR_FALLBACKS` (comma-separated list). Example:

```
TRANSLATOR_PROVIDER=openai
TRANSLATOR_FALLBACKS=deepl,google
```

---

## 📚 Glossary

Guild administrators can standardize terminology:

```bash
/scribe glossary add "API" "Interfaz de programación" "Use in documentation"
/scribe glossary list
/scribe glossary remove "API"
```

Glossary entries run after provider output (or inline if the provider supports glossaries) using word-boundary-aware replacements. Priority ordering allows nuanced overrides.

---

## 🔒 Privacy & Retention

- Only minimal metadata is stored: user language preferences, channel/guild settings, translation message mappings, and usage counters.
- Message bodies are cached for edit/delete sync and purged after `RETENTION_HOURS` (default 72h).
- `/scribe forgetme` triggers immediate removal of a user’s stored data.
- Logs redact API keys and avoid recording full message content at INFO level.

---

## 🧪 Testing & Tooling

| Command | Description |
| --- | --- |
| `make lint` | Run black + isort. |
| `make typecheck` | Run mypy. |
| `make test` | Run pytest (span parser, glossary, langid). |
| `make run` | Launch the bot with the current environment. |
| `make sync-commands` | Sync slash commands using `scripts/sync_commands.py`. |

Tests ship with lightweight fakes for translation providers and emphasize span parsing accuracy (>85% coverage), glossary application, and language detection heuristics.

---

## 🐳 Docker

```bash
docker compose up --build
```

The provided `docker-compose.yml` launches the bot container and includes commented sections for optional Postgres/Redis backends when scaling beyond SQLite.

---

## 🤝 Encouraging Diversity & Inclusion

Scribe’s mission is to help multilingual communities thrive. By blending precise translations with context-aware formatting, moderators can confidently welcome speakers of every language, and members keep their authentic voice without sacrificing clarity. Encourage onboarding from underrepresented regions, empower volunteer translators, and reduce the friction that often sidelines non-native speakers.

---

## 🧭 Troubleshooting

- **Slash commands missing?** Run `make sync-commands` or `/scribe admin sync`. Global propagation may take up to an hour.
- **Permissions errors?** Ensure the bot can Manage Webhooks, Manage Threads, and read message history.
- **Provider errors?** Check API quotas, cost caps, and rate limits. Logs surface backoff and retry attempts.
- **DM mirror silent?** Confirm the user shares a guild with the bot and has DMs open.

---

## 🗺 Roadmap

- OCR image translation (on-demand)
- Voice channel interpreter mode
- Postgres + Redis scaling profile
- Advanced glossary editor UI

Community contributions are welcome—fork the repo, create a feature branch, and open a pull request describing how your change advances inclusive, diverse communication on Discord.

