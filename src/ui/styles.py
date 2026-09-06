"""Estilos QSS para el Overlay de Atziri."""

OVERLAY_STYLE = """
QWidget#MainFrame {
    background-color: rgba(18, 18, 22, 0.92);
    border: 1px solid #3c3222;
    border-radius: 8px;
}

QLabel {
    color: #e0e0e0;
    font-family: 'Consolas', 'Segoe UI', monospace;
    font-size: 13px;
}

QLabel#HeaderTitle {
    color: #af9250;
    font-size: 15px;
    font-weight: bold;
}

QPushButton {
    background-color: #2a2418;
    color: #af9250;
    border: 1px solid #5a4828;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #3e321e;
    color: #ffd700;
    border: 1px solid #8a6d3b;
}

QPushButton:pressed {
    background-color: #1a150e;
}

QTextEdit {
    background-color: rgba(10, 10, 12, 0.8);
    color: #dcdcdc;
    border: 1px solid #2a2418;
    border-radius: 4px;
    font-family: 'Consolas', 'Segoe UI', monospace;
    font-size: 12px;
}
"""