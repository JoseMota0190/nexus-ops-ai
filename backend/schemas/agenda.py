"""Esquema de la conversación operador ↔ Coordinador de Agenda.

La IA "actúa" en el diálogo (unas pocas veces en la demo); el programa calcula
realmente el turno libre. Este esquema es lo que la IA devuelve cuando habla.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CoordinacionResponse(BaseModel):
    """Turno acordado entre el operador y el coordinador de agenda."""
    turno_propuesto: str = Field(..., description="Turno sugerido: '9am' | '12pm' | '4pm'")
    dia: int = Field(0, ge=0, le=5, description="0=lunes .. 5=sábado")
    cierra_acuerdo: bool = Field(True, description="¿Quedaron acordados día y hora?")
    texto_para_cliente: str = Field(..., description="Mensaje WhatsApp que le llega al cliente")
    nota_interna: str = Field("", description="Nota del coordinador al operador (interna)")
