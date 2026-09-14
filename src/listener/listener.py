import time
import pyperclip
import keyboard
import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("Ziri.Listener")

class PoEItemListener(QObject):
    # Ahora la señal envía (texto_limpio, tipo_de_objeto)
    item_copied = pyqtSignal(str, str) 

    def __init__(self):
        super().__init__()
        self._is_listening = False

    def sanitize_poe_text(self, raw_text: str) -> str:
        if not raw_text: return ""
        clean_text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
        return "\n".join(lines)

    def start(self):
        if not self._is_listening:
            try:
                # Atajos actualizados a Alt
                keyboard.add_hotkey("alt+z", lambda: self._on_hotkey_pressed("item"))
                keyboard.add_hotkey("alt+x", lambda: self._on_hotkey_pressed("gem"))
                self._is_listening = True
                logger.info("Escuchando: Alt+Z (Objetos) y Alt+X (Gemas).")
            except Exception as e:
                logger.error("Error al registrar hotkeys: %s", e)

    def stop(self):
        if self._is_listening:
            keyboard.unhook_all()
            self._is_listening = False
            logger.info("Listener detenido.")

    def _on_hotkey_pressed(self, item_type: str):
        try:
            pyperclip.copy("")
            keyboard.send("ctrl+c")
            time.sleep(0.05)  # Un pelín más de margen para asegurar la copia
            raw_text = pyperclip.paste()
            
            cleaned_item = self.sanitize_poe_text(raw_text)
            if cleaned_item:
                self.item_copied.emit(cleaned_item, item_type)
        except Exception as e:
            logger.error("Error capturando con %s: %s", item_type, e)