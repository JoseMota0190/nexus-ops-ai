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
from idioma import t
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
        return Veredicto(False, t("The Manager did not propose any concrete action.",
                                  "El Gerente no propuso ninguna acción concreta."))

    if d.palanca.value == "contratar_operadores":
        n = empresa.operadores + d.cantidad
        if n > MAX_OPERADORES:
            return Veredicto(False, t(f"We can't go past {MAX_OPERADORES} operators.",
                                      f"No podemos pasar de {MAX_OPERADORES} operadores."))
        costo = d.cantidad * SALARIO_OPERADOR_MES
        if caja < costo:
            return Veredicto(False, t(
                f"Cash is short: USD {costo:,.0f} needed and USD {caja:,.0f} available.",
                f"La caja no alcanza: hacen falta USD {costo:,.0f} y hay USD {caja:,.0f}."))
        return Veredicto(True, t(f"{d.cantidad} operator(s) for USD {costo:,.0f}/month.",
                                 f"{d.cantidad} operador(es) por USD {costo:,.0f}/mes."))

    if d.palanca.value == "contratar_tecnicos":
        n = empresa.tecnicos + d.cantidad
        limite = tecnicos_objetivo_del_mes(mes) if tope is None else tope
        if n > limite:
            return Veredicto(
                False,
                t(f"Sales don't yet justify that many hands: this month the cap is {limite} technicians.",
                  f"Las ventas todavía no justifican tantas manos: este mes el tope es {limite} técnicos."))
        costo = d.cantidad * SALARIO_TECNICO_MES
        if caja < costo:
            return Veredicto(False, t(
                f"Cash is short: USD {costo:,.0f} needed and USD {caja:,.0f} available.",
                f"La caja no alcanza: hacen falta USD {costo:,.0f} y hay USD {caja:,.0f}."))
        return Veredicto(True, t(f"{d.cantidad} technician(s) for USD {costo:,.0f}/month.",
                                 f"{d.cantidad} técnico(s) por USD {costo:,.0f}/mes."))

    if d.palanca.value == "mejorar_conversion":
        if empresa.mejoras + d.cantidad > MAX_MEJORAS:
            return Veredicto(False, t(
                f"The database is already at the maximum of {MAX_MEJORAS} improvements.",
                f"La base ya está en el máximo de {MAX_MEJORAS} mejoras."))
        costo = d.cantidad * _COSTO_MEJORA
        if caja < costo:
            return Veredicto(False, t(
                f"Cash is short: USD {costo:,.0f} needed and USD {caja:,.0f} available.",
                f"La caja no alcanza: hacen falta USD {costo:,.0f} y hay USD {caja:,.0f}."))
        return Veredicto(True, t(f"Investment of USD {costo:,.0f} in database and service.",
                                 f"Inversión de USD {costo:,.0f} en base y servicio."))

    return Veredicto(False, t("Unknown lever.", "Palanca desconocida."))


def _alta_operadores(empresa: Empresa, store: Store, n: int, caja: float) -> float:
    empresa.operadores += n
    nombres = [t(f"Operator {empresa.operadores - n + i + 1}",
                 f"Operador {empresa.operadores - n + i + 1}") for i in range(n)]
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
                t(f"Today you can do {potencia:.0f} sales/day and {objetivo_ventas:.0f} are needed. "
                  "Hire operators or improve conversion.",
                  f"Hoy se pueden hacer {potencia:.0f} ventas/día y hacen falta {objetivo_ventas:.0f}. "
                  "Contratar operadores o mejorar la conversión."))
    if empresa.tecnicos < objetivo_tecnicos or atraso > 0:
        if atraso > 0:
            detalle = t(f" sales are enough but there are {atraso} installs without a slot",
                        f" las ventas alcanzan pero hay {atraso} instalaciones sin turno")
        else:
            detalle = t(" sales are enough", " las ventas alcanzan")
        return ("falta_tecnicos",
                t(f"{detalle.strip().capitalize()}: there are {empresa.tecnicos} technicians and "
                  f"{objetivo_tecnicos} are needed for {objetivo_ventas:.0f} sales/day.",
                  f"{detalle.strip().capitalize()}: hay {empresa.tecnicos} técnicos y "
                  f"hacen falta {objetivo_tecnicos} para {objetivo_ventas:.0f} ventas/día."))
    return ("mantener", t("You are doing well: this month there is no need to force anything.",
                          "Vas bien: este mes no hace falta forzar nada."))


