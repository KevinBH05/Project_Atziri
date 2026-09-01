"""Orquestación de ingesta de alto nivel para documentos de conocimiento."""

from __future__ import annotations

from typing import Any, Iterable


def ingest_documents(sources: Iterable[Any]) -> list[Any]:
    """Dispara la ingesta para un conjunto de fuentes de documentos.

    Args:
        sources: Iterable con documentos o fuentes de datos externas.

    Returns:
        Una lista vacía como marcador de posición hasta que la pipeline real esté lista.
    """
    return []
