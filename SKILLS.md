# 🛠️ SKILLS.md — AI Gaming Copilot Architecture & Development Standards

> Este documento define las competencias técnicas, patrones de diseño y restricciones clave que deben aplicarse rigurosamente al escribir código en este repositorio.

---

## 1. 🛡️ Anti-Ban Rules & Security Constraints (CRÍTICO)

Cualquier código que viole estas reglas será rechazado inmediatamente:
* **REGLA 01:** Queda **estrictamente prohibido** el uso de `ctypes`, `pymem`, o cualquier función que interactúe con la memoria RAM de los procesos del juego (`ReadProcessMemory`).
* **REGLA 02:** Prohibido el uso de librerías de inyección de DLLs o hooks de API gráfica (DirectX/OpenGL/Vulkan hooks).
* **REGLA 03:** La interacción visual debe hacerse mediante capturas del sistema operativo (`Pillow.ImageGrab`, `pygetwindow` o APIs nativas de Windows/OS) operando de manera 100% pasiva.
* **REGLA 04:** El Overlay debe ser una ventana externa flotante, transparente e independiente (modo `FramelessWindowHint` + `WindowStaysOnTopHint` en PyQt).

---

## 2. 🧩 Patterns & Extensibility Skills

### A. Patrón Factoría / Adaptador para Juegos (`src/adapters/`)
* Todo soporte a un juego debe heredar de `BaseGameAdapter`.
* **Responsabilidad:** Mapear coordenadas de la interfaz, reglas de bounding box para el OCR y parseo de cajas de contexto.
* **Skill requerida:** Desacoplar el motor de IA/RAG de la lógica específica del juego. Ningún módulo en `src/rag/` o `src/llm/` debe saber qué juego se está ejecutando.

### B. Extensibilidad de Fuentes RAG (`src/rag/ingestors/`)
* Cada nueva fuente de datos (wikis, foros, APIs) debe implementar la interfaz `BaseIngestor`.
* El motor RAG (`LlamaIndex`) solo consume objetos normalizados de tipo `Document` enriquecidos con metadatos (`source`, `patch_version`, `timestamp`).

### C. Integración de Herramientas de Terceros (`src/integrations/`)
* **PoB Parsing:** Habilidad para trabajar con manipulación de strings comprimidos:
  * String Base64 → Decodificación bytes → Descompresión Zlib → XML/JSON Parsing.
* Comparación de deltas: El parser de PoB debe exponer métodos de cálculo de diferencias (ej. `compare_stats(current_gear, target_gear)`).

---

## 3. 📸 Vision & OCR Best Practices (`src/vision/`)

* **Preprocesamiento OpenCV obligatorio:** Antes de enviar un recorte a Tesseract/YOLO, es obligatorio:
  1. Escalar la imagen (Interpolación Cúbica).
  2. Convertir a escala de grises.
  3. Aplicar umbralizado binario (Thresholding / Otsu) para aislar el texto de los fondos oscuros del ARPG.
* **Rendimiento:** Evitar procesar pantallas completas a 60 FPS. El motor de visión funcionará **on-demand** (eventos de teclado/click del usuario) o por **polling de baja frecuencia** (1 frame cada 2-3 segundos).

---

## 4. 🧠 RAG & LLM Prompting Guidelines (`src/llm/`)

* **Aislamiento del Proveedor:** `src/llm/client.py` implementa un cliente agnóstico. Cambiar entre OpenAI, Gemini 2.5 o Ollama debe ser configurable mediante `config/config.yaml`.
* **System Prompting:** Los prompts en `config/prompts.py` deben exigir respuestas directas, formateadas en Markdown conciso, optimizadas para lectura rápida dentro de un overlay de pantalla mientras se juega.