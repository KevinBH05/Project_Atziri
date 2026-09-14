# 🎮 Proyecto Atziri (AI Gaming Copilot) — Path of Exile 2

> Asistente contextual e inteligente de IA para Path of Exile 2. Lee e ingesta el texto nativo de los objetos copiados desde el juego (`Ctrl + C`) y utiliza un sistema híbrido de RAG + Tool Calling para ofrecer recomendaciones y análisis en tiempo real a través de un overlay transparente, sin interactuar con la memoria del cliente.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Architecture](https://img.shields.io/badge/Architecture-Agentic%20RAG%20%2B%20Tools-orange?style=for-the-badge)
![UI](https://img.shields.io/badge/UI-PyQt6%20Overlay-purple?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-In%20Development-yellow?style=for-the-badge)
![Anti-Ban](https://img.shields.io/badge/Anti--Ban-Safe%20External-brightgreen?style=for-the-badge)

---

## 📌 Visión General

**Proyecto Atziri** nace para resolver la alta barrera de entrada y la sobrecarga de información en **Path of Exile 2**. 

A diferencia de bots o herramientas pesadas de análisis de imagen, este sistema actúa como un **copiloto ultra-ligero de respuesta instantánea**: escucha de forma pasiva el texto nativo copiado al portapapeles (`Ctrl + C`), comprende tu build importando tu Path of Building (PoB), y consulta tanto bases de datos estáticas (gemas, únicos, mecánicas) como el metagame en tiempo real para dar veredictos y consejos precisos sobre ítems, modificadores y precios.

### 🛡️ Filosofía Anti-Ban (Safe by Design)
El proyecto prioriza la seguridad de la cuenta por encima de todo:
* ❌ **No** lee memoria del proceso (`ReadProcessMemory`).
* ❌ **No** realiza inyección de DLLs ni hooks al cliente del juego.
* ❌ **No** automatiza entradas de teclado/ratón (sin autoplay ni macros de acciones en el juego).
* ✅ **100% Pasivo y Externo:** Utiliza únicamente la función nativa del motor de PoE 2 para exportar objetos al portapapeles de Windows (`Ctrl + C`) y se alimenta de archivos de texto/XML creados por el usuario (PoB).

---

## 🏗️ Arquitectura Híbrida del Sistema

La aplicación separa strictly la lectura pasiva de datos en tiempo real del motor de razonamiento del LLM.
```text
+------------------------------------+
|    Jugador en PoE 2 (Ctrl + C)     |
+------------------------------------+
                  |
                  v (Texto Plano Nativo)
+------------------------------------+        +------------------------------------+
| Clipboard Listener & ItemParser    |  <---> | Path of Building (PoB Integration) |
| (Soporte Español / Inglés)         |        +------------------------------------+
+------------------------------------+
                  |
                  v
+------------------------------------+        +------------------------------------+
|     Ziri (El Cerebro Entrenador)   |  <---> | YouTube Guiding & Market Linker    |
|   (Veredicto Directo & Accionable) |        +------------------------------------+
+------------------------------------+
                  |
                  v
+------------------------------------+
|     Overlay Transparente PyQt6     |
|   (Tarjetas, Análisis & Comodines) |
+------------------------------------+
```

 ---

## 🛠️ Tech Stack

* **Core & Backend:** Python 3.10+
* **Ingesta de Objetos:** Listener pasivo de portapapeles (`pyperclip`) y parser regex avanzado multi-idioma (Español / Inglés).
* **Interfaz de Usuario (UI):** PyQt6 (Overlay flotante, transparente e interactivo sobre la ventana del juego).
* **Integración de Terceros:** Parser integrado para Path of Building (PoB XML/JSON) para análisis dinámico del estado del personaje.
* **Base de Datos Vectorial:** ChromaDB (Indexado local súper ligero mediante *embeddings*).
* **Orquestación RAG y Agentes:** SDK de Google Gemini / OpenAI + LangChain para enrutamiento de *Tool Calling*.
* **Procesamiento Dinámico:** `youtube-transcript-api` (extracción de guías al vuelo sin descargas)

---

## 🚀 Roadmap de Desarrollo

- [x] **Fase 1: Ingesta Pasiva de Objetos** — Listener de portapapeles de baja latencia (`listener.py`) e `ItemParser` optimizado para español e inglés sin dependencia de OCR.
- [x] **Fase 2: Base de Conocimiento Estática (RAG)** — Vectorización unificada de Gemas, Objetos Únicos y Mecánicas en ChromaDB.
- [x] **Fase 3: Overlay UI** — Implementación de la ventana transparente e interactiva en PyQt6 para mostrar resultados al instante sobre el juego.
- [x] **Fase 4: Inteligencia Dinámica (APIs)** — Conectores optimizados para poe.ninja (generador de URLs de filtrado directo) y guías en vídeo.
- [ ] **Fase 5: Conector PoB & Cerebro del Agente** — Integración final del estado del personaje con el LLM para recomendaciones personalizadas de ítems.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para obtener más información.