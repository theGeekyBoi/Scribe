from __future__ import annotations

from config import ScribeSettings


def test_settings_load_from_env(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DISCORD_TOKEN=test-token",
                "DISCORD_CLIENT_ID=123",
                "DISCORD_GUILD_TEST_ID=456",
                "TRANSLATOR_PROVIDER=openai",
            ]
        ),
        encoding="utf-8",
    )

    settings = ScribeSettings(_env_file=env_file)
    assert settings.TRANSLATOR_PROVIDER == "openai"
