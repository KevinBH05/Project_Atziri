from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser
from PyQt6.QtCore import Qt

class ItemCardWidget(QWidget):
    """Muestra los datos clave parseados de un objeto escaneado."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setObjectName("ItemCardWidget")
        
        self.title_label = QLabel("<b>[Sin objeto cargado]</b>", self)
        self.title_label.setStyleSheet("color: #b0c4de; font-size: 14px; font-weight: bold;")
        
        self.details_label = QLabel("Copia un objeto con Alt+Z en el juego...", self)
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("color: #dcdcdc; font-size: 12px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.details_label)

    def _val(self, obj, key, default=""):
        """Extractor universal seguro para diccionarios y objetos de clase."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def update_item(self, parsed_item):
        if not parsed_item:
            self.title_label.setText("<b>[Objeto no reconocido]</b>")
            self.details_label.setText("No se pudieron extraer los datos del texto.")
            return

        name = self._val(parsed_item, "name", "Objeto sin nombre")
        rarity = self._val(parsed_item, "rarity", "Normal")
        
        self.title_label.setText(f"🛡️ [{rarity.upper()}] {name}")
        
        mods = self._val(parsed_item, "explicit_mods", [])
        
        text_info = f"<b>Rareza:</b> {str(rarity).capitalize()}<br>"
        if mods:
            text_info += "<b>Modificadores:</b><br>" + "".join(f"• {m}<br>" for m in mods)
        else:
            text_info += "Sin modificadores detectados."
            
        self.details_label.setText(text_info)


class GemCardWidget(QWidget):
    """Componente visual en tarjeta para mostrar los datos de la Gema."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.setObjectName("GemCardWidget")
        
        self.title_label = QLabel("<b>[Sin gema cargada]</b>", self)
        self.title_label.setStyleSheet("color: #b0c4de; font-size: 14px; font-weight: bold;")
        
        self.details_label = QLabel("Copia una gema con Alt+X en el juego...", self)
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("color: #dcdcdc; font-size: 12px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.details_label)

    def _val(self, obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def update_item(self, gem_data):
        if not gem_data:
            self.title_label.setText("<b>[Gema no reconocida]</b>")
            self.details_label.setText("No se pudieron extraer los datos del texto.")
            return

        name = self._val(gem_data, 'name', 'Gema Desconocida')
        gem_type = self._val(gem_data, 'gem_type', 'Habilidad / Soporte')
        level = self._val(gem_data, 'level', '-')
        
        self.title_label.setText(f"💎 {name}")
        
        text_info = (
            f"<b>Tipo:</b> {gem_type}<br>"
            f"<b>Nivel:</b> {level}<br>"
        )
        
        tags = self._val(gem_data, 'tags', [])
        if tags:
            text_info += f"<b>Etiquetas:</b> {', '.join(tags)}<br>"
            
        self.details_label.setText(text_info)


class AnalysisOutputWidget(QWidget):
    """Muestra el veredicto del LLM o el historial de respuestas en formato HTML/Markdown."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Cambiamos a QTextBrowser para que soporte HTML limpio e hipervínculos
        self.text_area = QTextBrowser(self)
        self.text_area.setReadOnly(True)
        self.text_area.setOpenExternalLinks(True)
        self.text_area.setPlaceholderText("El veredicto del Proyecto Atziri aparecerá aquí...")

        layout.addWidget(self.text_area)

    def set_text(self, text: str):
        self.text_area.setHtml(text)

    def append_text(self, text: str):
        self.text_area.append(text)