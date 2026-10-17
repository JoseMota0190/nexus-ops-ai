"""El Enjambre: los agentes dialogan y operan la empresa (del mes 7 en adelante).

Cómo funciona (decidido con el autor):
- El PROGRAMA calcula las opciones VÁLIDAS: qué turnos quedan libres en la
  semana siguiente y qué técnicos pueden cubrir cada uno (por zona y carga).
- Los AGENTES negocian entre ellos, VENTA POR VENTA:

      teleoperador -> coordinador de agenda             (decide CUÁNDO)
      coordinador de agenda -> coordinador de técnicos  (decide QUIÉN)

- El programa hace de ÁRBITRO: si la IA elige algo imposible, se usa la mejor
  opción válida. La charla nunca rompe la operación (regla del track: el LLM no
  es el único método; el volumen y las opciones los calcula Monte Carlo).
- Cada charla se devuelve como transcripción, para mostrarla y poder repetirla.

Esto NO reemplaza a `agendar_ventas` (el algoritmo): lo acompaña. El modo rápido
usa el algoritmo; el modo enjambre usa esta sala.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from llm import LLMClient
from schemas import CoordinacionResponse, TurnoOperador, TurnoTecnicos

from .agenda import Cita, ResultadoAgenda, tecnicos_de, turnos_ocupados
from .business import (DIAS_POR_SEMANA, TURNO_HORA, TURNOS_DIA, TURNOS_TODOS,
                       capacidad_tecnico_dia, turnos_de_capacidad)
from .zones import distancia_aprox, zona_por_nombre

# Cuántas opciones de turno se le muestran al coordinador de agenda (pizarra chica).
_OPCIONES_MAX = 8


@dataclass
class Charla:
    """La conversación completa de UNA venta (lo que se muestra en la pantalla)."""
    venta_id: int
    cliente: str
    barrio: str
    dia: int
    turno: str
    hora: str
    tecnico_id: int | None
    negociado: bool = False     # ¿hubo que ofrecer un turno distinto al que pidió el cliente?
    lineas: list[dict] = field(default_factory=list)  # [{"agente": ..., "dice": ...}]


# ------------------------------------------------------------------ opciones
def turnos_libres(tecnicos: list[dict], ocupados: set[tuple[int, int, str]],
                  barrio: str, semana: int,
                  tope: int = _OPCIONES_MAX) -> list[dict]:
    """Turnos (día, hora) que al menos un técnico puede cubrir, con sus candidatos.

    Ordenados por día y hora. Cada opción trae los técnicos libres en ese hueco,
    ya ordenados por cercanía al barrio del cliente (el reparto por zona lo
    calcula el PROGRAMA; la IA sólo elige de esa lista). Respeta la capacidad
    diaria de cada técnico (2, 3 o 4 instalaciones según cómo venga el día).
    """
    zona = zona_por_nombre(barrio)
    opciones: list[dict] = []
    for dia in range(DIAS_POR_SEMANA):
        dia_global = (semana - 1) * DIAS_POR_SEMANA + dia
        for turno in TURNOS_TODOS:
            candidatos: list[dict] = []
            for t in tecnicos:
                if t["id"] is None:
                    continue
                if turno not in turnos_de_capacidad(capacidad_tecnico_dia(int(t["id"]), dia_global)):
                    continue
                if (t["id"], dia, turno) in ocupados:
                    continue
                candidatos.append({
                    "id": int(t["id"]), "zona": str(t.get("zona", "")),
                    "nombre": str(t.get("nombre") or f"TEC-{t['id']}"),
                })
            if not candidatos:
                continue
            candidatos.sort(key=lambda c: (
                distancia_aprox(zona_por_nombre(c["zona"]), zona) if zona else 0.0,
                c["id"]))
            opciones.append({"dia": dia, "turno": turno, "candidatos": candidatos})
    return opciones[:tope]


def _mejor_turno(opciones: list[dict], pref: dict) -> dict:
    """La opción válida más parecida a lo que pidió el cliente (día, después turno)."""
    def idx(turno: str) -> int:
        return TURNOS_TODOS.index(turno) if turno in TURNOS_TODOS else 0

    def clave(o: dict) -> tuple[int, int]:
        d = abs(int(o["dia"]) - int(pref.get("dia", 0)))
        t = abs(idx(o["turno"]) - idx(pref.get("turno", TURNOS_DIA[0])))
        return (d, t)
    return min(opciones, key=clave)


def _turno_valido(ag: CoordinacionResponse, opciones: list[dict], pref: dict) -> dict:
    """Si la IA eligió un turno de la pizarra, se respeta; si no, manda el programa."""
    for o in opciones:
        if int(o["dia"]) == int(ag.dia) and o["turno"] == ag.turno_propuesto:
            return o
    return _mejor_turno(opciones, pref)


def _tecnico_valido(te: TurnoTecnicos, candidatos: list[dict]) -> int:
    """Si la IA eligió un técnico de la lista, se respeta; si no, el primero (el más cercano)."""
    ids = {int(c["id"]) for c in candidatos}
    if str(te.tecnico_id).strip() in {str(i) for i in ids}:
        return int(te.tecnico_id)
    return int(candidatos[0]["id"])


def _preferencia(rng: random.Random) -> dict:
    """Lo que el cliente pidió: un día y una franja. (El cliente tiene preferencias.)"""
    return {"dia": rng.randrange(DIAS_POR_SEMANA), "turno": rng.choice(list(TURNOS_DIA))}


def _nombre_cliente(store, cliente_id: int) -> str:
    fila = store.conn.execute("SELECT nombre FROM clientes WHERE id = ?",
                              (cliente_id,)).fetchone()
    return fila["nombre"] if fila else f"cliente {cliente_id}"


# ------------------------------------------------------------------- charla
def negociar_venta(llm: LLMClient, store, venta: dict, opciones: list[dict],
                   rng: random.Random, semana_objetivo: int) -> tuple[Cita, Charla]:
    """Una venta negociada en la sala: teleoperador -> agenda -> técnicos."""
    cliente = _nombre_cliente(store, venta["cliente_id"])
    barrio = venta["barrio"]
    pref = _preferencia(rng)
    lineas: list[dict] = []

    # Turno 1: el teleoperador propone a dónde mandar la venta.
    op = llm.complete(
        agent="operador",
        messages=[{"role": "user", "content": json.dumps({
            "cliente": cliente, "barrio": barrio,
            "producto": venta.get("producto", "una alarma"),
            "preferencia": pref}, ensure_ascii=False)}],
        schema=TurnoOperador,
    )
    lineas.append({"agente": "operador", "dice": op.habla})

    # Turno 2: el coordinador de agenda elige un turno de la pizarra.
    ag = llm.complete(
        agent="agenda",
        messages=[{"role": "user", "content": json.dumps({
            "cliente": cliente, "barrio": barrio,
            "dia_preferido": op.dia_preferido, "turno_preferido": op.turno_preferido,
            "turnos_libres": [{"dia": o["dia"], "turno": o["turno"]} for o in opciones]},
            ensure_ascii=False)}],
        schema=CoordinacionResponse,
    )
    elegido = _turno_valido(ag, opciones, {"dia": op.dia_preferido,
                                           "turno": op.turno_preferido})
    dia, turno = int(elegido["dia"]), str(elegido["turno"])
    lineas.append({"agente": "agenda", "dice": ag.nota_interna or ag.texto_para_cliente})

    # Turno 3: el coordinador de técnicos elige a quién mandar.
    candidatos = elegido["candidatos"]
    te = llm.complete(
        agent="tecnicos",
        messages=[{"role": "user", "content": json.dumps({
            "cliente": cliente, "barrio": barrio, "dia": dia, "turno": turno,
            "candidatos": candidatos}, ensure_ascii=False)}],
        schema=TurnoTecnicos,
    )
    tecnico_id = _tecnico_valido(te, candidatos)
    lineas.append({"agente": "tecnicos", "dice": te.habla})

    cita = Cita(
        venta_id=int(venta["id"]), cliente_id=int(venta["cliente_id"]),
        barrio=barrio, tecnico_id=tecnico_id, semana=semana_objetivo,
        dia=dia, turno=turno, mensaje=ag.texto_para_cliente,
    )
    charla = Charla(venta_id=int(venta["id"]), cliente=cliente, barrio=barrio,
                    dia=dia, turno=turno, hora=TURNO_HORA.get(turno, ""),
                    tecnico_id=tecnico_id,
                    negociado=(dia != int(pref["dia"]) or turno != str(pref["turno"])),
                    lineas=lineas)
    return cita, charla


def agendar_venta_en_sala(llm: LLMClient, store, venta: dict,
                          semana_objetivo: int, rng: random.Random
                          ) -> tuple[Cita | None, Charla | None]:
    """Negocia UNA venta en la sala y la agenda en la semana objetivo.

    Devuelve (None, None) si no hay ningún turno libre: la venta queda pendiente
    (esa es la señal que mira el Gerente para contratar más técnicos).
    """
    tecnicos = tecnicos_de(store)
    if not tecnicos:
        return None, None
    opciones = turnos_libres(tecnicos, turnos_ocupados(store, semana_objetivo),
                             venta["barrio"], semana_objetivo)
    if not opciones:
        return None, None
    return negociar_venta(llm, store, venta, opciones, rng, semana_objetivo)


def agendar_semana_enjambre(llm: LLMClient, store, semana: int,
                            rng: random.Random) -> tuple[ResultadoAgenda, list[Charla]]:
    """Cierra la semana como `agendar_ventas`, pero negociando cada venta en la sala.

    Devuelve el mismo `ResultadoAgenda` que usa el algoritmo (para no cambiar el
    resto de la simulación) más las charlas, que la pantalla puede mostrar.
    """
    pendientes = store.ventas_sin_cita()
    objetivo = semana + 1
    ocupados = turnos_ocupados(store, objetivo)
    tecnicos = tecnicos_de(store)

    res = ResultadoAgenda()
    charlas: list[Charla] = []

    if not tecnicos:
        res.sin_capacidad = len(pendientes)
        return res, charlas

    for v in pendientes:
        venta = {"id": int(v["id"]), "cliente_id": int(v["cliente_id"]),
                 "barrio": v["barrio"]}
        opciones = turnos_libres(tecnicos, ocupados, venta["barrio"], objetivo)
        if not opciones:
            res.sin_capacidad += 1
            continue
        cita, charla = negociar_venta(llm, store, venta, opciones, rng, objetivo)
        ocupados.add((cita.tecnico_id, cita.dia, cita.turno))  # type: ignore[arg-type]
        res.agendadas.append(cita)
        charlas.append(charla)

    res.sin_capacidad = len(pendientes) - len(res.agendadas)
    res.turnos_negociados = sum(1 for c in charlas if c.negociado)
    return res, charlas
