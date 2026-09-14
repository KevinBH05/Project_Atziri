import os
from dotenv import load_dotenv
from google import genai
from config.prompts import ZIRI_SYSTEM_PROMPT

# Ajusta esta ruta según dónde tengas tu clase ChromaDB
from src.rag.retriever import KnowledgeRetriever 

load_dotenv()

class ZiriBrain:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("⚠️ No se ha encontrado la variable GEMINI_API_KEY en el archivo .env ni en el entorno.")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3.5-flash" # o la versión que uses
        self.conversation_history = []
        
        # Inicializamos el cerebro de la base de datos
        try:
            self.retriever = KnowledgeRetriever()
        except Exception as e:
            print(f"⚠️ Error al conectar con ChromaDB. Ziri operará sin base de datos: {e}")
            self.retriever = None

    def ask_ziri(self, prompt: str, context_data = None, return_db_status: bool = False):
        db_context = ""
        found_in_db = False
        
        # Asegurar inicialización del historial si no existe
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []

        # 1. Recuperar información oficial de ChromaDB (con búsqueda inteligente si hay item)
        if self.retriever:
            is_gem_query = any(w in prompt.lower() for w in ["gema", "gemas", "soporte", "habilidad", "asistencia", "soportes"])
            
            if is_gem_query and context_data:
                # Extracción segura de atributos del objeto escaneado
                item_type = getattr(context_data, 'item_type', '') or (context_data.get('item_type', '') if isinstance(context_data, dict) else '')
                primary_stat = getattr(context_data, 'primary_attribute', '') or (context_data.get('primary_attribute', '') if isinstance(context_data, dict) else '')
                dynamic_query = f"{item_type} {primary_stat} {prompt}"
                db_results = self.retriever.search(dynamic_query, category="gems", top_k=3, max_distance=0.60)
            else:
                db_results = self.retriever.search(prompt, top_k=3, max_distance=0.60)

            if db_results:
                found_in_db = True
                db_context = "=== DATOS OFICIALES DE LA BASE DE DATOS (Usa esto como verdad absoluta) ===\n"
                for res in db_results:
                    doc_text = res.get("text", str(res)) if isinstance(res, dict) else str(res)
                    db_context += f"- {doc_text}\n"
                db_context += "=======================================================================\n"

        # 2. Construir el bloque con el historial reciente de chat
        history_str = ""
        if self.conversation_history:
            history_str = "=== HISTORIAL RECIENTE DE LA CONVERSACIÓN ===\n"
            for turn in self.conversation_history[-6:]:  # Últimos 3 turnos
                role = "Jugador" if turn["role"] == "user" else "Ziri"
                history_str += f"{role}: {turn['content']}\n"
            history_str += "==============================================\n\n"

        # 3. Ensamblar el megacontexto completo
        full_content = ""
        if history_str:
            full_content += history_str
        if context_data:
            full_content += f"Contexto del jugador / objeto analizado:\n{context_data}\n\n"
        if db_context:
            full_content += f"{db_context}\n\n"
        
        full_content += f"Consulta actual del usuario:\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_content,
                config={
                    "system_instruction": ZIRI_SYSTEM_PROMPT,
                    "temperature": 0.3,
                },
            )
            
            answer = response.text

            # 4. Guardar el turno completo en el historial (Usuario + Ziri)
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": answer})
            
            # Limitar el historial a los últimos 6 mensajes para no desbordar tokens
            if len(self.conversation_history) > 6:
                self.conversation_history = self.conversation_history[-6:]

            if return_db_status:
                return answer, found_in_db
            return answer
            
        except Exception as e:
            err_msg = f"⚠️ Ziri se ha quedado sin conexión con Wraeclast: {e}"
            if return_db_status:
                return err_msg, False
            return err_msg

    def search_gems_for_current_item(self, item_data, user_prompt: str):
        """Busca gemas compatibles cruzando la intención del usuario con el arma escaneada."""
        if not item_data:
            return self.retriever.search(user_prompt, category="gems")
        
        # Extracción segura de atributos del objeto
        item_type = getattr(item_data, 'item_type', '') or (item_data.get('item_type', '') if isinstance(item_data, dict) else '')
        primary_stat = getattr(item_data, 'primary_attribute', '') or (item_data.get('primary_attribute', '') if isinstance(item_data, dict) else '')
        
        # Query compuesta para guiar al vectorizador hacia las gemas correctas
        dynamic_query = f"{item_type} {primary_stat} {user_prompt}"
        
        return self.retriever.search(dynamic_query, category="gems", top_k=3)