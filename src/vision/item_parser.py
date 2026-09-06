"""Lógica de análisis para descripciones de objetos extraídas de capturas.

Este módulo convierte el texto bruto del OCR en dataclasses estructuradas
heredadas de ParsedItem (EquipmentItem, MapItem o GemItem) para separar
claramente las propiedades de equipamiento, mapas/waystones y gemas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedItem:
    """Clase base estricta para cualquier objeto detectado por el OCR."""
    name: str
    item_class: Optional[str]
    rarity: str
    item_level: Optional[int]
    raw_text: str

    def __post_init__(self) -> None:
        """Saneamiento ligero de strings para evitar errores de comparación."""
        self.name = self.name.strip() if self.name else "Unknown Item"
        self.rarity = self.rarity.upper().strip() if self.rarity else "NORMAL"
        self.raw_text = self.raw_text or ""


@dataclass
class MapItem(ParsedItem):
    """Objeto especializado para Mapas y Waystones en PoE 2."""
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
    spirit_reservation: int = 0                                  # Coste de Espíritu específico de PoE 2
    mana_cost: Optional[int] = None
    tags: List[str] = field(default_factory=list)                # Hechizo, Físico, Área, Fuego, Apoyo, etc.
    requirements: Dict[str, int] = field(default_factory=dict)   # Nivel, Fuerza, Destreza, Inteligencia
    description: List[str] = field(default_factory=list)         # Efectos explícitos y texto de la gema


# =============================================================================
# PARSER ENGINE
# =============================================================================

class ItemParser:
    """Convierte el texto OCR en una lista de instancias de EquipmentItem, MapItem o GemItem."""

    def __init__(self) -> None:
        # Tolerancia a espacios iniciales opcionales y variaciones de caracteres OCR
        self._patterns = {
            "item_class": re.compile(r"^\s*Item Class\s*:\s*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE),
            "rarity": re.compile(r"^\s*Rarity\s*:\s*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE),
            "item_level": re.compile(r"^\s*(?:Item Level|iLvl)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Waystones / Mapas
            "map_tier": re.compile(r"^\s*(?:Map Tier|Waystone Tier)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "item_quantity": re.compile(r"^\s*Item Quantity\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "item_rarity": re.compile(r"^\s*Item Rarity\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "pack_size": re.compile(r"^\s*Monster Pack Size\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            
            # Requisitos (Permite búsqueda en cualquier parte de la línea, no solo al inicio)
            "req_level": re.compile(r"Requires Level\s+(?P<value>\d+)", re.IGNORECASE),
            "req_str": re.compile(r"(?:Str|Strength)\s+(?P<value>\d+)", re.IGNORECASE),
            "req_dex": re.compile(r"(?:Dex|Dexterity)\s+(?P<value>\d+)", re.IGNORECASE),
            "req_int": re.compile(r"(?:Int|Intelligence)\s+(?P<value>\d+)", re.IGNORECASE),
            
            # Base Stats (Soporta múltiples tipos de guion en rangos de daño)
            "phys_damage": re.compile(r"^\s*Physical Damage\s*:\s*(?P<value>[\d\-\–\—\s]+)", re.IGNORECASE | re.MULTILINE),
            "armour": re.compile(r"^\s*Armour\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "evasion": re.compile(r"^\s*Evasion Rating\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "energy_shield": re.compile(r"^\s*Energy Shield\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "spirit": re.compile(r"^\s*Spirit\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Gemas
            "gem_level": re.compile(r"^\s*Level\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "quality": re.compile(r"^\s*Quality\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "spirit_reservation": re.compile(r"^\s*(?:Spirit Reserved|Reserved Spirit|Spirit Cost)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "mana_cost": re.compile(r"^\s*(?:Mana Cost|Mana Reserved)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
        }

        # La lista de cabeceras se usa para limpiar metadatos y aislar los modificadores (affixes)
        self._metadata_headers = [
            r"^\s*Rarity:", r"^\s*Item Class:", r"^\s*Item Level:", r"^\s*iLvl:", r"^\s*Map Tier:",
            r"^\s*Waystone Tier:", r"^\s*Quality:", r"^\s*Requirements:", r"^\s*Requires",
            r"^\s*Physical Damage:", r"^\s*Elemental Damage:", r"^\s*Chaos Damage:",
            r"^\s*Critical Strike Chance:", r"^\s*Attacks per Second:", r"^\s*Armour:",
            r"^\s*Evasion Rating:", r"^\s*Energy Shield:", r"^\s*Block Chance:", r"^\s*Spirit:",
            r"^\s*Spirit Reserved:", r"^\s*Item Quantity:", r"^\s*Item Rarity:", r"^\s*Monster Pack Size:",
            r"^\s*Sockets:", r"^\s*Level:", r"^\s*Unidentified$", r"^\s*Corrupted$", r"^\s*Mirrored$",
            r"Str\s+\d+", r"Dex\s+\d+", r"Int\s+\d+"
        ]

    from typing import List

    def parse_text(self, text: str) -> List[ParsedItem]:
        """Punto de entrada principal: analiza el texto OCR y devuelve una lista de ParsedItem."""
        if not text or not text.strip():
            return []

        blocks = self._split_into_item_blocks(text)
        items: List[ParsedItem] = []

        for block in blocks:
            try:
                parsed = self.parse_single_item(block)
                if parsed:
                    items.append(parsed)
            except Exception as e:
                # Captura fallos en un bloque concreto sin interrumpir la lista completa
                # Ideal para loguear el bloque problemático en desarrollo
                continue

        return items

    def parse_single_item(self, text: str) -> Optional[ParsedItem]:
        """Analiza un bloque de texto correspondiente a un único objeto y lo despacha a su dataclass."""
        cleaned = (text or "").strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return None

        item_class = self._extract_single_value(cleaned, self._patterns["item_class"])
        rarity = self._extract_rarity(cleaned)
        item_level = self._extract_int(cleaned, self._patterns["item_level"])
        name = self._extract_name(lines)

        # 1. Identificación de Gemas (Ampliación para Support Gems y Spirit Reserved)
        is_gem = (
            (item_class and any(tag in item_class.lower() for tag in ["gem", "support", "skill"])) or
            rarity.lower() in ("gem", "gema") or
            any(keyword in line.lower() for line in lines[:3] for keyword in ["gem", "support", "uncut"]) or
            self._patterns["spirit_reservation"].search(cleaned) is not None
        )

        if is_gem:
            return self._build_gem_item(cleaned, lines, name, item_class, rarity, item_level)

        # 2. Identificación de Mapas / Waystones
        is_map = (
            (item_class and any(tag in item_class.lower() for tag in ["waystone", "map", "mapa"])) or
            self._patterns["map_tier"].search(cleaned) is not None
        )

        if is_map:
            return self._build_map_item(cleaned, lines, name, item_class, rarity, item_level)

        # 3. Equipamiento (Armas, Armaduras, Joyas, Consumibles de equipo)
        return self._build_equipment_item(cleaned, lines, name, item_class, rarity, item_level)

    # =========================================================================
    # HELPERS DE CONSTRUCCIÓN Y PARSEO
    # =========================================================================

    def _split_into_item_blocks(self, full_text: str) -> List[str]:
        """Divide el texto capturado por OCR en bloques individuales preservando los nombres de cabecera."""
        lines = [line.strip() for line in (full_text or "").splitlines() if line.strip()]
        if not lines:
            return []

        blocks: List[str] = []
        current_block: List[str] = []
        
        # Rarity o Item Class precedidos opcionalmente de basura OCR (\s*)
        rarity_trigger = re.compile(r"^\s*Rarity\s*:", re.IGNORECASE)

        for line in lines:
            if rarity_trigger.match(line) and current_block:
                # Si en el bloque actual ya teníamos líneas, la última (o 2 últimas)
                # suelen ser el nombre del nuevo ítem. Las rescatamos para el nuevo bloque.
                title_lines = []
                
                # Si la línea anterior no es un modificador ni un separador, es el nombre
                if current_block and not current_block[-1].startswith("--------"):
                    title_lines.append(current_block.pop())

                # Guardamos el bloque anterior completado
                if current_block:
                    blocks.append("\n".join(current_block))

                # Iniciamos el nuevo bloque con el nombre rescatado y la línea actual
                current_block = title_lines + [line]
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

        # Extracción flexible de tags (admite tanto "Spell, AoE, Fire" como tags únicos)
        tags: List[str] = []
        for line in lines[1:5]:
            if not self._looks_like_metadata(line) and any(keyword in line.lower() for keyword in ["spell", "attack", "aoe", "fire", "cold", "lightning", "minion", "duration", "aura", "support", "melee", "bow"]):
                tags = [tag.strip() for tag in line.split(",") if tag.strip()]
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


    def _build_map_item(
        self, 
        cleaned: str, 
        lines: List[str], 
        name: str, 
        item_class: Optional[str], 
        rarity: str, 
        item_level: Optional[int]
    ) -> MapItem:
        """Helper para aislar la construcción de MapItem."""
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
            "elemental_damage": self._extract_single_value(cleaned, self._patterns.get("elem_damage")), # Si tienes el regex definido
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
        """Extrae el nombre del objeto (soporta nombres de 2 líneas para objetos Raros/Únicos)."""
        valid_lines = []
        for line in lines:
            if not self._looks_like_metadata(line) and line != "--------":
                valid_lines.append(line)
                if len(valid_lines) == 2:
                    break
        
        # Si las dos primeras líneas no son metadatos, en Rare/Unique son [Nombre, Base]
        if len(valid_lines) >= 2 and not any(kw in valid_lines[1].lower() for kw in ["item class", "rarity"]):
            return f"{valid_lines[0]} {valid_lines[1]}"
        
        return valid_lines[0] if valid_lines else (lines[0] if lines else "")

    def _extract_rarity(self, text: str) -> str:
        match = self._patterns["rarity"].search(text)
        if match:
            return match.group("value").strip().capitalize()

        fallback = re.search(r"\b(Rare|Magic|Normal|Unique|Gem)\b", text, re.IGNORECASE)
        return fallback.group(0).capitalize() if fallback else "unknown"

    def _extract_generic_mods(self, lines: List[str], item_name: str) -> List[str]:
        mods = []
        name_parts = item_name.split()
        for line in lines:
            # Filtra si es metadato, separador, demasiado corta o coincide con parte del nombre
            if self._looks_like_metadata(line) or line.startswith("--------") or len(line) <= 3:
                continue
            if line in item_name or any(part == line for part in name_parts):
                continue
            mods.append(line)
        return mods

    def _extract_equipment_mods(self, lines: List[str], item_name: str) -> Tuple[List[str], List[str]]:
        """Separa modificadores implícitos de explícitos, soportando múltiples implícitos."""
        raw_mods = self._extract_generic_mods(lines, item_name)
        
        implicits = []
        explicits = []

        for mod in raw_mods:
            if "(implicit)" in mod.lower() or self._is_typical_implicit(mod):
                # Limpia la etiqueta (implicit) si el OCR la capturó explícitamente
                clean_mod = re.sub(r"\s*\((?:implicit)\)", "", mod, flags=re.IGNORECASE).strip()
                implicits.append(clean_mod)
            else:
                explicits.append(mod)

        return implicits, explicits

    def _is_typical_implicit(self, line: str) -> bool:
        implicit_keywords = [
            "implicit", 
            "increased global", 
            "to all elemental resistances",
            "movement speed",
            "block chance",
            "spirit"
        ]
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