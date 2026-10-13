"""Monte Carlo: precalcula un historial largo (p. ej. 9 meses) SIN LLM.

Corre el motor de leads/conversión/visitas muchas veces con semillas distintas y
agrega resultados por día/mes. Es el "histórico" que el panel del dueño muestra
como contexto, mientras la jornada en vivo corre aparte a x120.

Rápido: son cientos de miles de eventos simples, segundos en Python puro.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from .leads import LeadsConfig, generar_leads
from .technicians import asignar_visita, nuevos_tecnicos


@dataclass
class DiaResumen:
    dia: date
    leads: int
    visitas: int
    conversion_pct: float
    leads_no_llamar: int


@dataclass
class ResumenHistorial:
    dias: list[DiaResumen] = field(default_factory=list)

    @property
    def total_leads(self) -> int:
        return sum(d.leads for d in self.dias)

    @property
    def total_visitas(self) -> int:
        return sum(d.visitas for d in self.dias)

    def por_mes(self) -> dict[str, dict[str, int]]:
        """Agrega por mes (clave 'YYYY-MM')."""
        out: dict[str, dict[str, int]] = {}
        for d in self.dias:
            k = d.dia.strftime("%Y-%m")
            m = out.setdefault(k, {"leads": 0, "visitas": 0, "dias": 0})
            m["leads"] += d.leads
            m["visitas"] += d.visitas
            m["dias"] += 1
        return out


def simular_historial(dias: int = 270, semilla: int = 42,
                      config: LeadsConfig | None = None,
                      n_tecnicos: int = 10,
                      visitas_por_tecnico: int = 3,
                      fecha_inicio: date | None = None) -> ResumenHistorial:
    """Simula `dias` de operación (p. ej. ~9 meses) con el motor determinista.

    Nota: cada día es independiente (se reseed por día) para que el resultado sea
    estable y paralelizable. La conversión se aplica con la tasa del config.
    """
    config = config or LeadsConfig()
    fecha_inicio = fecha_inicio or (date.today() - timedelta(days=dias))
    resumen = ResumenHistorial()

    for i in range(dias):
        rng = random.Random(semilla + i)
        dia = fecha_inicio + timedelta(days=i)
        leads = generar_leads(config, rng, dia=i)
        tecnicos = nuevos_tecnicos(n_tecnicos)

        visitas = 0
        no_llamar = 0
        for lead in leads:
            if lead.en_no_llamar:
                no_llamar += 1
                continue
            # Conversión: si el lead "convierte", se agenda visita.
            if rng.random() < config.tasa_conversion:
                tec, vis = asignar_visita(lead, tecnicos, visitas_por_tecnico)
                if vis is not None:
                    visitas += 1

        resumen.dias.append(DiaResumen(
            dia=dia,
            leads=len(leads),
            visitas=visitas,
            conversion_pct=round(100.0 * visitas / len(leads), 1) if leads else 0.0,
            leads_no_llamar=no_llamar,
        ))

    return resumen
