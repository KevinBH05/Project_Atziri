"""Adapter for Path of Exile 2 integration."""

from __future__ import annotations

from typing import Any, Dict

from src.adapters.base_adapter import BaseGameAdapter


class PoE2Adapter(BaseGameAdapter):
    """Concrete adapter for Path of Exile 2.

    This class contains the expected interface for receiving, normalizing, and
    exposing game-related information for the rest of the app.
    """

    def connect(self) -> bool:
        """Connect to the game or data source."""
        return True

    def fetch_data(self) -> Dict[str, Any]:
        """Return normalized game-state data."""
        return {}

    def parse(self, raw_data: Any) -> Dict[str, Any]:
        """Parse raw game payloads into a normalized dictionary."""
        return {"raw": raw_data}
