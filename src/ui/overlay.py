import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QPoint

from src.ui.styles import OVERLAY_STYLE
from src.ui.components import ItemCardWidget, AnalysisOutputWidget
from src.ui.events import ScanWorker


class AtziriOverlay(QWidget):
    """Ventana de Overlay Flotante Transparente para PoE 2."""

    def __init__(self):
        super().__init__()
        self.old_position = QPoint()
        self._init_window_flags()
        self._init_ui()

    def _init_window_flags(self):
        """Configura la ventana como marco sin bordes, flotante e interactiva."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(380, 500)

    def _init_ui(self):
        self.setStyleSheet(OVERLAY_STYLE)

        # Marco principal contenedor
        self.main_frame = QWidget(self)
        self.main_frame.setObjectName("MainFrame")
        
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)

        # 1. Barra de arrastre superior
        top_bar = QHBoxLayout()
        self.title_label = QLabel("✨ PROYECTO ATZIRI", self)
        self.title_label.setObjectName("HeaderTitle")
        
        btn_close = QPushButton("✕", self)
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.close)

        top_bar.addWidget(self.title_label)
        top_bar.addStretch()
        top_bar.addWidget(btn_close)

        # 2. Tarjeta del ítem
        self.item_card = ItemCardWidget(self)

        # 3. Área de veredicto del LLM
        self.analysis_widget = AnalysisOutputWidget(self)

        # 4. Botón de acción principal
        self.btn_scan = QPushButton("🔍 ESCANEAR OBJETO", self)
        self.btn_scan.clicked.connect(self._on_scan_clicked)

        # Ensamblar layout
        frame_layout.addLayout(top_bar)
        frame_layout.addWidget(self.item_card)
        frame_layout.addWidget(self.analysis_widget)
        frame_layout.addWidget(self.btn_scan)

        # Layout de la ventana externa
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.main_frame)

    # Lógica para permitir arrastrar la ventana desde cualquier parte del marco
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_position)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_position = event.globalPosition().toPoint()

    def _on_scan_clicked(self):
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Procesando...")
        self.analysis_widget.set_text("Capturando pantalla y analizando...")

        # Mocks temporales a reemplazar por la llamada real a capture.py y ocr_engine.py
        def dummy_capture(): return "fake_image_bytes"
        def dummy_ocr(img): return "Item Name: Honour Hold\nRare Shield"
        def dummy_parser(txt): return {"name": "Honour Hold", "rarity": "Rare", "explicit_mods": ["+45 to Armor", "+12% Fire Res"]}

        self.worker = ScanWorker(dummy_capture, dummy_ocr, dummy_parser)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()

    def _on_scan_finished(self, result: dict):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 ESCANEAR OBJETO")
        
        parsed = result.get("parsed_item", {})
        self.item_card.update_item(parsed)
        
        llm_res = result.get("llm_response", "Escaneo completado con éxito. Listo para consultar al LLM.")
        self.analysis_widget.set_text(str(llm_res))

    def _on_scan_error(self, err_msg: str):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 ESCANEAR OBJETO")
        self.analysis_widget.set_text(f"❌ {err_msg}")


def launch_overlay():
    app = QApplication(sys.argv)
    overlay = AtziriOverlay()
    overlay.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_overlay()