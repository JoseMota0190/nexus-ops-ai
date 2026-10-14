"""Leads: personas que llenaron el formulario web pidiendo que las llamen.

Decisión del autor (14 oct): TODOS los clientes llegan desde la web pidiendo ser
llamados, así que NO hay llamada en frío y se eliminó el Registro "No Llame".

Cada lead tiene nombre, teléfono y barrio ficticios (decisión del autor: ficticios
en barrios reales de CABA). El volumen no está hardcodeado: sale de
`business.leads_por_dia(...)`, que depende de las mejoras de base de datos.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .business import leads_por_dia
from .zones import ZONAS

# Nombres ficticios (no son personas reales).
_NOMBRES = [
    "Lucía Fernández", "Martín Gómez", "Sofía Ríos", "Diego Peralta",
    "Valentina Ortiz", "Nicolás Barrera", "Camila Duarte", "Julián Sosa",
    "Romina Vega", "Federico Ayala", "Paula Cabrera", "Tomás Ledesma",
    "Micaela Ferreyra", "Agustín Coronel", "Bianca Serrano", "Ezequiel Ponce",
    "Carla Roldán", "Matías Quiroga", "Antonella Paz", "Ramiro Ledezma",
]
_CALLES = [
    "Av. Santa Fe", "Calle Corrientes", "Av. Rivadavia", "Calle Florida",
    "Av. Cabildo", "Calle Belgrano", "Av. San Martín", "Calle Maipú",
]


@dataclass
class Lead:
    """Un contacto que pidió ser llamado (formulario web)."""
    id: str
    nombre: str
    telefono: str
    direccion: str
    barrio: str
    tipo: str                     # "hogar" | "comercio"
    minuto_llegada: int           # minuto de la jornada en que dejó el dato
    urgencia: int                 # 1..5
    franja_preferida: int | None  # franja que pidió (minuto) o None
    convertido: bool = False
    descartado: bool = False

    @property
    def origen(self) -> str:
        return "web"


def _telefono(rng: random.Random) -> str:
    return f"+54 9 11 {rng.randint(4000, 6999)}-{rng.randint(1000, 9999)}"


def generar_leads(rng: random.Random, dia: int = 0,
                  mejoras: int = 0,
                  volumen: int | None = None,
                  franjas_min: int = 0, franjas_max: int = 480) -> list[Lead]:
    """Leads del día, ordenados por minuto de llegada.

    `volumen` si ya se calculó (ej. los que sobran de ayer); si no, sale de
    `business.leads_por_dia(mejoras)`.
    """
    n = volumen if volumen is not None else leads_por_dia(mejoras)

    pesos = [z.peso for z in ZONAS]
    barrios_elegidos = rng.choices(ZONAS, weights=pesos, k=n)

    leads: list[Lead] = []
    for i, zona in enumerate(barrios_elegidos):
        minuto = rng.randint(franjas_min, franjas_max)
        urgencia = 1 if rng.random() < 0.7 else rng.randint(2, 5)
        # 60% piden una franja preferida; el resto no.
        franja = minuto if rng.random() < 0.6 else None
        nombre = rng.choice(_NOMBRES)
        calle = rng.choice(_CALLES)
        direccion = f"{calle} {rng.randint(100, 4999)}, {zona.nombre}"
        # ~85% hogar / 15% comercio (una empresa de alarmas).
        tipo = "hogar" if rng.random() < 0.85 else "comercio"
        leads.append(Lead(
            id=f"D{dia}-L{i:03d}",
            nombre=nombre,
            telefono=_telefono(rng),
            direccion=direccion,
            barrio=zona.nombre,
            tipo=tipo,
            minuto_llegada=minuto,
            urgencia=urgencia,
            franja_preferida=franja,
        ))
    leads.sort(key=lambda l: l.minuto_llegada)
    return leads
