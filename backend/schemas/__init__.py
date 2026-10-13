"""Esquemas de salida estructurada. Cada agente devuelve JSON validado contra estos."""
from .teleoperador import TeleoperadorResponse, Calificacion
from .despacho import DespachoResponse, AccionDespacho

__all__ = ["TeleoperadorResponse", "Calificacion", "DespachoResponse", "AccionDespacho"]
