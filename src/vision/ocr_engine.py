"""OCR integration layer for reading text from screenshots."""

from __future__ import annotations

from typing import Any


class OcrEngine:
    """OCR engine abstraction for extracting text from an image."""

    def extract_text(self, image: Any) -> str:
        """Extract text from a provided image object."""
        return ""
