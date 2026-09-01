"""UI component definitions used by the overlay and panels."""

from __future__ import annotations

from typing import Any, Dict


class InfoPanel:
    """Display high-level information for the user in an overlay panel."""

    def render(self, data: Dict[str, Any]) -> str:
        """Render a serializable representation of the given data."""
        return str(data)


class ActionButton:
    """Button-like UI element for assistant actions."""

    def click(self, **kwargs: Any) -> None:
        """Handle click actions for the component."""
        return None
