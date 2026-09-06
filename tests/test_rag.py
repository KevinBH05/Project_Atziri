import pytest
from pathlib import Path
from src.rag.retriever import KnowledgeRetriever

def test_retriever_initialization():
    """Verifica la carga del retriever si la BBDD existe."""
    try:
        retriever = KnowledgeRetriever()
        assert retriever is not None
    except FileNotFoundError:
        pytest.skip("ChromaDB aún no ha sido ingestado. Ejecuta general_ingestor.py primero.")

def test_retriever_search_top_k():
    """Verifica que el retriever devuelva el número correcto de resultados (top_k=5)."""
    try:
        retriever = KnowledgeRetriever()
        results = retriever.search(query="daño físico", top_k=5)
        
        assert isinstance(results, list)
        assert len(results) <= 5
    except FileNotFoundError:
        pytest.skip("Base de datos de Chroma no encontrada.")