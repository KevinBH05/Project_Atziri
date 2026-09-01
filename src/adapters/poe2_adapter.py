"""Adaptador para la integración de Path of Exile 2."""

from __future__ import annotations

from typing import Any, Dict

from src.adapters.base_adapter import BaseGameAdapter


class PoE2Adapter(BaseGameAdapter):
    """Adaptador concreto para Path of Exile 2.

    Esta clase define la interfaz esperada para recibir, normalizar y exponer
    la información relacionada con el juego al resto de la aplicación.
    """

    def connect(self) -> bool:
        """Conecta con el juego o la fuente de datos."""
        return True

    def fetch_data(self) -> Dict[str, Any]:
        """Devuelve datos del estado del juego ya normalizados."""
        return {}

    def parse(self, raw_data: Any) -> Dict[str, Any]:
        """Parsea cargas útiles crudas del juego en un diccionario normalizado."""
        return {"raw": raw_data}
