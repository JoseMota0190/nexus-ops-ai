"""Esquema del Agente de Despacho.

Recibe la asignación del motor y maneja excepciones (tráfico, lluvia, cancelaciones,
urgencias, garantías). Propone reasignaciones; el MOTOR valida que sean factibles
(el LLM no es el optimizador).
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class AccionDespacho(str, Enum):
    MANTENER = "mantener"
    REASIGNAR = "reasignar"
    REPROGRAMAR = "reprogramar"
    ESCALAR_URGENCIA = "escalar_urgencia"
    CANCELAR = "cancelar"


class DespachoResponse(BaseModel):
    """Decisión del agente de despacho ante una excepción."""
    accion: AccionDespacho
    tecnico_sugerido: str | None = Field(None, description="ID del técnico sugerido si reasigna")
    nueva_ventana: str | None = Field(None, description="Nueva franja horaria si reprograma")
    explicacion: str = Field(..., description="Explicación en lenguaje natural para el dueño")
    urgencia: int = Field(1, ge=1, le=5, description="1=normal, 5=emergencia")
