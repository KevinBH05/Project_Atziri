"""Capa de integración OCR para leer texto desde capturas de pantalla.

Este módulo es intencionalmente ligero y está centrado en el flujo principal
necesario para un asistente del juego: resolver el ejecutable de Tesseract,
preprocesar la captura y devolver texto limpio reconocido.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image


class OcrEngine:
    """Motor OCR para extraer texto de una captura o imagen de pantalla."""

    def __init__(self, tesseract_cmd: str | Path | None = None) -> None:
        """Inicializa el motor OCR y configura Tesseract.

        Args:
            tesseract_cmd: Ruta al ejecutable de Tesseract. Si no se proporciona,
                se usa la ruta de instalación por defecto dentro de Program Files.
        """
        default_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        resolved_path = Path(tesseract_cmd) if tesseract_cmd else default_path

        if resolved_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(resolved_path)
        elif tesseract_cmd is not None:
            pytesseract.pytesseract.tesseract_cmd = str(resolved_path)
        else:
            raise FileNotFoundError("Tesseract executable not found.")

    def preprocess_image(self, image: Image.Image) -> np.ndarray:
            """Convierte una imagen PIL en un array de OpenCV y la normaliza para OCR.

            Convierte a escala de grises y mejora el contraste para texto blanco o
            brillante sobre fondos oscuros, como tooltips o menús.
            """
            array = np.array(image)
            if array.ndim == 3:
                gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
            else:
                gray = array

            _, thresholded = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            return thresholded

    def extract_text(self, image: Image.Image, preprocess: bool = True) -> str:
        """Extrae texto OCR de una imagen y lo devuelve recortado limpiamente.

        Args:
            image: Imagen PIL a analizar.
            preprocess: Si es True, aplica la pipeline de grises + threshold de OpenCV.

        Returns:
            Texto reconocido con el espacio en blanco alrededor eliminado.
        """
        processed = self.preprocess_image(image) if preprocess else np.array(image)

        if processed.ndim == 3:
            rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            text = pytesseract.image_to_string(rgb)
        else:
            text = pytesseract.image_to_string(processed)

        return text.strip()