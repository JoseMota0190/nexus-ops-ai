"""Reloj de simulación.

Convierte tiempo de simulación a tiempo "visual" acelerado. La velocidad se calcula
desde la jornada real (min) y la duración visual (seg), para no hardcodear.

Ejemplo: 8 h reales (480 min = 28800 s) en 240 s visuales => x120.
"""
from __future__ import annotations

from dataclasses import dataclass


def velocidad(jornada_real_min: int, jornada_visual_seg: int) -> float:
    """Factor de aceleración = tiempo real (s) / tiempo visual (s)."""
    if jornada_visual_seg <= 0:
        raise ValueError("jornada_visual_seg debe ser > 0")
    return (jornada_real_min * 60.0) / jornada_visual_seg


@dataclass
class SimClock:
    """Reloj que avanza en minutos de simulación (tiempo real de negocio)."""
    minutos_por_jornada: int = 480   # 8 h
    minuto_actual: int = 0

    @property
    def terminada(self) -> bool:
        return self.minuto_actual >= self.minutos_por_jornada

    @property
    def hora_label(self) -> str:
        # Jornada arranca a las 08:00.
        h = 8 + self.minuto_actual // 60
        m = self.minuto_actual % 60
        return f"{h:02d}:{m:02d}"

    def avanzar(self, minutos: int = 1) -> None:
        self.minuto_actual = min(self.minuto_actual + minutos, self.minutos_por_jornada)

    def reset(self) -> None:
        self.minuto_actual = 0
