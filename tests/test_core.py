import pytest
from src.core.context_manager import ContextManager, ActiveCharacterState

def test_context_manager_singleton():
    """Verifica el comportamiento Singleton del ContextManager."""
    cm1 = ContextManager()
    cm2 = ContextManager()
    assert cm1 is cm2

def test_active_character_null_safety():
    """Garantiza defensas contra None al formatear datos para el LLM."""
    # Instanciamos usando solo los campos genéricos o pasando valores por defecto
    state = ActiveCharacterState()
    state.character_name = "TestTitan"
    state.life = None  # Valor ausente a propósito
    state.spirit = 100
    
    context_dict = state.to_llm_context_dict()
    assert isinstance(context_dict, (dict, str))