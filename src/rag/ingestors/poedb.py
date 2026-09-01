"""PoEDB-specific ingestor placeholder."""

from __future__ import annotations

from typing import Any, Iterable

from src.rag.base_ingestor import BaseIngestor


class PoEDBIngestor(BaseIngestor):
    """Load and normalize data from PoEDB-like sources."""

    def ingest(self, source: Any) -> Iterable[Any]:
        """Yield documents extracted from PoEDB source content."""
        yield from []
