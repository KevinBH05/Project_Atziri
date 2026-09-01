"""Utilities for parsing Path of Building data."""

from __future__ import annotations

import base64
import zlib
from typing import Any


class PoBParser:
    """Parse Path of Building payloads into structured data.

    This parser currently provides a minimal interface for decoding the common
    base64 + zlib payload format used by PoB exports.
    """

    @staticmethod
    def decode_base64_zlib(encoded_data: str) -> str:
        """Decode a base64-encoded zlib-compressed PoB payload.

        Args:
            encoded_data: The compressed string supplied by Path of Building.

        Returns:
            Decoded plain text payload.
        """
        compressed = base64.b64decode(encoded_data)
        return zlib.decompress(compressed).decode("utf-8")

    def parse(self, payload: str) -> Any:
        """Parse a PoB payload and return a structured representation."""
        return self.decode_base64_zlib(payload)
