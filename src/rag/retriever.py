"""Capa de recuperación para búsquedas de documentos y contexto."""

from __future__ import annotations

from typing import Any, List


class Retriever:
    """Recupera contexto relevante desde un vector store o base de conocimiento."""

    def search(self, query: str, top_k: int = 5) -> List[Any]:
        """Busca documentos relevantes para una consulta del usuario."""
        return []
