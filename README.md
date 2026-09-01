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

```mermaid
graph TD
    A[🎮 Cliente de PoE 2] -->|Captura de Pantalla| B[📸 Módulo Vision / OCR]
    B -->|Extracción de Contexto / Stats| C[🧠 Extractor de Contexto]
    C -->|Query Enriquecida| D[🔍 Engine RAG / LlamaIndex]
    E[(📚 Base de Conocimiento\nWikis, Guides, PoE Ninja)] -->|Context Retrieval| D
    D -->|Prompt + Contexto| F[🤖 LLM Provider\nGPT / Gemini]
    F -->|Respuesta Generada| G[💻 Overlay GUI]
