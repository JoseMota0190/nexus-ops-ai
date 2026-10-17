"""Esquemas del Enjambre — la "Sala de Agentes".

A partir del mes 7 la empresa la opera un enjambre de agentes que **dialogan
entre ellos** y toman las decisiones del día. El motor calcula las opciones
válidas (turnos libres de la pizarra, técnicos candidatos por zona) y hace de
**árbitro**: la IA elige, el programa valida que la elección sea posible. Nunca
se decide algo imposible.

Estos esquemas son lo que devuelve cada agente cuando "habla" en la sala:

  - TurnoOperador   -> el teleoperador propone a dónde mandar una venta cerrada
  - CoordinacionResponse (ya existente) -> el coordinador de agenda elige el turno
  - TurnoTecnicos   -> el coordinador de técnicos elige a quién mandar
  - DespachoResponse (ya existente) -> el despacho reacciona ante un imprevisto

El volumen (cuántas llamadas, quién atiende, quién compra) sigue calculándolo el
programa con Monte Carlo: la IA decide LO ESTRATÉGICO, la planilla hace las cuentas.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TurnoOperador(BaseModel):
    """El teleoperador propone al coordinador a dónde mandar una venta recién cerrada."""
    habla: str = Field(..., description="Lo que el teleoperador le dice al coordinador (corto, español)")
    dia_preferido: int = Field(0, ge=0, le=5, description="0=lunes .. 5=sábado")
    turno_preferido: str = Field("9am", description="'9am' | '12pm' | '4pm' (lo que pidió el cliente)")


class TurnoTecnicos(BaseModel):
    """El coordinador de técnicos elige un técnico de la lista de candidatos."""
    habla: str = Field(..., description="Lo que le dice al teleoperador al mandar el técnico")
    tecnico_id: str = Field(..., description="ID del técnico elegido, de los candidatos que pasó el motor")
    explicacion: str = Field("", description="Por qué ese técnico y no otro (zona, recorrido, carga)")
