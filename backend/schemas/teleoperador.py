"""Esquema del Agente Teleoperador.

Salida estructurada que devuelve el modelo en cada turno de diálogo. Se valida con
Pydantic antes de usarse; si el JSON no valida, se reintenta (máx. 2) y hay fallback.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Calificacion(str, Enum):
    CALIDO = "calido"       # quiere visita, con urgencia
    TIBIO = "tibio"         # interesado pero sin urgencia
    FRIELO = "frio"         # solo cotiza, baja prioridad
    NO_LLEVAR = "no_llamar" # tiene el número en el Registro "No Llame"


class TeleoperadorResponse(BaseModel):
    """Una intervención del teleoperador."""
    reply_text: str = Field(..., description="Texto que se le muestra al cliente (español, corto)")
    calificacion: Calificacion
    direccion_valida_caba: bool = Field(..., description="¿La dirección está en CABA?")
    barrio: str | None = Field(None, description="Barrio de CABA inferido de la dirección")
    propone_horario: str | None = Field(None, description="Franja horaria propuesta, p.ej. '10:00-12:00'")
    cierra_cita: bool = Field(False, description="¿Cerró la visita agendada en este turno?")
    en_registro_no_llamar: bool = Field(False, description="¿Cliente en Registro 'No Llame'?")
    requiere_visita_humana: bool = Field(False, description="¿Derivar a un humano?")
    motivo: str = Field("", description="Breve justificación de la calificación")
