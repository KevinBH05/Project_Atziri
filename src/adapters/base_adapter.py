"""Clases base abstractas para los adaptadores del juego."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseGameAdapter(ABC):
    """Interfaz abstracta implementada por todos los adaptadores del juego.

    Cada adaptador concreto es responsable de traducir los datos brutos del
    juego a la representación interna de la aplicación.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establece una conexión con el juego o backend objetivo."""

    @abstractmethod
    def fetch_data(self) -> Dict[str, Any]:
        """Obtiene el estado o los metadatos relevantes del juego."""

    @abstractmethod
    def parse(self, raw_data: Any) -> Dict[str, Any]:
        """Transforma los datos brutos en objetos normalizados del dominio."""
