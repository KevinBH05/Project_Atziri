from PyQt6.QtCore import QThread, pyqtSignal
from src.integrations.ninja_links import PoeNinjaBuildsAPI
from src.integrations.youtube_api import YouTubeFreeSearch
from src.llm.ziri_brain import ZiriBrain

class ScanWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, raw_text: str, parser_fn, item_type: str = "item", skill_name: str = "Sunder", ascendancy: str = "Titan"):
        super().__init__()
        self.raw_text = raw_text
        self.parser_fn = parser_fn
        self.item_type = item_type
        self.skill_name = skill_name
        self.ascendancy = ascendancy
        
        # Clientes e instancia del cerebro de Ziri
        self.ninja_api = PoeNinjaBuildsAPI(league="Runes of Aldur")
        self.yt_client = YouTubeFreeSearch()
        self.ziri = ZiriBrain()

    def run(self):
        try:
            # 1. Parsear texto del portapapeles (PoB u objeto)
            parsed_item = self.parser_fn(self.raw_text)
            name = getattr(parsed_item, "name", "Desconocido")

            # 2. Obtener enlace directo de poe.ninja como comodín opcional
            ninja_url = self.ninja_api.get_search_url(skill_name=self.skill_name, class_name=self.ascendancy)

            # 3. Buscar vídeos de referencia en YouTube
            videos = self.yt_client.search_build_videos(f"{self.skill_name} {self.ascendancy}", max_results=2)

            # 4. Preparar el contexto estructurado para la IA
            context_payload = f"""
            Tipo de elemento: {self.item_type}
            Nombre detectado: {name}
            Texto plano del portapapeles:
            {self.raw_text}
            Build actual del jugador: {self.skill_name} ({self.ascendancy})
            """

            user_prompt = f"Analiza este objeto para mi build y dame el veredicto de 3 pasos."
            
            # Llamada real al cerebro de Ziri
            raw_ai_response = self.ziri.ask_ziri(prompt=user_prompt, context_data=context_payload)
            formatted_ai_text = raw_ai_response.replace("\n", "<br>")

            # 5. Montar respuesta final combinando IA y recursos externos
            verdict = f"✨ <b>[Veredicto de Ziri]</b><br><br>"
            verdict += f"{formatted_ai_text}<br><br>"
            
            if videos:
                verdict += f"<b>🎥 Referencias clave:</b><br>"
                for v in videos:
                    verdict += f"• <a href='{v['url']}'>{v['title']}</a> <i>({v['channel']})</i><br>"
                verdict += "<br>"

            verdict += f"<b>🔗 Comodín de mercado:</b> <a href='{ninja_url}'>Ver tendencia actual en poe.ninja</a>"

            self.finished.emit({
                "parsed_item": parsed_item,
                "llm_response": verdict
            })

        except Exception as e:
            self.error.emit(str(e))