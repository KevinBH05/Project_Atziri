"""Utilidades para construir contexto de prompts y sistema para LLM."""

from __future__ import annotations

from typing import Any, Dict, List


class LLMContext:
    """Genera payloads contextuales para la inferencia del modelo."""

    def build(self, user_message: str, memory: List[str] | None = None, **kwargs: Any) -> Dict[str, Any]:
        """Construye un payload contextual para la solicitud al modelo."""
        return {
            "user_message": user_message,
            "memory": memory or [],
            "extra": kwargs,
        }
