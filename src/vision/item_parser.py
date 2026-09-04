"""Lógica de análisis para descripciones de objetos extraídas de capturas.

Este módulo convierte el texto bruto del OCR en dataclasses estructuradas
heredadas de ParsedItem (EquipmentItem, MapItem o GemItem) para separar
claramente las propiedades de equipamiento, mapas/waystones y gemas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ParsedItem:
    """Clase base para cualquier objeto parseado desde el OCR."""
    name: str
    item_class: Optional[str]
    rarity: str
    item_level: Optional[int]
    raw_text: str


@dataclass
class MapItem(ParsedItem):
    """Objeto especializado para Mapas y Waystones."""
    map_tier: Optional[int] = None
    quantity: Optional[int] = None
    rarity_stat: Optional[int] = None
    pack_size: Optional[int] = None
    modifiers: List[str] = field(default_factory=list)


@dataclass
class EquipmentItem(ParsedItem):
    """Objeto especializado para Equipamiento (Armas, Armaduras, Joyería)."""
    base_stats: Dict[str, Any] = field(default_factory=dict)     # Armadura, DPS, Escudo de Energía, Espíritu, etc.
    requirements: Dict[str, int] = field(default_factory=dict)   # Nivel, Fuerza, Destreza, Inteligencia
    implicit_mods: List[str] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)


@dataclass
class GemItem(ParsedItem):
    """Objeto especializado para Gemas de Habilidad, Asistencia y Auras/Reservas."""
    gem_level: int = 1
    quality: int = 0
    spirit_reservation: int = 0                                  # Coste de Espíritu en PoE2
    mana_cost: Optional[int] = None
    tags: List[str] = field(default_factory=list)                # Hechizo, Físico , Area, Fuego, Apoyo, etc.
    requirements: Dict[str, int] = field(default_factory=dict)   # Nivel, Fuerza, Destreza, Inteligencia
    description: List[str] = field(default_factory=list)         # Efectos explícitos y texto de la gema


# =============================================================================
# PARSER ENGINE
# =============================================================================

class ItemParser:
    """Convierte el texto OCR en una lista de instancias de EquipmentItem, MapItem o GemItem."""

    def __init__(self) -> None:
        self._patterns = {
            "item_class": re.compile(r"^Item Class\s*:\s*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE),
            "rarity": re.compile(r"^Rarity\s*:\s*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE),
            "item_level": re.compile(r"^(?:Item Level|iLvl)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Metadatos de Mapas / Waystones
            "map_tier": re.compile(r"^(?:Map Tier|Waystone Tier)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "item_quantity": re.compile(r"^Item Quantity\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "item_rarity": re.compile(r"^Item Rarity\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "pack_size": re.compile(r"^Monster Pack Size\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            
            # Requisitos comunes
            "req_level": re.compile(r"^Requires Level\s+(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "req_str": re.compile(r"^(?:Str|Strength)\s+(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "req_dex": re.compile(r"^(?:Dex|Dexterity)\s+(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "req_int": re.compile(r"^(?:Int|Intelligence)\s+(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Base Stats de Equipamiento
            "phys_damage": re.compile(r"^Physical Damage\s*:\s*(?P<value>[\d\-]+)", re.IGNORECASE | re.MULTILINE),
            "armour": re.compile(r"^Armour\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "evasion": re.compile(r"^Evasion Rating\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "energy_shield": re.compile(r"^Energy Shield\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "spirit": re.compile(r"^Spirit\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Específicos de Gemas
            "gem_level": re.compile(r"^Level\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "quality": re.compile(r"^Quality\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "spirit_reservation": re.compile(r"^(?:Spirit Reserved|Reserved Spirit|Spirit Cost)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "mana_cost": re.compile(r"^(?:Mana Cost|Mana Reserved)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
        }

        self._metadata_headers = [
            r"^Rarity:", r"^Item Class:", r"^Item Level:", r"^iLvl:", r"^Map Tier:",
            r"^Waystone Tier:", r"^Quality:", r"^Requirements:", r"^Requires",
            r"^Physical Damage:", r"^Elemental Damage:", r"^Chaos Damage:",
            r"^Critical Strike Chance:", r"^Attacks per Second:", r"^Armour:",
            r"^Evasion Rating:", r"^Energy Shield:", r"^Block Chance:", r"^Spirit:",
            r"^Spirit Reserved:", r"^Item Quantity:", r"^Item Rarity:", r"^Monster Pack Size:",
            r"^Sockets:", r"^Level:", r"^Unidentified$", r"^Corrupted$", r"^Mirrored$",
            r"^Str\s+\d+", r"^Dex\s+\d+", r"^Int\s+\d+"
        ]

    def parse_text(self, text: str) -> List[ParsedItem]:
        """Punto de entrada principal: analiza el texto OCR y devuelve una lista de ParsedItem."""
        blocks = self._split_into_item_blocks(text)
        items: List[ParsedItem] = []

        for block in blocks:
            parsed = self.parse_single_item(block)
            if parsed:
                items.append(parsed)

        return items

    def parse_single_item(self, text: str) -> Optional[ParsedItem]:
        """Analiza un bloque de texto correspondiente a un único objeto."""
        cleaned = (text or "").strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return None

        item_class = self._extract_single_value(cleaned, self._patterns["item_class"])
        rarity = self._extract_rarity(cleaned)
        item_level = self._extract_int(cleaned, self._patterns["item_level"])
        name = self._extract_name(lines)

        # 1. ¿Es una Gema?
        is_gem = (
            (item_class and "gem" in item_class.lower()) or
            rarity.lower() == "gem" or
            any("gem" in line.lower() for line in lines[:3])
        )

        if is_gem:
            return self._build_gem_item(cleaned, lines, name, item_class, rarity, item_level)

        # 2. ¿Es un Mapa o Waystone?
        is_map = (
            (item_class and "waystone" in item_class.lower()) or
            (item_class and "map" in item_class.lower()) or
            self._patterns["map_tier"].search(cleaned) is not None
        )

        if is_map:
            return MapItem(
                name=name,
                item_class=item_class,
                rarity=rarity,
                item_level=item_level,
                raw_text=cleaned,
                map_tier=self._extract_int(cleaned, self._patterns["map_tier"]),
                quantity=self._extract_int(cleaned, self._patterns["item_quantity"]),
                rarity_stat=self._extract_int(cleaned, self._patterns["item_rarity"]),
                pack_size=self._extract_int(cleaned, self._patterns["pack_size"]),
                modifiers=self._extract_generic_mods(lines, name)
            )

        # 3. De lo contrario, procesar como Equipamiento
        return self._build_equipment_item(cleaned, lines, name, item_class, rarity, item_level)

    # =========================================================================
    # HELPERS DE CONSTRUCCIÓN Y PARSEO
    # =========================================================================

    def _split_into_item_blocks(self, full_text: str) -> List[str]:
        """Divide el texto capturado por OCR en bloques individuales si hay más de un ítem."""
        lines = [line.strip() for line in (full_text or "").splitlines() if line.strip()]
        if not lines:
            return []

        blocks: List[str] = []
        current_block: List[str] = []

        header_triggers = re.compile(r"^(Item Class:|Rarity:)", re.IGNORECASE)

        for line in lines:
            if header_triggers.match(line) and current_block:
                blocks.append("\n".join(current_block))
                current_block = [line]
            else:
                current_block.append(line)

        if current_block:
            blocks.append("\n".join(current_block))

        return blocks

    def _build_gem_item(
        self, cleaned: str, lines: List[str], name: str, item_class: Optional[str], rarity: str, item_level: Optional[int]
    ) -> GemItem:
        requirements = {
            "level": self._extract_int(cleaned, self._patterns["req_level"]),
            "str": self._extract_int(cleaned, self._patterns["req_str"]),
            "dex": self._extract_int(cleaned, self._patterns["req_dex"]),
            "int": self._extract_int(cleaned, self._patterns["req_int"]),
        }
        
        # Extracción de tags (suele ser la 2ª o 3ª línea en gemas: ej. "Spell, AoE, Fire")
        tags: List[str] = []
        for line in lines[1:4]:
            if "," in line and not self._looks_like_metadata(line):
                tags = [tag.strip() for tag in line.split(",")]
                break

        return GemItem(
            name=name,
            item_class=item_class,
            rarity=rarity if rarity != "unknown" else "Gem",
            item_level=item_level,
            raw_text=cleaned,
            gem_level=self._extract_int(cleaned, self._patterns["gem_level"]) or 1,
            quality=self._extract_int(cleaned, self._patterns["quality"]) or 0,
            spirit_reservation=self._extract_int(cleaned, self._patterns["spirit_reservation"]) or 0,
            mana_cost=self._extract_int(cleaned, self._patterns["mana_cost"]),
            tags=tags,
            requirements={k: v for k, v in requirements.items() if v is not None},
            description=self._extract_generic_mods(lines, name)
        )

    def _build_equipment_item(
        self, cleaned: str, lines: List[str], name: str, item_class: Optional[str], rarity: str, item_level: Optional[int]
    ) -> EquipmentItem:
        requirements = {
            "level": self._extract_int(cleaned, self._patterns["req_level"]),
            "str": self._extract_int(cleaned, self._patterns["req_str"]),
            "dex": self._extract_int(cleaned, self._patterns["req_dex"]),
            "int": self._extract_int(cleaned, self._patterns["req_int"]),
        }

        base_stats = {
            "physical_damage": self._extract_single_value(cleaned, self._patterns["phys_damage"]),
            "armour": self._extract_int(cleaned, self._patterns["armour"]),
            "evasion": self._extract_int(cleaned, self._patterns["evasion"]),
            "energy_shield": self._extract_int(cleaned, self._patterns["energy_shield"]),
            "spirit": self._extract_int(cleaned, self._patterns["spirit"]),
        }

        implicits, explicits = self._extract_equipment_mods(lines, name)

        return EquipmentItem(
            name=name,
            item_class=item_class,
            rarity=rarity,
            item_level=item_level,
            raw_text=cleaned,
            requirements={k: v for k, v in requirements.items() if v is not None},
            base_stats={k: v for k, v in base_stats.items() if v is not None},
            implicit_mods=implicits,
            explicit_mods=explicits
        )

    def _extract_name(self, lines: List[str]) -> str:
        for line in lines:
            if not self._looks_like_metadata(line):
                return line
        return lines[0] if lines else ""

    def _extract_rarity(self, text: str) -> str:
        match = self._patterns["rarity"].search(text)
        if match:
            return match.group("value").strip().capitalize()

        fallback = re.search(r"\b(Rare|Magic|Normal|Unique|Gem)\b", text, re.IGNORECASE)
        return fallback.group(0).capitalize() if fallback else "unknown"

    def _extract_generic_mods(self, lines: List[str], item_name: str) -> List[str]:
        mods = []
        for line in lines:
            if self._looks_like_metadata(line) or line == item_name or len(line) <= 3:
                continue
            mods.append(line)
        return mods

    def _extract_equipment_mods(self, lines: List[str], item_name: str) -> tuple[List[str], List[str]]:
        raw_mods = []
        for line in lines:
            if self._looks_like_metadata(line) or line == item_name or len(line) <= 3:
                continue
            raw_mods.append(line)

        if len(raw_mods) > 1 and ("(implicit)" in raw_mods[0].lower() or self._is_typical_implicit(raw_mods[0])):
            return [raw_mods[0]], raw_mods[1:]

        return [], raw_mods

    def _is_typical_implicit(self, line: str) -> bool:
        implicit_keywords = ["implicit", "increased global", "to all elemental resistances"]
        return any(kw in line.lower() for kw in implicit_keywords)

    def _extract_single_value(self, text: str, pattern: re.Pattern[str]) -> Optional[str]:
        match = pattern.search(text)
        return match.group("value").strip() if match else None

    def _extract_int(self, text: str, pattern: re.Pattern[str]) -> Optional[int]:
        val = self._extract_single_value(text, pattern)
        if val and val.isdigit():
            return int(val)
        return None

    def _looks_like_metadata(self, line: str) -> bool:
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in self._metadata_headers)