from typing import Optional
from pydantic import BaseModel, Field

class ItemAnalysisResponse(BaseModel):
    """Estructura de respuesta para la evaluación de un objeto escaneado."""
    item_name: str = Field(description="Nombre del objeto analizado")
    score: int = Field(description="Puntuación de utilidad para la build actual de 1 a 10")
    verdict: str = Field(description="Veredicto rápido: 'Equipar', 'Guardar en alijo' o 'Vender/Descartar'")
    key_reasons: list[str] = Field(description="Motivos principales por los que beneficia o perjudica a la build")
    suggested_changes: Optional[list[str]] = Field(default=None, description="Modificaciones sugeridas (crafted mod, cambio de sockets, etc.)")

class RecommendationResponse(BaseModel):
    """Estructura de respuesta para consultas libres o consejos de optimización."""
    summary: str = Field(description="Resumen ejecutivo del consejo")
    recommendations: list[str] = Field(description="Puntos de acción concretos paso a paso")
    synergies: Optional[list[str]] = Field(default=None, description="Sinergias encontradas con el árbol o habilidades actuales")