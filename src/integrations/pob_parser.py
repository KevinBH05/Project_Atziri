"""Utilidades para cargar y analizar builds de Path of Building 2 (PoB2).

Integra los modelos de datos compartidos de item_parser (EquipmentItem y GemItem)
para garantizar interoperabilidad directa con el motor de OCR y recomendaciones.
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reutilización de tipos desde item_parser
from item_parser import EquipmentItem, GemItem, ItemParser


# =============================================================================
# DATA MODELS PARA EL ÁRBOL Y HABILIDADES EN POB
# =============================================================================

@dataclass
class PassiveTreeData:
    """Representa el estado del árbol de pasivas y su mapa global de conocimiento."""
    unallocated_points: int = 0
    allocated_node_ids: List[int] = field(default_factory=list)
    active_keystones: List[str] = field(default_factory=list)
    active_notables: List[str] = field(default_factory=list)
    
    # Datos para evaluación de recomendaciones
    adjacent_node_ids: List[int] = field(default_factory=list)      # Frontera a 1-2 pasos
    all_keystones: Dict[str, int] = field(default_factory=dict)     # Mapa {Nombre_Keystone: node_id}
    all_notables: Dict[str, int] = field(default_factory=dict)      # Mapa {Nombre_Notable: node_id}


@dataclass
class SkillGroup:
    """Grupo de gemas (Principal, Auras/Reservas o Utilidad)."""
    label: str
    is_main: bool = False
    is_active_auras: bool = False
    gems: List[GemItem] = field(default_factory=list)


@dataclass
class PoBStats:
    """Estadísticas agregadas del personaje calculadas por PoB."""
    # Daño y Métricas de Combate
    dps: float = 0.0
    hit_damage: float = 0.0
    attack_speed: float = 0.0
    crit_chance: float = 0.0
    crit_multiplier: float = 0.0

    # Recursos
    life: float = 0.0
    mana: float = 0.0
    spirit_total: float = 0.0
    spirit_reserved: float = 0.0
    spirit_unreserved: float = 0.0

    # Defensas
    armour: float = 0.0
    evasion: float = 0.0
    energy_shield: float = 0.0

    # Resistencias
    fire_resistance: float = 0.0
    cold_resistance: float = 0.0
    lightning_resistance: float = 0.0
    chaos_resistance: float = 0.0

    # Atributos actuales y requeridos
    strength: float = 0.0
    dexterity: float = 0.0
    intelligence: float = 0.0
    req_strength: float = 0.0
    req_dexterity: float = 0.0
    req_intelligence: float = 0.0


@dataclass
class PoBBuild:
    """Representa un build completo de PoB2 con modelos compartidos."""
    character_name: str
    character_class: str
    level: int
    main_skill_name: str
    stats: PoBStats
    passive_tree: PassiveTreeData
    equipped_items: Dict[str, EquipmentItem] = field(default_factory=dict)  # Mapped por Slot Name
    skill_groups: List[SkillGroup] = field(default_factory=list)


# =============================================================================
# ENGINE DE LOADER / PARSER DE POB
# =============================================================================

class PoBLoader:
    """Carga y parsea un build de Path of Building 2 desde XML local o payload Base64+zlib."""

    def __init__(self, source: str | Path) -> None:
        self.source = (
            Path(source)
            if not isinstance(source, str) or not self._looks_like_encoded_payload(source)
            else source
        )
        self._item_parser = ItemParser()

    @staticmethod
    def _looks_like_encoded_payload(value: str) -> bool:
        return bool(value) and len(value) > 20 and all(ch.isalnum() or ch in "=+/\r\n" for ch in value)

    @staticmethod
    def decode_base64_zlib(payload: str) -> ET.Element:
        if not payload or not isinstance(payload, str):
            raise ValueError("La cadena de entrada está vacía o no es válida.")

        clean_payload = payload.strip().replace("\r", "").replace("\n", "")

        try:
            compressed = base64.b64decode(clean_payload, validate=True)
        except Exception as exc:
            raise ValueError("La cadena Base64 de PoB es inválida o está corrupta.") from exc

        try:
            decoded = zlib.decompress(compressed)
        except zlib.error as exc:
            raise ValueError("La cadena Base64 de PoB no pudo descomprimirse con zlib.") from exc

        try:
            root = ET.fromstring(decoded)
        except ET.ParseError as exc:
            raise ValueError("El XML decodificado de PoB está mal formado.") from exc

        return root

    def _load_xml_from_source(self) -> ET.Element:
        if isinstance(self.source, Path):
            xml_path = self.source
            if not xml_path.exists():
                raise FileNotFoundError(f"No se encontró el archivo XML de PoB: {xml_path}")
            try:
                tree = ET.parse(xml_path)
            except ET.ParseError as exc:
                raise ValueError(f"El XML del archivo de PoB está mal formado: {xml_path}") from exc
            return tree.getroot()

        if isinstance(self.source, str):
            return self.decode_base64_zlib(self.source)

        raise TypeError("La fuente de entrada debe ser una ruta de archivo o una cadena codificada.")

    @staticmethod
    def _safe_float(value: str | None, default: float = 0.0) -> float:
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: str | None, default: int = 0) -> int:
        try:
            return int(float(value)) if value is not None else default
        except (TypeError, ValueError):
            return default

    # -------------------------------------------------------------------------
    # Extracción de Datos
    # -------------------------------------------------------------------------

    def _extract_player_stats(self, root: ET.Element) -> PoBStats:
        stats = PoBStats()
        raw_stats: Dict[str, float] = {}

        for elem in root.findall(".//PlayerStat"):
            stat_name = elem.attrib.get("stat") or elem.attrib.get("name")
            val = elem.attrib.get("value") or elem.attrib.get("amount")
            if stat_name and val is not None:
                raw_stats[stat_name] = self._safe_float(val)

        stats.dps = (
            raw_stats.get("CombinedDPS")
            or raw_stats.get("TotalDPS")
            or raw_stats.get("WithPoisonDPS")
            or raw_stats.get("MainHandDPS")
            or 0.0
        )
        stats.hit_damage = raw_stats.get("AverageHit") or raw_stats.get("AverageDamage") or 0.0
        stats.attack_speed = raw_stats.get("Speed") or raw_stats.get("HitSpeed") or 0.0
        stats.crit_chance = raw_stats.get("CritChance", 0.0)
        stats.crit_multiplier = raw_stats.get("CritMultiplier", 0.0)

        stats.life = raw_stats.get("Life", 0.0)
        stats.mana = raw_stats.get("Mana", 0.0)
        stats.spirit_total = raw_stats.get("Spirit") or raw_stats.get("SpiritLimit") or 0.0
        stats.spirit_reserved = raw_stats.get("SpiritReserved") or raw_stats.get("ManaReserved") or 0.0
        stats.spirit_unreserved = max(0.0, stats.spirit_total - stats.spirit_reserved)

        stats.armour = raw_stats.get("Armour", 0.0)
        stats.evasion = raw_stats.get("Evasion", 0.0)
        stats.energy_shield = raw_stats.get("EnergyShield", 0.0)

        stats.fire_resistance = raw_stats.get("FireResist", 0.0)
        stats.cold_resistance = raw_stats.get("ColdResist", 0.0)
        stats.lightning_resistance = raw_stats.get("LightningResist", 0.0)
        stats.chaos_resistance = raw_stats.get("ChaosResist", 0.0)

        stats.strength = raw_stats.get("Strength", 0.0)
        stats.dexterity = raw_stats.get("Dexterity", 0.0)
        stats.intelligence = raw_stats.get("Intelligence", 0.0)

        stats.req_strength = raw_stats.get("ReqStr", 0.0)
        stats.req_dexterity = raw_stats.get("ReqDex", 0.0)
        stats.req_intelligence = raw_stats.get("ReqInt", 0.0)

        return stats

    def _extract_equipped_items(self, root: ET.Element) -> Dict[str, EquipmentItem]:
        """Extrae y convierte el XML de ítems de PoB directamente a instancias de EquipmentItem."""
        equipped: Dict[str, EquipmentItem] = {}
        items_root = root.find(".//Items")
        if items_root is None:
            return equipped

        parsed_items_by_id: Dict[str, EquipmentItem] = {}

        for item_elem in items_root.findall("Item"):
            item_id = item_elem.attrib.get("id")
            raw_text = (item_elem.text or "").strip()
            if not item_id or not raw_text:
                continue

            parsed = self._item_parser.parse_single_item(raw_text)
            if isinstance(parsed, EquipmentItem):
                parsed_items_by_id[item_id] = parsed

        for slot_elem in items_root.findall("Slot"):
            slot_name = slot_elem.attrib.get("name")
            item_id = slot_elem.attrib.get("itemId")
            if slot_name and item_id and item_id in parsed_items_by_id:
                equipped[slot_name] = parsed_items_by_id[item_id]

        return equipped

    def _extract_passive_tree(self, root: ET.Element) -> PassiveTreeData:
        """Extrae los nodos asignados, puntos pendientes y directorio global de pasivas."""
        tree_data = PassiveTreeData()
        tree_node = root.find(".//Tree")
        if tree_node is None:
            return tree_data

        spec = tree_node.find("Spec")
        if spec is not None:
            tree_data.unallocated_points = self._safe_int(spec.attrib.get("pointsUnused"), 0)
            
            # IDs de nodos asignados en PoB
            nodes_attr = spec.attrib.get("nodes", "")
            if nodes_attr:
                tree_data.allocated_node_ids = [
                    int(n) for n in nodes_attr.split(",") if n.strip().isdigit()
                ]

        # Parseo de Keystones / Notables del XML global si existen
        for node in tree_node.findall(".//EditedNodes/Node"):
            name = node.attrib.get("name", "")
            node_id = self._safe_int(node.attrib.get("id"))
            is_ks = node.attrib.get("isKeystone") == "true"
            is_notable = node.attrib.get("isNotable") == "true"

            if is_ks and name:
                tree_data.all_keystones[name] = node_id
                if node_id in tree_data.allocated_node_ids:
                    tree_data.active_keystones.append(name)
            elif is_notable and name:
                tree_data.all_notables[name] = node_id
                if node_id in tree_data.allocated_node_ids:
                    tree_data.active_notables.append(name)

        return tree_data

    def _extract_skill_groups(self, root: ET.Element) -> Tuple[str, List[SkillGroup]]:
        """Extrae todos los grupos de gemas (principales, auras, utilidad) convertidos a GemItem."""
        skills_root = root.find(".//Skills")
        if skills_root is None:
            return "Unknown Skill", []

        groups: List[SkillGroup] = []
        main_skill_name = "Unknown Skill"

        for skill_elem in skills_root.findall("Skill"):
            is_enabled = skill_elem.attrib.get("enabled") != "false"
            if not is_enabled:
                continue

            label = skill_elem.attrib.get("label") or "Skill Group"
            is_main = skill_elem.attrib.get("mainActiveSkill") is not None
            gems: List[GemItem] = []

            for gem_elem in skill_elem.findall("Gem"):
                gem_enabled = gem_elem.attrib.get("enabled") != "false"
                if not gem_enabled:
                    continue

                name = gem_elem.attrib.get("nameSpec") or gem_elem.attrib.get("skillId") or "Unknown Gem"
                gem_level = self._safe_int(gem_elem.attrib.get("level"), 1)
                quality = self._safe_int(gem_elem.attrib.get("quality"), 0)
                spirit = self._safe_int(gem_elem.attrib.get("spiritReservation"), 0)

                tags_attr = (
                    gem_elem.attrib.get("tags") 
                    or gem_elem.attrib.get("types") 
                    or gem_elem.attrib.get("supportsGems") 
                    or ""
                )
                tags = [t.strip() for t in tags_attr.split(",") if t.strip()]

                gem_item = GemItem(
                    name=name,
                    item_class="Support Gem" if "support" in name.lower() else "Skill Gem",
                    rarity="Gem",
                    item_level=None,
                    raw_text=f"{name} (Lvl {gem_level})",
                    gem_level=gem_level,
                    quality=quality,
                    spirit_reservation=spirit,
                    tags=tags  # <-- Aquí guardamos los tags reales de la gema
                )
                gems.append(gem_item)

            if gems:
                is_auras = any(g.spirit_reservation > 0 for g in gems)
                group = SkillGroup(label=label, is_main=is_main, is_active_auras=is_auras, gems=gems)
                groups.append(group)

                if is_main and main_skill_name == "Unknown Skill":
                    main_skill_name = gems[0].name

        if main_skill_name == "Unknown Skill" and groups and groups[0].gems:
            main_skill_name = groups[0].gems[0].name

        return main_skill_name, groups

    def _extract_character_details(self, root: ET.Element) -> Tuple[str, str, int]:
        build_node = root.find(".//Build")
        if build_node is not None:
            name = build_node.attrib.get("targetVersion") or root.attrib.get("name") or "Build PoB2"
            character_class = build_node.attrib.get("className") or "Unknown"
            level = self._safe_int(build_node.attrib.get("level"), 0)
            return name, character_class, level

        return "Build PoB2", "Unknown", 0

    def load_build(self) -> PoBBuild:
        root = self._load_xml_from_source()
        if root is None or root.tag is None:
            raise ValueError("El XML de PoB está vacío o no se pudo cargar.")

        name, character_class, level = self._extract_character_details(root)
        stats = self._extract_player_stats(root)
        equipped_items = self._extract_equipped_items(root)
        passive_tree = self._extract_passive_tree(root)
        main_skill_name, skill_groups = self._extract_skill_groups(root)

        return PoBBuild(
            character_name=name,
            character_class=character_class,
            level=level,
            main_skill_name=main_skill_name,
            stats=stats,
            passive_tree=passive_tree,
            equipped_items=equipped_items,
            skill_groups=skill_groups
        )


class PoBParser(PoBLoader):
    """Alias compatible."""

    def parse(self, payload: str | Path) -> PoBBuild:
        return PoBLoader(payload).load_build()