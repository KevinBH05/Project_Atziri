"""Prueba de humo tipo integración para la pipeline de captura y OCR."""

import time

from src.vision.capture import ScreenCapturer
from src.vision.ocr_engine import OcrEngine


def test_screen_capture_and_ocr_flow() -> None:
    """Captura un frame y lo procesa con OCR mientras mide el tiempo de la pipeline."""
    start_time = time.perf_counter()

    capturer = ScreenCapturer(window_title="Path of Exile 2")
    image = capturer.capture_window()

    if image is None:
        image = capturer.capture_screen()

    assert image is not None
    print(f"Captured image size: {image.size}")

    ocr_engine = OcrEngine()
    text = ocr_engine.extract_text(image, preprocess=True)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"Detected text: {text[:200]}" if text else "Detected text: <empty>")
    print(f"Total elapsed time: {elapsed_ms:.2f} ms")

    assert isinstance(text, str)