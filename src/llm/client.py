import json
import yaml
from pathlib import Path
from typing import Optional, Type
from pydantic import BaseModel
import requests

# Rutas absolutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"

def _load_config() -> dict:
    """Carga de forma segura el archivo config.yaml desde la raíz."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

CONFIG = _load_config()

class LLMClient:
    """Conector genérico compatible con Ollama / LocalAI / OpenAI API."""
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        model: Optional[str] = None
    ):
        llm_conf = CONFIG.get("llm", {})
        self.base_url = base_url or llm_conf.get("base_url", "http://localhost:11434")
        self.model = model or llm_conf.get("model", "llama3.2")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Envío estándar de prompt de texto."""
        endpoint = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"❌ Error comunicando con el LLM: {e}")
            return "Error al generar la respuesta del LLM."

    def generate_structured(
        self, 
        prompt: str, 
        schema: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> Optional[BaseModel]:
        """Envía el prompt y fuerza al LLM a devolver un JSON estructurado."""
        endpoint = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            raw_text = response.json().get("response", "{}")
            
            data = json.loads(raw_text)
            return schema.model_validate(data)
        except Exception as e:
            print(f"❌ Error parsing JSON estructurado del LLM: {e}")
            return None