from pathlib import Path
from typing import Optional, Any
import chromadb, re
from chromadb.utils import embedding_functions

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_DIR = BASE_DIR / "data" / "vector_store" / "chroma"

class KnowledgeRetriever:
    """Gestor de consultas a la base de datos vectorial de Atziri."""
    
    def __init__(self):
        if not CHROMA_DIR.exists():
            raise FileNotFoundError(
                f"No se encontró la base de datos en {CHROMA_DIR}. "
                "Ejecuta general_ingestor.py primero."
            )
            
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        
        try:
            self.collection = self.client.get_collection(
                name="poe2_knowledge",
                embedding_function=self.emb_fn
            )
        except ValueError:
            raise ValueError("La colección 'poe2_knowledge' no existe. ¿Se ejecutó la ingestión?")

    def _clean_query(self, query: str) -> str:
        """Elimina muletillas, términos temporales y de versión en español para aislar la gema en inglés."""
        stopwords = {
            # Peticiones y verbos
            "dime", "dame", "busca", "encuentra", "muéstrame", "explícame", "tengo",
            # Artículos y determinantes
            "los", "las", "el", "la", "un", "una", "unos", "unas", "este", "esta", "estos", "estas",
            # Conectores y preposiciones
            "y", "o", "de", "del", "a", "en", "por", "para", "con", "sin", "sobre", "que", "se",
            # Atributos y estadísticas genéricas
            "hace", "como", "funciona", "estadísticas", "stats", "datos", "exactos", "asistencia", "soporte", "habilidad", "gema", "gemas",
            "multiplicadores", "daño", "cuales", "nivel", "clase", "equipo", "arma", "objeto", "soportes", "habilidades", "multiplicador",
            # Temporalidad y parches (el talón de Aquiles anterior)
            "según", "ultimo", "último", "parche", "version", "versión", "patch", "actual", 
            "nuevo", "nueva", "cambios", "notas", "juego"
        }
        
        # Limpiar puntuación, tildes y pasar a minúsculas
        cleaned = re.sub(r'[^\w\s]', '', query.lower())
        
        # Filtrar palabras y opcionalmente descartar números sueltos (como el '20' de nivel)
        words = [
            word for word in cleaned.split() 
            if word not in stopwords and not word.isdigit()
        ]

        return " ".join(words) if words else query

    def search(
        self, 
        query: str, 
        category: Optional[str] = None, 
        top_k: int = 5,  # Subimos a 5 para dar margen
        max_distance: float = 0.75  # Ampliamos ligeramente el umbral
    ) -> list[dict[str, Any]]:
        """Busca en la base de datos usando similitud semántica y filtrado inteligente."""
        normalized_query = self._clean_query(query)

        # Si el usuario pregunta por una gema, forzamos el filtro de categoría 'gems'
        if not category and any(w in query.lower() for w in ["gema", "gemas", "soporte", "asistencia", "soportes", "habilidad"]):
            category = "gems"

        where_clause = {"category": category} if category else None
        
        results = self.collection.query(
            query_texts=[normalized_query],
            n_results=top_k,
            where=where_clause
        )
        
        formatted_results = []
        if results.get('documents') and results['documents'][0]:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            dists = results['distances'][0]
            
            for doc, meta, dist in zip(docs, metas, dists):
                if dist <= max_distance:
                    formatted_results.append({
                        "text": doc,
                        "metadata": meta,
                        "distance": dist
                    })
                
        return formatted_results

    def search_as_text(self, query: str, category: Optional[str] = None, top_k: int = 3) -> str:
        """Devuelve un string pre-formateado listo para inyectar en el LLM."""
        results = self.search(query, category, top_k)
        if not results:
            return "No se encontró información relevante en la base de datos."
            
        context_blocks = []
        for i, res in enumerate(results, 1):
            cat = res['metadata'].get('category', 'desconocido').upper()
            name = res['metadata'].get('name', 'Sin nombre')
            context_blocks.append(f"--- RECURSO {i} [{cat} - {name}] ---\n{res['text']}")
            
        return "\n\n".join(context_blocks)

if __name__ == "__main__":
    print("--- INICIANDO PRUEBAS DE FILTRADO Y RETRIEVAL ---")
    
    try:
        retriever = KnowledgeRetriever()
    except Exception as e:
        print(f"❌ Error al inicializar el retriever: {e}")
        exit(1)

    # Consultas de prueba diseñadas para romper el filtrado clásico
    test_queries = [
        "Dime los datos exactos y multiplicadores de daño de la gema Sunder nivel 20 según el último parche.",
        "¿Cómo funciona la asistencia de Herald of Plague en la versión actual?",
        "Busca estadísticas de daño para Ground Slam",
    ]

    for query in test_queries:
        print(f"\n==================================================")
        print(f"📝 CONSULTA ORIGINAL: {query}")
        print(f"--------------------------------------------------")
        
        results = retriever.search(query, top_k=3)
        
        if results:
            print(f"✅ Resultados encontrados ({len(results)}):")
            for i, res in enumerate(results, 1):
                cat = res['metadata'].get('category', 'N/A')
                name = res['metadata'].get('name', 'N/A')
                dist = res['distance']
                print(f"  [{i}] Categoría: {cat} | Nombre: {name} | Distancia: {dist:.4f}")
                print(f"      Extracto: {res['text'][:100]}...")
        else:
            print("⚠️ No se encontraron resultados que cumplan el umbral de distancia.")