"""Abstract base classes for RAG ingestors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class BaseIngestor(ABC):
    """Abstract contract for ingestion pipelines.

    Concrete ingestors read source content and return normalized documents for
    indexing in a vector store or knowledge base.
    """

    @abstractmethod
    def ingest(self, source: Any) -> Iterable[Any]:
        """Ingest content from a source and yield normalized documents."""
