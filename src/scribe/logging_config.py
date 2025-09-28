from __future__ import annotations

import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": numeric_level,
                }
            },
            "loggers": {
                "discord": {"level": "INFO", "handlers": ["console"], "propagate": False},
                "scribe": {"level": numeric_level, "handlers": ["console"], "propagate": False},
            },
            "root": {"level": numeric_level, "handlers": ["console"]},
        }
    )
