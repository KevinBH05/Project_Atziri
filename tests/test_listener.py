import pytest
from unittest.mock import MagicMock, patch
from src.listener import PoEItemListener


def test_listener_sanitize_poe_text_spanish():
    """Verifica que el listener limpia correctamente el texto en español copiado desde el juego."""
    raw_clipboard_text = (
        "Clase de objeto: Escudos\r\n"
        "Rareza: Único\r\n"
        "Ocaso\xa0\r\n"
        "Fortaleza glacial perfeccionada con runas\r\n"
        "--------\r\n"
        "Armadura: 1306 (augmented)\r\n"
    )

    listener = PoEItemListener(on_item_copied_callback=MagicMock())
    sanitized = listener.sanitize_poe_text(raw_clipboard_text)

    # Debe eliminar \r\n y sustituir caracteres invisibles como \xa0
    assert "\r" not in sanitized
    assert "\xa0" not in sanitized
    assert "Clase de objeto: Escudos" in sanitized
    assert "Rareza: Único" in sanitized


def test_is_poe_item_validation():
    """Comprueba la detección de textos válidos de PoE frente a texto aleatorio."""
    listener = PoEItemListener(on_item_copied_callback=MagicMock())

    valid_spanish_item = "Clase de objeto: Báculos\nRareza: Raro\n--------"
    valid_english_item = "Item Class: Shields\nRarity: Unique\n--------"
    invalid_text = "Hola, esta es una frase cualquiera copiada al portapapeles."

    assert listener._is_poe_item(valid_spanish_item) is True
    assert listener._is_poe_item(valid_english_item) is True
    assert listener._is_poe_item(invalid_text) is False


@patch("pyperclip.paste")
def test_check_clipboard_triggers_callback(mock_paste):
    """Simula la copia de un ítem al portapapeles y valida el callback."""
    raw_item_text = (
        "Clase de objeto: Escudos\n"
        "Rareza: Único\n"
        "Ocaso\n"
        "--------\n"
        "Requiere: Nivel 70"
    )
    mock_paste.return_value = raw_item_text

    mock_callback = MagicMock()
    listener = PoEItemListener(on_item_copied_callback=mock_callback)

    # Primera comprobación: debe detectar el ítem y devolverlo limpio
    cleaned_item = listener.check_clipboard()
    assert cleaned_item is not None
    assert "Clase de objeto: Escudos" in cleaned_item

    # Segunda comprobación seguida con el mismo texto: no debe duplicar la lectura
    duplicate_check = listener.check_clipboard()
    assert duplicate_check is None


@patch("pyperclip.paste")
def test_listener_loop_thread(mock_paste):
    """Verifica que el demonio en segundo plano procesa y envía el texto al callback."""
    mock_paste.return_value = "Clase de objeto: Anillos\nRareza: Normal\n--------"
    
    mock_callback = MagicMock()
    listener = PoEItemListener(on_item_copied_callback=mock_callback)

    listener.start(interval=0.05)
    # Esperamos un pequeño margen para que el hilo ejecute al menos una vuelta
    import time
    time.sleep(0.15)
    listener.stop()

    assert mock_callback.called
    assert "Clase de objeto: Anillos" in mock_callback.call_args[0][0]