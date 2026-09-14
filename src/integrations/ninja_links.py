import re
from urllib.parse import quote_plus
from curl_cffi import requests

class PoeNinjaBuildsAPI:
    """Extrae los enlaces directos a los perfiles de las mejores builds en poe.ninja/builds."""

    def __init__(self, league="Runes of Aldur"):
        # "Runes of Aldur" -> "runesofaldur"
        self.league_slug = league.lower().replace(" ", "")
        self.base_url = "https://poe.ninja"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"https://poe.ninja/poe2/builds/{self.league_slug}"
        }

    def get_search_url(self, skill_name: str, class_name: str = None) -> str:
        """
        Devuelve el enlace directo a poe.ninja con los filtros aplicados
        para que el usuario lo consulte con un solo clic.
        """
        formatted_skill = quote_plus(skill_name)
        search_url = f"{self.base_url}/poe2/builds/{self.league_slug}?allskills={formatted_skill}&sort=dps"
        if class_name:
            search_url += f"&class={quote_plus(class_name)}"
        return search_url


if __name__ == "__main__":
    ninja = PoeNinjaBuildsAPI(league="Runes of Aldur")
    url = ninja.get_search_url(skill_name="Sunder", class_name="Titan")
    print(f"🔗 Enlace directo al meta: {url}")