from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scribe.cogs.reminders import parse_time_spec


@pytest.mark.parametrize(
    ("spec", "expected_delta"),
    [
        ("in 10m", timedelta(minutes=10)),
        ("in 2h", timedelta(hours=2)),
        ("in 1d", timedelta(days=1)),
        ("in 1h30m", timedelta(hours=1, minutes=30)),
        ("in 2d4h15m", timedelta(days=2, hours=4, minutes=15)),
    ],
)
def test_parse_relative(spec: str, expected_delta: timedelta) -> None:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    result = parse_time_spec(spec, now=now)
    assert result == now + expected_delta


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("2024-05-01 14:30", datetime(2024, 5, 1, 14, 30)),
        ("2024-05-01T14:30Z", datetime(2024, 5, 1, 14, 30, tzinfo=UTC)),
        ("2024-05-01T14:30:00+0200", datetime(2024, 5, 1, 12, 30, tzinfo=UTC)),
        ("2024-05-01T14:30:00-04:00", datetime(2024, 5, 1, 18, 30, tzinfo=UTC)),
    ],
)
def test_parse_absolute(spec: str, expected: datetime) -> None:
    result = parse_time_spec(spec)
    assert result.tzinfo is UTC
    assert result == expected.astimezone(UTC)


@pytest.mark.parametrize(
    "spec",
    [
        "",
        "soon",
        "in 0m",
        "in -5m",
        "2024-02-30 10:00",
        "20240101",
    ],
)
def test_parse_invalid(spec: str) -> None:
    with pytest.raises(Exception):
        parse_time_spec(spec)
