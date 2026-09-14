import requests
import re
import json
import time

class YouTubeFreeSearch:
    """Buscador directo de YouTube sin dependencias externas extrañas ni API keys."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }
        self._cache = {}
        self.cache_duration = 3600  # 1 hora

    def search_build_videos(self, search_query: str, max_results: int = 3) -> list:
        full_query = f"Path of Exile 2 {search_query} build"
        now = time.time()

        if full_query in self._cache:
            ts, cached_data = self._cache[full_query]
            if now - ts < self.cache_duration:
                return cached_data

        try:
            url = f"https://www.youtube.com/results?search_query={requests.utils.quote(full_query)}"
            res = requests.get(url, headers=self.headers, timeout=5)
            
            if res.status_code != 200:
                print(f"❌ Error HTTP {res.status_code} al consultar YouTube.")
                return []

            # Extraer el JSON de datos iniciales que mete YouTube en la página
            match = re.search(r"var ytInitialData = ({.*?});</script>", res.text)
            if not match:
                print("❌ No se pudieron parsear los resultados de YouTube.")
                return []

            data = json.loads(match.group(1))
            contents = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]

            parsed_videos = []
            for item in contents:
                if "videoRenderer" in item:
                    video = item["videoRenderer"]
                    video_id = video.get("videoId")
                    
                    # Extraer título y canal de forma segura
                    title_runs = video.get("title", {}).get("runs", [])
                    title = title_runs[0].get("text", "") if title_runs else "Sin título"
                    
                    owner_runs = video.get("ownerText", {}).get("runs", [])
                    channel = owner_runs[0].get("text", "Desconocido") if owner_runs else "Desconocido"

                    if video_id and title:
                        parsed_videos.append({
                            "title": title,
                            "channel": channel,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                        })
                        
                        if len(parsed_videos) >= max_results:
                            break

            self._cache[full_query] = (now, parsed_videos)
            return parsed_videos

        except Exception as e:
            print(f"❌ Error buscando vídeos en YouTube: {e}")
            return []