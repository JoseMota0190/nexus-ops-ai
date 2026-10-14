"""Esquema del Agente Teleoperador.

Salida estructurada que devuelve el modelo cuando "actúa" en una llamada en vivo.
Se valida con Pydantic antes de usarse.

NOTA (decisión del autor, 14 oct): se eliminó el Registro "No Llame" — todos los
clientes llegan pidiendo ser llamados desde la web, así que no hay llamada en frío.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Calificacion(str, Enum):
    CALIDO = "calido"       # quiere visita, con urgencia
    TIBIO = "tibio"         # interesado pero sin urgencia
    FRIELO = "frio"         # solo cotiza, baja prioridad
    NO_COMPRA = "no_compra" # atendió pero decidió no comprar


class TeleoperadorResponse(BaseModel):
    """Una intervención del teleoperador en una llamada en vivo."""
    reply_text: str = Field(..., description="Texto que se le dice al cliente (español, corto)")
    calificacion: Calificacion
    direccion_valida_caba: bool = Field(..., description="¿La dirección está en CABA?")
    barrio: str | None = Field(None, description="Barrio de CABA inferido")
    propone_horario: str | None = Field(None, description="Franja horaria propuesta, p.ej. '10:00-12:00'")
    cierra_cita: bool = Field(False, description="¿Cerró la venta en este turno?")
    producto: str | None = Field(None, description="Kit sugerido: hogar_basico | hogar_plus | comercial")
    motivo_no_compra: str = Field("", description="Si no compró: el motivo anotado (siempre vacío si cerró)")
    requiere_visita_humana: bool = Field(False, description="¿Derivar a un humano?")
    motivo: str = Field("", description="Breve justificación de la calificación")
