# 🎮 Proyecto Atziri (AI Gaming Copilot) — Path of Exile 2

> Asistente contextual e inteligente de IA para Path of Exile 2. Analiza el contexto de juego mediante visión artificial (LLM Vision) y un sistema híbrido de RAG + Tool Calling para ofrecer recomendaciones y guías en tiempo real, sin interactuar con la memoria del cliente.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Architecture](https://img.shields.io/badge/Architecture-Agentic%20RAG%20%2B%20Tools-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-In%20Development-yellow?style=for-the-badge)
![Anti-Ban](https://img.shields.io/badge/Anti--Ban-Safe%20External-brightgreen?style=for-the-badge)

---

## 📌 Visión General

**Proyecto Atziri** nace para resolver la alta barrera de entrada y la sobrecarga de información en **Path of Exile 2**. 

A diferencia de bots o macros tradicionales, este sistema actúa como un **copiloto inteligente**: observa tus capturas de pantalla, comprende tu build importando tu Path of Building (PoB), y consulta tanto bases de datos estáticas (gemas, únicos) como el metagame en tiempo real (poe.ninja, YouTube) para dar consejos precisos. Todo ello manteniendo la aplicación local extremadamente ligera.

### 🛡️ Filosofía Anti-Ban (Safe by Design)
El proyecto prioriza la seguridad de la cuenta por encima de todo:
* ❌ **No** lee memoria (`ReadProcessMemory`).
* ❌ **No** realiza inyección de DLLs ni hooks al proceso del juego.
* ❌ **No** automatiza entradas de teclado/ratón (sin autoplay).
* ✅ **100% Externo:** Funciona analizando capturas de pantalla de forma pasiva y se alimenta de archivos de texto exportados por el usuario (XML de PoB).

---

## 🏗️ Arquitectura Híbrida del Sistema

La aplicación separa estrictamente el conocimiento inmutable (guardado en local) del conocimiento volátil (consultado bajo demanda).

+------------------------------------+
|   Input del Jugador (Capturas)     |
+------------------------------------+
                  |
                  v
+------------------------------------+       +------------------------------------+
|  Parseo de Usuario (Contexto)      | <---> | Path of Building (PoB Integration) |
|  (LLM Vision API + PoB Parser)     |       +------------------------------------+
+------------------------------------+
                  |
                  v
+------------------------------------+
|      Agente LLM (El Cerebro)       | <---> [ Memoria de Sesión de la Build ]
|    (Enrutador + Tool Calling)      |
+------------------------------------+
       |          |          |
       v          v          v
+----------+ +----------+ +----------+
| Base RAG | | APIs Live| | Web/YT   |
| (Local)  | | (Meta)   | | (Guías)  |
+----------+ +----------+ +----------+
  Gemas,      poe.ninja,   Maxroll,
  Únicos,     Precios      Transcripts
  Pasivas

---

## 🛠️ Tech Stack

* **Core & Backend:** Python 3.10+
* **Ingesta de Datos Estáticos:** Playwright, BeautifulSoup (Extracción JIT a JSON).
* **Visión Artificial:** LLM Vision API (sustituyendo a OCR tradicional para mayor precisión semántica).
* **Integración de Terceros:** Parser integrado para Path of Building (PoB XML/JSON) para análisis dinámico del estado del jugador.
* **Base de Datos Vectorial:** ChromaDB (Indexado en local súper ligero mediante *embeddings*).
* **Orquestación RAG y Agentes:** LangChain / LlamaIndex (Para enrutamiento de *Tool Calling*).
* **Procesamiento Dinámico (Zero-Bloat):** `youtube-transcript-api` (extracciones de guías al vuelo sin descargas de vídeo) + API requests (poe.ninja).
* **UI:** Gradio / Streamlit / Discord Bot (Pendiente de decisión).

---

## 🚀 Roadmap de Desarrollo

- [ ] **Fase 1: Base de Conocimiento Estática (RAG)** — Vectorización unificada de Gemas, Objetos Únicos y Mecánicas en ChromaDB. *(En progreso)*
- [x] **Fase 2: Conectores de Usuario** — Parser de XML de Path of Building y análisis de capturas de pantalla integrados.
- [ ] **Fase 3: Inteligencia Dinámica (APIs)** — Herramientas en tiempo real (*Tool Calling*) para poe.ninja, YouTube y Maxroll (Just-In-Time, sin saturar el almacenamiento local).
- [ ] **Fase 4: Cerebro del Agente** — Orquestación del LLM para decidir de forma autónoma cuándo buscar en local, cuándo llamar a una API y cómo mantener el contexto/memoria de la sesión.
- [ ] **Fase 5: Interfaz de Usuario (UI)** — Implementación del frontend amigable para la interacción final con el jugador.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para obtener más información.