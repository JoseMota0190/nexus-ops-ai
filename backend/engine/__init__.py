"""Motor de eventos determinista (SIN LLM).

Genera leads, aplica conversión, gestiona el reloj y asigna técnicos por algoritmo
(zona, ventana horaria, distancia aproximada, carga). El LLM NO es el optimizador.

Todo es reproducible: se configura con una semilla aleatoria.
"""
from .zones import ZONAS, distancia_aprox
from .clock import SimClock, velocidad
from .leads import Lead, generar_leads, LeadsConfig
from .technicians import Tecnico, asignar_visita, Visita, nuevos_tecnicos
from .montecarlo import simular_historial, ResumenHistorial

__all__ = [
    "ZONAS", "distancia_aprox", "SimClock", "velocidad",
    "Lead", "generar_leads", "LeadsConfig",
    "Tecnico", "asignar_visita", "Visita", "nuevos_tecnicos",
    "simular_historial", "ResumenHistorial",
]
