"""Extrae objetos únicos de PoE2DB, soporta múltiples habilidades otorgadas, 
reconstruye atributos fragmentados y exporta todo a un único JSON."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "data" / "knowledge_base" / "uniques"
UNIQUES_URL = "https://poe2db.tw/us/Unique_item"

@dataclass(frozen=True)
class UniqueItem:
    name: str
    item_type: str
    requirements: str
    grants_skills: List[str]
    attributes: List[str]
    category: str

class PoE2DBSeparatedScraper:
    def __init__(self, output_dir: Path = OUTPUT_DIR, delay: float = 2.0) -> None:
        self.output_dir = output_dir
        self.delay = delay

    def fetch_page_content(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36 Project-Atziri/1.0"
                )
            )
            print(f"[Scraper] Navegando a: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(self.delay)
            content = page.content()
            browser.close()
            return content

    def scrape_uniques(self) -> Dict[str, List[UniqueItem]]:
        html = self.fetch_page_content(UNIQUES_URL)
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select("div.card .col")
        print(f"[Scraper] Elementos analizados: {len(cards)}")

        items_by_category: Dict[str, List[UniqueItem]] = {
            "weapons": [],
            "armours": [],
            "others": []
        }

        for card in cards:
            source_category = self._category_from_card(card)
            if source_category == "cultivated":
                continue

            raw_lines = self._extract_card_lines(card)
            
            if len(raw_lines) < 3:
                continue
            
            name = raw_lines[0]
            if self._is_ui_noise(name) or not self._looks_like_item_name(name):
                continue

            item_type = raw_lines[1]
            if self._is_ui_noise(item_type) or self._looks_like_fragment(item_type):
                item_type = "Desconocido"

            content_lines = raw_lines[2:]
            requirements, content_lines = self._extract_requirements(content_lines)
            grants_skills, content_lines = self._extract_granted_skills(content_lines)
            structured_attributes = self._extract_structured_modifiers(card)
            content_lines = structured_attributes or content_lines
            raw_attributes = []
            for line in content_lines:
                if (
                    not self._is_ui_noise(line)
                    and not self._is_granted_skill_line(line)
                ):
                    raw_attributes.extend(
                        [line]
                        if structured_attributes
                        else self._split_embedded_modifiers(line)
                    )

            attributes = self._clean_and_merge_attributes(raw_attributes)

            if attributes or requirements != "No especificado":
                category = source_category or self._determine_category(item_type)
                if category == "armours" and source_category == "others":
                    continue
                item = UniqueItem(
                    name=name, 
                    item_type=item_type, 
                    requirements=requirements, 
                    grants_skills=grants_skills, 
                    attributes=attributes,
                    category=category
                )
                items_by_category[category].append(item)

        cleaned_categories: Dict[str, List[UniqueItem]] = {}
        for cat, items in items_by_category.items():
            unique_dict: Dict[str, UniqueItem] = {}
            for item in items:
                key = item.name.casefold()
                previous = unique_dict.get(key)
                if previous is None or self._item_completeness(item) > self._item_completeness(previous):
                    unique_dict[key] = item
            cleaned_categories[cat] = list(unique_dict.values())
            print(f"[Scraper] {cat}: {len(cleaned_categories[cat])} objetos únicos extraídos")

        return cleaned_categories

    @staticmethod
    def _category_from_card(card: BeautifulSoup) -> str:
        tab = card.find_parent("div", class_="tab-pane")
        tab_id = tab.get("id", "") if tab is not None else ""
        return {
            "WeaponUnique": "weapons",
            "ArmourUnique": "armours",
            "OtherUnique": "others",
            "CultivatedUniques": "cultivated",
        }.get(tab_id, "")

    @staticmethod
    def _looks_like_item_name(value: str) -> bool:
        normalized = value.casefold().strip()
        if normalized in {
            "weapon unique", "armour unique", "other unique", "reset",
            "search", "filter", "edit", "sites",
        }:
            return False
        return not normalized.startswith("# objetos únicos")

    @staticmethod
    def _looks_like_fragment(value: str) -> bool:
        return bool(re.match(r"^[+\-(]?\s*\d", value.strip()))

    @staticmethod
    def _item_completeness(item: UniqueItem) -> int:
        return (
            len(item.requirements)
            + sum(len(skill) for skill in item.grants_skills)
            + sum(len(attribute) for attribute in item.attributes)
        )

    @staticmethod
    def _extract_card_lines(card: BeautifulSoup) -> List[str]:
        lines: List[str] = []
        for value in card.stripped_strings:
            normalized = re.sub(r"\s+", " ", value).strip()
            if normalized:
                lines.append(normalized)
        return lines

    def _extract_structured_modifiers(self, card: BeautifulSoup) -> List[str]:
        selectors = (
            ".text-col-mod",
            ".explicitMod",
            ".implicitMod",
            ".item-mod",
            ".mods > li",
            ".stats > li",
            ".stats li",
            ".mod",
        )
        nodes = card.select(", ".join(selectors))
        if nodes:
            modifiers: List[str] = []
            seen: set[str] = set()
            for node in nodes:
                text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                if (
                    text
                    and text not in seen
                    and not self._is_ui_noise(text)
                    and not self._is_granted_skill_line(text)
                ):
                    modifiers.append(text)
                    seen.add(text)
            return modifiers

        stats_container = card.select_one(".stats, .mods, .item-mods")
        raw_text = (
            stats_container.get_text(separator="\n")
            if stats_container is not None
            else card.get_text(separator="\n")
        )
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        cleaned_lines: List[str] = []
        for line in lines:
            lower_line = line.casefold()
            if any(
                noise in lower_line
                for noise in ("enable", "clip", "task", "grand design")
            ):
                continue

            if re.match(r"^[\),\]]+$", line) and cleaned_lines:
                cleaned_lines[-1] += f" {line}"
            elif (
                re.match(r"^\(\d+", line)
                and cleaned_lines
                and not cleaned_lines[-1].endswith("(")
            ):
                cleaned_lines[-1] += f" {line}"
            else:
                cleaned_lines.append(line)

        return cleaned_lines

    @staticmethod
    def _split_embedded_modifiers(line: str) -> List[str]:
        normalized = re.sub(r"\s+", " ", line).strip()
        if not normalized:
            return []

        boundary = re.compile(
            r"\s+(?=(?:[+-]\d|Adds\b|Gain(?:s)?\b|Leeches\b|Causes\b|"
            r"When\b|Trigger(?:s)?\b|Cannot\b|Deal(?:s)?\b|Attacks?\b|"
            r"Spells?\b|Minions?\b|Skills?\s+(?:reserve|gain|have)))",
            re.IGNORECASE,
        )
        return [part.strip() for part in boundary.split(normalized) if part.strip()]

    def write_json_file(self, items_by_category: Dict[str, List[UniqueItem]], filename: str = "uniques.json") -> None:
        """Agrupa todos los objetos únicos en una sola lista y los exporta a un archivo JSON."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / filename

        all_items = []
        for category, items in items_by_category.items():
            for item in items:
                all_items.append(asdict(item))

        # Ordenar por nombre para mantener consistencia
        all_items.sort(key=lambda x: x["name"].casefold())

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)

        print(f"[Scraper] Guardado: {output_path} ({len(all_items)} objetos en total)")

    @staticmethod
    def _clean_and_merge_attributes(lines: List[str]) -> List[str]:
        merged: List[str] = []
        buffer = ""

        for raw_line in lines:
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue

            if line in {",", "—"}:
                buffer = f"{buffer}{line}".strip()
                continue

            if buffer and PoE2DBSeparatedScraper._starts_new_attribute(line, buffer):
                merged.append(buffer)
                buffer = line
                continue

            if not buffer:
                buffer = line
                continue

            if PoE2DBSeparatedScraper._is_attribute_continuation(line, buffer):
                separator = "" if buffer.endswith(("(", "+")) else " "
                buffer = f"{buffer}{separator}{line}"
            else:
                merged.append(buffer)
                buffer = line

        if buffer:
            merged.append(buffer)

        cleaned: List[str] = []
        for item in merged:
            item_clean = re.sub(r"\s*,\s*", ", ", item)
            item_clean = re.sub(r"\(\s*", "(", item_clean)
            item_clean = re.sub(r"\s*\)", ")", item_clean)
            item_clean = re.sub(r"\s*—\s*", " — ", item_clean)
            item_clean = re.sub(r"\s+", " ", item_clean).strip()
            if item_clean and item_clean not in {",", "—"}:
                cleaned.append(item_clean)

        cleaned = PoE2DBSeparatedScraper._merge_long_attribute_fragments(cleaned)
        return PoE2DBSeparatedScraper._merge_projectile_attributes(cleaned)

    @staticmethod
    def _merge_long_attribute_fragments(attributes: List[str]) -> List[str]:
        merged: List[str] = []
        continuation_words = {
            "deal", "deals", "gain", "gains", "have", "has", "is", "are",
            "with", "on", "from", "against", "after", "before", "if", "when",
            "to", "of", "as", "per", "for", "in", "by", "into", "their",
            "your", "you", "and", "or",
        }

        for attribute in attributes:
            if not merged:
                merged.append(attribute)
                continue

            previous = merged[-1]
            first_word = attribute.split(maxsplit=1)[0].casefold()
            previous_words = previous.casefold().split()
            should_join = (
                first_word in continuation_words
                and attribute[:1].islower()
            )
            should_join = should_join or (
                attribute.startswith("%") and previous.endswith(")")
            )
            should_join = should_join or (
                previous.casefold() == "all"
                and first_word == "attacks"
            )
            should_join = should_join or (
                previous_words[-1:] == ["strikes"]
                and first_word in {"deal", "deals"}
            )
            should_join = should_join or (
                previous.casefold().startswith("cannot use projectile")
                and first_word == "attacks"
            )

            if should_join:
                merged[-1] = f"{previous} {attribute}"
            else:
                merged.append(attribute)

        return merged

    @staticmethod
    def _merge_projectile_attributes(attributes: List[str]) -> List[str]:
        merged: List[str] = []
        index = 0

        while index < len(attributes):
            current = attributes[index]
            if (
                current.casefold() == "arrows"
                and index + 1 < len(attributes)
                and attributes[index + 1].casefold() == "fork"
            ):
                merged.append("Arrows Fork")
                index += 2
                continue

            if (
                current.casefold() == "arrows"
                and index + 2 < len(attributes)
                and attributes[index + 1].casefold().startswith("pierce all targets after")
                and attributes[index + 2].casefold() == "forking"
            ):
                merged.append(f"Arrows {attributes[index + 1]} Forking")
                index += 3
                continue

            merged.append(current)
            index += 1

        return merged

    @staticmethod
    def _extract_requirements(lines: List[str]) -> tuple[str, List[str]]:
        requirements = "No especificado"
        start = next(
            (index for index, line in enumerate(lines) if line.casefold().startswith("requires")),
            None,
        )
        if start is None and lines and re.match(r"^Level\s+\d+", lines[0], re.IGNORECASE):
            start = 0
            marker = "Requires:"
        elif start is not None:
            marker = lines[start].rstrip()
        else:
            return requirements, lines

        fragments: List[str] = []
        index = start + 1 if not marker.casefold().startswith("requires:") or marker.casefold() == "requires:" else start + 1
        inline_value = marker.split(":", 1)[1].strip() if ":" in marker else ""
        if inline_value:
            fragments.append(inline_value)

        while index < len(lines):
            line = lines[index].strip()
            if line == ",":
                fragments.append(line)
                index += 1
                continue
            is_requirement_fragment = bool(
                re.match(r"^(?:Level\s+\d+|\d+\s*(?:Str|Dex|Int)\b|(?:Str|Dex|Int)\s+\d+)", line, re.IGNORECASE)
            )
            if not is_requirement_fragment:
                break
            fragments.append(line)
            index += 1

        if fragments:
            value = re.sub(r"\s+", " ", " ".join(fragments)).strip()
            value = re.sub(r"\s*,\s*", ", ", value)
            requirements = f"Requires: {value}"
            return requirements, lines[:start] + lines[index:]

        return requirements, lines[:start] + lines[start + 1:]

    @staticmethod
    def _extract_granted_skills(lines: List[str]) -> tuple[List[str], List[str]]:
        skills: List[str] = []
        remaining: List[str] = []
        index = 0

        while index < len(lines):
            line = lines[index].strip()
            if "grants skill" not in line.casefold():
                remaining.append(line)
                index += 1
                continue

            value = line.split(":", 1)[1].strip() if ":" in line else ""
            if not value and index + 1 < len(lines):
                index += 1
                value = lines[index].strip()

            if value.casefold().startswith("level ") and index + 1 < len(lines):
                index += 1
                value = f"{value} {lines[index].strip()}"

            if value and value not in skills:
                skills.append(value)
            index += 1

        return skills, remaining

    @staticmethod
    def _starts_new_attribute(line: str, previous: str) -> bool:
        normalized = line.casefold()
        previous_normalized = previous.casefold().rstrip()
        if normalized in {"trigger", "triggers"} and previous_normalized.endswith(" charge"):
            return False
        if normalized in {"adds", "increases", "increased", "gain", "gains", "leech", "leeches", "causes", "causing", "when", "trigger", "triggers", "spells", "attacks", "minions", "deal", "deals", "cannot", "you", "your"}:
            return True
        if re.match(r"^(?:\+?\d|\(\d|[+-]?\d+%)", line):
            return not (
                previous_normalized in {"adds", "gain", "gains", "leech", "leeches", "to", "of", "as", "per"}
                or previous_normalized.endswith((" adds", " gain", " gains", " to", " of", " as", " per"))
                or previous.endswith(("(", "+", "—"))
            )
        return False

    @staticmethod
    def _is_attribute_continuation(line: str, previous: str) -> bool:
        normalized = line.casefold()
        previous_normalized = previous.casefold().rstrip()
        continuation_words = {
            "speed", "damage", "chance", "hit", "armor", "armour", "energy",
            "shield", "mana", "life", "chaos", "physical", "elemental", "fire",
            "cold", "lightning", "blocked", "is", "are", "has", "have", "as",
            "of", "to", "for", "per", "with", "on", "from", "against", "when",
            "you", "your", "skills", "skill", "rating", "buildup", "spell",
            "spells", "attack", "attacks", "cast", "critical", "strike", "surges",
            "charge", "fork", "forking", "pierce", "arrows", "the", "a", "an",
            "gain", "gains", "deal", "deals", "trigger", "triggers",
        }
        if normalized in continuation_words:
            return True
        if normalized.startswith(("damage ", "speed ", "chance ", "resistance ")):
            return True
        return previous_normalized.endswith(("(", "+", "—", ",", ":", " to", " of", " as", " per", " with", " on", " from", " against", " a", " an", " the"))

    @staticmethod
    def _determine_category(item_type: str) -> str:
        low_type = item_type.casefold()
        weapon_keywords = ["wand", "bow", "sword", "axe", "mace", "dagger", "staff", "spear", "crossbow", "flail", "claw", "trap", "quarterstaff", "hammer"]
        armour_keywords = ["helmet", "cap", "cuirass", "armour", "chest", "gloves", "gauntlets", "boots", "greaves", "shield", "focus", "crest", "circlet", "plate", "robe", "coat"]
        
        if any(kw in low_type for kw in weapon_keywords):
            return "weapons"
        if any(kw in low_type for kw in armour_keywords):
            return "armours"
        return "others"

    @staticmethod
    def _is_ui_noise(value: str) -> bool:
        val_lower = value.casefold()
        noise_keywords = {
            "name", "item", "type", "base type", "unique item", "uniques", 
            "reset", "weapon unique", "armour unique", "other unique", 
            "cultivated uniques", "search", "filter"
        }
        if re.search(r"\b(?:enable|clip|task)\b", val_lower):
            return True
        if re.search(r"\[\s*\d+\s*\]", value):
            return True
        if re.search(
            r"\[[^\]]*(?:custom|internal|development|dev|prefix|suffix)[^\]]*\]",
            value,
            re.IGNORECASE,
        ):
            return True
        if val_lower in noise_keywords or "/" in value:
            return True
        if any(char.isdigit() and ("/" in value or "unique" in val_lower) for char in value):
            return True
        return False

    @staticmethod
    def _is_granted_skill_line(value: str) -> bool:
        return bool(re.match(r"^grants\s+skill\s*:", value.strip(), re.IGNORECASE))

def main() -> None:
    scraper = PoE2DBSeparatedScraper()
    items_by_cat = scraper.scrape_uniques()
    scraper.write_json_file(items_by_cat)
    print("[Scraper] Proceso completado con éxito.")

if __name__ == "__main__":
    main()