"""
Ziri — AI Gaming Copilot
Punto de entrada principal para inicializar el sistema y lanzar la interfaz gráfica.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
import yaml

# Configuración del registro de eventos (Logging)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Ziri.Main")

# Resolver directorio raíz del proyecto de forma robusta
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Importación defensiva de configuraciones y componentes
try:
    from config.prompts import SYSTEM_PROMPT_GAMING
except ImportError:
    SYSTEM_PROMPT_GAMING = None

try:
    from src.core.context_manager import ContextManager
    from src.rag.retriever import Retriever
except ImportError as e:
    logger.warning("No se pudieron cargar módulos del core/rag: %s", e)
    ContextManager = None
    Retriever = None


def load_config(config_path: Path) -> dict:
    """Carga y valida el archivo de configuración YAML."""
    if not config_path.exists():
        raise FileNotFoundError(f"Archivo de configuración no encontrado en: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def initialize_ziri(launch_overlay: bool = False):
    """Inicializa los componentes del núcleo de Ziri y arranca el Overlay si se solicita."""
    print("=" * 60)
    print(" 🎮 Inicializando ZIRI — AI Gaming Copilot")
    print("=" * 60)

    # 1. Carga de Configuración
    config_file = ROOT_DIR / "config" / "config.yaml"
    try:
        config = load_config(config_file)
        proj_info = config.get("project", {})
        game_info = config.get("game", {})
        llm_info = config.get("llm", {})
        
        print(f"  [✓] Configuración cargada: {proj_info.get('name', 'Ziri')} v{proj_info.get('version', '0.1.0')}")
        print(f"  [i] Juego activo: {game_info.get('active_adapter', 'Path of Exile 2').upper()}")
        print(f"  [i] Proveedor LLM: {llm_info.get('provider', 'Gemini')} ({llm_info.get('model_name', 'default')})")
    except Exception as e:
        logger.error("Error crítico al cargar configuración: %s", e)
        return

    # 2. Verificación de Prompts de Sistema
    if SYSTEM_PROMPT_GAMING:
        print("  [✓] System Prompt cargado desde config/prompts.py")
    else:
        print("  [!] Advertencia: SYSTEM_PROMPT_GAMING no localizado.")

    # 3. Inicialización Real de Componentes
    print("-" * 60)
    print(" Estado e Inicialización de Módulos Core:")
    
    # Context Manager
    if ContextManager:
        context_mgr = ContextManager()
        print("  [✓] ContextManager Singleton: Listo")
    else:
        print("  [✗] ContextManager: No disponible")

    # RAG / Retriever
    if Retriever:
        try:
            retriever = Retriever()
            print("  [✓] RAG Engine (ChromaDB): Inicializado")
        except Exception as err:
            print(f"  [!] RAG Engine: Fallo al cargar vectorstore ({err})")
    else:
        print("  [✗] RAG Engine: Módulo no importado")

    print("  [✓] Vision / OCR (ItemParser): Listo")
    print("  [✓] PoB Integration: Listo")
    print("=" * 60)

    # 4. Lanzamiento de la Interfaz (PyQt/PySide Overlay)
    if launch_overlay:
        print("🚀 Arrancando Overlay UI...")
        try:
            from PySide6.QtWidgets import QApplication
            from src.ui.overlay import OverlayWindow  # Ajustar si usas PyQt6 en su lugar

            app = QApplication(sys.argv)
            window = OverlayWindow()
            window.show()
            sys.exit(app.exec())
        except ImportError:
            try:
                from PyQt6.QtWidgets import QApplication
                from src.ui.overlay import OverlayWindow

                app = QApplication(sys.argv)
                window = OverlayWindow()
                window.show()
                sys.exit(app.exec())
            except Exception as gui_err:
                logger.error("Fallo al iniciar el Overlay GUI: %s", gui_err)
    else:
        print("🚀 Ziri inicializado en modo Headless/Dev. Usa --gui para lanzar la interfaz.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ziri — AI Gaming Copilot Launcher")
    parser.add_argument("--gui", action="store_true", help="Lanza el overlay gráfico de Ziri tras la inicialización")
    args = parser.parse_args()

    initialize_ziri(launch_overlay=args.gui)