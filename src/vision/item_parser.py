"""Parsing logic for item descriptions extracted from screenshots."""

from __future__ import annotations

from typing import Any, Dict


class ItemParser:
    """Convert OCR text into structured item metadata."""

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse raw OCR text into item data structure."""
        return {"raw_text": text}
