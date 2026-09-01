"""LLM client abstraction for model interactions."""

from __future__ import annotations

from typing import Any, Dict, List


class LLMClient:
    """Minimal abstraction for sending prompts to an LLM provider."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """Initialize the client with a target model."""
        self.model = model

    def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> str:
        """Generate a model response from a prompt and optional context."""
        return ""

    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Send a chat-style prompt to the model provider."""
        return ""
