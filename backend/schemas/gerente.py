"""Esquema del Gerente IA.

La IA decide QUÉ palanca mover y por qué. El PROGRAMA valida si la decisión es
posible (plata, turnos, capacidad) y le devuelve el aviso si va corto: es la
"red de seguridad" acordada con el autor (ver AGENTS.md).
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Palanca(str, Enum):
    CONTRATAR_OPERADORES = "contratar_operadores"
    CONTRATAR_TECNICOS = "contratar_tecnicos"
    MEJORAR_CONVERSION = "mejorar_conversion"


class DecisionGerente(BaseModel):
    """Una palanca que el Gerente quiere mover este mes."""
    palanca: Palanca
    cantidad: int = Field(0, ge=0, le=20, description="Cuántos contrata o de qué nivel es la mejora")
    razon: str = Field(..., description="Por qué la toma (español, para el acta)")


class ReunionGerente(BaseModel):
    """Salida completa de la reunión mensual del Gerente IA."""
    decisiones: list[DecisionGerente] = Field(
        default_factory=list, description="Palancas que quiere mover este mes")
    titulo: str = Field(..., description="Encabezado del acta del mes")
    resumen: str = Field(..., description="2-3 frases en criollo, para el dueño")
    presion: str = Field("sin novedad", description="Si va corto contra la meta, lo dice acá")


__all__ = ["Palanca", "DecisionGerente", "ReunionGerente"]
