"""Monte Carlo: precalcula un historial largo (9 meses) SIN LLM.

Sirve como "histórico de referencia" y como test rápido del motor: corre el
crecimiento del negocio muchas veces con semillas distintas y agrega por día/mes.
No reemplaza a `Simulacion` (que sí guarda todo en SQLite): es la vista barata.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from .business import DIAS_POR_SEMANA, SEMANAS_POR_MES, tasa_cierre, tasa_respuesta
from .leads import generar_leads
from .technicians import asignar_visita, nuevos_tecnicos


@dataclass
class DiaResumen:
    dia: date
    leads: int
    llamadas: int
    atendidas: int
    visitas: int
    conversion_pct: float


@dataclass
class ResumenHistorial:
    dias: list[DiaResumen] = field(default_factory=list)

    @property
    def total_leads(self) -> int:
        return sum(d.leads for d in self.dias)

    @property
    def total_visitas(self) -> int:
        return sum(d.visitas for d in self.dias)

    @property
    def total_atendidas(self) -> int:
        return sum(d.atendidas for d in self.dias)

    def por_mes(self) -> dict[str, dict[str, float]]:
        """Agrega por mes (clave 'YYYY-MM')."""
        out: dict[str, dict[str, float]] = {}
        for d in self.dias:
            k = d.dia.strftime("%Y-%m")
            m = out.setdefault(k, {"leads": 0, "llamadas": 0, "atendidas": 0,
                                   "ventas": 0, "dias": 0})
            m["leads"] += d.leads
            m["llamadas"] += d.llamadas
            m["atendidas"] += d.atendidas
            m["ventas"] += d.visitas
            m["dias"] += 1
        return out


def simular_historial(dias: int = 9 * SEMANAS_POR_MES * DIAS_POR_SEMANA,
                      semilla: int = 42,
                      fecha_inicio: date | None = None) -> ResumenHistorial:
    """Simula `dias` de operación con el motor determinista.

    El crecimiento NO está hardcodeado: cada día se aplica la mejora que el
    Gerente habría ido aplicando, y las tasas salen de `business`.
    """
    fecha_inicio = fecha_inicio or (date.today() - timedelta(days=dias))
    resumen = ResumenHistorial()

    for i in range(dias):
        rng = random.Random(semilla + i)
        dia = fecha_inicio + timedelta(days=i)
        # Mes simulado: cada 4 semanas x 6 días (lo mismo que la simulación real).
        semana = i // DIAS_POR_SEMANA
        mes = semana // SEMANAS_POR_MES + 1
        mejoras = min(5, max(0, mes - 1))

        leads = generar_leads(rng, dia=i, mejoras=mejoras)
        operadores = min(20, 3 + max(0, mes - 1))
        llamadas = min(len(leads), operadores * 50)
        t_resp = tasa_respuesta(mejoras)
        t_cierre = tasa_cierre(mejoras)

        atendidas = sum(1 for _ in range(llamadas) if rng.random() < t_resp)
        tecnicos = nuevos_tecnicos(max(2, min(10, round(mes * 10 / 9))))

        visitas = 0
        for _ in range(atendidas):
            if rng.random() < t_cierre:
                # Elige un lead al azar para agendar (el motor valida capacidad).
                lead = leads[rng.randrange(len(leads))]
                _, vis = asignar_visita(lead, tecnicos, visitas_por_tecnico=3)
                if vis is not None:
                    visitas += 1

        resumen.dias.append(DiaResumen(
            dia=dia, leads=len(leads), llamadas=llamadas, atendidas=atendidas,
            visitas=visitas,
            conversion_pct=round(100.0 * visitas / atendidas, 1) if atendidas else 0.0,
        ))

    return resumen
