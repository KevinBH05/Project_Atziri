"""Utilidades de captura pasiva de pantalla para PoE 2 y fallback de escritorio.

Este módulo evita intencionalmente la lectura de memoria y la inyección de DLL.
Primero usa una captura basada en la ventana y, si no se detecta ninguna,
recurre a la captura de pantalla completa.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import mss
import pygetwindow as gw
from PIL import Image


class ScreenCapturer:
    """Captura la ventana activa del juego o la pantalla completa en un formato compatible con PIL.

    La clase intenta localizar una ventana por su título (ideal para Path of Exile 2)
    y luego captura su área visible. Si no encuentra una ventana coincidente,
    usa la pantalla principal completa como fallback.
    """

    def __init__(self, window_title: str | None = None) -> None:
        self.window_title = window_title
        self._sct = mss.MSS()

    def find_window(self, title: str | None = None) -> Optional[gw.Win32Window]:
        """Localiza una ventana por nombre usando pygetwindow.

        Args:
            title: Título objetivo de la ventana. Si se omite, se usa el valor
                definido en la instancia.

        Returns:
            El primer objeto de ventana coincidente o None si no se encuentra.
        """
        target_title = title or self.window_title
        if not target_title:
            return None

        windows = gw.getWindowsWithTitle(target_title)
        if not windows:
            return None

        return windows[0]

    def capture_window(self, title: str | None = None) -> Image.Image | None:
        """Captura una ventana concreta como una imagen PIL.

        Args:
            title: Título opcional que sobrescribe el objetivo de la ventana.

        Returns:
            Una imagen PIL o None si no se encuentra ninguna ventana coincidente.
        """
        window = self.find_window(title)
        if window is None:
            return self.capture_screen()

        if getattr(window, "isMinimized", False):
            return self.capture_screen()

        left = max(0, int(window.left))
        top = max(0, int(window.top))
        width = max(1, int(window.width))
        height = max(1, int(window.height))

        monitor = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }

        screenshot = self._sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return image

    def capture_screen(self) -> Image.Image:
        """Captura la pantalla principal como imagen PIL como fallback."""
        monitor = self._sct.monitors[1]  # Monitor principal
        screenshot = self._sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return image

    def save_capture(
        self,
        output_path: str | Path,
        title: str | None = None,
        image: Image.Image | None = None,
    ) -> Path:
        """Captura y guarda una imagen en disco.

        Args:
            output_path: Ruta de destino para el archivo guardado.
            title: Título opcional para localizar la ventana del juego.
            image: Imagen precalculada opcional para guardar.

        Returns:
            La ruta absoluta de la imagen generada.
        """
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if image is None:
            image = self.capture_window(title)

        if image is None:
            raise RuntimeError("No screen capture could be produced.")

        image.save(destination)
        return destination

    def close(self) -> None:
        """Libera el recurso subyacente de MSS."""
        self._sct.close()

    def __enter__(self) -> "ScreenCapturer":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()