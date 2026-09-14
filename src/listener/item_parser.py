"""Lógica de análisis para descripciones de objetos extraídas de capturas en PoE 2.

Convierte el texto bruto en dataclasses estructuradas (EquipmentItem o GemItem),
adaptado tanto para textos en español como en inglés.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedItem:
    """Clase base estricta para cualquier objeto detectado."""
    name: str
    item_class: Optional[str]
    rarity: str
    item_level: Optional[int]
    raw_text: str

    def __post_init__(self) -> None:
        self.name = self.name.strip() if self.name else "Objeto Desconocido"
        self.rarity = self.rarity.upper().strip() if self.rarity else "NORMAL"
        self.raw_text = self.raw_text or ""


@dataclass
class EquipmentItem(ParsedItem):
    """Objeto especializado para Equipamiento (Armas, Armaduras, Joyería, Escudos)."""
    base_stats: Dict[str, Any] = field(default_factory=dict)     # Armadura, DPS, Escudo de Energía, Barrera Rúnica, Bloqueo, Espíritu
    requirements: Dict[str, int] = field(default_factory=dict)   # Nivel, Fuerza, Destreza, Inteligencia
    implicit_mods: List[str] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)
    flavor_text: Optional[str] = None                            # Lore / citas al final de objetos únicos


@dataclass
class GemItem(ParsedItem):
    """Objeto especializado para Gemas de Habilidad, Asistencia y Auras/Reservas."""
    gem_level: int = 1
    quality: int = 0
    spirit_reservation: int = 0
    mana_cost: Optional[int] = None
    tags: List[str] = field(default_factory=list)                 # Ataque, AdE, Cuerpo a cuerpo, Embate, etc.
    requirements: Dict[str, int] = field(default_factory=dict)    # Nivel, Fuerza, Destreza, Inteligencia
    description: List[str] = field(default_factory=list)          # Descripción principal de la gema
    sub_effects: Dict[str, List[str]] = field(default_factory=dict) # Sub-habilidades (ej: {"Ola": [...], "Onda expansiva": [...]})


# =============================================================================
# PARSER ENGINE
# =============================================================================

class ItemParser:
    """Procesador de texto para equipamiento y gemas en PoE 2."""

    def __init__(self) -> None:
        self._patterns = {
            # Cabeceras
            "item_class": re.compile(r"^\s*(?:Item Class|Clase de objeto)\s*:\s*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE),
            "rarity": re.compile(r"^\s*(?:Rarity|Rareza)\s*:\s*(?P<value>[^\n]+)", re.IGNORECASE | re.MULTILINE),
            "item_level": re.compile(r"^\s*(?:Item Level|Nivel de objeto|iLvl)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Requisitos
            "req_level": re.compile(r"(?:Requires Level|Requiere:\s*Nivel|Nivel)\s+(?P<value>\d+)", re.IGNORECASE),
            "req_str": re.compile(r"(?:Str|Strength|Fue|Fuerza)\s+(?P<value>\d+)", re.IGNORECASE),
            "req_dex": re.compile(r"(?:Dex|Dexterity|Des|Destreza)\s+(?P<value>\d+)", re.IGNORECASE),
            "req_int": re.compile(r"(?:Int|Intelligence|Inteligencia)\s+(?P<value>\d+)", re.IGNORECASE),
            
            # Base Stats
            "phys_damage": re.compile(r"^\s*(?:Physical Damage|Daño físico)\s*:\s*(?P<value>[\d\-\–\—\s]+)", re.IGNORECASE | re.MULTILINE),
            "armour": re.compile(r"^\s*(?:Armour|Armadura)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "evasion": re.compile(r"^\s*(?:Evasion Rating|Evasión)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "energy_shield": re.compile(r"^\s*(?:Energy Shield|Escudo de energía)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "runic_shield": re.compile(r"^\s*(?:Runic Shield|Barrera rúnica)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "block_chance": re.compile(r"^\s*(?:Block Chance|Probabilidad de bloqueo)\s*:\s*(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "spirit": re.compile(r"^\s*(?:Spirit|Espíritu)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            
            # Gemas
            "gem_level": re.compile(r"^\s*(?:Level|Nivel)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "quality": re.compile(r"^\s*(?:Quality|Calidad)\s*:\s*\+?(?P<value>\d+)%", re.IGNORECASE | re.MULTILINE),
            "spirit_reservation": re.compile(r"^\s*(?:Spirit Reserved|Reserved Spirit|Espíritu reservado|Coste de espíritu)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
            "mana_cost": re.compile(r"^\s*(?:Mana Cost|Costo|Coste de maná)\s*:\s*(?P<value>\d+)", re.IGNORECASE | re.MULTILINE),
        }

        self._metadata_headers = [
            r"^\s*(?:Rarity|Rareza):", r"^\s*(?:Item Class|Clase de objeto):", 
            r"^\s*(?:Item Level|Nivel de objeto|iLvl):", r"^\s*(?:Quality|Calidad):", 
            r"^\s*(?:Requirements|Requiere):", r"^\s*(?:Physical Damage|Daño físico):", 
            r"^\s*(?:Elemental Damage|Daño elemental):", r"^\s*(?:Armour|Armadura):", 
            r"^\s*(?:Evasion Rating|Evasión):", r"^\s*(?:Energy Shield|Escudo de energía):", 
            r"^\s*(?:Runic Shield|Barrera rúnica):", r"^\s*(?:Block Chance|Probabilidad de bloqueo):", 
            r"^\s*(?:Spirit|Espíritu):", r"^\s*(?:Sockets|Engarces):", r"^\s*(?:Level|Nivel):", 
            r"^\s*(?:Unidentified|Sin identificar)$", r"^\s*(?:Corrupted|Corrupto)$",
            r"^\s*Las habilidades se administran"
        ]

    def parse_equipment(self, text: str) -> EquipmentItem:
        """Parsea de forma directa texto correspondiente a equipamiento."""
        cleaned = (text or "").strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        
        item_class = self._extract_single_value(cleaned, self._patterns["item_class"])
        rarity = self._extract_rarity(cleaned)
        item_level = self._extract_int(cleaned, self._patterns["item_level"])
        name = self._extract_name(lines)

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
            "runic_shield": self._extract_int(cleaned, self._patterns["runic_shield"]),
            "block_chance": self._extract_int(cleaned, self._patterns["block_chance"]),
            "spirit": self._extract_int(cleaned, self._patterns["spirit"]),
        }

        implicits, explicits, flavor = self._extract_equipment_mods_and_flavor(lines, name)

        return EquipmentItem(
            name=name,
            item_class=item_class,
            rarity=rarity,
            item_level=item_level,
            raw_text=cleaned,
            requirements={k: v for k, v in requirements.items() if v is not None},
            base_stats={k: v for k, v in base_stats.items() if v is not None},
            implicit_mods=implicits,
            explicit_mods=explicits,
            flavor_text=flavor
        )

    def parse_gem(self, text: str) -> GemItem:
        """Parsea de forma directa texto correspondiente a gemas de habilidad o asistencia."""
        cleaned = (text or "").strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]

        item_class = self._extract_single_value(cleaned, self._patterns["item_class"])
        rarity = self._extract_rarity(cleaned)
        item_level = self._extract_int(cleaned, self._patterns["item_level"])
        name = self._extract_name(lines)

        requirements = {
            "level": self._extract_int(cleaned, self._patterns["req_level"]),
            "str": self._extract_int(cleaned, self._patterns["req_str"]),
            "dex": self._extract_int(cleaned, self._patterns["req_dex"]),
            "int": self._extract_int(cleaned, self._patterns["req_int"]),
        }

        # Extracción de etiquetas/tags (ej. Ataque, AdE, Cuerpo a cuerpo, Embate...)
        tags: List[str] = []
        for line in lines[1:6]:
            if "," in line and not self._looks_like_metadata(line):
                tags = [tag.strip() for tag in line.split(",") if tag.strip()]
                break

        # División en bloques por '--------' para estructurar la descripción principal y sub-efectos
        blocks = [b.strip() for b in cleaned.split("--------") if b.strip()]
        
        description: List[str] = []
        sub_effects: Dict[str, List[str]] = {}
        current_sub_name: Optional[str] = None

        for block in blocks:
            block_lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not block_lines:
                continue

            # Omitir metadata
            if any(self._looks_like_metadata(l) for l in block_lines):
                continue
            if any(l.startswith("Engarces:") or l.startswith("Sockets:") for l in block_lines):
                continue

            # Encabezado de sub-habilidad/efecto secundario (ej. "Ola", "Onda expansiva")
            if len(block_lines) == 1 and not block_lines[0].endswith(".") and not block_lines[0].startswith("Las habilidades"):
                current_sub_name = block_lines[0]
                sub_effects[current_sub_name] = []
                continue

            # Contenido dentro de sub-efecto o descripción general
            filtered_lines = [l for l in block_lines if not l.startswith("Las habilidades se administran")]
            
            if current_sub_name:
                sub_effects[current_sub_name].extend(filtered_lines)
            else:
                # Filtrar redundancias con nombre o tags
                valid_desc = [l for l in filtered_lines if l not in tags and l != name]
                if valid_desc:
                    description.extend(valid_desc)

        return GemItem(
            name=name,
            item_class=item_class,
            rarity=rarity if rarity != "UNKNOWN" else "GEM",
            item_level=item_level,
            raw_text=cleaned,
            gem_level=self._extract_int(cleaned, self._patterns["gem_level"]) or 1,
            quality=self._extract_int(cleaned, self._patterns["quality"]) or 0,
            spirit_reservation=self._extract_int(cleaned, self._patterns["spirit_reservation"]) or 0,
            mana_cost=self._extract_int(cleaned, self._patterns["mana_cost"]),
            tags=tags,
            requirements={k: v for k, v in requirements.items() if v is not None},
            description=description,
            sub_effects=sub_effects
        )

    # =========================================================================
    # HELPERS AUXILIARES
    # =========================================================================

    def _extract_name(self, lines: List[str]) -> str:
        """Extrae el nombre del objeto (soporta nombres de 2 líneas para Raros/Únicos)."""
        valid_lines = []
        for line in lines:
            if not self._looks_like_metadata(line) and not line.startswith("--------"):
                valid_lines.append(line)
                if len(valid_lines) == 2:
                    break
        
        if len(valid_lines) >= 2 and not any(kw in valid_lines[1].lower() for kw in ["clase de objeto", "rareza", "item class", "rarity"]):
            return f"{valid_lines[0]} ({valid_lines[1]})"
        
        return valid_lines[0] if valid_lines else "Objeto Desconocido"

    def _extract_rarity(self, text: str) -> str:
        match = self._patterns["rarity"].search(text)
        if match:
            return match.group("value").strip().capitalize()

        fallback = re.search(r"\b(Rare|Raro|Magic|Mágico|Normal|Unique|Único|Gem|Gema)\b", text, re.IGNORECASE)
        return fallback.group(0).capitalize() if fallback else "UNKNOWN"

    def _extract_equipment_mods_and_flavor(self, lines: List[str], item_name: str) -> Tuple[List[str], List[str], Optional[str]]:
        """Separa modificadores implícitos, explícitos y cita de ambientación."""
        raw_mods = []
        flavor_lines = []
        in_flavor = False

        for line in lines:
            if line.startswith('"') or in_flavor:
                in_flavor = True
                flavor_lines.append(line)
                continue

            if self._looks_like_metadata(line) or line.startswith("--------") or len(line) <= 2:
                continue
            if line in item_name or line.startswith("Engarces:") or line.startswith("Sockets:"):
                continue

            raw_mods.append(line)

        implicits = []
        explicits = []

        for mod in raw_mods:
            if "(implicit)" in mod.lower() or "(rune)" in mod.lower() or self._is_typical_implicit(mod):
                clean_mod = re.sub(r"\s*\((?:implicit|rune)\)", "", mod, flags=re.IGNORECASE).strip()
                implicits.append(clean_mod)
            else:
                explicits.append(mod)

        flavor_text = " ".join(flavor_lines) if flavor_lines else None
        return implicits, explicits, flavor_text

    def _is_typical_implicit(self, line: str) -> bool:
        implicit_keywords = [
            "implicit", "increased global", "resistances", "resistencia",
            "movement speed", "velocidad de movimiento", "block chance", 
            "probabilidad de bloqueo", "spirit", "espíritu"
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