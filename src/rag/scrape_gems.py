"""Extrae gemas de PoE2DB en un JSON listo para ingestión RAG."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[2]
GEM_SUMMARY_URL = "https://poe2db.tw/us/Gem"
OUTPUT_PATH = ROOT_DIR / "data" / "knowledge_base" / "gems" / "gems.json"
REQUEST_DELAY = 0.75
MAX_RETRIES = 3
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 "
    "Project-Atziri/1.0"
)


@dataclass(frozen=True)
class GemIndexEntry:
    """Referencia a una gema obtenida del resumen."""

    name: str
    gem_type: str
    url: str


@dataclass
class GemRecord:
    """Información estructurada de una gema individual."""

    name: str
    type: str
    tags: List[str]
    requirements: Dict[str, int]
    description: str
    stats: List[str]
    url: str


class PoE2DBGemScraper:
    """Scraper de dos fases para el índice y detalle de gemas de PoE2DB."""

    def __init__(
        self,
        output_path: Path = OUTPUT_PATH,
        delay: float = REQUEST_DELAY,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.output_path = output_path
        self.delay = max(0.0, delay)
        self.max_retries = max(1, max_retries)

    def scrape(self) -> List[GemRecord]:
        """Ejecuta la recolección del índice y la extracción detallada."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            try:
                print("[Gemas] Fase 1: leyendo Gem Summary...")
                summary_html = self._load_page(page, GEM_SUMMARY_URL)
                entries = self._collect_index_entries(summary_html)
                print(f"[Gemas] Gemas indexadas: {len(entries)}")

                records: List[GemRecord] = []
                for index, entry in enumerate(entries, start=1):
                    try:
                        print(f"[Gemas] Fase 2: {index}/{len(entries)} {entry.name}")
                        detail_html = self._load_page(page, entry.url)
                        records.append(self._parse_detail(detail_html, entry))
                    except RuntimeError as exc:
                        print(f"[Gemas] ERROR en {entry.name}: {exc}")
                    if index < len(entries):
                        time.sleep(self.delay)
            finally:
                browser.close()

        self._write_json(records)
        return records

    def _load_page(self, page: Page, url: str) -> str:
        """Carga una página con reintentos ante fallos HTTP o de navegación."""
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                if response is not None and response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status}")
                page.wait_for_load_state("networkidle", timeout=30000)
                return page.content()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait_seconds = min(2.0 * attempt, 5.0)
                    print(f"[Gemas] Reintento {attempt}/{self.max_retries - 1} para {url}")
                    time.sleep(wait_seconds)

        raise RuntimeError(f"No se pudo descargar {url}: {last_error}") from last_error

    def _collect_index_entries(self, html: str) -> List[GemIndexEntry]:
        """Extrae nombre, categoría y URL directamente del DOM procesado."""
        soup = BeautifulSoup(html, "html.parser")
        entries: Dict[str, GemIndexEntry] = {}

        # poe2db renderiza las gemas en tablas con enlaces que contienen imágenes o nombres de gemas.
        # Buscamos todas las tablas presentes en la página renderizada.
        tables = soup.find_all("table")
        print(f"[Gemas] Tablas detectadas en el DOM: {len(tables)}")

        for table in tables:
            rows = table.select("tbody tr") if table.select("tbody tr") else table.select("tr")
            for row in rows:
                # Buscamos el enlace principal de la gema en la fila
                anchors = row.select("a[href]")
                for anchor in anchors:
                    href = anchor.get("href", "")
                    name = self._clean_text(anchor)

                    if not name or not href or not self._looks_like_gem_link(href, name):
                        continue

                    row_text = self._clean_text(row)
                    gem_type = self._infer_gem_type(row_text)
                    absolute_url = urljoin(GEM_SUMMARY_URL, href)
                    
                    # Normalizamos URL para evitar duplicados
                    key = absolute_url.split("#", 1)[0].rstrip("/").casefold()

                    if key not in entries:
                        entries[key] = GemIndexEntry(name=name, gem_type=gem_type, url=absolute_url)

        self._debug_missing_rows(soup, entries)
        return sorted(entries.values(), key=lambda entry: entry.name.casefold())

    @staticmethod
    def _find_summary_container(soup: BeautifulSoup) -> Optional[Tag]:
        """Localiza de forma estricta el contenedor de la tabla Gem Summary."""
        # 1. Búsqueda por ID directo de la pestaña/tabla Gem Summary en poe2db
        for target_id in ("GemSummary", "GemSummaryTable", "tab-gem-summary"):
            container = soup.find(id=target_id)
            if container:
                return container

        # 2. Búsqueda por el encabezado "Gem Summary" navegando a su contenedor hermano/padre
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            if "gem summary" in heading.get_text(" ", strip=True).casefold():
                # Buscar la primera tabla o div adyacente
                parent = heading.find_parent(["div", "section"])
                if parent:
                    table = parent.find("table")
                    if table:
                        return table
                return heading.parent

        # 3. Fallback: buscar la primera tabla que contenga columnas típicas de gemas
        for table in soup.find_all("table"):
            text = table.get_text().casefold()
            if "support" in text and "active" in text:
                return table

        return None

    @staticmethod
    def _looks_like_gem_link(href: str, name: str) -> bool:
        """Filtra enlaces estrictos a fichas de gemas de poe2db."""
        normalized_href = href.casefold().strip()
        normalized_name = name.casefold().strip()

        excluded_names = {
            "name", "type", "active", "support", "search", "filter",
            "gem summary", "reset", "next", "previous", "level", "str", "dex", "int",
            "gem", "gems", "icon"
        }

        if not normalized_href or normalized_href.startswith(("javascript:", "mailto:", "#")):
            return False

        if normalized_name in excluded_names or len(normalized_name) < 2:
            return False

        # Excluimos links que vuelvan a la página general de Gemas o a categorías/filtros
        if normalized_href.rstrip("/") in ["https://poe2db.tw/us/gem", "/us/gem", "https://poe2db.tw/us", "/us"]:
            return False

        # En poe2db las gemas apuntan a rutas de detalle como /us/Armor_Breaker o /us/gem.php...
        if "/us/" in normalized_href and not any(param in normalized_href for param in ["cn=", "tw=", "lang="]):
            return True

        return False

    @staticmethod
    def _infer_gem_type(row_text: str) -> str:
        normalized = row_text.casefold()
        if "support" in normalized:
            return "Support"
        if "active" in normalized:
            return "Active"
        return "Active"

    def _parse_detail(self, html: str, entry: GemIndexEntry) -> GemRecord:
        soup = BeautifulSoup(html, "html.parser")
        name = self._extract_name(soup, entry.name)
        tags = self._extract_tags(soup)
        requirements = self._extract_requirements(soup)
        description = self._extract_description(soup)
        stats = self._extract_stats(soup, description)
        return GemRecord(
            name=name,
            type=entry.gem_type,
            tags=tags,
            requirements=requirements,
            description=description,
            stats=stats,
            url=entry.url,
        )

    @staticmethod
    def _extract_name(soup: BeautifulSoup, fallback: str) -> str:
        for selector in ("h1", ".gem-name", ".item-name", "title"):
            node = soup.select_one(selector)
            if node:
                text = PoE2DBGemScraper._clean_text(node)
                if text:
                    return text.split(" - ", 1)[0].strip()
        return fallback

    @staticmethod
    def _extract_tags(soup: BeautifulSoup) -> List[str]:
        nodes = soup.select(
            ".gem-tags .tag, .gem-tags span, .tags .tag, .tags span"
        )
        if not nodes:
            nodes = [
                node
                for node in soup.select("[class*='tag']")
                if not node.find(True)
            ]
        tags: List[str] = []
        seen: set[str] = set()
        for node in nodes:
            value = PoE2DBGemScraper._clean_text(node)
            if value and value.casefold() not in seen:
                tags.append(value)
                seen.add(value.casefold())
        return tags

    @staticmethod
    def _extract_requirements(soup: BeautifulSoup) -> Dict[str, int]:
        requirement_nodes = soup.select(
            ".requirements, .gem-requirements, .requirements-list, [class*='require']"
        )
        text = " ".join(
            PoE2DBGemScraper._clean_text(node) for node in requirement_nodes
        )
        if not text:
            text = PoE2DBGemScraper._clean_text(soup)
        requirements: Dict[str, int] = {}
        patterns = {
            "level": r"(?:requires\s+level|level)\s*[:]?\s*(\d+)",
            "str": r"(?:(?:str|strength)\s*[:]?\s*(\d+)|(\d+)\s*(?:str|strength))",
            "dex": r"(?:(?:dex|dexterity)\s*[:]?\s*(\d+)|(\d+)\s*(?:dex|dexterity))",
            "int": r"(?:(?:int|intelligence)\s*[:]?\s*(\d+)|(\d+)\s*(?:int|intelligence))",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                requirements[key] = int(next(value for value in match.groups() if value is not None))
        return requirements

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        selectors = (".gem-description", ".description", ".gemDesc", ".gem-info .text")
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                return PoE2DBGemScraper._clean_text(node)
        return ""

    @staticmethod
    def _extract_stats(soup: BeautifulSoup, description: str) -> List[str]:
        selectors = (
            ".gem-stats li", ".gem-stats .stat", ".stats li", ".stats .stat",
            ".gem-mod", ".text-col-mod", ".explicitMod", ".implicitMod",
        )
        nodes = soup.select(", ".join(selectors))
        stats: List[str] = []
        seen: set[str] = set()
        for node in nodes:
            value = PoE2DBGemScraper._clean_text(node)
            if value and value != description and value.casefold() not in seen:
                stats.append(value)
                seen.add(value.casefold())
        return stats

    def _write_json(self, records: Iterable[GemRecord]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in records]
        self.output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[Gemas] JSON guardado en {self.output_path}: {len(payload)} gemas")

    @staticmethod
    def _clean_text(node: object) -> str:
        if node is None:
            return ""
        if hasattr(node, "get_text"):
            value = node.get_text(" ", strip=True)
        else:
            value = str(node)
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"\s+([,.;:])", r"\1", value)
        return value.strip()

    def _debug_missing_rows(self, summary_container: BeautifulSoup, entries: Dict[str, GemIndexEntry]) -> None:
        """Compara el total de filas visibles en las tablas contra las gemas indexadas."""
        indexed_urls = set(entries.keys())
        missing_count = 0
        
        print("\n--- [DIAGNÓSTICO DE GEMAS OMITIDAS] ---")
        for table in summary_container.find_all("table"):
            rows = table.select("tbody tr") if table.select("tbody tr") else table.select("tr")
            for row in rows:
                anchors = row.select("a[href]")
                row_text = self._clean_text(row)
                
                # Si la fila no produjo ninguna gema válida en el diccionario
                row_has_indexed_gem = False
                for anchor in anchors:
                    href = anchor.get("href", "")
                    abs_url = urljoin(GEM_SUMMARY_URL, href).split("#", 1)[0].rstrip("/").casefold()
                    if abs_url in indexed_urls:
                        row_has_indexed_gem = True
                        break
                
                if not row_has_indexed_gem and row_text:
                    missing_count += 1
                    # Mostramos solo un resumen corto de la fila ignorada
                    print(f"Omitida #{missing_count}: {row_text[:80]}...")
        
        print(f"Total de filas ignoradas/filtradas: {missing_count}\n---------------------------------------\n")


def main() -> None:
    PoE2DBGemScraper().scrape()


if __name__ == "__main__":
    main()
