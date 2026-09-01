"""Abstract base classes for game adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseGameAdapter(ABC):
    """Abstract interface implemented by all game adapters.

    Each concrete adapter is responsible for translating raw game data into the
    application's internal representation.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish a connection to the target game or backend."""

    @abstractmethod
    def fetch_data(self) -> Dict[str, Any]:
        """Retrieve relevant game state or metadata."""

    @abstractmethod
    def parse(self, raw_data: Any) -> Dict[str, Any]:
        """Transform raw game data into normalized domain objects."""
