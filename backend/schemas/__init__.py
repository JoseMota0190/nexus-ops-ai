"""Esquemas de salida estructurada. Cada agente devuelve JSON validado contra estos."""
from .teleoperador import TeleoperadorResponse, Calificacion
from .despacho import DespachoResponse, AccionDespacho
from .gerente import DecisionGerente, ReunionGerente, Palanca
from .agenda import CoordinacionResponse

__all__ = [
    "TeleoperadorResponse", "Calificacion",
    "DespachoResponse", "AccionDespacho",
    "DecisionGerente", "ReunionGerente", "Palanca",
    "CoordinacionResponse",
]
