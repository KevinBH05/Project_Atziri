"""Clases base abstractas para ingestors RAG."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class BaseIngestor(ABC):
    """Contrato abstracto para pipelines de ingestión.

    Los ingestors concretos leen contenido desde una fuente y devuelven
    documentos normalizados para indexarlos en un vector store o base de
    conocimiento.
    """

    @abstractmethod
    def ingest(self, source: Any) -> Iterable[Any]:
        """Ingesta contenido desde una fuente y devuelve documentos normalizados."""
