"""Evaluación preliminar de mejoras de equipo para builds de PoE 2."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from integrations.pob_parser import PoBBuild
    from vision.item_parser import EquipmentItem, GemItem


@dataclass
class RecommendationEngine:
    """Compara un objeto nuevo con el equipo actual de un personaje."""

    build: PoBBuild
    resistance_cap: float = 75.0

    _RESISTANCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%?\s*"
        r"(?:to\s+)?(?P<resistance>fire|cold|lightning|chaos)\s+resistance",
        re.IGNORECASE,
    )
    _ALL_ELEMENTAL_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%?\s*"
        r"(?:to\s+)?all\s+elemental\s+resistances",
        re.IGNORECASE,
    )
    _SPANISH_RESISTANCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%?\s*"
        r"(?:a\s+la\s+resistencia\s+a\s+|a\s+la\s+resistencia\s+|a\s+)?"
        r"(?P<resistance>fuego|frio|frío|rayos|caos)",
        re.IGNORECASE,
    )
    _MAX_LIFE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*(?:to\s+)?maximum\s+life",
        re.IGNORECASE,
    )
    _ENERGY_SHIELD_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*(?:to\s+)?maximum\s+energy\s+shield",
        re.IGNORECASE,
    )
    _INCREASED_ENERGY_SHIELD_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+energy\s+shield",
        re.IGNORECASE,
    )
    _ADDED_DAMAGE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"adds\s+(?P<minimum>\d+(?:\.\d+)?)\s+to\s+(?P<maximum>\d+(?:\.\d+)?)\s+"
        r"(?P<damage>physical|fire|cold|lightning|chaos)\s+damage",
        re.IGNORECASE,
    )
    _INCREASED_SPEED_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+"
        r"(?P<speed>attack|cast)\s+speed",
        re.IGNORECASE,
    )
    _MOVEMENT_SPEED_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+movement\s+speed",
        re.IGNORECASE,
    )
    _LIFE_REGEN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*(?:to\s+)?life\s+regeneration\s+per\s+second",
        re.IGNORECASE,
    )
    _LIFE_REGEN_PERCENT_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+life\s+regeneration\s+rate",
        re.IGNORECASE,
    )
    _MANA_REGEN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*(?:to\s+)?mana\s+regeneration\s+per\s+second",
        re.IGNORECASE,
    )
    _MANA_REGEN_PERCENT_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+mana\s+regeneration\s+rate",
        re.IGNORECASE,
    )
    _DAMAGE_OVER_TIME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+damage\s+over\s+time",
        re.IGNORECASE,
    )
    _ELEMENTAL_DAMAGE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+elemental\s+damage",
        re.IGNORECASE,
    )
    _AILMENT_DAMAGE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+increased\s+"
        r"(?P<ailment>ignite|poison|chill)(?:\s+damage|\s+effect)",
        re.IGNORECASE,
    )
    _CRITICAL_CHANCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+(?:(?:to|increased)\s+)?"
        r"critical\s+strike\s+chance",
        re.IGNORECASE,
    )
    _CRITICAL_MULTIPLIER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)%\s+(?:(?:to|increased)\s+)?"
        r"critical\s+(?:strike\s+)?damage\s+bonus",
        re.IGNORECASE,
    )

    def evaluate_item_upgrade(
        self, slot_name: str, new_item: EquipmentItem
    ) -> Dict[str, object]:
        """Devuelve requisitos, cambios de resistencias y alertas de caps."""
        current_item = self.build.equipped_items.get(slot_name)
        requirements = self._evaluate_requirements(new_item)
        resistance_delta = self._calculate_resistance_delta(current_item, new_item)
        projected_resistances = self._project_resistances(resistance_delta)
        cap_alert = {
            resistance: value < self.resistance_cap
            for resistance, value in projected_resistances.items()
        }
        stat_delta = self._calculate_stat_delta(current_item, new_item)
        score = self._calculate_upgrade_score(
            slot_name,
            resistance_delta,
            projected_resistances,
            stat_delta,
            requirements,
        )

        return {
            "slot_name": slot_name,
            "new_item": new_item,
            "current_item": current_item,
            "requirements": requirements,
            "resistance_delta": resistance_delta,
            "projected_resistances": projected_resistances,
            "cap_alert": cap_alert,
            "is_upgrade_usable": bool(requirements["met"]),
            "has_resistance_cap_alert": any(cap_alert.values()),
            "stat_delta": stat_delta,
            "defensive_delta": {
                "life": stat_delta["life"],
                "energy_shield": stat_delta["energy_shield"],
                "movement_speed": stat_delta["movement_speed"],
                "life_regeneration": stat_delta["life_regeneration"],
                "life_regeneration_percent": stat_delta["life_regeneration_percent"],
                "mana_regeneration": stat_delta["mana_regeneration"],
                "mana_regeneration_percent": stat_delta["mana_regeneration_percent"],
            },
            "offensive_delta": {
                key: value for key, value in stat_delta.items()
                if key in {
                    "added_damage", "attack_speed", "cast_speed",
                    "critical_chance", "critical_multiplier", "damage_over_time",
                    "elemental_damage", "ignite_damage", "poison_damage", "chill_effect",
                    "combined_dps", "hit_dps",
                }
            },
            "score": score,
            "is_strict_upgrade": score > 0 and bool(requirements["met"]),
        }

    def _evaluate_requirements(self, item: EquipmentItem) -> Dict[str, object]:
        stats = self.build.stats
        required = {
            "level": item.requirements.get("level", 0),
            "strength": item.requirements.get("str", 0),
            "dexterity": item.requirements.get("dex", 0),
            "intelligence": item.requirements.get("int", 0),
        }
        available = {
            "level": self.build.level,
            "strength": stats.strength,
            "dexterity": stats.dexterity,
            "intelligence": stats.intelligence,
        }
        met = {
            name: available[name] >= value for name, value in required.items()
        }
        return {
            "met": all(met.values()),
            "required": required,
            "available": available,
            "checks": met,
            "missing": [name for name, passed in met.items() if not passed],
        }

    def _calculate_stat_delta(
        self,
        current_item: Optional[EquipmentItem],
        new_item: EquipmentItem,
    ) -> Dict[str, float]:
        current = self._extract_item_stats(current_item)
        new = self._extract_item_stats(new_item)
        baseline_es = float(getattr(self.build.stats, "energy_shield", 0.0))
        return {
            "life": new["life"] - current["life"],
            "energy_shield": (
                new["energy_shield"] - current["energy_shield"]
                + baseline_es
                * (new["increased_energy_shield"] - current["increased_energy_shield"])
                / 100.0
            ),
            "energy_shield_percent": (
                new["increased_energy_shield"]
                - current["increased_energy_shield"]
            ),
            "added_damage": new["added_damage"] - current["added_damage"],
            "attack_speed": new["attack_speed"] - current["attack_speed"],
            "cast_speed": new["cast_speed"] - current["cast_speed"],
            "movement_speed": new["movement_speed"] - current["movement_speed"],
            "life_regeneration": new["life_regeneration"] - current["life_regeneration"],
            "life_regeneration_percent": (
                new["life_regeneration_percent"] - current["life_regeneration_percent"]
            ),
            "mana_regeneration": new["mana_regeneration"] - current["mana_regeneration"],
            "mana_regeneration_percent": (
                new["mana_regeneration_percent"] - current["mana_regeneration_percent"]
            ),
            "critical_chance": new["critical_chance"] - current["critical_chance"],
            "critical_multiplier": (
                new["critical_multiplier"] - current["critical_multiplier"]
            ),
            "damage_over_time": new["damage_over_time"] - current["damage_over_time"],
            "elemental_damage": new["elemental_damage"] - current["elemental_damage"],
            "ignite_damage": new["ignite_damage"] - current["ignite_damage"],
            "poison_damage": new["poison_damage"] - current["poison_damage"],
            "chill_effect": new["chill_effect"] - current["chill_effect"],
            "combined_dps": new.get("combined_dps", 0.0) - current.get("combined_dps", 0.0),
            "hit_dps": new.get("hit_dps", 0.0) - current.get("hit_dps", 0.0),
        }

    @classmethod
    def _extract_item_stats(
        cls, item: Optional[EquipmentItem]
    ) -> Dict[str, float]:
        values = {
            "life": 0.0,
            "energy_shield": 0.0,
            "increased_energy_shield": 0.0,
            "added_damage": 0.0,
            "attack_speed": 0.0,
            "cast_speed": 0.0,
            "movement_speed": 0.0,
            "life_regeneration": 0.0,
            "life_regeneration_percent": 0.0,
            "mana_regeneration": 0.0,
            "mana_regeneration_percent": 0.0,
            "critical_chance": 0.0,
            "critical_multiplier": 0.0,
            "damage_over_time": 0.0,
            "elemental_damage": 0.0,
            "ignite_damage": 0.0,
            "poison_damage": 0.0,
            "chill_effect": 0.0,
            "combined_dps": 0.0,
            "hit_dps": 0.0,
        }
        if item is None:
            return values

        # Soporte para campos directos si el parser ya los inyecta en el objeto
        for dps_key in ("combined_dps", "hit_dps"):
            if hasattr(item, dps_key):
                values[dps_key] = float(getattr(item, dps_key, 0.0) or 0.0)

        for modifier in [*item.implicit_mods, *item.explicit_mods]:
            life = cls._MAX_LIFE_PATTERN.search(modifier)
            if life:
                values["life"] += float(life.group("value"))

            energy_shield = cls._ENERGY_SHIELD_PATTERN.search(modifier)
            if energy_shield:
                values["energy_shield"] += float(energy_shield.group("value"))

            increased_es = cls._INCREASED_ENERGY_SHIELD_PATTERN.search(modifier)
            if increased_es:
                values["increased_energy_shield"] += float(increased_es.group("value"))

            for damage in cls._ADDED_DAMAGE_PATTERN.finditer(modifier):
                values["added_damage"] += (
                    float(damage.group("minimum"))
                    + float(damage.group("maximum"))
                ) / 2.0

            speed = cls._INCREASED_SPEED_PATTERN.search(modifier)
            if speed:
                values[f"{speed.group('speed').lower()}_speed"] += float(speed.group("value"))

            movement_speed = cls._MOVEMENT_SPEED_PATTERN.search(modifier)
            if movement_speed:
                values["movement_speed"] += float(movement_speed.group("value"))

            for pattern, key in (
                (cls._LIFE_REGEN_PATTERN, "life_regeneration"),
                (cls._LIFE_REGEN_PERCENT_PATTERN, "life_regeneration_percent"),
                (cls._MANA_REGEN_PATTERN, "mana_regeneration"),
                (cls._MANA_REGEN_PERCENT_PATTERN, "mana_regeneration_percent"),
                (cls._DAMAGE_OVER_TIME_PATTERN, "damage_over_time"),
                (cls._ELEMENTAL_DAMAGE_PATTERN, "elemental_damage"),
            ):
                match = pattern.search(modifier)
                if match:
                    values[key] += float(match.group("value"))

            ailment = cls._AILMENT_DAMAGE_PATTERN.search(modifier)
            if ailment:
                ailment_name = ailment.group("ailment").lower()
                target_key = "chill_effect" if ailment_name == "chill" else f"{ailment_name}_damage"
                values[target_key] += float(ailment.group("value"))

            critical_chance = cls._CRITICAL_CHANCE_PATTERN.search(modifier)
            if critical_chance:
                values["critical_chance"] += float(critical_chance.group("value"))

            critical_multiplier = cls._CRITICAL_MULTIPLIER_PATTERN.search(modifier)
            if critical_multiplier:
                values["critical_multiplier"] += float(critical_multiplier.group("value"))

        return values

    def _calculate_upgrade_score(
        self,
        slot_name: str,
        resistance_delta: Dict[str, float],
        projected_resistances: Dict[str, float],
        stat_delta: Dict[str, float],
        requirements: Dict[str, object],
    ) -> float:
        """Calcula una puntuación transparente de supervivencia y daño."""
        if not bool(requirements["met"]):
            return -1000.0

        resistance_score = sum(
            delta for name, delta in resistance_delta.items()
            if projected_resistances[name] < self.resistance_cap and delta > 0
        )
        life_score = stat_delta.get("life", 0) / 10.0
        energy_shield_score = stat_delta.get("energy_shield", 0) / 10.0
        mobility_score = stat_delta.get("movement_speed", 0) * (1.5 if "boot" in slot_name.lower() else 0.75)
        sustain_score = (
            stat_delta.get("life_regeneration", 0) / 5.0
            + stat_delta.get("life_regeneration_percent", 0) / 5.0
            + stat_delta.get("mana_regeneration", 0) / 5.0
            + stat_delta.get("mana_regeneration_percent", 0) / 5.0
        )
        
        dps_delta = stat_delta.get("combined_dps") or stat_delta.get("hit_dps", 0.0)
        if dps_delta != 0:
            damage_score = dps_delta / 10.0
        else:
            damage_score = (
                stat_delta.get("added_damage", 0) / 10.0
                + stat_delta.get("attack_speed", 0)
                + stat_delta.get("cast_speed", 0)
                + stat_delta.get("critical_chance", 0)
                + stat_delta.get("critical_multiplier", 0) / 10.0
            )
            if self._build_archetypes() & {"dot", "ignite", "poison", "chill"}:
                damage_score += (
                    stat_delta.get("damage_over_time", 0) / 5.0
                    + stat_delta.get("ignite_damage", 0) / 5.0
                    + stat_delta.get("poison_damage", 0) / 5.0
                    + stat_delta.get("chill_effect", 0) / 5.0
                )
            if self._build_archetypes() & {"fire", "cold", "lightning"}:
                damage_score += stat_delta.get("elemental_damage", 0) / 5.0

        return round(
            resistance_score + life_score + energy_shield_score
            + mobility_score + sustain_score + damage_score,
            2,
        )

    def evaluate_gem_change(
        self, new_gem: GemItem, replacing_gem: Optional[GemItem] = None
    ) -> Dict[str, object]:
        """Evalúa espíritu, atributos y compatibilidad básica de una gema."""
        spirit_available = self._spirit_unreserved()
        replacing_spirit = self._gem_spirit_reservation(replacing_gem)
        new_spirit = self._gem_spirit_reservation(new_gem)
        spirit_balance = spirit_available + replacing_spirit - new_spirit
        requirements = self._evaluate_requirements(new_gem)
        tag_evaluation = self._evaluate_gem_tags(new_gem)
        benefit = self._evaluate_gem_benefit(
            new_gem,
            requirements_met=bool(requirements["met"]),
            spirit_overflow=spirit_balance < 0,
            tag_evaluation=tag_evaluation,
        )

        return {
            "new_gem": new_gem,
            "replacing_gem": replacing_gem,
            "spirit_available": spirit_available,
            "replacing_spirit": replacing_spirit,
            "new_spirit": new_spirit,
            "spirit_balance": spirit_balance,
            "spirit_overflow": spirit_balance < 0,
            "requirements": requirements,
            "tag_evaluation": tag_evaluation,
            "is_beneficial": benefit["is_beneficial"],
            "reason": benefit["reason"],
            "benefit": benefit,
            "is_usable": bool(requirements["met"] and spirit_balance >= 0),
        }

    def _spirit_unreserved(self) -> float:
        stats = self.build.stats
        spirit_unreserved = getattr(stats, "spirit_unreserved", None)
        spirit_total = float(getattr(stats, "spirit_total", 0.0))
        spirit_reserved = float(getattr(stats, "spirit_reserved", 0.0))
        calculated_unreserved = max(0.0, spirit_total - spirit_reserved)

        if spirit_unreserved is None:
            return calculated_unreserved

        explicit_unreserved = float(spirit_unreserved)
        if explicit_unreserved <= 0.0 and calculated_unreserved > 0.0:
            return calculated_unreserved
        return max(0.0, explicit_unreserved)

    @staticmethod
    def _gem_spirit_reservation(gem: Optional[GemItem]) -> float:
        if gem is None:
            return 0.0
        return float(getattr(gem, "spirit_reservation", 0) or 0)

    def _evaluate_gem_tags(self, gem: GemItem) -> Dict[str, object]:
        tags = [tag.strip() for tag in gem.tags if tag.strip()]
        normalized_tags = {self._normalize_tag(tag) for tag in tags}
        build_context = self._build_tag_context()
        warnings: List[str] = []

        if "minion" in normalized_tags and not (
            {"minion", "minions"} & build_context
        ):
            warnings.append(
                "La gema tiene el tag Minion, pero no se detectan minions en la build."
            )

        return {
            "tags": tags,
            "compatible": not warnings,
            "warnings": warnings,
        }

    def _evaluate_gem_benefit(
        self,
        gem: GemItem,
        requirements_met: bool,
        spirit_overflow: bool,
        tag_evaluation: Dict[str, object],
    ) -> Dict[str, object]:
        """Estima si la gema aporta valor según el arquetipo detectado."""
        if not requirements_met:
            return {
                "is_beneficial": False,
                "reason": "La gema no puede utilizarse porque faltan requisitos de atributos o nivel.",
            }

        if spirit_overflow:
            return {
                "is_beneficial": False,
                "reason": "La gema supera el Espíritu disponible para la build.",
            }

        if not bool(tag_evaluation["compatible"]):
            warnings = tag_evaluation["warnings"]
            return {
                "is_beneficial": False,
                "reason": str(warnings[0]) if warnings else "Los tags de la gema no encajan con la build.",
            }

        gem_tags = {self._normalize_tag(tag) for tag in gem.tags}
        build_archetypes = self._build_archetypes()
        damage_tags = {
            "fire", "cold", "lightning", "chaos", "physical",
            "attack", "spell", "minion",
        }
        matching_tags = sorted((gem_tags & damage_tags) & build_archetypes)
        if matching_tags:
            return {
                "is_beneficial": True,
                "reason": f"Aporta daño o sinergia con el arquetipo de la build: {', '.join(matching_tags)}.",
            }

        if gem.spirit_reservation > 0 and {"aura", "buff", "reservation"} & gem_tags:
            return {
                "is_beneficial": True,
                "reason": "Aporta una utilidad de aura o buff y cabe en el Espíritu disponible.",
            }

        conflicting_tags = sorted(
            (gem_tags & damage_tags)
            - build_archetypes
            & {"fire", "cold", "lightning", "chaos", "physical"}
        )
        if conflicting_tags and build_archetypes & {
            "fire", "cold", "lightning", "chaos", "physical"
        }:
            return {
                "is_beneficial": False,
                "reason": f"El tipo de daño {', '.join(conflicting_tags)} no coincide con el enfoque elemental o físico detectado.",
            }

        return {
            "is_beneficial": False,
            "reason": "No se detecta una sinergia clara de daño o utilidad con la build.",
        }

    def _build_archetypes(self) -> Set[str]:
        """Extrae arquetipos de nombres, tags de gemas y nodos relevantes."""
        values: List[str] = [self.build.main_skill_name]
        for group in self.build.skill_groups:
            for gem in group.gems:
                values.extend([gem.name, *gem.tags])

        passive_tree = self.build.passive_tree
        values.extend(passive_tree.active_keystones)
        values.extend(passive_tree.active_notables)
        context = " ".join(self._normalize_tag(value) for value in values)
        archetypes: Set[str] = set()
        for archetype in (
            "fire", "cold", "ice", "lightning", "chaos", "poison", "physical",
            "dot", "ignite", "chill",
            "attack", "spell", "minion", "melee", "ranged", "projectile",
        ):
            if archetype in context:
                archetypes.add("cold" if archetype == "ice" else archetype)
        return archetypes

    def _build_tag_context(self) -> Set[str]:
        context = {self._normalize_tag(self.build.main_skill_name)}
        for group in self.build.skill_groups:
            for gem in group.gems:
                context.add(self._normalize_tag(gem.name))
                context.update(self._normalize_tag(tag) for tag in gem.tags)
        return context

    @staticmethod
    def _normalize_tag(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return normalized.lower().strip()

    def _calculate_resistance_delta(
        self,
        current_item: Optional[EquipmentItem],
        new_item: EquipmentItem,
    ) -> Dict[str, float]:
        current = self._extract_resistances(current_item)
        new = self._extract_resistances(new_item)
        return {resistance: new[resistance] - current[resistance] for resistance in current}

    def _project_resistances(self, delta: Dict[str, float]) -> Dict[str, float]:
        stats = self.build.stats
        current = {
            "fire": stats.fire_resistance,
            "cold": stats.cold_resistance,
            "lightning": stats.lightning_resistance,
            "chaos": stats.chaos_resistance,
        }
        return {resistance: current[resistance] + change for resistance, change in delta.items()}

    @classmethod
    def _extract_resistances(
        cls, item: Optional[EquipmentItem]
    ) -> Dict[str, float]:
        values = {"fire": 0.0, "cold": 0.0, "lightning": 0.0, "chaos": 0.0}
        if item is None:
            return values

        for modifier in [*item.implicit_mods, *item.explicit_mods]:
            for match in cls._RESISTANCE_PATTERN.finditer(modifier):
                resistance = match.group("resistance").lower()
                values[resistance] += float(match.group("value"))

            for match in cls._SPANISH_RESISTANCE_PATTERN.finditer(modifier):
                resistance = cls._normalize_spanish_resistance(match.group("resistance"))
                values[resistance] += float(match.group("value"))

            all_elemental = cls._ALL_ELEMENTAL_PATTERN.search(modifier)
            if all_elemental:
                value = float(all_elemental.group("value"))
                for resistance in ("fire", "cold", "lightning"):
                    values[resistance] += value

        return values

    @staticmethod
    def _normalize_spanish_resistance(value: str) -> str:
        normalized = value.lower()
        return {
            "fuego": "fire",
            "frio": "cold",
            "frío": "cold",
            "rayos": "lightning",
            "caos": "chaos",
        }[normalized]