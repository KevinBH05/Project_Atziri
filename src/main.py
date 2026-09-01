"""
Ziri — AI Gaming Copilot
Punto de entrada principal para verificar la inicialización del sistema.
"""

import os
import sys
from pathlib import Path
import yaml

# Asegurar que la raíz del proyecto esté en el PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

# Importar el prompt del sistema desde la carpeta config
try:
    from config.prompts import SYSTEM_PROMPT_GAMING
except ImportError:
    SYSTEM_PROMPT_GAMING = None


def load_config(config_path: Path) -> dict:
    """Carga el archivo de configuración YAML."""
    if not config_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración en: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def initialize_ziri():
    """Inicializa los componentes clave de Ziri y muestra el estado en consola."""
    print("=" * 60)
    print(" 🎮 Inicializando ZIRI — AI Gaming Copilot")
    print("=" * 60)

    # 1. Cargar configuración
    config_file = ROOT_DIR / "config" / "config.yaml"
    try:
        config = load_config(config_file)
        print(f"  [✓] Configuración cargada correctamente ({config['project']['name']} v{config['project']['version']})")
        print(f"  [i] Juego activo: {config['game']['active_adapter'].upper()}")
        print(f"  [i] Proveedor LLM: {config['llm']['provider']} ({config['llm']['model_name']})")
    except Exception as e:
        print(f"  [✗] Error al cargar la configuración: {e}")
        return

    # 2. Verificar Prompt del Sistema
    if SYSTEM_PROMPT_GAMING:
        print("  [✓] System Prompt cargado correctamente desde config/prompts.py")
    else:
        print("  [!] Advertencia: No se pudo importar SYSTEM_PROMPT_GAMING")

    # 3. Estado de la arquitectura de Ziri
    print("-" * 60)
    print(" Estado de Módulos (Entorno de Desarrollo):")
    print("  • Vision / OCR: Ready (Pausa)")
    print("  • PoB Integration: Ready (Pausa)")
    print("  • RAG Engine: Ready (Pausa)")
    print("  • Overlay GUI: Ready (Pausa)")
    print("=" * 60)
    print("🚀 Ziri inicializado con éxito. Listo para comenzar el desarrollo por fases.")


if __name__ == "__main__":
    initialize_ziri()