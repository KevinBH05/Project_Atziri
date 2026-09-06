import json
from pathlib import Path
from typing import Any
import chromadb
from chromadb.utils import embedding_functions

# Resolviendo rutas absolutas basadas en la ubicación de este script
BASE_DIR = Path(__file__).resolve().parent.parent.parent
KB_DIR = BASE_DIR / "data" / "knowledge_base"
CHROMA_DIR = BASE_DIR / "data" / "vector_store" / "chroma"

def _dict_to_text(item_data: dict[str, Any]) -> str:
    """Transforma el diccionario en un string plano y digerible para los embeddings."""
    lines = []
    for key, value in item_data.items():
        if isinstance(value, list):
            val_str = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            # Por si un nodo del árbol contiene sub-diccionarios (ej: stats o requisitos)
            val_str = ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            val_str = str(value)
        
        if val_str and val_str.lower() != "none":
            lines.append(f"{key.capitalize()}: {val_str}")
            
    return "\n".join(lines)

def ingest_json_to_chroma(collection: chromadb.Collection, json_path: Path, category: str) -> None:
    """Lee un archivo JSON y vuelca su contenido en la colección."""
    if not json_path.exists():
        print(f"⚠️ Aviso: No se encontró la ruta {json_path}. Saltando...")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Defensa de estructura: soporta lista de nodos, dict raíz con lista, o dict con IDs como llaves
    if isinstance(data, dict):
        # Caso 1: Dict con clave contenedora (ej: {"nodes": [...]})
        for val in data.values():
            if isinstance(val, list):
                data = val
                break
        else:
            # Caso 2: Dict de nodos indexados por ID (ej: {"1234": {"name": "Strength", ...}})
            if all(isinstance(v, dict) for v in data.values()):
                data = list(data.values())
            else:
                data = [data] # Fallback
            
    if not data:
        return

    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        item_name = str(item.get("name", item.get("Name", str(i))))
        clean_id = item_name.replace(" ", "_").replace("'", "").lower()
        
        doc_text = _dict_to_text(item)
        documents.append(doc_text)
        
        metadatas.append({"category": category, "name": item_name})
        ids.append(f"{category}_{clean_id}_{i}")

    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ [{category.upper()}] Ingestados {len(documents)} elementos.")

def run_ingestion() -> None:
    """Punto de entrada para poblar la base de datos vectorial."""
    print("Iniciando ingestión de la Base de Conocimiento hacia ChromaDB...")
    
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name="poe2_knowledge",
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"} 
    )

    # Si la subcarpeta en lugar de 'tree' se llamara distinto, ajústala aquí
    sources = {
        "classes": KB_DIR / "classes" / "classes.json",
        "gems": KB_DIR / "gems" / "gems.json",
        "uniques": KB_DIR / "uniques" / "uniques.json",
        "tree": KB_DIR / "tree" / "clean_tree.json"
    }

    for category, json_path in sources.items():
        ingest_json_to_chroma(collection, json_path, category)
        
    print("🚀 Ingestión completada. Base de datos vectorial lista.")

if __name__ == "__main__":
    run_ingestion()