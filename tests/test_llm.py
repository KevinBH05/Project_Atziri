import pytest
from unittest.mock import patch, MagicMock
from src.llm.schemas import ItemAnalysisResponse
from src.llm.client import LLMClient

def test_item_analysis_schema_validation():
    """Valida la integridad de la estructura Pydantic."""
    raw_json = {
        "item_name": "Honour Hold Dusk Shield",
        "score": 8,
        "verdict": "Equipar",
        "key_reasons": ["Aumenta la probabilidad de bloqueo", "Aporta resistencia a fuego necesaria"],
        "suggested_changes": ["Craftear vida plana"]
    }
    
    validated = ItemAnalysisResponse.model_validate(raw_json)
    assert validated.score == 8
    assert validated.verdict == "Equipar"

@patch("requests.post")
def test_llm_client_mock_response(mock_post):
    """Prueba la respuesta estructurada del LLM usando mocks para no consumir API/recursos."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "response": '{"item_name": "Test Shield", "score": 9, "verdict": "Equipar", "key_reasons": ["Top tier"]}'
    }

    client = LLMClient()
    result = client.generate_structured(
        prompt="Analiza este objeto",
        schema=ItemAnalysisResponse
    )

    assert result is not None
    assert result.item_name == "Test Shield"
    assert result.score == 9