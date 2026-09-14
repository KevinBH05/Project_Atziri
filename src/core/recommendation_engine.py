"""Evaluación preliminar de mejoras de equipo para builds de PoE 2."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from integrations.pob_parser import PoBBuild
    from listener.item_parser import EquipmentItem, GemItem


from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class RecommendationAnalysis:
    """Resultado completo del análisis comparativo de un equipamiento."""
    slot_name: str
    new_item: EquipmentItem
    current_item: Optional[EquipmentItem]
    requirements: Dict[str, bool | int]      # ej: {"met": True, "req_str": 120}
    resistance_delta: Dict[str, float]
    projected_resistances: Dict[str, float]
    cap_alert: Dict[str, bool]
    is_upgrade_usable: bool
    has_resistance_cap_alert: bool
    stat_delta: Dict[str, float]             # todas las deltas numéricas
    defensive_delta: Dict[str, float]
    offensive_delta: Dict[str, float]
    score: float
    is_strict_upgrade: bool

@dataclass
class RecommendationEngine:
    """Compara un objeto nuevo con el equipo actual usando el estado en RAM."""

    build: PoBBuild
    resistance_cap: float = 75.0

    def evaluate_replacement(
        self, slot_name: str, new_item: EquipmentItem
    ) -> RecommendationAnalysis:
        """Calcula el impacto numérico y defensivo/ofensivo de reemplazar el ítem de un slot."""
        current_item = self.build.equipped_items.get(slot_name)
        
        # 1. Validar requisitos de nivel/atributos
        requirements = self._evaluate_requirements(new_item)
        
        # 2. Calcular deltas de resistencias y proyección frente al cap (75%)
        resistance_delta = self._calculate_resistance_delta(current_item, new_item)
        projected_resistances = self._project_resistances(resistance_delta)
        
        cap_alert = {
            res: val < self.resistance_cap
            for res, val in projected_resistances.items()
        }
        
        # 3. Extraer deltas generales de atributos, vida, ES y DPS
        stat_delta = self._calculate_stat_delta(current_item, new_item)
        
        # 4. Agrupar métricas defensivas y ofensivas
        defensive_keys = {
            "life", "energy_shield", "movement_speed",
            "life_regeneration", "life_regeneration_percent",
            "mana_regeneration", "mana_regeneration_percent",
        }
        offensive_keys = {
            "added_damage", "attack_speed", "cast_speed",
            "critical_chance", "critical_multiplier", "damage_over_time",
            "elemental_damage", "ignite_damage", "poison_damage", "chill_effect",
            "combined_dps", "hit_dps",
        }
        
        defensive_delta = {k: v for k, v in stat_delta.items() if k in defensive_keys}
        offensive_delta = {k: v for k, v in stat_delta.items() if k in offensive_keys}

        # 5. Calcular puntuación del upgrade
        score = self._calculate_upgrade_score(
            slot_name,
            resistance_delta,
            projected_resistances,
            stat_delta,
            requirements,
        )

        # 6. Generar notas contextuales para que el LLM las interprete rápido
        summary_notes: List[str] = []
        if not requirements["met"]:
            summary_notes.append("Advertencia: No cumples los requisitos de atributos o nivel para equipar este objeto.")
        if any(cap_alert.values()):
            uncovered = [res for res, is_below in cap_alert.items() if is_below]
            summary_notes.append(f"Alerta de Resistencia: El cambio te deja por debajo del cap ({self.resistance_cap}%) en: {', '.join(uncovered)}.")
        if score > 0:
            summary_notes.append("Mejora General: El objeto supera en estadísticas globales al equipo actual.")

        return RecommendationAnalysis(
            slot_name=slot_name,
            new_item=new_item,
            current_item=current_item,
            requirements=requirements,
            resistance_delta=resistance_delta,
            projected_resistances=projected_resistances,
            cap_alert=cap_alert,
            is_upgrade_usable=bool(requirements["met"]),
            has_resistance_cap_alert=any(cap_alert.values()),
            stat_delta=stat_delta,
            defensive_delta=defensive_delta,
            offensive_delta=offensive_delta,
            score=score,
            is_strict_upgrade=score > 0 and bool(requirements["met"]),
            summary_notes=summary_notes,
        )

    def evaluate_item_upgrade(
        self, slot_name: str, new_item: EquipmentItem
    ) -> RecommendationAnalysis:
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

        defensive_keys = {
            "life", "energy_shield", "movement_speed",
            "life_regeneration", "life_regeneration_percent",
            "mana_regeneration", "mana_regeneration_percent",
        }
        
        offensive_keys = {
            "added_damage", "attack_speed", "cast_speed",
            "critical_chance", "critical_multiplier", "damage_over_time",
            "elemental_damage", "ignite_damage", "poison_damage", "chill_effect",
            "combined_dps", "hit_dps",
        }

        return RecommendationAnalysis(
            slot_name=slot_name,
            new_item=new_item,
            current_item=current_item,
            requirements=requirements,
            resistance_delta=resistance_delta,
            projected_resistances=projected_resistances,
            cap_alert=cap_alert,
            is_upgrade_usable=bool(requirements["met"]),
            has_resistance_cap_alert=any(cap_alert.values()),
            stat_delta=stat_delta,
            defensive_delta={k: v for k, v in stat_delta.items() if k in defensive_keys},
            offensive_delta={k: v for k, v in stat_delta.items() if k in offensive_keys},
            score=score,
            is_strict_upgrade=score > 0 and bool(requirements["met"]),
        )

    def _evaluate_requirements(self, item: EquipmentItem) -> Dict[str, bool | List[str] | Dict[str, int | bool]]:
        stats = self.build.stats
        
        # Extraer requisitos aceptando tanto nombres cortos como largos
        reqs = item.requirements or {}
        required = {
            "level": int(reqs.get("level") or reqs.get("lvl") or 0),
            "strength": int(reqs.get("str") or reqs.get("strength") or 0),
            "dexterity": int(reqs.get("dex") or reqs.get("dexterity") or 0),
            "intelligence": int(reqs.get("int") or reqs.get("intelligence") or 0),
        }
        
        available = {
            "level": int(self.build.level),
            "strength": int(stats.strength),
            "dexterity": int(stats.dexterity),
            "intelligence": int(stats.intelligence),
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
        """Calcula las diferencias absolutas de estadísticas entre dos ítems."""
        current = self._extract_item_stats(current_item)
        new = self._extract_item_stats(new_item)
        
        baseline_es = float(getattr(self.build.stats, "energy_shield", 0.0))

        # Delta de Energy Shield plano del ítem
        es_flat_delta = new.get("energy_shield", 0.0) - current.get("energy_shield", 0.0)
        
        # Delta del % aumentado aplicado a la base actual del personaje
        es_pct_delta = (
            new.get("increased_energy_shield", 0.0) - current.get("increased_energy_shield", 0.0)
        )
        es_scaled_from_pct = (baseline_es * es_pct_delta) / 100.0

        return {
            "life": new.get("life", 0.0) - current.get("life", 0.0),
            "energy_shield": es_flat_delta + es_scaled_from_pct,
            "energy_shield_percent": es_pct_delta,
            "added_damage": new.get("added_damage", 0.0) - current.get("added_damage", 0.0),
            "attack_speed": new.get("attack_speed", 0.0) - current.get("attack_speed", 0.0),
            "cast_speed": new.get("cast_speed", 0.0) - current.get("cast_speed", 0.0),
            "movement_speed": new.get("movement_speed", 0.0) - current.get("movement_speed", 0.0),
            "life_regeneration": new.get("life_regeneration", 0.0) - current.get("life_regeneration", 0.0),
            "life_regeneration_percent": (
                new.get("life_regeneration_percent", 0.0) - current.get("life_regeneration_percent", 0.0)
            ),
            "mana_regeneration": new.get("mana_regeneration", 0.0) - current.get("mana_regeneration", 0.0),
            "mana_regeneration_percent": (
                new.get("mana_regeneration_percent", 0.0) - current.get("mana_regeneration_percent", 0.0)
            ),
            "critical_chance": new.get("critical_chance", 0.0) - current.get("critical_chance", 0.0),
            "critical_multiplier": (
                new.get("critical_multiplier", 0.0) - current.get("critical_multiplier", 0.0)
            ),
            "damage_over_time": new.get("damage_over_time", 0.0) - current.get("damage_over_time", 0.0),
            "elemental_damage": new.get("elemental_damage", 0.0) - current.get("elemental_damage", 0.0),
            "ignite_damage": new.get("ignite_damage", 0.0) - current.get("ignite_damage", 0.0),
            "poison_damage": new.get("poison_damage", 0.0) - current.get("poison_damage", 0.0),
            "chill_effect": new.get("chill_effect", 0.0) - current.get("chill_effect", 0.0),
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

        # 1. Extraer stats directas del objeto si existen
        for dps_key in ("combined_dps", "hit_dps", "energy_shield", "life"):
            if hasattr(item, dps_key):
                val = float(getattr(item, dps_key, 0.0) or 0.0)
                if val > 0:
                    values[dps_key] = val

        # 2. Parsear modificadores implícitos y explícitos
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

            # Validación segura para ataque / hechizo
            speed = cls._INCREASED_SPEED_PATTERN.search(modifier)
            if speed:
                speed_type = speed.group("speed").lower()
                key = f"{speed_type}_speed"
                if key in values:
                    values[key] += float(speed.group("value"))

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

            # Evitar KeyError en alteraciones de estado no contempladas
            ailment = cls._AILMENT_DAMAGE_PATTERN.search(modifier)
            if ailment:
                ailment_name = ailment.group("ailment").lower()
                target_key = "chill_effect" if ailment_name == "chill" else f"{ailment_name}_damage"
                if target_key in values:
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
        spirit_available = float(self._spirit_unreserved() or 0.0)
        
        # Asegurar que si reemplaza a None devuelva 0.0 sin romper el cálculo
        replacing_spirit = float(self._gem_spirit_reservation(replacing_gem) or 0.0) if replacing_gem else 0.0
        new_spirit = float(self._gem_spirit_reservation(new_gem) or 0.0)
        
        # Espíritu restante tras quitar la vieja y equipar la nueva
        spirit_balance = spirit_available + replacing_spirit - new_spirit
        
        requirements = self._evaluate_requirements(new_gem)
        tag_evaluation = self._evaluate_gem_tags(new_gem)
        
        benefit = self._evaluate_gem_benefit(
            new_gem,
            requirements_met=bool(requirements.get("met", False)),
            spirit_overflow=spirit_balance < 0,
            tag_evaluation=tag_evaluation,
        )

        is_usable = bool(requirements.get("met", False) and spirit_balance >= 0)

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
            "is_beneficial": benefit.get("is_beneficial", False),
            "reason": benefit.get("reason", ""),
            "benefit": benefit,
            "is_usable": is_usable,
        }

    def _spirit_unreserved(self) -> float:
        """Calcula el espíritu libre garantizando un fallback si el dato del XML es inconsistente."""
        stats = self.build.stats
        spirit_total = float(getattr(stats, "spirit_total", 0.0) or 0.0)
        spirit_reserved = float(getattr(stats, "spirit_reserved", 0.0) or 0.0)
        calculated_unreserved = max(0.0, spirit_total - spirit_reserved)

        explicit_unreserved = getattr(stats, "spirit_unreserved", None)
        
        if explicit_unreserved is None:
            return calculated_unreserved

        explicit_unreserved = float(explicit_unreserved or 0.0)
        
        # Si el valor explícito indica 0 pero matemáticamente hay sobrante, usamos el calculado
        if explicit_unreserved <= 0.0 and calculated_unreserved > 0.0:
            return calculated_unreserved
            
        return max(0.0, explicit_unreserved)

    @staticmethod
    def _gem_spirit_reservation(gem: Optional[GemItem]) -> float:
        """Retorna la reserva de Espíritu de una gema de forma segura."""
        if gem is None:
            return 0.0
        return max(0.0, float(getattr(gem, "spirit_reservation", 0.0) or 0.0))

    def _evaluate_gem_tags(self, gem: GemItem) -> Dict[str, object]:
        """Evalúa las etiquetas de la gema contra el contexto de la build."""
        raw_tags = getattr(gem, "tags", []) or []
        tags = [tag.strip() for tag in raw_tags if tag and tag.strip()]
        normalized_tags = {self._normalize_tag(tag) for tag in tags}
        build_context = self._build_tag_context()
        warnings: List[str] = []

        # 1. Alerta de Minion en builds sin esbirros
        if "minion" in normalized_tags and not ({"minion", "minions"} & build_context):
            warnings.append(
                "La gema tiene la etiqueta 'Minion', pero la build no utiliza habilidades de esbirros."
            )

        # 2. Ejemplo de extensión: Alerta de Totem/Trap/Mine si la build no los soporta
        if {"totem", "trap", "mine"} & normalized_tags and not (
            {"totem", "trap", "mine"} & build_context
        ):
            warnings.append(
                "La gema requiere soporte de Totem/Trap/Mine, pero la build no está orientada a esta mecánica."
            )

        return {
            "tags": tags,
            "compatible": len(warnings) == 0,
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

        if not bool(tag_evaluation.get("compatible", False)):
            raw_warnings = tag_evaluation.get("warnings", [])
            warnings = raw_warnings if isinstance(raw_warnings, list) else []
            return {
                "is_beneficial": False,
                "reason": str(warnings[0]) if warnings else "Las etiquetas de la gema no encajan con la build.",
            }

        # Extracción defensiva de atributos de la gema
        raw_tags = getattr(gem, "tags", []) or []
        gem_tags = {self._normalize_tag(tag) for tag in raw_tags if tag}
        spirit_reservation = float(getattr(gem, "spirit_reservation", 0.0) or 0.0)

        build_archetypes = self._build_archetypes()
        damage_tags = {
            "fire", "cold", "lightning", "chaos", "physical",
            "attack", "spell", "minion",
        }
        
        # 1. Sinergia directa de daño o tipo de habilidad
        matching_tags = sorted((gem_tags & damage_tags) & build_archetypes)
        if matching_tags:
            return {
                "is_beneficial": True,
                "reason": f"Aporta daño o sinergia con el arquetipo de la build: {', '.join(matching_tags)}.",
            }

        # 2. Utilidades de aura, buff o reserva de Espíritu
        if spirit_reservation > 0 or {"aura", "buff", "reservation", "banner", "herald"} & gem_tags:
            return {
                "is_beneficial": True,
                "reason": "Aporta una utilidad de aura o potenciador y encaja en la build.",
            }

        # 3. Utilidad activa (Movimiento, Maldiciones, Marcas, Guardias)
        utility_tags = {"travel", "movement", "curse", "mark", "guard", "utility", "warcry"}
        if gem_tags & utility_tags:
            return {
                "is_beneficial": True,
                "reason": "Aporta movilidad, control o capacidad defensiva activa a la build.",
            }

        # 4. Conflicto elemental directo
        elemental_types = {"fire", "cold", "lightning", "chaos", "physical"}
        conflicting_tags = sorted((gem_tags & elemental_types) - build_archetypes)
        
        if conflicting_tags and (build_archetypes & elemental_types):
            return {
                "is_beneficial": False,
                "reason": f"El tipo de daño {', '.join(conflicting_tags)} entra en conflicto con el enfoque principal de la build.",
            }

        return {
            "is_beneficial": False,
            "reason": "No se detecta una sinergia clara de daño, utilidad o movilidad con la build.",
        }

    def _build_archetypes(self) -> Set[str]:
        """Extrae arquetipos de nombres, tags de gemas y nodos relevantes."""
        values: List[str] = []
        
        if self.build.main_skill_name:
            values.append(str(self.build.main_skill_name))

        # Lectura defensiva de grupos y gemas de la build
        for group in getattr(self.build, "skill_groups", []) or []:
            for gem in getattr(group, "gems", []) or []:
                if gem.name:
                    values.append(gem.name)
                
                raw_tags = getattr(gem, "tags", []) or []
                values.extend([str(t) for t in raw_tags if t])

        # Nodos del árbol pasivo
        passive_tree = getattr(self.build, "passive_tree", None)
        if passive_tree:
            values.extend(getattr(passive_tree, "active_keystones", []) or [])
            values.extend(getattr(passive_tree, "active_notables", []) or [])

        # Normalización del contexto global
        context = " ".join(self._normalize_tag(value) for value in values if value)
        
        archetypes: Set[str] = set()
        possible_archetypes = (
            "fire", "cold", "ice", "lightning", "chaos", "poison", "physical",
            "dot", "ignite", "chill",
            "attack", "spell", "minion", "melee", "ranged", "projectile",
        )
        
        for archetype in possible_archetypes:
            if archetype in context:
                # Mapeo de alias para estandarizar
                archetypes.add("cold" if archetype == "ice" else archetype)

        return archetypes

    @staticmethod
    def _normalize_tag(value: object) -> str:
        """Normaliza cadenas eliminando tildes, mayúsculas y espacios extra de forma segura."""
        if not value or not isinstance(value, str):
            return ""
        
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return normalized.lower().strip()

    def _calculate_resistance_delta(
        self,
        current_item: Optional[EquipmentItem],
        new_item: EquipmentItem,
    ) -> Dict[str, float]:
        """Calcula la diferencia neta de resistencias entre el objeto equipado y el nuevo."""
        current = self._extract_resistances(current_item)
        new = self._extract_resistances(new_item)
        
        # Lista canónica de resistencias en PoE 2
        res_types = ("fire", "cold", "lightning", "chaos")
        
        return {
            res: float(new.get(res, 0.0) or 0.0) - float(current.get(res, 0.0) or 0.0)
            for res in res_types
        }

    def _project_resistances(self, delta: Dict[str, float]) -> Dict[str, float]:
        """Proyecta los valores finales de resistencias sumando la diferencia (delta)."""
        stats = getattr(self.build, "stats", None)

        # Valores base seguros con fallback a 0.0
        current = {
            "fire": float(getattr(stats, "fire_resistance", 0.0) or 0.0),
            "cold": float(getattr(stats, "cold_resistance", 0.0) or 0.0),
            "lightning": float(getattr(stats, "lightning_resistance", 0.0) or 0.0),
            "chaos": float(getattr(stats, "chaos_resistance", 0.0) or 0.0),
        }

        projected: Dict[str, float] = {}
        for res_type, base_val in current.items():
            change = float(delta.get(res_type, 0.0) or 0.0)
            projected[res_type] = base_val + change

        return projected

    @classmethod
    def _extract_resistances(
        cls, item: Optional[EquipmentItem]
    ) -> Dict[str, float]:
        """Extrae y acumula los valores numéricos de resistencias de un objeto."""
        values = {"fire": 0.0, "cold": 0.0, "lightning": 0.0, "chaos": 0.0}
        if item is None:
            return values

        # Lectura segura de modificadores evitando NoneType
        implicit_mods = getattr(item, "implicit_mods", []) or []
        explicit_mods = getattr(item, "explicit_mods", []) or []
        all_mods = list(implicit_mods) + list(explicit_mods)

        for modifier in all_mods:
            if not modifier or not isinstance(modifier, str):
                continue

            # Track para evitar sumar dos veces el mismo mod si encaja en inglés y español
            matched_in_line = False

            # 1. Patrón en inglés
            for match in cls._RESISTANCE_PATTERN.finditer(modifier):
                res_key = (match.group("resistance") or "").lower().strip()
                if res_key in values:
                    values[res_key] += float(match.group("value"))
                    matched_in_line = True

            # 2. Patrón en español (solo si no matcheó previamente)
            if not matched_in_line and hasattr(cls, "_SPANISH_RESISTANCE_PATTERN"):
                for match in cls._SPANISH_RESISTANCE_PATTERN.finditer(modifier):
                    raw_res = match.group("resistance")
                    res_key = cls._normalize_spanish_resistance(raw_res)
                    if res_key in values:
                        values[res_key] += float(match.group("value"))

            # 3. Resistencias elementales globales ("+#% to all Elemental Resistances")
            if hasattr(cls, "_ALL_ELEMENTAL_PATTERN"):
                all_elemental = cls._ALL_ELEMENTAL_PATTERN.search(modifier)
                if all_elemental:
                    val = float(all_elemental.group("value"))
                    for res_key in ("fire", "cold", "lightning"):
                        values[res_key] += val

        return values

    @staticmethod
    def _normalize_spanish_resistance(value: object) -> str:
        """Mapea términos de resistencia en español a las claves internas del motor."""
        if not value or not isinstance(value, str):
            return ""

        normalized = value.lower().strip()
        
        mapping = {
            "fuego": "fire",
            "frio": "cold",
            "frío": "cold",
            "rayos": "lightning",
            "rayo": "lightning",
            "relámpago": "lightning",
            "caos": "chaos",
        }
        
        return mapping.get(normalized, "")