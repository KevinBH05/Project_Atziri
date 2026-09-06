import json
from pathlib import Path

#Ejecutar antes con tree.json: Get-Content data\knowledge_base\tree\tree.json | ConvertFrom-Json | ConvertTo-Json -Depth 100 | Set-Content data\knowledge_base\tree\tree_pretty.json

def extract_essential_nodes(input_path: str, output_path: str):
    """Filtra el JSON masivo del árbol de PoB y extrae solo Notables y Keystones para el RAG."""
    path = Path(input_path)
    if not path.exists():
        print(f"❌ No se encontró el archivo: {input_path}")
        return

    print("📖 Leyendo archivo JSON del árbol...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # PoB suele guardar los nodos en data["nodes"] o dentro de la clave del árbol
    nodes_source = data.get("nodes", {})
    if not nodes_source and "tree" in data:
        nodes_source = data["tree"].get("nodes", {})

    cleaned_nodes = []

    for node_id, node in nodes_source.items():
        # Ignoramos nodos que no sean diccionarios o nodos de inicio/clase
        if not isinstance(node, dict):
            continue

        is_notable = node.get("isNotable", False) or node.get("isnotable", False)
        is_keystone = node.get("isKeystone", False) or node.get("iskeystone", False)

        # Solo nos interesan Notables y Keystones (descartamos pasivas pequeñas de stats menores)
        if is_notable or is_keystone:
            node_name = node.get("name", "").strip()
            stats = node.get("stats", []) or node.get("sd", [])

            if node_name and stats:
                cleaned_nodes.append({
                    "id": str(node_id),
                    "name": node_name,
                    "type": "Keystone" if is_keystone else "Notable",
                    "stats": stats,
                    "flavour_text": node.get("flavourText", [])
                })

    # Guardamos un JSON ultra limpio e indentado
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_nodes, f, indent=2, ensure_ascii=False)

    print(f"✅ ¡Completado! Se extrajeron {len(cleaned_nodes)} nodos clave en '{output_path}'.")

if __name__ == "__main__":
    
    extract_essential_nodes("data/knowledge_base/tree/tree_pretty.json", "data/knowledge_base/tree/clean_tree.json")