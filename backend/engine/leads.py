"""Generación de leads sintéticos (determinista, con semilla).

Volumen parametrizable (no hardcodeado). Distribución por barrio según peso de
demanda y por franja horaria. Cada lead tiene nombre y dirección ficticios mapeados
a un barrio real de CABA (decisión del autor: ficticios en barrios reales).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .zones import ZONAS

# Nombres ficticios (no son personas reales).
_NOMBRES = [
    "Lucía Fernández", "Martín Gómez", "Sofía Ríos", "Diego Peralta",
    "Valentina Ortiz", "Nicolás Barrera", "Camila Duarte", "Julián Sosa",
    "Romina Vega", "Federico Ayala", "Paula Cabrera", "Tomás Ledesma",
]
_CALLES = [
    "Av. Santa Fe", "Calle Corrientes", "Av. Rivadavia", "Calle Florida",
    "Av. Cabildo", "Calle Belgrano", "Av. San Martín", "Calle Maipú",
]


@dataclass
class LeadsConfig:
    leads_por_dia_min: int = 200
    leads_por_dia_max: int = 250
    tasa_conversion: float = 0.20   # ~20% => 40-50 ventas/día
    # Franja horaria de la jornada (0 = 08:00 ... 480 = 16:00)
    franjas_min: int = 0
    franjas_max: int = 480


@dataclass
class Lead:
    id: str
    nombre: str
    direccion: str
    barrio: str
    minuto_llegada: int      # minuto de la jornada en que llega
    urgencia: int            # 1..5
    en_no_llamar: bool       # en Registro "No Llame"
    convertido: bool = False
    # franja preferida que pide el lead (minuto inicio)
    franja_preferida: int | None = None


def generar_leads(config: LeadsConfig, rng: random.Random,
                  dia: int = 0) -> list[Lead]:
    """Devuelve la lista de leads de un día, ordenados por minuto de llegada."""
    n = rng.randint(config.leads_por_dia_min, config.leads_por_dia_max)

    # Pesos de demanda por barrio.
    pesos = [z.peso for z in ZONAS]
    barrios_elegidos = rng.choices(ZONAS, weights=pesos, k=n)

    leads: list[Lead] = []
    for i, zona in enumerate(barrios_elegidos):
        minuto = rng.randint(config.franjas_min, config.franjas_max)
        urgencia = 1 if rng.random() < 0.7 else rng.randint(2, 5)
        no_llamar = rng.random() < 0.08  # 8% en Registro "No Llame"
        nombre = rng.choice(_NOMBRES)
        calle = rng.choice(_CALLES)
        direccion = f"{calle} {rng.randint(100, 4999)}, {zona.nombre}"
        franja = minuto if rng.random() < 0.6 else None
        leads.append(Lead(
            id=f"D{dia}-L{i:03d}",
            nombre=nombre,
            direccion=direccion,
            barrio=zona.nombre,
            minuto_llegada=minuto,
            urgencia=urgencia,
            en_no_llamar=no_llamar,
            franja_preferida=franja,
        ))
    leads.sort(key=lambda l: l.minuto_llegada)
    return leads
