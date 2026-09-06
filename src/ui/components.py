from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import Qt

class ItemCardWidget(QWidget):
    """Muestra los datos clave parseados de un objeto escaneado."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.title_label = QLabel("Esperando escaneo...", self)
        self.title_label.setObjectName("HeaderTitle")
        
        self.details_label = QLabel("Presiona el botón para escanear un objeto.", self)
        self.details_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.details_label)

    def update_item(self, parsed_item: dict):
        name = getattr(parsed_item, "name", parsed_item.get("name", "Objeto sin nombre"))
        rarity = getattr(parsed_item, "rarity", parsed_item.get("rarity", "Normal"))
        
        self.title_label.setText(f"[{rarity.upper()}] {name}")
        
        # Formatear el contenido de modificadores
        mods = getattr(parsed_item, "explicit_mods", parsed_item.get("explicit_mods", []))
        mods_str = "\n".join(f"• {m}" for m in mods) if mods else "Sin modificadores detectados."
        self.details_label.setText(mods_str)


class AnalysisOutputWidget(QWidget):
    """Muestra el veredicto del LLM o el historial de respuestas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.text_area = QTextEdit(self)
        self.text_area.setReadOnly(True)
        self.text_area.setPlaceholderText("El veredicto del Proyecto Atziri aparecerá aquí...")

        layout.addWidget(self.text_area)

    def set_text(self, text: str):
        self.text_area.setPlainText(text)

    def append_text(self, text: str):
        self.text_area.append(text)