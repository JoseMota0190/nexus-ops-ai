"""Teleoperadores: el día a día de llamadas (Fase 3).

"Regla del actor" (decisión del autor): el PROGRAMA calcula el resultado de las
miles de llamadas del día al instante y sin gastar tokens. La IA "actúa" de verdad
solo en las llamadas en vivo que elegimos para la demo (ver `llamada_en_vivo`).

Reglas de negocio:
- 50 llamadas por operador por día (fluctúa, promedia 50).
- De las llamadas ~20 atienden en total (mes 1) y de ahí salen las ventas.
- Cada teleoperador vende 2/día => 6 ventas/día con 3 operadores.
- Si atiende y no compra, se anota el MOTIVO (lista fija con probabilidades).
- Si no atiende, se descarta al primer intento (decisión del autor).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .business import COSTO_POR_LEAD, LLAMADAS_POR_OPERADOR_DIA, Producto, elegir_kit
from .leads import Lead

# Motivos por los que no atienden (se descarta al primero, no se reintenta).
MOTIVOS_NO_RESPUESTA = [
    ("No contestó", 0.62),
    ("Buzón de voz", 0.23),
    ("Cortó la llamada", 0.15),
]

# Motivos por los que atendieron y no compraron (lista fija, decisión del autor).
MOTIVOS_NO_COMPRA = [
    ("Muy caro para mí", 0.30),
    ("Ya tiene otra empresa de seguridad", 0.22),
    ("No le interesa tener alarma", 0.25),
    ("No es el momento / lo piensa", 0.15),
    ("Quiere consultar con la familia", 0.08),
]


@dataclass
class VentaGenerada:
    lead: Lead
    operador_id: int
    kit: str
    accesorio: str | None
    monto: float
    plan: str
    monitoreo: float


@dataclass
class DiaLlamadas:
    leads: int = 0
    llamadas: int = 0
    atendidas: int = 0
    ventas: int = 0
    motivos_no_respuesta: dict[str, int] = field(default_factory=dict)
    motivos_no_compra: dict[str, int] = field(default_factory=dict)
    ventas_lista: list[VentaGenerada] = field(default_factory=list)
    # Log índice-igualado con `leads[:llamadas]`
    estados: list[str] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)
    operadores: list[int] = field(default_factory=list)

    def operador_de(self, i: int) -> int:
        return self.operadores[i] if i < len(self.operadores) else 1

    def motivo_de(self, i: int) -> str:
        return self.motivos[i] if i < len(self.motivos) else ""

    @property
    def tasa_respuesta_real(self) -> float:
        return self.atendidas / self.llamadas if self.llamadas else 0.0

    @property
    def tasa_cierre_real(self) -> float:
        return self.ventas / self.atendidas if self.atendidas else 0.0


def _elegir(pares: list[tuple[str, float]], rng: random.Random) -> str:
    return rng.choices([n for n, _ in pares], weights=[p for _, p in pares], k=1)[0]


def llamadas_planificadas(operadores: int, rng: random.Random) -> int:
    """Llamadas del día: fluctúa alrededor de 50 por operador (no es fijo)."""
    return sum(rng.randint(LLAMADAS_POR_OPERADOR_DIA - 5,
                           LLAMADAS_POR_OPERADOR_DIA + 5)
               for _ in range(operadores))


def simular_dia_de_llamadas(leads_del_dia: list[Lead], empresa, rng: random.Random,
                            semana: int, dia: int) -> DiaLlamadas:
    """Resuelve todas las llamadas del día. Determinista dado el rng."""
    res = DiaLlamadas(leads=len(leads_del_dia))

    plan = llamadas_planificadas(empresa.operadores, rng)
    llamadas = min(plan, len(leads_del_dia))
    res.llamadas = llamadas

    tasa_respuesta = empresa.tasa_respuesta
    tasa_cierre = empresa.tasa_cierre

    # Operador que atiende cada llamada (round-robin entre los activos).
    operadores = list(range(1, empresa.operadores + 1))

    for i, lead in enumerate(leads_del_dia[:llamadas]):
        op = operadores[i % len(operadores)] if operadores else 1
        if rng.random() >= tasa_respuesta:
            # No atendieron: se descarta al primer intento (decisión del autor).
            motivo = _elegir(MOTIVOS_NO_RESPUESTA, rng)
            res.motivos_no_respuesta[motivo] = res.motivos_no_respuesta.get(motivo, 0) + 1
            res.estados.append("perdido")
            res.motivos.append(motivo)
            res.operadores.append(op)
            continue

        res.atendidas += 1
        if rng.random() >= tasa_cierre:
            motivo = _elegir(MOTIVOS_NO_COMPRA, rng)
            res.motivos_no_compra[motivo] = res.motivos_no_compra.get(motivo, 0) + 1
            res.estados.append("no_compra")
            res.motivos.append(motivo)
            res.operadores.append(op)
            continue

        # ¡Venta!
        kit = elegir_kit(rng)
        accesorio = "sensor_inundacion" if rng.random() < 0.2 else (
            "extensor_zona" if rng.random() < 0.2 else None)
        plan_monitoreo = "plus" if kit in ("hogar_plus", "comercial") else "basico"
        precio_kit = Producto.precio(kit)
        precio_accesorio = Producto.precio(accesorio) if accesorio else 0.0
        res.ventas += 1
        res.estados.append("vendido")
        res.motivos.append("Cerró la venta")
        res.operadores.append(op)
        res.ventas_lista.append(VentaGenerada(
            lead=lead,
            operador_id=op,
            kit=kit,
            accesorio=accesorio,
            monto=round(precio_kit + precio_accesorio, 2),
            plan=plan_monitoreo,
            monitoreo=Producto.monitoreo(plan_monitoreo),
        ))
        lead.convertido = True

    return res


def costo_leads(leads: int) -> float:
    """Costo de marketing del día (lo que paga cada lead que llega del formulario)."""
    return round(leads * COSTO_POR_LEAD, 2)
