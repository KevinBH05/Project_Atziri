"""Utilidades para cargar y analizar builds de Path of Building 2 (PoB2).

Integra los modelos de datos compartidos de item_parser (EquipmentItem y GemItem)
para garantizar interoperabilidad directa con el motor de OCR y recomendaciones.
"""

from __future__ import annotations

import base64
import json
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from src.listener.item_parser import EquipmentItem, GemItem, ItemParser


# =============================================================================
# DATA MODELS PARA EL ÁRBOL Y HABILIDADES EN POB
# =============================================================================

@dataclass
class PassiveTreeData:
    """Representa el estado del árbol de pasivas del personaje en PoB."""
    unallocated_points: int = 0
    allocated_node_ids: List[int] = field(default_factory=list)


@dataclass
class SkillGroup:
    """Grupo de gemas (Skill Group en el XML de PoB)."""
    label: str = ""
    is_main: bool = False
    gems: List[GemItem] = field(default_factory=list)


@dataclass
class PoBStats:
    """Estadísticas agregadas del personaje extraídas directamente de PoB."""
    # DPS y Ataque/Hechizo
    combined_dps: float = 0.0
    hit_dps: float = 0.0
    poison_dps: float = 0.0
    dot_dps: float = 0.0
    average_damage: float = 0.0
    attack_cast_rate: float = 0.0

    # Recursos (Vida, Maná y Espíritu para PoB2)
    life: float = 0.0
    mana: float = 0.0
    spirit_total: float = 0.0
    spirit_reserved: float = 0.0
    spirit_unreserved: float = 0.0

    # Defensas principales
    armour: float = 0.0
    evasion: float = 0.0
    energy_shield: float = 0.0

    # Resistencias
    fire_resistance: float = 0.0
    cold_resistance: float = 0.0
    lightning_resistance: float = 0.0
    chaos_resistance: float = 0.0

    # Atributos y Requisitos
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
    ascendancy_name: str
    level: int
    main_skill_name: str
    stats: PoBStats
    passive_tree: PassiveTreeData
    equipped_items: Dict[str, EquipmentItem] = field(default_factory=dict)
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
        return bool(value) and len(value) > 20 and all(ch.isalnum() or ch in "=+/\r\n-_" for ch in value)

    @staticmethod
    def decode_base64_zlib(payload: str) -> ET.Element:
        if not payload or not isinstance(payload, str):
            raise ValueError("La cadena de entrada está vacía o no es válida.")

        clean_payload = (
            payload.strip()
            .replace("\r", "")
            .replace("\n", "")
            .replace("-", "+")
            .replace("_", "/")
        )

        try:
            compressed = base64.b64decode(clean_payload)
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

    def _extract_player_stats(self, root: ET.Element) -> PoBStats:
        stats = PoBStats()
        raw_stats: Dict[str, float] = {}

        for elem in root.findall(".//PlayerStat"):
            stat_name = elem.attrib.get("stat") or elem.attrib.get("name")
            val = elem.attrib.get("value") or elem.attrib.get("amount")
            if stat_name and val is not None:
                raw_stats[stat_name] = self._safe_float(val)

        stats.combined_dps = next(
            (raw_stats[k] for k in ("CombinedDPS", "TotalDPS", "Total DPS per Poison") if k in raw_stats),
            0.0
        )
        stats.hit_dps = next(
            (raw_stats[k] for k in ("HitDPS", "WithHitDPS", "Hit DPS", "MainHandDPS") if k in raw_stats),
            0.0
        )
        stats.poison_dps = next(
            (raw_stats[k] for k in ("PoisonDPS", "TotalPoisonDPS", "Poison DPS") if k in raw_stats),
            0.0
        )
        stats.dot_dps = next(
            (raw_stats[k] for k in ("TotalDot", "TotalDotDPS", "Total DoT DPS") if k in raw_stats),
            0.0
        )
        stats.average_damage = next(
            (raw_stats[k] for k in ("AverageDamage", "AverageHit", "Average Damage") if k in raw_stats),
            0.0
        )
        stats.attack_cast_rate = next(
            (raw_stats[k] for k in ("Speed", "Attack/Cast Rate") if k in raw_stats),
            0.0
        )

        stats.life = raw_stats.get("Life", 0.0)
        stats.mana = raw_stats.get("Mana", 0.0)
        stats.spirit_total = raw_stats.get("Spirit", 0.0)
        stats.spirit_reserved = raw_stats.get("SpiritReserved", 0.0)
        stats.spirit_unreserved = raw_stats.get(
            "SpiritUnreserved", 
            max(0.0, stats.spirit_total - stats.spirit_reserved)
        )

        stats.armour = raw_stats.get("Armour", 0.0)
        stats.evasion = raw_stats.get("Evasion", 0.0)
        stats.energy_shield = raw_stats.get("EnergyShield", 0.0)

        stats.fire_resistance = raw_stats.get("FireResist", 0.0)
        stats.cold_resistance = raw_stats.get("ColdResist", 0.0)
        stats.lightning_resistance = raw_stats.get("LightningResist", 0.0)
        stats.chaos_resistance = raw_stats.get("ChaosResist", 0.0)

        stats.strength = raw_stats.get("Str", raw_stats.get("Strength", 0.0))
        stats.dexterity = raw_stats.get("Dex", raw_stats.get("Dexterity", 0.0))
        stats.intelligence = raw_stats.get("Int", raw_stats.get("Intelligence", 0.0))
        stats.req_strength = raw_stats.get("ReqStr", 0.0)
        stats.req_dexterity = raw_stats.get("ReqDex", 0.0)
        stats.req_intelligence = raw_stats.get("ReqInt", 0.0)

        return stats

    def _extract_equipped_items(self, root: ET.Element) -> Dict[str, EquipmentItem]:
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

        active_set_id = items_root.attrib.get("activeItemSet", "1")
        target_item_set = None

        for item_set in items_root.findall("ItemSet"):
            if item_set.attrib.get("id") == active_set_id:
                target_item_set = item_set
                break

        if target_item_set is None:
            target_item_set = items_root.find("ItemSet") or items_root

        for slot_elem in target_item_set.findall("Slot"):
            slot_name = slot_elem.attrib.get("name")
            item_id = slot_elem.attrib.get("itemId")
            if slot_name and item_id and item_id in parsed_items_by_id:
                equipped[slot_name] = parsed_items_by_id[item_id]

        return equipped

    def _extract_passive_tree(self, root: ET.Element) -> PassiveTreeData:
        tree_data = PassiveTreeData()
        tree_node = root.find(".//Tree")
        if tree_node is None:
            return tree_data

        active_spec_id = tree_node.attrib.get("activeSpec", "1")
        spec = None
        
        for s in tree_node.findall("Spec"):
            if s.attrib.get("id") == active_spec_id:
                spec = s
                break
                
        if spec is None:
            spec = tree_node.find("Spec")

        if spec is not None:
            tree_data.unallocated_points = self._safe_int(spec.attrib.get("pointsUnused"), 0)
            
            nodes_attr = spec.attrib.get("nodes", "")
            if nodes_attr:
                tree_data.allocated_node_ids = [
                    int(n) for n in nodes_attr.split(",") if n.strip().isdigit()
                ]

        return tree_data

    def _extract_skill_groups(self, root: ET.Element) -> Tuple[str, List[SkillGroup]]:
        skills_root = root.find(".//Skills")
        if skills_root is None:
            return "Unknown Skill", []

        active_set_id = skills_root.attrib.get("mainActiveSkillSet", "1")
        target_skill_set = None

        for skill_set in skills_root.findall("SkillSet"):
            if skill_set.attrib.get("id") == active_set_id:
                target_skill_set = skill_set
                break

        if target_skill_set is None:
            target_skill_set = skills_root.find("SkillSet") or skills_root

        main_group_index = self._safe_int(target_skill_set.attrib.get("mainActiveSkill"), 1)

        groups: List[SkillGroup] = []
        main_skill_name = "Unknown Skill"

        for idx, skill_elem in enumerate(target_skill_set.findall("Skill"), start=1):
            is_enabled = skill_elem.attrib.get("enabled") != "false"
            if not is_enabled:
                continue

            is_main = (idx == main_group_index) or (skill_elem.attrib.get("mainActiveSkill") == "1")
            gems: List[GemItem] = []

            for gem_elem in skill_elem.findall("Gem"):
                gem_enabled = gem_elem.attrib.get("enabled") != "false"
                if not gem_enabled:
                    continue

                name = gem_elem.attrib.get("nameSpec") or gem_elem.attrib.get("skillId") or "Unknown Gem"
                gem_level = self._safe_int(gem_elem.attrib.get("level"), 1)
                quality = self._safe_int(gem_elem.attrib.get("quality"), 0)
                spirit = self._safe_int(gem_elem.attrib.get("spiritReservation"), 0)

                is_support = gem_elem.attrib.get("support") == "true" or "support" in name.lower()

                tags_attr = (
                    gem_elem.attrib.get("tags")
                    or gem_elem.attrib.get("types")
                    or gem_elem.attrib.get("supportsGems")
                    or ""
                )
                tags = [t.strip() for t in tags_attr.split(",") if t.strip()]

                gem_item = GemItem(
                    name=name,
                    item_class="Support Gem" if is_support else "Skill Gem",
                    rarity="Gem",
                    item_level=None,
                    raw_text=f"{name} (Lvl {gem_level})",
                    gem_level=gem_level,
                    quality=quality,
                    spirit_reservation=spirit,
                    tags=tags
                )
                gems.append(gem_item)

            if gems:
                label = skill_elem.attrib.get("label") or gems[0].name
                group = SkillGroup(label=label, is_main=is_main, gems=gems)
                groups.append(group)

                if is_main and main_skill_name == "Unknown Skill":
                    active_gem = next((g for g in gems if g.item_class != "Support Gem"), gems[0])
                    main_skill_name = active_gem.name

        if main_skill_name == "Unknown Skill" and groups and groups[0].gems:
            main_skill_name = groups[0].gems[0].name

        return main_skill_name, groups

    def _extract_character_details(self, root: ET.Element) -> Tuple[str, str, str, int]:
        build_node = root.find(".//Build")
        if build_node is not None:
            name = build_node.attrib.get("name") or root.attrib.get("name") or "Build PoB2"
            character_class = build_node.attrib.get("className") or "Unknown"
            ascendancy = build_node.attrib.get("ascendClassName") or ""
            level = self._safe_int(build_node.attrib.get("level"), 0)
            return name, character_class, ascendancy, level

        return "Build PoB2", "Unknown", "", 0

    def load_build(self) -> PoBBuild:
        root = self._load_xml_from_source()
        if root is None or root.tag is None:
            raise ValueError("El XML de PoB está vacío o no se pudo cargar.")

        name, character_class, ascendancy, level = self._extract_character_details(root)
        stats = self._extract_player_stats(root)
        equipped_items = self._extract_equipped_items(root)
        passive_tree = self._extract_passive_tree(root)
        main_skill_name, skill_groups = self._extract_skill_groups(root)

        return PoBBuild(
            character_name=name,
            character_class=character_class,
            ascendancy_name=ascendancy,
            level=level,
            main_skill_name=main_skill_name,
            stats=stats,
            passive_tree=passive_tree,
            equipped_items=equipped_items,
            skill_groups=skill_groups
        )


class PoBParser(PoBLoader):
    """Parser principal compatible con integración de contexto de usuario."""

    def parse(self, payload: str | Path) -> PoBBuild:
        return PoBLoader(payload).load_build()

    def update_user_context(self, context_json_path: str | Path, source_payload: str | Path) -> Tuple[PoBBuild, dict]:
        build = self.parse(source_payload)
        path = Path(context_json_path)

        context = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    context = json.load(f)
            except json.JSONDecodeError:
                context = {}

        context["character_name"] = build.character_name
        context["character_class"] = build.character_class
        context["ascendancy"] = build.ascendancy_name
        context["level"] = build.level
        
        if isinstance(source_payload, str) and self._looks_like_encoded_payload(source_payload):
            context["pob_link"] = source_payload

        context["last_updated"] = datetime.now(timezone.utc).isoformat()

        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
        temp_path.replace(path)

        return build, context