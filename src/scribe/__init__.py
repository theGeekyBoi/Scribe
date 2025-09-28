from __future__ import annotations

from discord import app_commands

__all__ = ["__version__", "UserError"]

__version__ = "0.1.0"


class UserError(app_commands.AppCommandError):
    """Exception raised for user-facing command errors."""
