import pytest
from PyQt6.QtWidgets import QApplication
import sys

# Fixture obligatorio para inicializar QApplication en tests de PyQt
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_overlay_instantiation(qapp):
    """Garantiza que el Overlay se instancie sin errores de sintaxis o de PyQt."""
    from src.ui.overlay import AtziriOverlay
    overlay = AtziriOverlay()
    assert overlay.windowTitle() == "" or overlay is not None
    overlay.close()