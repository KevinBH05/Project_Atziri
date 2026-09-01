"""Context-building utilities for LLM prompts and system instructions."""

from __future__ import annotations

from typing import Any, Dict, List


class LLMContext:
    """Build contextual prompt payloads for model inference."""

    def build(self, user_message: str, memory: List[str] | None = None, **kwargs: Any) -> Dict[str, Any]:
        """Construct a contextual payload for the model request."""
        return {
            "user_message": user_message,
            "memory": memory or [],
            "extra": kwargs,
        }
