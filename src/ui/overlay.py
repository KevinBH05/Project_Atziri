import sys, os, markdown
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QLineEdit, QStackedWidget, QTextBrowser,
    QSplitter, QScrollArea
)
from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal

from src.ui.styles import OVERLAY_STYLE
from src.ui.components import ItemCardWidget, GemCardWidget, AnalysisOutputWidget
from src.ui.events import ScanWorker
from src.integrations.ninja_links import PoeNinjaBuildsAPI
from src.llm.ziri_brain import ZiriBrain

from src.listener.listener import PoEItemListener    # Escucha de portapapeles
from src.listener.item_parser import ItemParser      # Parser de texto
from src.core.context_manager import ContextManager  # Gestor de contexto para LLM


class ChatWorker(QThread):
    """Worker en segundo plano para procesar el chat con Ziri sin congelar la UI."""
    finished = pyqtSignal(str, bool) 
    error = pyqtSignal(str)

    def __init__(self, prompt: str, context_data: str):
        super().__init__()
        self.prompt = prompt
        self.context_data = context_data
        self.ziri = ZiriBrain()

    def run(self):
        try:
            response, used_db = self.ziri.ask_ziri(
                prompt=self.prompt, 
                context_data=self.context_data, 
                return_db_status=True
            )
            formatted_html = markdown.markdown(response, extensions=['fenced_code', 'tables'])
            self.finished.emit(formatted_html, used_db)
        except Exception as e:
            self.error.emit(str(e))


