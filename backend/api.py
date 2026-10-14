"""API de Nexus Alarm (FastAPI).

Sirve todo lo que necesita la pantalla del dueño: estado, KPIs, el acta del
Gerente, el log de llamadas, el mapa, las métricas AMD y los botones de la
simulación (avanzar 1 mes / correr todo).

Arranque:  `uvicorn api:app --reload`  (desde `backend/`)
"""
from __future__ import annotations

import random
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import LLMClient, get_metrics
from llm.config import get_config
from schemas import TeleoperadorResponse
from store import Store

from engine import Simulacion, ZONAS
from engine.business import (
    DIAS_POR_SEMANA,
    MESES_AUTOMATICOS,
    MESES_TOTALES,
    SEMANAS_POR_MES,
)
from engine.gerente import (
    tecnicos_objetivo_del_mes,
    ventas_objetivo_del_mes,
    ventas_potenciales,
)
from engine.leads import generar_leads

import os

DATA = Path(os.getenv("NEXUS_DB", str(Path(__file__).resolve().parent / "data" / "nexus.db")))

app = FastAPI(title="Nexus Alarm — Gemelo Digital", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = Store(DATA)
llm = LLMClient()
sim = Simulacion(store, llm)
sim.inicializar()
# Primera vez que arranca (base recién creada) → corren solos los primeros 6 meses,
# como quedó decidido. Los 3 últimos los mueve el dueño con "Avanzar 1 mes".
if not store.conn.execute("SELECT 1 FROM resumen_mes LIMIT 1").fetchone():
    sim.correr_todo(MESES_AUTOMATICOS)
_rng = random.Random(2026)


class Vacio(BaseModel):
    ok: bool = True


# ------------------------------------------------------------------ estado
@app.get("/api/estado")
def estado() -> dict:
    """Todo lo que la pantalla del dueño muestra de un saque."""
    e = sim.estado()
    acta = store.conn.execute(
        "SELECT * FROM actas_gerente ORDER BY mes DESC LIMIT 1").fetchone()
    e["acta_actual"] = dict(acta) if acta else None
    e["decisiones"] = [dict(r) for r in store.conn.execute(
        "SELECT mes, accion, valor, motivo, aprobada, aviso FROM decisiones_gerente "
        "ORDER BY id DESC LIMIT 12").fetchall()]
    e["motivos"] = motivos()
    e["puede_avanzar"] = sim.empresa.mes <= MESES_TOTALES
    return e


def motivos() -> dict:
    """Motivos agregados de todo el log de llamadas."""
    filas = store.conn.execute(
        "SELECT motivo, COUNT(*) AS n FROM llamadas WHERE atendio = 1 "
        "AND motivo <> 'Cerró la venta' GROUP BY motivo ORDER BY n DESC").fetchall()
    sin_responder = store.conn.execute(
        "SELECT motivo, COUNT(*) AS n FROM llamadas WHERE atendio = 0 "
        "GROUP BY motivo ORDER BY n DESC").fetchall()
    return {"no_compra": [{"motivo": f["motivo"], "n": f["n"]} for f in filas],
            "no_respondio": [{"motivo": f["motivo"], "n": f["n"]} for f in sin_responder]}


# ------------------------------------------------------------------ KPIs
@app.get("/api/resumenes")
def resumenes() -> list[dict]:
    """Histórico mes a mes (para los gráficos de ingresos vs costos)."""
    return [dict(r) for r in store.resumenes_mes()]


@app.get("/api/dias")
def dias(semana: int | None = None) -> list[dict]:
    if semana is None:
        semana = sim.empresa.semana
    filas = store.conn.execute(
        "SELECT * FROM resumen_dia WHERE semana = ? ORDER BY dia", (semana,))
    return [dict(r) for r in filas.fetchall()]


# ------------------------------------------------------------- simulación
@app.post("/api/mes")
def avanzar_mes() -> dict:
    """Botón 'Avanzar 1 mes': corre la reunión del Gerente y el mes entero."""
    if sim.empresa.mes > MESES_TOTALES:
        raise HTTPException(409, "Ya se corrieron los 9 meses.")
    return sim.correr_mes()


@app.post("/api/todo")
def correr_todo(meses: int = 6) -> dict:
    """Corre de una los primeros `meses` (la fase automática: 6 meses solos)."""
    salidas = []
    for _ in range(min(meses, MESES_TOTALES - sim.empresa.mes + 1)):
        salidas.append(sim.correr_mes())
    return {"corridos": len(salidas), "ultimo": salidas[-1] if salidas else None,
            "estado": sim.estado()}


@app.post("/api/dia")
def correr_un_dia() -> dict:
    if sim.empresa.mes > MESES_TOTALES:
        raise HTTPException(409, "Ya se corrieron los 9 meses.")
    return sim.correr_dia()


@app.post("/api/reiniciar")
def reiniciar() -> dict:
    sim.empresa = sim.inicializar(reiniciar=True)
    return sim.estado()


# ---------------------------------------------------------- actas / log
@app.get("/api/actas")
def actas() -> list[dict]:
    return [dict(r) for r in store.conn.execute(
        "SELECT * FROM actas_gerente ORDER BY mes").fetchall()]


@app.get("/api/llamadas")
def llamadas(limite: int = 40) -> list[dict]:
    """Log reciente de llamadas (quién contestó, quién no y el motivo)."""
    filas = store.conn.execute(
        "SELECT l.id, l.mes, l.semana, l.dia, l.atendio, l.motivo, l.venta_id, "
        "c.nombre, c.barrio, c.telefono "
        "FROM llamadas l JOIN clientes c ON c.id = l.cliente_id "
        "ORDER BY l.id DESC LIMIT ?", (limite,))
    return [dict(r) for r in filas.fetchall()]


@app.get("/api/mensajes")
def mensajes(tipo: str = "whatsapp_cliente", limite: int = 25) -> list[dict]:
    return [dict(r) for r in store.ultimos_mensajes(tipo, limite)]


# ------------------------------------------------------------------ mapa
@app.get("/api/mapa")
def mapa() -> dict:
    """Técnicos + turnos de la semana actual, con coordenadas para el mapa."""
    semana = max(1, sim.empresa.semana - 1) if sim.empresa.semana > 1 else 1
    coords = {z.nombre: {"lat": z.lat, "lon": z.lon} for z in ZONAS}
    tecnicos = [dict(r) for r in store.conn.execute(
        "SELECT id, nombre, zona_base, activo FROM tecnicos").fetchall()]
    citas = store.conn.execute(
        "SELECT c.id, c.barrio, c.dia, c.turno, c.tecnico_id, c.semana, "
        "cl.nombre AS cliente "
        "FROM citas c JOIN clientes cl ON cl.id = c.cliente_id "
        "WHERE c.semana = ? AND c.estado = 'confirmada' ORDER BY c.dia, c.turno",
        (semana,)).fetchall()
    return {
        "semana": semana,
        "zonas": coords,
        "tecnicos": tecnicos,
        "citas": [{**dict(c), "lat": coords.get(c["barrio"], {}).get("lat"),
                   "lon": coords.get(c["barrio"], {}).get("lon")} for c in citas],
        "capacidad_dia": sim.empresa.capacidad_instalaciones,
    }


# ------------------------------------------------------------ métricas AMD
@app.get("/api/metricas")
def metricas() -> dict:
    """Panel AMD: latencia, tokens y tokens/segundo del cerebro servido por TokenFactory."""
    m = get_metrics()
    cfg = get_config()
    resumen = m.summary() if hasattr(m, "summary") else {}
    return {
        "modelo": cfg.model or "mock",
        "modo_mock": cfg.use_mock,
        "base_url": cfg.base_url,
        **resumen,
    }


# ---------------------------------------------------- la IA habla (en vivo)
@app.post("/api/llamada_en_vivo")
def llamada_en_vivo() -> dict:
    """Una llamada donde el AGENTE (IA) habla de verdad. Es la de la demo."""
    fila = store.conn.execute(
        "SELECT * FROM clientes WHERE estado = 'nuevo' ORDER BY id LIMIT 1").fetchone()
    if fila is None:
        leads = generar_leads(_rng, dia=999, volumen=1)
        ids = store.insertar_leads(leads, sim.empresa.mes)
        fila = store.conn.execute("SELECT * FROM clientes WHERE id = ?", (ids[0],)).fetchone()

    mensajes_llamada = [
        {"role": "system",
         "content": "Sos teleoperador de Nexus Alarm, empresa de alarmas en CABA. "
                    "Hablás en español rioplatense, corto y amable."},
        {"role": "user",
         "content": (f"{fila['nombre']} ({fila['telefono']}), {fila['barrio']}, "
                     f"{fila['direccion'] if 'direccion' in fila.keys() else ''}. "
                     "Hola, me llegó su formulario. ¿Qué tipo de alarma le interesa?")},
    ]
    resp = llm.complete(agent="teleoperador", messages=mensajes_llamada,
                        schema=TeleoperadorResponse)
    return {"cliente": fila["nombre"], "barrio": fila["barrio"],
            "telefono": fila["telefono"], "respuesta": resp.model_dump()}


@app.get("/api/objetivos")
def objetivos() -> list[dict]:
    return [{"mes": m, "ventas_por_dia": round(ventas_objetivo_del_mes(m), 1),
             "tecnicos": tecnicos_objetivo_del_mes(m)} for m in range(1, MESES_TOTALES + 1)]


class Escenario(BaseModel):
    operadores: int = 3
    tecnicos: int = 2
    mejoras: int = 0


@app.post("/api/escenario")
def escenario(e: Escenario) -> dict:
    """'¿Qué pasa si…?' — el dueño mueve las palancas y el programa calcula el resultado.

    No toca la simulación: es una cuenta al aire (la planilla de Excel del dueño).
    """
    from engine.business import (
        Empresa, MANTENIMIENTO_ANUAL, MONITOREO_PROMEDIO, SALARIO_OPERADOR_MES,
        SALARIO_TECNICO_MES, DIAS_POR_SEMANA, SEMANAS_POR_MES,
    )
    prob = Empresa(operadores=max(1, e.operadores), tecnicos=max(1, e.tecnicos),
                   mejoras=max(0, e.mejoras))
    ventas = ventas_potenciales(prob)
    capacidad = prob.capacidad_instalaciones
    dias = SEMANAS_POR_MES * DIAS_POR_SEMANA
    ingreso_inst = round(ventas * dias * 298.0, 2)      # ticket promedio de instalación
    ingreso_rec = round(prob.clientes_activos * (MONITOREO_PROMEDIO + MANTENIMIENTO_ANUAL / 12), 2)
    costo = round(prob.operadores * SALARIO_OPERADOR_MES
                  + prob.tecnicos * SALARIO_TECNICO_MES
                  + prob.leads_por_dia * 1.2 * dias, 2)
    return {
        "ventas_por_dia": round(ventas, 1),
        "capacidad_instalaciones": capacidad,
        "sobra_capacidad": max(0, capacidad - round(ventas, 0)),
        "falta_capacidad": max(0, round(ventas, 0) - capacidad),
        "ingresos_mes": round(ingreso_inst + ingreso_rec, 2),
        "costos_mes": costo,
        "balance_mes": round(ingreso_inst + ingreso_rec - costo, 2),
        "tasa_respuesta": round(100 * prob.tasa_respuesta, 1),
        "tasa_cierre": round(100 * prob.tasa_cierre, 1),
        "leads_por_dia": prob.leads_por_dia,
        "meta_cumplida": prob.tecnicos >= 10,
    }
