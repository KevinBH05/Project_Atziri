"""Marcador de posición para un ingestor específico de PoEDB."""

from __future__ import annotations

from typing import Any, Iterable

from src.rag.base_ingestor import BaseIngestor


class PoEDBIngestor(BaseIngestor):
    """Carga y normaliza datos procedentes de fuentes tipo PoEDB."""

    def ingest(self, source: Any) -> Iterable[Any]:
        """Genera documentos extraídos del contenido de una fuente PoEDB."""
        yield from []
