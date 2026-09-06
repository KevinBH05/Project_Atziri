from pathlib import Path
from typing import Optional, Any
import chromadb
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

    def search(self, query: str, category: Optional[str] = None, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Busca en la base de datos usando similitud semántica.
        :param query: Texto a buscar (ej. 'nodos de daño de fuego con mazas').
        :param category: Filtro opcional ('gems', 'uniques', 'classes', 'tree').
        :param top_k: Número de resultados a devolver.
        """
        where_clause = {"category": category} if category else None
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )
        
        formatted_results = []
        # Validación defensiva por si Chroma devuelve listas vacías
        if results.get('documents') and results['documents'][0]:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            dists = results['distances'][0]
            
            for doc, meta, dist in zip(docs, metas, dists):
                formatted_results.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": dist  # Menos es mejor (más similitud)
                })
                
        return formatted_results

    def search_as_text(self, query: str, category: Optional[str] = None, top_k: int = 3) -> str:
        """
        Igual que search, pero devuelve un string pre-formateado listo para inyectar en el LLM.
        """
        results = self.search(query, category, top_k)
        if not results:
            return "No se encontró información relevante en la base de datos."
            
        context_blocks = []
        for i, res in enumerate(results, 1):
            cat = res['metadata'].get('category', 'desconocido').upper()
            name = res['metadata'].get('name', 'Sin nombre')
            context_blocks.append(f"--- RECURSO {i} [{cat} - {name}] ---\n{res['text']}")
            
        return "\n\n".join(context_blocks)

# ==========================================
# Zona de pruebas por consola
# ==========================================
if __name__ == "__main__":
    print("Iniciando pruebas del Retriever...")
    try:
        retriever = KnowledgeRetriever()
        
        test_query = "daño físico cuerpo a cuerpo y aturdimiento"
        print(f"\nBuscando: '{test_query}' en el árbol (tree)...")
        
        # Probamos el formato directo para el LLM
        resultado_texto = retriever.search_as_text(query=test_query, category="tree", top_k=2)
        print("\nResultado para inyectar en el prompt:\n")
        print(resultado_texto)
        
    except Exception as e:
        print(f"Error durante la prueba: {e}")