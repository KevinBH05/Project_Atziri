"""High-level ingestion orchestration for knowledge documents."""

from __future__ import annotations

from typing import Any, Iterable


def ingest_documents(sources: Iterable[Any]) -> list[Any]:
    """Trigger ingestion for a set of document sources.

    Args:
        sources: Iterable of input documents or external data sources.

    Returns:
        An empty list placeholder until the real ingestion pipeline is ready.
    """
    return []
