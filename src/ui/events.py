from typing import Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

class ScanWorker(QThread):
    """Hilo secundario para no bloquear la UI durante el OCR y la inferencia del LLM."""
    
    # Señales para devolver resultados o errores a la UI principal
    finished = pyqtSignal(dict)  # Devuelve el resultado del análisis/llm
    error = pyqtSignal(str)      # Devuelve un mensaje de error si algo falla

    def __init__(self, capture_fn, ocr_fn, parser_fn, llm_builder_fn=None):
        super().__init__()
        self.capture_fn = capture_fn
        self.ocr_fn = ocr_fn
        self.parser_fn = parser_fn
        self.llm_builder_fn = llm_builder_fn

    def run(self):
        try:
            # 1. Capturar pantalla / región
            image = self.capture_fn()
            if image is None:
                self.error.emit("No se pudo realizar la captura de pantalla.")
                return

            # 2. Pasar a texto por OCR
            raw_text = self.ocr_fn(image)
            if not raw_text:
                self.error.emit("OCR no detectó texto en la captura.")
                return

            # 3. Parsear texto a objeto de PoE 2
            parsed_item = self.parser_fn(raw_text)
            
            # 4. (Opcional) Pasar por el LLM si está configurado
            analysis_result = {"parsed_item": parsed_item, "raw_text": raw_text}
            if self.llm_builder_fn:
                llm_response = self.llm_builder_fn(parsed_item)
                analysis_result["llm_response"] = llm_response

            self.finished.emit(analysis_result)

        except Exception as e:
            self.error.emit(f"Error procesando el escaneo: {str(e)}")