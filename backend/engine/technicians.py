"""Técnicos y asignación de visitas.

La asignación es por ALGORITMO (zona, ventana horaria, distancia aproximada,
carga). El LLM NO optimiza rutas; solo explica excepciones. El motor valida que
una reasignación propuesta por el LLM sea factible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .leads import Lead
from .zones import ZONAS, Zona, distancia_aprox, zona_por_nombre

# Velocidad "efectiva" en CABA (km/h) para convertir distancia a minutos de traslado.
_VELOCIDAD_KMH = 18.0


@dataclass
class Tecnico:
    id: str
    zona_base: Zona
    visitas_hoy: int = 0
    minutos_ocupado: int = 0          # minutos ya comprometidos en su jornada
    minuto_libre_desde: int = 8 * 60  # arranca a las 08:00 (minuto 0 = 08:00)
    ubicacion_actual: Zona = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.ubicacion_actual is None:
            self.ubicacion_actual = self.zona_base


@dataclass
class Visita:
    lead_id: str
    tecnico_id: str
    barrio: str
    minuto_inicio: int
    duracion_min: int = 120           # 2 h
    traslado_min: int = 0

    @property
    def minuto_fin(self) -> int:
        return self.minuto_inicio + self.duracion_min


def _traslado_min(a: Zona, b: Zona) -> int:
    km = distancia_aprox(a, b)
    return int(round(km / _VELOCIDAD_KMH * 60.0))


def asignar_visita(lead: Lead, tecnicos: list[Tecnico], visitas_por_tecnico: int = 3,
                   duracion_visita_min: int = 120) -> tuple[Tecnico | None, Visita | None]:
    """Elige el técnico más adecuado para el lead. Devuelve (técnico, visita) o (None, None).

    Criterio (en orden): capacidad libre, cercanía al barrio del lead y encaje de
    la ventana horaria preferida. Determinista dado el orden de `tecnicos`.
    """
    zona_lead = zona_por_nombre(lead.barrio)
    if zona_lead is None:
        return None, None

    candidatos = [t for t in tecnicos if t.visitas_hoy < visitas_por_tecnico]
    if not candidatos:
        return None, None

    # Puntaje: menor distancia + menor saturación = mejor.
    def puntaje(t: Tecnico) -> tuple[float, int]:
        dist = distancia_aprox(t.ubicacion_actual, zona_lead)
        satur = t.visitas_hoy
        return (dist, satur)

    tecnico = min(candidatos, key=puntaje)

    traslado = _traslado_min(tecnico.ubicacion_actual, zona_lead)
    inicio = max(tecnico.minuto_libre_desde + traslado,
                 lead.franja_preferida if lead.franja_preferida is not None else 0)
    inicio = max(inicio, 0)

    visita = Visita(
        lead_id=lead.id,
        tecnico_id=tecnico.id,
        barrio=lead.barrio,
        minuto_inicio=inicio,
        duracion_min=duracion_visita_min,
        traslado_min=traslado,
    )
    # Actualiza estado del técnico.
    tecnico.visitas_hoy += 1
    tecnico.minuto_libre_desde = visita.minuto_fin
    tecnico.ubicacion_actual = zona_lead
    return tecnico, visita


def nuevos_tecnicos(n: int) -> list[Tecnico]:
    """Crea n técnicos repartidos por zonas (round-robin)."""
    tecnicos = []
    for i in range(n):
        zona = ZONAS[i % len(ZONAS)]
        tecnicos.append(Tecnico(id=f"TEC-{i + 1:02d}", zona_base=zona))
    return tecnicos
