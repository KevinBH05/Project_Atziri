"""Gestor de estado en memoria (RAM) para el contexto del personaje activo."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from ..integrations.pob_parser import PoBBuild


@dataclass
class ActiveCharacterState:
    """Representa el estado actual del personaje alojado en la memoria RAM."""

    character_name: str = ""
    account_name: str = ""
    build_data: Optional[PoBBuild] = None
    last_synced: Optional[datetime] = None

    def update_from_pob(self, build: PoBBuild, account_name: str = "") -> None:
        """Actualiza el estado actual usando el objeto cargado desde el PoB Parser."""
        self.build_data = build
        self.character_name = build.character_name or ""
        if account_name:
            self.account_name = account_name
        self.last_synced = datetime.now(timezone.utc)

    def clear(self) -> None:
        """Limpia el estado en memoria al desvincular el personaje."""
        self.character_name = ""
        self.account_name = ""
        self.build_data = None
        self.last_synced = None

    def to_llm_context_dict(self) -> Dict[str, Any]:
        """Formatea los datos clave de la build para inyectarlos en el prompt del LLM."""
        if not self.build_data:
            return {"status": "No hay personaje cargado en memoria."}

        b = self.build_data
        stats = b.stats if hasattr(b, "stats") and b.stats else None
        p_tree = b.passive_tree if hasattr(b, "passive_tree") and b.passive_tree else None

        return {
            "character_name": b.character_name,
            "class": getattr(b, "character_class", "Desconocida"),
            "level": getattr(b, "level", 1),
            "main_skill": getattr(b, "main_skill_name", "N/A"),
            "stats": {
                "combined_dps": getattr(stats, "combined_dps", 0.0),
                "hit_dps": getattr(stats, "hit_dps", 0.0),
                "life": getattr(stats, "life", 0),
                "mana": getattr(stats, "mana", 0),
                "spirit": getattr(stats, "spirit", 0),  # Clave para PoE 2
                "armour": getattr(stats, "armour", 0),
                "evasion": getattr(stats, "evasion", 0),
                "energy_shield": getattr(stats, "energy_shield", 0),
                "resistances": {
                    "fire": getattr(stats, "fire_resistance", 0),
                    "cold": getattr(stats, "cold_resistance", 0),
                    "lightning": getattr(stats, "lightning_resistance", 0),
                    "chaos": getattr(stats, "chaos_resistance", 0),
                },
            },
            "active_keystones": getattr(p_tree, "active_keystones", []),
            "active_notables": getattr(p_tree, "active_notables", []),
            "equipped_slots": list(b.equipped_items.keys()) if hasattr(b, "equipped_items") and b.equipped_items else [],
            "last_synced_utc": self.last_synced.isoformat() if self.last_synced else None,
        }


class ContextManager:
    """Singleton/Contenedor global para acceder al estado en tiempo real."""

    _instance: Optional[ContextManager] = None

    def __new__(cls) -> ContextManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.state = ActiveCharacterState()
        return cls._instance


# Instancia accesible globalmente
context_manager = ContextManager()