"""Capa de integración OCR optimizada para tooltips y menús de PoE 2."""

from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image


class OcrEngine:
    """Motor OCR especializado en extracción de texto estructurado sobre fondo oscuro."""

    def __init__(self, tesseract_cmd: str | Path | None = None) -> None:
        if tesseract_cmd:
            resolved_path = Path(tesseract_cmd)
            if resolved_path.exists():
                pytesseract.pytesseract.tesseract_cmd = str(resolved_path)
            else:
                raise FileNotFoundError(f"Ejecutable de Tesseract no encontrado en: {resolved_path}")
        else:
            # Revisa si está en el PATH del sistema o en la ruta por defecto de Windows
            system_tesseract = shutil.which("tesseract")
            default_win_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

            if system_tesseract:
                pytesseract.pytesseract.tesseract_cmd = system_tesseract
            elif default_win_path.exists():
                pytesseract.pytesseract.tesseract_cmd = str(default_win_path)
            else:
                raise FileNotFoundError(
                    "Tesseract no se encuentra en el PATH ni en C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
                )

    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Aumenta la resolución y resalta el contraste manteniendo los detalles de color."""
        array = np.array(image)

        # 1. Redimensionar 2x con interpolación CÚBICA para mejorar la nitidez de la fuente
        height, width = array.shape[:2]
        scaled = cv2.resize(array, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

        # 2. Conversión a escala de grises
        if scaled.ndim == 3:
            gray = cv2.cvtColor(scaled, cv2.COLOR_RGB2GRAY)
        else:
            gray = scaled

        # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # Saca a la luz el texto de color tenue (azul, amarillo, rojo) sobre fondos oscuros
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 4. Otsu's Thresholding (Calcula el umbral óptimo de forma dinámica)
        _, thresholded = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return thresholded

    def extract_text(self, image: Image.Image, preprocess: bool = True) -> str:
        """Extrae texto con configuración óptima para bloques de tooltips."""
        processed = self.preprocess_image(image) if preprocess else np.array(image)

        # --psm 6: Asume un único bloque uniforme de texto (ideal para tooltips)
        # --oem 3: Usa el motor de red neuronal LSTM por defecto
        custom_config = r"--psm 6 --oem 3"

        if processed.ndim == 3:
            rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            text = pytesseract.image_to_string(rgb, config=custom_config)
        else:
            text = pytesseract.image_to_string(processed, config=custom_config)

        return text.strip()