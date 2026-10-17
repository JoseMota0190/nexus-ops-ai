"""Coordinador de Agenda: convierte ventas en turnos para la semana siguiente.

Reglas (decididas con el autor):
- Las ventas NO se instalan el mismo día: se agendan para la SEMANA SIGUIENTE.
  Por eso los técnicos empiezan a trabajar recién en la semana 2.
- Lunes a sábados, 3 turnos por técnico: 9am / 12pm / 4pm.
- El PROGRAMA elige el turno (zona + capacidad). La IA solo "actúa" en unas pocas
  conversaciones para la demo.
- Si el cliente no puede en ese horario, se le ofrece el turno libre más cercano.
- Si no queda capacidad, la venta queda "sin capacidad": es la señal de alarma
  que el Gerente IA tiene que ver para contratar más técnicos.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .business import DIAS_POR_SEMANA, DIAS_SEMANA, MAX_INTENTOS_TURNO, PROB_NO_PUEDE, \
    TURNO_HORA, TURNOS_DIA, capacidad_tecnico_dia, turnos_de_capacidad
from .zones import ZONAS, distancia_aprox, zona_por_nombre

_TECNICOS_NOMBRES = [
    "Nicolás Ferreyra", "Ezequiel Roldán", "Santiago Paz", "Gonzalo Quiroga",
    "Martín Sosa", "Iván Duarte", "Ramiro Vega", "Facundo Ayala",
    "Leandro Cabrera", "Bruno Ledesma",
]


@dataclass
class Cita:
    venta_id: int
    cliente_id: int
    barrio: str
    tecnico_id: int | None
    semana: int
    dia: int                  # 0 = lunes .. 5 = sábado
    turno: str                # "9am" | "12pm" | "4pm"
    estado: str = "confirmada"
    intentos: int = 0
    mensaje: str = ""


@dataclass
class ResultadoAgenda:
    agendadas: list[Cita] = field(default_factory=list)
    sin_capacidad: int = 0
    turnos_negociados: int = 0     # cuántas veces hubo que dar un turno alternativo


def _nombre_tecnico(i: int) -> str:
    return _TECNICOS_NOMBRES[i % len(_TECNICOS_NOMBRES)]


def nombres_tecnicos(n: int, desde: int = 0) -> list[str]:
    return [_nombre_tecnico(desde + i) for i in range(n)]


def _turno_mensaje(barrio: str, dia: int, turno: str) -> str:
    hora = TURNO_HORA[turno]
    return (f"¡Hola! Te confirmo la instalación de tu alarma en {barrio} el "
            f"{DIAS_SEMANA[dia]} a las {hora}. El técnico te avisa al llegar. "
            "Gracias por confiar en Nexus Alarm.")


def _puntaje_turno(zona_tecnico, barrio: str) -> float:
    zona = zona_por_nombre(barrio)
    if zona is None or zona_tecnico is None:
        return 0.0
    return distancia_aprox(zona_tecnico, zona)


def agendar_ventas(ventas: list[dict], ocupados: set[tuple[int, int, str]],
                   tecnicos: list[dict], semana_objetivo: int,
                   rng: random.Random) -> ResultadoAgenda:
    """Agenda `ventas` (de la semana recién cerrada) en `semana_objetivo`.

    `ocupados` son los (tecnico_id, dia, turno) ya reservados en esa semana.
    `tecnicos`: [{'id': int, 'zona': str}, ...] activos.
    """
    res = ResultadoAgenda()

    if not tecnicos:
        res.sin_capacidad = len(ventas)
        return res

    # Capacidades libres, ordenadas por conveniencia de zona.
    zonas = {t["id"]: zona_por_nombre(t.get("zona", "")) for t in tecnicos}
    for venta in ventas:
        candidatos = [t for t in tecnicos if t["id"] is not None]
        if not candidatos:
            res.sin_capacidad += 1
            continue

        # Ordena técnicos por cercanía al barrio del cliente (reparto por zona).
        candidatos = sorted(
            candidatos,
            key=lambda t: (_puntaje_turno(zonas.get(t["id"]), venta["barrio"]),
                           t["id"]))

        # Slots que el cliente rechazó en esta negociación (siguen libres para otros).
        rechazados: set[tuple[int, int, str]] = set()
        cita = None
        intentos = 0
        for intento in range(MAX_INTENTOS_TURNO):
            intentos = intento + 1
            libre = None
            # Preferir el técnico más cercano que tenga un hueco libre.
            for t in candidatos:
                for dia in range(DIAS_POR_SEMANA):
                    dia_global = (semana_objetivo - 1) * DIAS_POR_SEMANA + dia
                    cap = capacidad_tecnico_dia(t["id"], dia_global)
                    for turno in turnos_de_capacidad(cap):
                        clave = (t["id"], dia, turno)
                        if clave in ocupados or clave in rechazados:
                            continue
                        libre = clave
                        break
                    if libre:
                        break
                if libre:
                    break

            if libre is None:
                break

            # El cliente a veces no puede en ese horario (flujo de negociación).
            if rng.random() < PROB_NO_PUEDE and intento < MAX_INTENTOS_TURNO - 1:
                rechazados.add(libre)
                res.turnos_negociados += 1
                continue

            tec_id, dia, turno = libre
            cita = Cita(
                venta_id=venta["id"], cliente_id=venta["cliente_id"],
                barrio=venta["barrio"], tecnico_id=tec_id,
                semana=semana_objetivo, dia=dia, turno=turno,
                intentos=intentos,
                mensaje=_turno_mensaje(venta["barrio"], dia, turno),
            )
            ocupados.add(libre)
            break

        if cita is None:
            res.sin_capacidad += 1
        else:
            res.agendadas.append(cita)

    # Recalcula de forma simple: lo que no se agendó, se quedó sin capacidad.
    res.sin_capacidad = len(ventas) - len(res.agendadas)
    return res


def tecnicos_de(store) -> list[dict]:
    """Técnicos activos con su zona base, leyéndolos de la base de datos."""
    rows = store.conn.execute(
        "SELECT id, nombre, zona_base FROM tecnicos WHERE activo = 1 ORDER BY id").fetchall()
    return [{"id": int(r["id"]), "zona": str(r["zona_base"]),
             "nombre": str(r["nombre"])} for r in rows]


def turnos_ocupados(store, semana: int) -> set[tuple[int, int, str]]:
    return store.slots_ocupados(semana)


def nombres_para_alta(n: int, desde: int = 0) -> list[tuple[str, str]]:
    """(nombre, zona_base) para dar de alta N técnicos, repartidos por zonas."""
    zonas = [z.nombre for z in ZONAS]
    return [(nombres_tecnicos(n, desde)[i], zonas[i % len(zonas)]) for i in range(n)]
