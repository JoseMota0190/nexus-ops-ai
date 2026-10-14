"""Gerente IA: reuniones mensuales, palancas y la "red de seguridad" (Fase 6).

Cómo funciona (decidido con el autor):

1. El PROGRAMA junta las métricas del mes y le dice **qué falta** (la planilla).
2. La IA **decide el CÓMO**: mueve las palancas (contratar operadores, contratar
   técnicos, mejorar conversión) y explica por qué.
3. El PROGRAMA **valida** cada decisión: ¿hay plata? ¿la venta justifica más manos?
   Si algo no va, se lo rechaza y le explica por qué.
4. **Red de seguridad:** si tras volver a pensar sigue corto, el programa aplica lo
   mínimo necesario **y lo deja escrito en el acta** (transparente, no cocinado).
5. Todo queda guardado en SQLite: acta, decisiones y avisos.

Regla del concurso: el LLM no es el único método de pronóstico. El cálculo de
cuántos técnicos hacen falta para N ventas/día lo hace el PROGRAMA
(`tecnicos_objetivo_del_mes`), no el modelo.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from llm import LLMClient
from store import Store
from schemas import DecisionGerente, ReunionGerente

from .agenda import nombres_para_alta
from .business import (
    COSTO_POR_MEJORA as _COSTO_MEJORA,
    DIAS_POR_SEMANA,
    META_MES,
    META_TECNICOS,
    SALARIO_OPERADOR_MES,
    SALARIO_TECNICO_MES,
    SEMANAS_POR_MES,
    Empresa,
    tasa_cierre,
    tasa_respuesta,
    tecnicos_necesarios,
)

MAX_MEJORAS = 5
MAX_OPERADORES = 20
MAX_TECNICOS = 12
RONDAS_MAX = 3


# --------------------------------------------------- lo que calcula el PROGRAMA
def ventas_objetivo_del_mes(mes: int) -> float:
    """Ventas/día que deberíamos estar haciendo en este mes (hoja de ruta 6 -> 30)."""
    if mes <= 1:
        return 6.0
    if mes >= META_MES:
        return 30.0
    return 6.0 + (30.0 - 6.0) * (mes - 1) / (META_MES - 1)


def tecnicos_objetivo_del_mes(mes: int) -> int:
    """Técnicos que deberían estar activos este mes (1 por cada 3 ventas/día)."""
    return max(2, min(META_TECNICOS, int(round(ventas_objetivo_del_mes(mes) / 3))))


def ventas_potenciales(empresa: Empresa) -> float:
    """Cuántas ventas/día podría hacer HOY con lo que tiene (cálculo, no opinión)."""
    llamadas = min(empresa.leads_por_dia, empresa.llamadas_por_dia)
    return llamadas * empresa.tasa_respuesta * empresa.tasa_cierre


def operadores_necesarios(ventas_objetivo: float, mejoras: int) -> int:
    """Operadores que hacen falta para `ventas_objetivo` con `mejoras` aplicadas."""
    tasa = tasa_respuesta(mejoras) * tasa_cierre(mejoras)
    if tasa <= 0:
        return MAX_OPERADORES
    return min(MAX_OPERADORES, math.ceil(ventas_objetivo / tasa / 50))


def mejoras_necesarias(ventas_objetivo: float, operadores: int) -> int:
    """Mejoras mínimas para alcanzar `ventas_objetivo` con `operadores`."""
    llamadas = min(operadores * 50, 180 + 40 * MAX_MEJORAS)
    for m in range(MAX_MEJORAS + 1):
        if llamadas * tasa_respuesta(m) * tasa_cierre(m) >= ventas_objetivo:
            return m
    return MAX_MEJORAS


# ------------------------------------------------------------ validación
@dataclass
class Veredicto:
    ok: bool
    motivo: str


def ventas_reales_promedio(store) -> float:
    """Ventas/día del último mes cerrado (datos reales, no el plan)."""
    row = store.conn.execute(
        "SELECT ventas FROM resumen_mes ORDER BY mes DESC LIMIT 1").fetchone()
    if row is None:
        return 6.0
    return float(row["ventas"]) / (SEMANAS_POR_MES * DIAS_POR_SEMANA)


def tope_tecnicos(store, mes: int) -> int:
    """Hasta cuántos técnicos se puede contratar este mes.

    Regla de negocio (no es un guion): no se contrata por delante de lo que la
    venta justifica. Se mira el objetivo del plan Y lo que realmente se vendió.
    """
    objetivo = tecnicos_objetivo_del_mes(mes)
    por_realidad = tecnicos_necesarios(ventas_reales_promedio(store)) + 1
    return min(META_TECNICOS, max(objetivo, por_realidad))


def validar_decision(d: DecisionGerente, empresa: Empresa, caja: float,
                     mes: int, tope: int | None = None) -> Veredicto:
    if d.cantidad <= 0:
        return Veredicto(False, "El Gerente no propuso ninguna acción concreta.")

    if d.palanca.value == "contratar_operadores":
        n = empresa.operadores + d.cantidad
        if n > MAX_OPERADORES:
            return Veredicto(False, f"No podemos pasar de {MAX_OPERADORES} operadores.")
        costo = d.cantidad * SALARIO_OPERADOR_MES
        if caja < costo:
            return Veredicto(False, f"La caja no llega: hacen falta USD {costo:,.0f} y hay USD {caja:,.0f}.")
        return Veredicto(True, f"{d.cantidad} operador(es) por USD {costo:,.0f}/mes.")

    if d.palanca.value == "contratar_tecnicos":
        n = empresa.tecnicos + d.cantidad
        limite = tecnicos_objetivo_del_mes(mes) if tope is None else tope
        if n > limite:
            return Veredicto(
                False,
                f"La venta todavía no justifica tantas manos: este mes el tope es {limite} técnicos.")
        costo = d.cantidad * SALARIO_TECNICO_MES
        if caja < costo:
            return Veredicto(False, f"La caja no llega: hacen falta USD {costo:,.0f} y hay USD {caja:,.0f}.")
        return Veredicto(True, f"{d.cantidad} técnico(s) por USD {costo:,.0f}/mes.")

    if d.palanca.value == "mejorar_conversion":
        if empresa.mejoras + d.cantidad > MAX_MEJORAS:
            return Veredicto(False, f"La base de datos ya está al máximo de {MAX_MEJORAS} mejoras.")
        costo = d.cantidad * _COSTO_MEJORA
        if caja < costo:
            return Veredicto(False, f"La caja no llega: hacen falta USD {costo:,.0f} y hay USD {caja:,.0f}.")
        return Veredicto(True, f"Inversión de USD {costo:,.0f} en base de datos y servicio.")

    return Veredicto(False, "Palanca desconocida.")


def _alta_operadores(empresa: Empresa, store: Store, n: int, caja: float) -> float:
    empresa.operadores += n
    nombres = [f"Operador {empresa.operadores - n + i + 1}" for i in range(n)]
    store.alta_operadores(n, nombres)
    return caja - n * SALARIO_OPERADOR_MES


def _alta_tecnicos(empresa: Empresa, store: Store, n: int, caja: float) -> float:
    desde = empresa.tecnicos
    empresa.tecnicos += n
    altas = nombres_para_alta(n, desde=desde)
    store.alta_tecnicos(n, [x for x, _ in altas], [z for _, z in altas])
    return caja - n * SALARIO_TECNICO_MES


def aplicar_decision(d: DecisionGerente, empresa: Empresa, store: Store,
                     caja: float) -> float:
    """Aplica una decisión aprobada. Devuelve la caja resultante."""
    if d.palanca.value == "contratar_operadores":
        return _alta_operadores(empresa, store, d.cantidad, caja)
    if d.palanca.value == "contratar_tecnicos":
        return _alta_tecnicos(empresa, store, d.cantidad, caja)
    empresa.mejoras += d.cantidad
    return caja - d.cantidad * _COSTO_MEJORA


# --------------------------------------------------------- la reunión mensual
def _que_falta(empresa: Empresa, mes: int, store=None) -> tuple[str, str]:
    """Le dice al Gerente qué falta. El programa calcula; la IA decide cómo llenarlo."""
    objetivo_ventas = ventas_objetivo_del_mes(mes)
    objetivo_tecnicos = tecnicos_objetivo_del_mes(mes)
    potencia = ventas_potenciales(empresa)
    atraso = len(store.ventas_sin_cita()) if store is not None else 0

    if potencia < objetivo_ventas:
        return ("falta_ventas",
                f"Hoy podés hacer {potencia:.0f} ventas/día y hacen falta {objetivo_ventas:.0f}. "
                "Contratá operadores o mejorá la conversión.")
    if empresa.tecnicos < objetivo_tecnicos or atraso > 0:
        detalle = (f" la venta alcanza pero hay {atraso} instalaciones sin turno" if atraso > 0
                   else " la venta alcanza")
        return ("falta_tecnicos",
                f"{detalle.strip().capitalize()}: hay {empresa.tecnicos} técnicos y hacen falta "
                f"{objetivo_tecnicos} para las {objetivo_ventas:.0f} ventas/día.")
    return ("mantener", "Vas bien: este mes no hace falta forzar nada.")


def _prompt(directiva: str, empresa: Empresa, mes: int, aviso: str = "",
            tope: int = 10, reales: float = 0.0, atraso: int = 0) -> str:
    objetivo_ventas = ventas_objetivo_del_mes(mes)
    objetivo_tecnicos = tecnicos_objetivo_del_mes(mes)
    potencia = ventas_potenciales(empresa)
    return (
        f"DIRECTIVA={directiva}\n"
        f"Mes {mes} de {META_MES}. Meta del dueño: {META_TECNICOS} técnicos para el mes {META_MES}.\n"
        f"Ventas/día hoy: {potencia:.0f} (objetivo de este mes: {objetivo_ventas:.0f}; "
        f"último mes cerrado: {reales:.0f}).\n"
        f"Técnicos activos: {empresa.tecnicos} (objetivo: {objetivo_tecnicos}; "
        f"tope de contratación: {tope}).\n"
        f"Operadores: {empresa.operadores}. Mejoras de base/servicio: {empresa.mejoras}.\n"
        f"Instalaciones sin turno: {atraso}. Caja: USD {empresa.caja:,.0f}.\n"
        "Palancas disponibles: contratar operadores, contratar tecnicos, mejorar conversión.\n"
        + (f"AVISO DEL PROGRAMA: {aviso}\n" if aviso else "")
        + "Decidí cuánto mover y por qué."
    )


def _ya_cumple(empresa: Empresa, mes: int, store=None) -> bool:
    return (ventas_potenciales(empresa) >= ventas_objetivo_del_mes(mes)
            and empresa.tecnicos >= tecnicos_objetivo_del_mes(mes))


def _red_seguridad(llm: LLMClient, store: Store, empresa: Empresa,
                   mes: int) -> tuple[list[str], float]:
    """Si el Gerente va corto, el programa aplica lo mínimo y lo deja escrito."""
    avisos: list[str] = []
    inversion = 0.0
    objetivo_ventas = ventas_objetivo_del_mes(mes)
    objetivo_tecnicos = tecnicos_objetivo_del_mes(mes)

    # (a) que la venta alcance: primero operadores, después mejoras de conversión.
    guardia = 0
    while ventas_potenciales(empresa) < objetivo_ventas and guardia < MAX_OPERADORES:
        guardia += 1
        if empresa.operadores < MAX_OPERADORES and (
                empresa.operadores + 1) * 50 <= empresa.leads_por_dia * 1.2:
            empresa.caja = _alta_operadores(empresa, store, 1, empresa.caja)
            inversion += SALARIO_OPERADOR_MES
            store.guardar_decision(
                mes, "contratar_operadores", "1",
                "Corrección del programa: sin más llamadas no se llega a la meta.",
                True, "Red de seguridad: el programa lo corrigió.")
        elif empresa.mejoras < MAX_MEJORAS:
            empresa.mejoras += 1
            empresa.caja -= _COSTO_MEJORA
            inversion += _COSTO_MEJORA
            store.guardar_decision(
                mes, "mejorar_conversion", "1",
                "Corrección del programa: mejorar la base y el servicio sube la conversión.",
                True, "Red de seguridad: el programa lo corrigió.")
        else:
            break

    if ventas_potenciales(empresa) < objetivo_ventas:
        avisos.append(
            f"AVISO: se quedaron en {ventas_potenciales(empresa):.0f} ventas/día "
            f"frente a las {objetivo_ventas:.0f} del objetivo del mes.")

    # (b) que alcancen los técnicos.
    faltan = objetivo_tecnicos - empresa.tecnicos
    if faltan > 0:
        empresa.caja = _alta_tecnicos(empresa, store, faltan, empresa.caja)
        inversion += faltan * SALARIO_TECNICO_MES
        for _ in range(faltan):
            store.guardar_decision(
                mes, "contratar_tecnicos", "1",
                "Corrección del programa: si no sumamos manos, no instalamos todo lo vendido.",
                True, "Red de seguridad: el programa lo corrigió.")
        avisos.append(
            f"AVISO: el Gerente llegó corto a los {objetivo_tecnicos} técnicos; "
            f"el programa sumó {faltan} para no dejar la meta incumplida.")
    return avisos, inversion


def reunion_mensual(llm: LLMClient, store: Store, empresa: Empresa, mes: int,
                    rng: random.Random | None = None) -> dict:
    """Corre la reunión mensual del Gerente IA y devuelve lo que pasó."""
    directiva, razon = _que_falta(empresa, mes, store)
    aprobadas: list[DecisionGerente] = []
    avisos: list[str] = []
    rondas = 0
    inversion = 0.0

    for ronda in range(1, RONDAS_MAX + 1):
        rondas = ronda
        aviso = ""
        prompt = _prompt(directiva, empresa, mes, razon,
                         tope=tope_tecnicos(store, mes),
                         reales=ventas_reales_promedio(store),
                         atraso=len(store.ventas_sin_cita()))
        reunion = llm.complete(
            agent="gerente",
            messages=[{"role": "user", "content": prompt}],
            schema=ReunionGerente,
        )
        for d in reunion.decisiones:
            v = validar_decision(d, empresa, empresa.caja, mes,
                                 tope=tope_tecnicos(store, mes))
            store.guardar_decision(mes, d.palanca.value, str(d.cantidad), d.razon,
                                   v.ok, "" if v.ok else v.motivo)
            if v.ok:
                inversion += _costo(d)
                empresa.caja = aplicar_decision(d, empresa, store, empresa.caja)
                aprobadas.append(d)
                aviso = ""
            else:
                aviso = v.motivo

        if _ya_cumple(empresa, mes, store):
            break
        nueva_directiva, razon = _que_falta(empresa, mes, store)
        if nueva_directiva == directiva and aviso:
            razon = f"{razon} Además: {aviso}"
        directiva = nueva_directiva

    # Red de seguridad: transparencia total, queda escrito en el acta.
    if not _ya_cumple(empresa, mes, store):
        avisos, extra = _red_seguridad(llm, store, empresa, mes)
        inversion += extra

    acta = _escribir_acta(llm, empresa, mes, aprobadas, avisos,
                          tecnicos_objetivo_del_mes(mes))
    store.guardar_acta(mes, acta["titulo"], acta["cuerpo"], acta["meta"])
    return {"mes": mes, "decisiones": aprobadas, "acta": acta,
            "avisos": avisos, "rondas": rondas, "inversion": inversion}


def _costo(d: DecisionGerente) -> float:
    if d.palanca.value == "contratar_operadores":
        return d.cantidad * SALARIO_OPERADOR_MES
    if d.palanca.value == "contratar_tecnicos":
        return d.cantidad * SALARIO_TECNICO_MES
    return d.cantidad * _COSTO_MEJORA


def _escribir_acta(llm: LLMClient, empresa: Empresa, mes: int,
                   decisiones: list[DecisionGerente], avisos: list[str],
                   objetivo_tecnicos: int) -> dict:
    """Pide al Gerente el resumen en criollo (o arma el fallback si no hay red)."""
    titulo = f"Acta {mes} — reunión mensual de gerencia"
    resumen_ia = ""
    try:
        reunion = llm.complete(
            agent="gerente",
            messages=[{"role": "user",
                       "content": (f"DIRECTIVA=escribe_acta\n"
                                   f"Mes {mes}. {len(decisiones)} decisiones aplicadas. "
                                   f"Técnicos: {empresa.tecnicos} de {objetivo_tecnicos}.")}],
            schema=ReunionGerente)
        titulo = reunion.titulo or titulo
        resumen_ia = reunion.resumen
    except Exception:  # noqa: BLE001  (sin red => fallback determinista)
        resumen_ia = ""

    acciones = ", ".join(
        f"{d.cantidad}x {d.palanca.value.replace('_', ' ')}" for d in decisiones) or "sin cambios"
    cuerpo = (
        f"{resumen_ia}\n\n"
        f"Decisiones aplicadas: {acciones}.\n"
        f"Estado: {empresa.operadores} operadores, {empresa.tecnicos} técnicos, "
        f"{empresa.mejoras} mejoras de base/servicio. Caja: USD {empresa.caja:,.0f}.\n"
        + ("".join(f"\n- {a}" for a in avisos) if avisos else "")
    )
    return {"titulo": titulo, "cuerpo": cuerpo,
            "meta": f"{empresa.tecnicos}/{META_TECNICOS} técnicos (meta mes {META_MES})"}
