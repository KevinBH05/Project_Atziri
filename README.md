# 🎮 AI Gaming Copilot — Path of Exile 2

> Asistente contextual e inteligente de IA para videojuegos complejos. Analiza el contexto de juego mediante visión artificial externa y RAG para ofrecer recomendaciones y guías en tiempo real, sin interactuar con la memoria del cliente ni automatizar el gameplay.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Architecture](https://img.shields.io/badge/Architecture-RAG%20%2B%20CV-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-In%20Design-yellow?style=for-the-badge)
![Anti--Ban](https://img.shields.io/badge/Anti--Ban-Safe%20External%20Overlay-brightgreen?style=for-the-badge)

---

## 📌 Visión General

**AI Gaming Copilot** nace para resolver la alta barrera de entrada y la sobrecarga de información en ARPGs como **Path of Exile 2**. 

A diferencia de bots o macros tradicionales, este sistema actúa como un **copiloto inteligente**: observa la pantalla de forma externa, comprende qué está ocurriendo (items, stats, pasivas, jefes) y consulta bases de conocimiento actualizadas para dar consejos precisos en tiempo real mediante un overlay intuitivo.

### 🛡️ Filosofía Anti-Ban (Safe by Design)
El proyecto prioriza la seguridad de la cuenta por encima de todo:
* ❌ **No** lee memoria (`ReadProcessMemory`).
* ❌ **No** realiza inyección de DLLs ni hooks al proceso del juego.
* ❌ **No** automatiza entradas de teclado/ratón (sin autoplay).
* ✅ **100% Externo:** Funciona analizando capturas de pantalla (OCR/Vision) y sirviendo información sobre una interfaz gráfica superpuesta totalmente independiente.

---

## 🏗️ Arquitectura del Sistema

## 🏗️ Arquitectura del Sistema

```text
+---------------------+
|  Cliente de PoE 2   |
+---------------------+
           |
           | (Captura de pantalla externa)
           v
+---------------------+
|  Módulo Vision/OCR  |
+---------------------+
           |
           | (Extracción de stats / texto)
           v
+---------------------+       +------------------------+
| Extractor Contexto  | ----> | Engine RAG (LlamaIndex)| <--- [ Base de Conocimiento ]
+---------------------+       +------------------------+      (Wikis, Guides, PoE Ninja)
                                           |
                                           v
                              +------------------------+
                              |   LLM (GPT / Gemini)   |
                              +------------------------+
                                           |
                                           v
                              +------------------------+
                              |      Overlay GUI       |
                              +------------------------+
```
---

## 🛠️ Tech Stack

* **Core & Backend:** Python 3.10+
* **Visión Artificial & OCR:** OpenCV, Tesseract OCR *(YOLO en fases avanzadas)*
* **Orquestación RAG:** LlamaIndex
* **Vector DB:** ChromaDB / FAISS
* **Procesamiento de Vídeos:** `yt-dlp` + OpenAI Whisper
* **UI / Overlay:** PyQt / DearPyGui (Pendiente de decisión)

---

## 🚀 Roadmap de Desarrollo

- [ ] **Fase 1: MVP Básico** — Captura manual, integración con LLM y respuestas contextuales simples.
- [ ] **Fase 2: Motor OCR** — Detección automática de texto en pantalla y extracción de stats de items.
- [ ] **Fase 3: Pipeline RAG** — Indexado de wikis, base de datos de items y guías actualizadas del meta.
- [ ] **Fase 4: Build Fingerprinting** — Detección automática de arquetipos, gemas y pasivas del personaje.
- [ ] **Fase 5: Ingesta de Vídeo** — Transcripción e indexado de guías de YouTube mediante embeddings.
- [ ] **Fase 6: Overlay In-Game** — Interfaz flotante externa para lectura cómoda en partida.
- [ ] **Fase 7: Memoria Persistente** — Seguimiento del progreso del personaje a lo largo del tiempo.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para obtener más información.