class ZiriOverlay(QWidget):
    """Ventana Overlay Flotante de ZIRI Copilot para PoE 2."""

    def __init__(self):
        super().__init__()
        self.old_position = QPoint()
        self.is_fullscreen = False
        
        # Historial de escaneos y contexto activo del jugador
        self.last_item_text = ""
        self.last_gem_text = ""
        self.current_processing_type = ""
        self.current_skill = ""
        self.current_ascendancy = ""

        self._init_window_flags()
        self._init_ui()
        
        self.item_parser = ItemParser()
        self.context_manager = ContextManager()
        self.ninja_api = PoeNinjaBuildsAPI(league="Runes of Aldur")

        self.item_listener = PoEItemListener()
        self.item_listener.item_copied.connect(self._on_item_captured)
        self.item_listener.start()

    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # Quitar transparencia para permitir fondo carbón sólido profesional
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.resize(800, 550)

    def _init_ui(self):
        self.setStyleSheet(OVERLAY_STYLE)

        self.main_frame = QWidget(self)
        self.main_frame.setObjectName("MainFrame")
        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Barra superior
        top_bar = QHBoxLayout()
        self.title_label = QLabel("⚡ ZIRI - AI Assistant", self)
        self.title_label.setObjectName("HeaderTitle")
        
        # Botón Pantalla Completa con carácter universal
        self.btn_fullscreen = QPushButton("🗖", self)
        self.btn_fullscreen.setObjectName("HeaderButton")
        self.btn_fullscreen.setFixedSize(28, 28)
        self.btn_fullscreen.setToolTip("Alternar Pantalla Completa")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)

        # Botón Cierre con 'X' limpia centrada
        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("CloseButton")
        btn_close.setFixedSize(28, 28)
        btn_close.setToolTip("Cerrar ZIRI")
        btn_close.clicked.connect(self.close)

        top_bar.addWidget(self.title_label)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_fullscreen)
        top_bar.addWidget(btn_close)
        main_layout.addLayout(top_bar)

        # 2. Contenido
        content_layout = QHBoxLayout()
        
        # Panel lateral
        side_panel = QVBoxLayout()
        self.btn_chat = QPushButton("💬 Chat Ziri")
        self.btn_last_item = QPushButton("🛡️ Último Objeto")
        self.btn_last_gem = QPushButton("💎 Última Gema")
        self.btn_pob = QPushButton("⚙️ Cargar PoB")
        
        for btn in [self.btn_chat, self.btn_last_item, self.btn_last_gem, self.btn_pob]:
            btn.setMinimumHeight(40)
            side_panel.addWidget(btn)
        side_panel.addStretch()

        # Vistas apiladas
        self.stack = QStackedWidget()

        # Vista 0: Chat IA
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Haz una consulta a Ziri... (Enter para enviar)")
        self.chat_input.returnPressed.connect(self._send_chat)
        chat_layout.addWidget(self.chat_display)
        chat_layout.addWidget(self.chat_input)
        self.stack.addWidget(chat_widget)

        # Vista 1: Último Objeto (Tarjeta + Análisis con QSplitter)
        item_widget = QWidget()
        item_layout = QVBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)

        item_splitter = QSplitter(Qt.Orientation.Vertical)
        
        item_scroll = QScrollArea()
        item_scroll.setWidgetResizable(True)
        self.item_card = ItemCardWidget(self)
        item_scroll.setWidget(self.item_card)

        self.item_analysis = AnalysisOutputWidget(self)
        
        item_splitter.addWidget(item_scroll)
        item_splitter.addWidget(self.item_analysis)
        item_splitter.setStretchFactor(0, 3)
        item_splitter.setStretchFactor(1, 7)

        item_layout.addWidget(item_splitter)
        self.stack.addWidget(item_widget)

        # Vista 2: Última Gema (Tarjeta + Análisis con QSplitter)
        gem_widget = QWidget()
        gem_layout = QVBoxLayout(gem_widget)
        gem_layout.setContentsMargins(0, 0, 0, 0)

        gem_splitter = QSplitter(Qt.Orientation.Vertical)
        
        gem_scroll = QScrollArea()
        gem_scroll.setWidgetResizable(True)
        self.gem_card = GemCardWidget(self)
        gem_scroll.setWidget(self.gem_card)

        self.gem_analysis = AnalysisOutputWidget(self)
        
        gem_splitter.addWidget(gem_scroll)
        gem_splitter.addWidget(self.gem_analysis)
        gem_splitter.setStretchFactor(0, 3)
        gem_splitter.setStretchFactor(1, 7)

        gem_layout.addWidget(gem_splitter)
        self.stack.addWidget(gem_widget)

        # Vista 3: PoB
        pob_widget = QWidget()
        pob_layout = QVBoxLayout(pob_widget)
        self.pob_input = QTextEdit()
        self.pob_input.setPlaceholderText("Pega aquí el código base64 de Path of Building...")
        self.btn_update_pob = QPushButton("Actualizar Build")
        pob_layout.addWidget(QLabel("<b>Importar Personaje:</b>"))
        pob_layout.addWidget(self.pob_input)
        pob_layout.addWidget(self.btn_update_pob)
        self.stack.addWidget(pob_widget)

        content_layout.addLayout(side_panel, 1)
        content_layout.addWidget(self.stack, 4)
        main_layout.addLayout(content_layout)

        self.btn_chat.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_last_item.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_last_gem.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.btn_pob.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.main_frame)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.btn_fullscreen.setText("🗖")  # Icono de maximizar
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("🗗")  # Icono de restaurar
            self.is_fullscreen = True

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_fullscreen:
            self.old_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_fullscreen:
            delta = QPoint(event.globalPosition().toPoint() - self.old_position)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_position = event.globalPosition().toPoint()

    def _send_chat(self):
        user_text = self.chat_input.text().strip()
        if not user_text: 
            return
        
        self.chat_display.append(f"<b style='color:#C5A059;'>Tú:</b> {user_text}")
        self.chat_input.clear()
        
        self.chat_display.append("<i>Ziri está pensando...</i>")

        active_context = f"Build activa del jugador: {self.current_skill} ({self.current_ascendancy})"
        
        low_text = user_text.lower()
        if any(keyword in low_text for keyword in ["objeto", "esto", "equipo", "pieza", "arma", "armadura"]):
            if self.current_processing_type == "item" and self.last_item_text:
                active_context += f"\nÚltimo objeto analizado:\n{self.last_item_text}"
            elif self.current_processing_type == "gem" and self.last_gem_text:
                active_context += f"\nÚltima gema analizada:\n{self.last_gem_text}"

        self.chat_worker = ChatWorker(prompt=user_text, context_data=active_context)
        self.chat_worker.finished.connect(self._on_chat_finished)
        self.chat_worker.error.connect(self._on_chat_error)
        self.chat_worker.start()

    def _on_chat_finished(self, response_html: str, used_db: bool):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()

        if used_db:
            db_badge = "<span style='color:#2ECC71; font-size:11px;'>[📚 Datos Oficiales]</span>"
        else:
            db_badge = "<span style='color:#7F8C8D; font-size:11px;'>[🧠 Memoria]</span>"

        message_block = f"<div style='margin-bottom: 12px;'><b style='color:#E6C687;'>Ziri {db_badge}:</b><br>{response_html}</div>"
        self.chat_display.append(message_block)

    def _on_chat_error(self, err_msg: str):
        self.chat_display.append(f"<b style='color:#E74C3C;'>⚠️ Error de Ziri:</b> {err_msg}<br>")

    def _on_item_captured(self, clean_text: str, item_type: str):
        self.current_processing_type = item_type
        
        if item_type == "item":
            self.last_item_text = clean_text
            self.stack.setCurrentIndex(1)
            self.item_analysis.set_text("Evaluando objeto con Ziri...")
        elif item_type == "gem":
            self.last_gem_text = clean_text
            self.stack.setCurrentIndex(2)
            self.gem_analysis.set_text("Evaluando gema con Ziri...")

        tipo_str = "Objeto" if item_type == "item" else "Gema"
        self.chat_display.append(f"<i style='color:#7F8C8D;'>[{tipo_str} capturado en memoria]</i>")

        self._process_text_pipeline(clean_text, item_type)

    def _process_text_pipeline(self, clean_text: str, item_type: str):
        def parse_step(text):
            if item_type == "item":
                return self.item_parser.parse_equipment(text)
            else:
                return self.item_parser.parse_gem(text)

        self.worker = ScanWorker(
            raw_text=clean_text,
            parser_fn=parse_step,
            item_type=item_type,
            skill_name=self.current_skill,
            ascendancy=self.current_ascendancy
        )
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()

    def _on_scan_finished(self, result: dict):
        parsed = result.get("parsed_item", {})
        llm_res = result.get("llm_response", "Análisis completado.")

        if self.current_processing_type == "item":
            self.item_card.update_item(parsed)
            self.item_analysis.set_text(str(llm_res))
        else:
            self.gem_card.update_item(parsed)
            self.gem_analysis.set_text(str(llm_res))

    def _on_scan_error(self, err_msg: str):
        if self.current_processing_type == "item":
            self.item_analysis.set_text(f"❌ Error al procesar el objeto: {err_msg}")
        else:
            self.gem_analysis.set_text(f"❌ Error al procesar la gema: {err_msg}")

    def closeEvent(self, event):
        if hasattr(self, 'item_listener'):
            self.item_listener.stop()
        event.accept()
        os._exit(0)


# Alias de compatibilidad por si alguna referencia antigua busca 'AtziriOverlay'
AtziriOverlay = ZiriOverlay


def launch_overlay():
    app = QApplication(sys.argv)
    overlay = ZiriOverlay()
    overlay.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_overlay()