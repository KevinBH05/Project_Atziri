"""Abstracción del cliente LLM para interactuar con modelos."""

from __future__ import annotations

from typing import Any, Dict, List


class LLMClient:
    """Abstracción mínima para enviar prompts a un proveedor de LLM."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """Inicializa el cliente con el modelo objetivo."""
        self.model = model

    def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> str:
        """Genera una respuesta del modelo a partir de un prompt y contexto opcional."""
        return ""

    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Envía un prompt tipo chat al proveedor del modelo."""
        return ""