def _prompt(directiva: str, empresa: Empresa, mes: int, aviso: str = "",
            tope: int = 10, reales: float = 0.0, atraso: int = 0) -> str:
    objetivo_ventas = ventas_objetivo_del_mes(mes)
    objetivo_tecnicos = tecnicos_objetivo_del_mes(mes)
    potencia = ventas_potenciales(empresa)
    return (
        f"DIRECTIVE={directiva}\n"
        f"Month {mes} of {META_MES}. Owner goal: {META_TECNICOS} technicians by month {META_MES}.\n"
        f"Sales/day today: {potencia:.0f} (this month's target: {objetivo_ventas:.0f}; "
        f"last closed month: {reales:.0f}).\n"
        f"Active technicians: {empresa.tecnicos} (target: {objetivo_tecnicos}; "
        f"hiring cap: {tope}).\n"
        f"Operators: {empresa.operadores}. Database/service improvements: {empresa.mejoras}.\n"
        f"Installs without a slot: {atraso}. Cash: USD {empresa.caja:,.0f}.\n"
        "Available levers: hire operators, hire technicians, improve conversion.\n"
        + (f"PROGRAM NOTICE: {aviso}\n" if aviso else "")
        + "Decide how much to move and why.\n"
        + t("Write your reasoning and the minutes in ENGLISH.",
            "Escribí tu razonamiento y el acta en ESPAÑOL.")
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
                t("Program correction: without more calls the goal is not reached.",
                  "Corrección del programa: sin más llamadas no se llega a la meta."),
                True, t("Safety net: the program corrected it.",
                        "Red de seguridad: el programa lo corrigió."))
        elif empresa.mejoras < MAX_MEJORAS:
            empresa.mejoras += 1
            empresa.caja -= _COSTO_MEJORA
            inversion += _COSTO_MEJORA
            store.guardar_decision(
                mes, "mejorar_conversion", "1",
                t("Program correction: improving the database and service raises conversion.",
                  "Corrección del programa: mejorar la base y el servicio sube la conversión."),
                True, t("Safety net: the program corrected it.",
                        "Red de seguridad: el programa lo corrigió."))
        else:
            break

    if ventas_potenciales(empresa) < objetivo_ventas:
        avisos.append(t(
            f"NOTICE: they stayed at {ventas_potenciales(empresa):.0f} sales/day "
            f"against the {objetivo_ventas:.0f} of the month's target.",
            f"AVISO: quedaron en {ventas_potenciales(empresa):.0f} ventas/día "
            f"contra las {objetivo_ventas:.0f} de la meta del mes."))

    # (b) que alcancen los técnicos.
    faltan = objetivo_tecnicos - empresa.tecnicos
    if faltan > 0:
        empresa.caja = _alta_tecnicos(empresa, store, faltan, empresa.caja)
        inversion += faltan * SALARIO_TECNICO_MES
        for _ in range(faltan):
            store.guardar_decision(
                mes, "contratar_tecnicos", "1",
                t("Program correction: if we don't add hands, we can't install everything sold.",
                  "Corrección del programa: si no sumamos manos, no podemos instalar todo lo vendido."),
                True, t("Safety net: the program corrected it.",
                        "Red de seguridad: el programa lo corrigió."))
        avisos.append(t(
            f"NOTICE: the Manager fell short of {objetivo_tecnicos} technicians; "
            f"the program added {faltan} so the goal isn't missed.",
            f"AVISO: el Gerente quedó corto de {objetivo_tecnicos} técnicos; "
            f"el programa sumó {faltan} para no perderse la meta."))
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
            razon = f"{razon} Also: {aviso}"
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


def inversion_del_mes(store: Store, mes: int) -> float:
    """Reconstruye la inversión del mes sumando las decisiones APROBADAS.

    Se usa en el modo día a día: la reunión se corre al ABRIR el mes (igual que
    en `correr_mes`) y el cierre llega unos días después, en otro pedido. Como
    cada decisión aplicada quedó guardada en `decisiones_gerente`, acá se vuelve
    a sumar su costo con la MISMA fórmula de `_costo`, sin volver a decidir nada.
    """
    filas = store.conn.execute(
        "SELECT accion, valor FROM decisiones_gerente WHERE mes = ? AND aprobada = 1",
        (mes,)).fetchall()
    total = 0.0
    for f in filas:
        try:
            n = int(float(f["valor"]))
        except (TypeError, ValueError):
            n = 0
        if f["accion"] == "contratar_operadores":
            total += n * SALARIO_OPERADOR_MES
        elif f["accion"] == "contratar_tecnicos":
            total += n * SALARIO_TECNICO_MES
        elif f["accion"] == "mejorar_conversion":
            total += n * _COSTO_MEJORA
    return total


def _escribir_acta(llm: LLMClient, empresa: Empresa, mes: int,
                   decisiones: list[DecisionGerente], avisos: list[str],
                   objetivo_tecnicos: int) -> dict:
    """Pide al Gerente el resumen en criollo (o arma el fallback si no hay red)."""
    titulo = t(f"Minutes {mes} — monthly management meeting",
               f"Acta {mes} — reunión mensual de gerencia")
    resumen_ia = ""
    try:
        reunion = llm.complete(
            agent="gerente",
            messages=[{"role": "user",
                       "content": (f"DIRECTIVE=escribe_acta\n"
                                   f"Month {mes}. {len(decisiones)} decisions applied. "
                                   f"Technicians: {empresa.tecnicos} of {objetivo_tecnicos}.\n"
                                   + t("Write the minutes in ENGLISH.",
                                       "Escribí el acta en ESPAÑOL."))}],
            schema=ReunionGerente)
        titulo = reunion.titulo or titulo
        resumen_ia = reunion.resumen
    except Exception:  # noqa: BLE001  (sin red => fallback determinista)
        resumen_ia = ""

    acciones = ", ".join(
        f"{d.cantidad}x {d.palanca.value.replace('_', ' ')}" for d in decisiones) \
        or t("no changes", "sin cambios")
    cuerpo = (
        f"{resumen_ia}\n\n"
        + t(f"Decisions applied: {acciones}.",
            f"Decisiones aplicadas: {acciones}.") + "\n"
        + t(f"Status: {empresa.operadores} operators, {empresa.tecnicos} technicians, "
            f"{empresa.mejoras} database/service improvements. Cash: USD {empresa.caja:,.0f}.",
            f"Situación: {empresa.operadores} operadores, {empresa.tecnicos} técnicos, "
            f"{empresa.mejoras} mejoras de base/servicio. Caja: USD {empresa.caja:,.0f}.") + "\n"
        + ("".join(f"\n- {a}" for a in avisos) if avisos else "")
    )
    return {"titulo": titulo, "cuerpo": cuerpo,
            "meta": t(f"{empresa.tecnicos}/{META_TECNICOS} technicians (month {META_MES} goal)",
                      f"{empresa.tecnicos}/{META_TECNICOS} técnicos (meta del mes {META_MES})")}
