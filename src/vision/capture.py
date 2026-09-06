from __future__ import annotations

import ctypes
import threading
from pathlib import Path

import mss
import pygetwindow as gw
from PIL import Image

# Configurar DPI Awareness para evitar escalados erróneos
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ScreenCapturer:
    """Captura la ventana activa del juego o la pantalla completa en formato PIL."""

    def __init__(self, window_title: str | None = None) -> None:
        self.window_title = window_title
        self._local = threading.local()

    @property
    def sct(self) -> mss.mss:
        """Instancia aislada de MSS por hilo (thread-safe)."""
        if not getattr(self._local, "sct", None):
            self._local.sct = mss.mss()
        return self._local.sct

    def find_window(self, title: str | None = None) -> gw.Win32Window | None:
        """Localiza una ventana visible y no minimizada por título parcial."""
        target_title = title or self.window_title
        if not target_title:
            return None

        try:
            windows = [
                w for w in gw.getWindowsWithTitle(target_title)
                if w.visible and not w.isMinimized
            ]
            return windows[0] if windows else None
        except Exception:
            return None

    def capture_window(self, title: str | None = None) -> Image.Image:
        """Captura la ventana especificada o cae en fallback a pantalla completa."""
        window = self.find_window(title)

        if window is None:
            return self.capture_screen()

        left, top, width, height = int(window.left), int(window.top), int(window.width), int(window.height)

        if width <= 0 or height <= 0:
            return self.capture_screen()

        # MSS soporta coordenadas negativas (monitores secundarios/ventanas maximizadas)
        monitor = {"left": left, "top": top, "width": width, "height": height}

        try:
            screenshot = self.sct.grab(monitor)
            # mss devuelve BGRA nativamente; es más eficiente convertir desde 'RGBX'
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except mss.exception.ScreenShotError:
            return self.capture_screen()

    def capture_screen(self) -> Image.Image:
        """Captura el monitor principal completo."""
        monitor = self.sct.monitors[1]
        screenshot = self.sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def save_capture(
        self,
        output_path: str | Path,
        title: str | None = None,
        image: Image.Image | None = None,
    ) -> Path:
        """Guarda la captura en disco creando la ruta si no existe."""
        destination = Path(output_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        img_to_save = image or self.capture_window(title)
        img_to_save.save(destination)
        return destination

    def close(self) -> None:
        """Libera los recursos de MSS asociados al hilo actual."""
        sct_instance = getattr(self._local, "sct", None)
        if sct_instance is not None:
            sct_instance.close()
            self._local.sct = None

    def __enter__(self) -> ScreenCapturer:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()