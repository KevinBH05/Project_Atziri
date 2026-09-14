# src/ui/styles.py

OVERLAY_STYLE = """
/* Ventana Principal */
QWidget#MainFrame {
    background-color: #0D0F12;
    border: 2px solid #C5A059;
    border-radius: 8px;
}

/* Encabezado */
QLabel#HeaderTitle {
    color: #E6C687;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
}

/* Botones de la Barra Superior (Pantalla completa y Cierre) */
QPushButton#HeaderButton {
    background-color: #1A1D24;
    color: #C5A059;
    font-size: 13px;
    font-weight: bold;
    border: 1px solid #2B3342;
    border-radius: 4px;
    padding: 0px;
    text-align: center;
}

QPushButton#HeaderButton:hover {
    background-color: #2A2415;
    border: 1px solid #C5A059;
    color: #FFF;
}

QPushButton#CloseButton {
    background-color: #1A1D24;
    color: #E74C3C;
    font-size: 14px;
    font-weight: bold;
    border: 1px solid #3D1414;
    border-radius: 4px;
    padding: 0px;
    text-align: center;
}

QPushButton#CloseButton:hover {
    background-color: #3D1414;
    color: #FF6B6B;
    border: 1px solid #E74C3C;
}

/* Botones del Panel Lateral */
QPushButton {
    background-color: #14171E;
    color: #C5A059;
    border: 1px solid #2B3342;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1E232D;
    border: 1px solid #C5A059;
    color: #FFF;
}

QPushButton:pressed {
    background-color: #2B5C8F;
    color: #FFF;
}

/* Cajas de texto y Chat */
QTextBrowser, QTextEdit, QLineEdit {
    background-color: #101218;
    color: #DCDCDC;
    border: 1px solid #2B3342;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #2B5C8F;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #C5A059;
}

/* Divisor Ajustable (QSplitter) */
QSplitter::handle {
    background-color: #2B3342;
    height: 4px;
    border-radius: 2px;
    margin: 2px 0px;
}

QSplitter::handle:hover {
    background-color: #C5A059;
}

/* Barras de Desplazamiento (Scrollbars) */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background-color: #0D0F12;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2B3342;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #C5A059;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""