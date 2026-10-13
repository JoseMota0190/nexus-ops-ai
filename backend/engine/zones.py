"""Zonas/barrios de CABA con coordenadas aproximadas (lat, lon).

La distancia es euclideana sobre lat/lon escalada: suficiente para simular tiempos
de traslado relativos entre barrios sin depender de datos externos. No es una
ruta real de calles (el AGENTS.md aclara que el motor usa "distancia aproximada").
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zona:
    nombre: str
    lat: float
    lon: float
    # Peso de demanda relativo (más peso => más leads). Plausible para una
    # empresa de alarmas: zonas con más viviendas/comercios generan más demanda.
    peso: float


# ~15 barrios/zonas repartidos por CABA (norte, sur, este, oeste, centro).
ZONAS: list[Zona] = [
    Zona("Palermo", -34.5880, -58.4260, 1.30),
    Zona("Belgrano", -34.5620, -58.4540, 1.15),
    Zona("Caballito", -34.6180, -58.4410, 1.10),
    Zona("Flores", -34.6260, -58.4400, 1.10),
    Zona("Villa Urquiza", -34.5550, -58.4920, 1.05),
    Zona("Recoleta", -34.5900, -58.3920, 1.10),
    Zona("San Nicolas", -34.6080, -58.3900, 0.90),
    Zona("Almagro", -34.5980, -58.4210, 1.05),
    Zona("Boedo", -34.6250, -58.4160, 0.85),
    Zona("Villa Devoto", -34.6060, -58.5150, 0.90),
    Zona("Nunez", -34.5440, -58.4660, 1.00),
    Zona("Saavedra", -34.5430, -58.4530, 0.95),
    Zona("Coghlan", -34.5530, -58.4600, 0.85),
    Zona("Barracas", -34.6350, -58.3820, 0.90),
    Zona("Liniers", -34.6390, -58.5150, 0.80),
]

_POR_NOMBRE = {z.nombre.lower(): z for z in ZONAS}


def zona_por_nombre(nombre: str) -> Zona | None:
    return _POR_NOMBRE.get(nombre.strip().lower())


def distancia_aprox(a: Zona, b: Zona) -> float:
    """Distancia aproximada en km entre dos zonas (euclideana escalada).

    Un grado de latitud ~111 km; de longitud ~111*cos(lat) km. Suficiente para
    comparar traslados relativos dentro de CABA.
    """
    import math
    lat_m = 111.0
    lon_m = 111.0 * math.cos(math.radians((a.lat + b.lat) / 2))
    dx = (a.lon - b.lon) * lon_m
    dy = (a.lat - b.lat) * lat_m
    return math.hypot(dx, dy)
