"""Esquema del INFORME DE SECTOR.

Cada sector de Nexus Alarm (gerencia, ventas, agenda, facturación) tiene un
"agente" que, cerrado el mes, ANALIZA los números y escribe un informe corto.
El PROGRAMA calcula los números (no el LLM, regla del concurso); la IA los
interpreta y redacta los hallazgos.

Si el cerebro real (AMD) no responde, el informe lo escribe el redactor LOCAL
(ver `engine/redactor.py`): la demo nunca se queda sin informe.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Hallazgo(BaseModel):
    """Un punto que el agente encontró en los números del mes."""

    titulo: str = Field(..., description="Título corto del hallazgo (3-5 palabras)")
    detalle: str = Field(..., description="Qué significa, en criollo (1-2 frases)")
    dato: str = Field("", description="El número que lo respalda (ej. '32 ventas/día')")


class InformeSector(BaseModel):
    """Salida completa del agente de un sector al cerrar el mes."""

    titulo: str = Field(..., description="Encabezado del informe del mes")
    resumen: str = Field(..., description="2-3 frases en criollo, para el dueño")
    hallazgos: list[Hallazgo] = Field(
        default_factory=list, description="Entre 2 y 4 hallazgos concretos del mes")
    recomendacion: str = Field(
        ..., description="Una acción concreta para el mes que viene")
    semaforo: str = Field(
        "verde", description="'verde' | 'ambar' | 'rojo' según cómo viene el sector")


__all__ = ["Hallazgo", "InformeSector"]
