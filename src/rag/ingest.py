"""Extrae objetos únicos de PoE2DB, corrige la fragmentación de estadísticas y guarda en archivos separados."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List
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
    grants_skill: str
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

        cards = soup.select(".card, div[class*='item'], tr, .col")
        print(f"[Scraper] Elementos analizados: {len(cards)}")

        items_by_category: Dict[str, List[UniqueItem]] = {
            "weapons": [],
            "armours": [],
            "others": []
        }

        for card in cards:
            text = card.get_text("\n", strip=True)
            raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
            
            if len(raw_lines) < 3:
                continue
            
            name = raw_lines[0]
            if self._is_ui_noise(name):
                continue

            item_type = raw_lines[1]
            if self._is_ui_noise(item_type):
                item_type = "Desconocido"

            requirements = "No especificado"
            grants_skill = "Ninguna"
            raw_attributes: List[str] = []

            for line in raw_lines[2:]:
                low_line = line.casefold()
                if "level" in low_line or "requires" in low_line:
                    requirements = line
                elif "grants skill" in low_line or ("level" in low_line and "skill" in low_line):
                    if ":" in line:
                        parts = line.split(":", 1)
                        if len(parts[1].strip()) > 0:
                            grants_skill = parts[1].strip()
                    else:
                        grants_skill = line
                elif not self._is_ui_noise(line):
                    raw_attributes.append(line)

            attributes = self._clean_and_merge_attributes(raw_attributes)

            if attributes or requirements != "No especificado":
                category = self._determine_category(item_type)
                item = UniqueItem(
                    name=name, 
                    item_type=item_type, 
                    requirements=requirements, 
                    grants_skill=grants_skill, 
                    attributes=attributes[:15],
                    category=category
                )
                items_by_category[category].append(item)

        cleaned_categories: Dict[str, List[UniqueItem]] = {}
        for cat, items in items_by_category.items():
            unique_dict = {item.name.lower(): item for item in items}
            cleaned_categories[cat] = list(unique_dict.values())
            print(f"[Scraper] {cat}: {len(cleaned_categories[cat])} objetos únicos extraídos")

        return cleaned_categories

    def write_markdown_files(self, items_by_category: Dict[str, List[UniqueItem]]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        file_mapping = {
            "weapons": "weapons_uniques.md",
            "armours": "armours_uniques.md",
            "others": "others_uniques.md"
        }

        for category, filename in file_mapping.items():
            items = items_by_category.get(category, [])
            output_path = self.output_dir / filename
            ordered_items = sorted(items, key=lambda item: item.name.casefold())
            
            lines = [f"# Objetos únicos de Path of Exile 2: {category.title()}", ""]

            for item in ordered_items:
                lines.extend([
                    f"## {item.name}",
                    "",
                    f"- **Tipo:** {item.item_type}",
                    f"- **Requisitos:** {item.requirements}",
                ])
                if item.grants_skill != "Ninguna":
                    lines.append(f"- **Habilidad otorgada:** {item.grants_skill}")
                
                lines.append("- **Estadísticas e Implícitos:**")
                for attr in item.attributes:
                    lines.append(f"  - {attr}")
                lines.append("")

            output_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"[Scraper] Guardado: {output_path} ({len(ordered_items)} objetos)")

    @staticmethod
    def _clean_and_merge_attributes(lines: List[str]) -> List[str]:
        """Une fragmentos partidos como rangos numéricos o porcentajes separados por el parser."""
        merged: List[str] = []
        buffer = ""
        
        for line in lines:
            # Si la línea empieza con símbolos de continuación, paréntesis cerrados o fragmentos pequeños, unir al buffer
            if buffer and (line.startswith("—") or line.startswith("%") or line.startswith(")") or line.isdigit() or len(line) <= 3 and not line.isupper()):
                if buffer.endswith("(") or buffer.endswith("—") or line.startswith("—"):
                    buffer += line
                else:
                    buffer += " " + line
            else:
                if buffer:
                    merged.append(buffer)
                buffer = line
        if buffer:
            merged.append(buffer)
        
        # Limpieza final de espacios alrededor de guiones de rango
        cleaned = []
        for item in merged:
            item_clean = re.sub(r"\(\s*", "(", item)
            item_clean = re.sub(r"\s*\)", ")", item_clean)
            item_clean = re.sub(r"\s*—\s*", " — ", item_clean)
            cleaned.append(item_clean)
        return cleaned

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
            "cultivated uniques", "search", "filter", "grants skill:"
        }
        if val_lower in noise_keywords or "/" in value or len(value) > 40:
            return True
        if any(char.isdigit() and ("/" in value or "unique" in val_lower) for char in value):
            return True
        return False

def main() -> None:
    scraper = PoE2DBSeparatedScraper()
    items_by_cat = scraper.scrape_uniques()
    scraper.write_markdown_files(items_by_cat)
    print("[Scraper] Proceso completado con archivos de únicos estructurados.")

if __name__ == "__main__":
    main()