from typing import Any, Optional
from src.core.context_manager import ContextManager
from src.rag.retriever import KnowledgeRetriever

class PromptBuilder:
    """Ensambla toda la información de RAM, RAG e inputs en un prompt único para el LLM."""
    
    def __init__(self, retriever: KnowledgeRetriever):
        self.retriever = retriever
        self.context_manager = ContextManager()

    def build_item_analysis_prompt(self, item_data: dict[str, Any]) -> str:
        """Genera el prompt para evaluar un ítem escaneado en pantalla."""
        # 1. Recuperar contexto del personaje desde la RAM
        char_state = self.context_manager.get_active_character()
        char_context = char_state.to_llm_context_dict() if char_state else "No hay personaje cargado desde PoB."

        # 2. Consultar RAG usando el nombre o tipo de objeto para enriquecer
        item_name = item_data.get("name", "Objeto Desconocido")
        rag_info = self.retriever.search_as_text(query=item_name, top_k=5)

        # 3. Construir el cuerpo del prompt
        prompt = f"""
[ESTADO DEL PERSONAJE ACTUAL]
{char_context}

[INFORMACIÓN DE BASE DE CONOCIMIENTO (RAG)]
{rag_info}

[OBJETO ESCANEADO]
{item_data}

[TAREA]
Analiza si el objeto escaneado supone una mejora para la build del personaje.
Compara sus estadísticas con las necesidades prioritarias del personaje (resistencias, vida/atributos faltantes, daño, etc.).
""".strip()
        return prompt