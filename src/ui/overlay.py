"""Overlay UI for in-game assistant interactions."""

from __future__ import annotations

from typing import Any


class Overlay:
    """Minimal overlay application used to render assistant UI elements."""

    def show(self, text: str | None = None, **kwargs: Any) -> None:
        """Display the overlay with optional content."""
        return None

    def hide(self) -> None:
        """Hide the overlay from view."""
        return None
