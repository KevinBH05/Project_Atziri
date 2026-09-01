"""Definiciones de componentes de interfaz usados por el overlay y paneles."""

from __future__ import annotations

from typing import Any, Dict


class InfoPanel:
    """Muestra información de alto nivel para el usuario en un panel del overlay."""

    def render(self, data: Dict[str, Any]) -> str:
        """Genera una representación serializable de los datos recibidos."""
        return str(data)


class ActionButton:
    """Elemento tipo botón para acciones del asistente."""

    def click(self, **kwargs: Any) -> None:
        """Gestiona los clics del componente."""
        return None
