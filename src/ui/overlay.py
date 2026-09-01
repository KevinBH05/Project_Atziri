"""Interfaz overlay para interacciones del asistente dentro del juego."""

from __future__ import annotations

from typing import Any


class Overlay:
    """Aplicación overlay mínima para renderizar elementos de la interfaz del asistente."""

    def show(self, text: str | None = None, **kwargs: Any) -> None:
        """Muestra el overlay con contenido opcional."""
        return None

    def hide(self) -> None:
        """Oculta el overlay de la vista."""
        return None
