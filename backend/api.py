"""API de Nexus Alarm (FastAPI).

Sirve todo lo que necesita la pantalla del dueño: estado, KPIs, el acta del
Gerente, el log de llamadas, el mapa, las métricas AMD y los botones de la
simulación (avanzar 1 mes / correr todo).

Arranque:  `uvicorn api:app --reload`  (desde `backend/`)
"""
from __future__ import annotations

import random
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import LLMClient, get_metrics
from llm.config import LLMConfig, get_config
from schemas import TeleoperadorResponse
from store import Store

from engine import Simulacion, ZONAS
from engine import sectores as sectores_agentes
from engine.facturas import sello
from idioma import set_idioma, t
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

llm = LLMClient()

# ------------------------------------------------------------------ idiomas
# El sitio habla inglés y español. Cada idioma tiene su PROPIA base (así el avance
# de uno no pisa al otro) y su propia simulación. El botón ES/EN llama a
# `POST /api/idioma` y desde ahí todo se lee de la base del idioma elegido.
_IDIOMA = "en"
_MUNDOS: dict[str, "tuple[Store, Simulacion]"] = {}


def _ruta_db(lang: str) -> Path:
    """La base de un idioma (la inglesa es la histórica `nexus.db`)."""
    if lang == "en":
        return DATA
    return DATA.with_name(f"{DATA.stem}_{lang}{DATA.suffix}")


def _construir_mundo(lang: str) -> "tuple[Store, Simulacion]":
    """Levanta (o crea) el "mundo" de un idioma: su base + su simulación.

    La primera vez corre solo los primeros 6 meses, sembrados con el motor LOCAL
    (sin red ni créditos), para que el arranque sea en segundos.

    Red de seguridad: si la siembra truena (cerebro caído, JSON inesperado, lo que
    sea), el programa NO se apaga. Se anota el error y la API sigue viva con la
    base que haya — una demo a medio cargar siempre es mejor que una pantalla en
    blanco frente a un jurado.
    """
    set_idioma(lang)
    st = Store(_ruta_db(lang))
    sm = Simulacion(st, llm)
    sm.enjambre_desde = 7
    sm.inicializar()
    if not st.conn.execute("SELECT 1 FROM resumen_mes LIMIT 1").fetchone():
        try:
            llm_real = sm.llm
            sm.llm = LLMClient(config=LLMConfig(use_mock=True, model="mock"))
            sm.reportes_con_ia = False  # la siembra escribe los informes localmente
            try:
                sm.correr_todo(MESES_AUTOMATICOS)
            finally:
                sm.llm = llm_real
                sm.reportes_con_ia = True
        except Exception as exc:  # noqa: BLE001 — nada debe apagar el arranque
            import logging
            logging.getLogger("nexus.api").exception(
                "La siembra de los primeros %s meses falló; se arranca igual: %s",
                MESES_AUTOMATICOS, exc)
    try:
        sectores_agentes.asegurar_informes(st)
        sm.reportes_con_ia = True
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger("nexus.api").exception(
            "No se pudieron asegurar los informes de sector")
    return st, sm


# El DÍA EN VIVO: el que corre en segundo plano, negociando venta por venta, para
# que la pantalla vea a los agentes hablar mientras piensan (AMD tarda ~15 s por
# agente y un día del mes 7 tiene ~24 ventas: son minutos).
_DIA_LOCK = threading.Lock()
_DIA: dict = {"corriendo": False, "listo": False, "error": None, "resultado": None}

# El TURNO DE SIMULACIÓN: hay UNO solo, compartido por todos. Mientras alguien
# está simulando (un día, un mes, cambiar de idioma o rearmar la empresa), NADIE
# más puede simular: se le avisa con un mensaje amable y espera su turno. Es la
# "sala de espera": dos jueces no se pisan la misma base.
_TURNO_LOCK = threading.Lock()
_TURNO: dict = {"activo": False, "que": None}


def _reclamar_turno(que: str) -> None:
    """Toma el único turno de simulación.

    Si ya hay uno corriendo (lo esté corriendo quien lo esté), frena con un aviso
    amable para que el otro espere. Así nunca hay dos simulaciones a la vez sobre
    la misma base.
    """
    with _TURNO_LOCK:
        if _TURNO["activo"]:
            raise HTTPException(
                409,
                t("Someone is already running the simulation. Wait a moment — your "
                  "turn is coming and the buttons unlock on their own.",
                  "Otra persona ya está corriendo la simulación. Esperá un momento: "
                  "ya llega tu turno y los botones se destraban solos."))
        _TURNO["activo"] = True
        _TURNO["que"] = que


def _liberar_turno() -> None:
    with _TURNO_LOCK:
        _TURNO["activo"] = False
        _TURNO["que"] = None


# Arranca el mundo INGLÉS (el que ve el jurado por defecto). El español se arma
# la primera vez que alguien toca el botón ES.
store, sim = _construir_mundo("en")
_MUNDOS["en"] = (store, sim)

_rng = random.Random(2026)


class Vacio(BaseModel):
    ok: bool = True


class ModoSim(BaseModel):
    """Interruptor del modo: rápido (sin charla) o sala (los agentes negocian)."""
    rapido: bool = False


class Idioma(BaseModel):
    """Idioma de la pantalla: 'en' (inglés) o 'es' (español)."""
    lang: str = "en"


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
    with _TURNO_LOCK:
        e["turno"] = {"activo": _TURNO["activo"], "que": _TURNO["que"]}
    e["puede_avanzar"] = True  # sin tope: la app puede seguir día a día
    return e


def motivos() -> dict:
    """Motivos agregados de todo el log de llamadas."""
    filas = store.conn.execute(
        "SELECT motivo, COUNT(*) AS n FROM llamadas WHERE atendio = 1 "
        "AND motivo <> ? GROUP BY motivo ORDER BY n DESC",
        (t("Closed the sale", "Cerró la venta"),)).fetchall()
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
    """Botón 'Avanzar 1 mes': corre la reunión del Gerente y el mes entero.

    La app no tiene tope de meses: pasada la meta, la empresa se ESTABILIZA y
    sigue operando (el Gerente deja de contratar sin control).
    """
    _reclamar_turno("month")
    try:
        return sim.correr_mes()
    finally:
        _liberar_turno()


@app.post("/api/todo")
def correr_todo(meses: int = 6) -> dict:
    """Corre de una los primeros `meses` (la fase automática: 6 meses solos)."""
    _reclamar_turno("months")
    try:
        salidas = []
        for _ in range(max(0, meses)):
            salidas.append(sim.correr_mes())
        return {"corridos": len(salidas), "ultimo": salidas[-1] if salidas else None,
                "estado": sim.estado()}
    finally:
        _liberar_turno()


@app.post("/api/dia")
def correr_un_dia() -> dict:
    """Corre un día. Cuando se acaba la última semana del mes, el mes se cierra
    solo: reunión del Gerente (al abrir), informes de los 4 sectores e ingresos
    recurrentes (al cerrar). Sin tope: se puede seguir día por día indefinidamente."""
    _reclamar_turno("day")
    try:
        return sim.correr_dia_completo()
    finally:
        _liberar_turno()


@app.post("/api/dia/en-vivo")
def dia_en_vivo() -> dict:
    """Arranca el día en SEGUNDO PLANO, para ver a los agentes negociar en vivo.

    Devuelve enseguida (no bloquea la pantalla). La base se va guardando venta por
    venta (Store.commit_ahora), así el panel de la Sala muestra la charla mientras
    los agentes todavía están pensando. Cuando termina, `GET /api/dia/en-vivo`
    trae el resultado completo (el detalle del día y la película).
    """
    _reclamar_turno("live day")
    with _DIA_LOCK:
        _DIA.update({"corriendo": True, "listo": False, "error": None,
                     "resultado": None})

    def _trabajo() -> None:
        try:
            res = sim.correr_dia_completo()
            with _DIA_LOCK:
                _DIA.update({"corriendo": False, "listo": True, "resultado": res})
        except Exception as exc:  # noqa: BLE001 — el error se muestra, no tumba la app
            with _DIA_LOCK:
                _DIA.update({"corriendo": False, "listo": True, "error": str(exc)})
        finally:
            _liberar_turno()  # se acabó el día: el turno queda libre para el otro

    threading.Thread(target=_trabajo, name="dia-en-vivo", daemon=True).start()
    return {"corriendo": True}


@app.get("/api/dia/en-vivo")
def dia_en_vivo_estado() -> dict:
    """¿Cómo va el día en vivo? Progreso + resultado cuando termina."""
    with _DIA_LOCK:
        estado_dia = {
            "corriendo": _DIA["corriendo"],
            "listo": _DIA["listo"],
            "error": _DIA["error"],
            "resultado": _DIA["resultado"],
        }
    estado_dia["progreso"] = {
        "agendadas_hoy": getattr(sim, "_agendadas_dia", 0),
        "negociados_hoy": getattr(sim, "_negociados_dia", 0),
    }
    return estado_dia


@app.post("/api/modo")
def modo(m: ModoSim) -> dict:
    """Interruptor: 'modo sala' (los agentes negocian) vs 'modo rápido' (sin charla)."""
    _reclamar_turno("mode")
    try:
        sim.modo_sala = not m.rapido
        return {"ok": True, "rapido": m.rapido, "modo_sala": sim.modo_sala,
                "enjambre_desde": sim.enjambre_desde}
    finally:
        _liberar_turno()


@app.post("/api/reiniciar")
def reiniciar() -> dict:
    _reclamar_turno("reset")
    try:
        sim.empresa = sim.inicializar(reiniciar=True)
        sim.enjambre_desde = 7
        return sim.estado()
    finally:
        _liberar_turno()


@app.post("/api/idioma")
def cambiar_idioma(body: Idioma) -> dict:
    """Cambia el idioma del sitio (inglés / español) y de qué base se lee.

    La primera vez que se elige español se arma su base (los 6 meses sembrados,
    con el motor local) y queda guardada. El avance de cada idioma es
    independiente: pasar a español y volver a inglés no pierde nada.
    """
    global store, sim, _IDIOMA
    lang = body.lang if body.lang in ("en", "es") else "en"
    if lang == _IDIOMA:
        return {"idioma": _IDIOMA}
    _reclamar_turno("language change")
    try:
        if lang not in _MUNDOS:
            _MUNDOS[lang] = _construir_mundo(lang)
        store, sim = _MUNDOS[lang]
        set_idioma(lang)
        _IDIOMA = lang
        return {"idioma": _IDIOMA, "estado": sim.estado()}
    finally:
        _liberar_turno()


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


@app.get("/api/sala")
def sala(limite: int = 60) -> list[dict]:
    """La Sala de Agentes: la última charla del enjambre (teleoperador -> agenda ->
    técnicos), en orden cronológico, para mostrarla en el panel."""
    filas = store.ultimos_mensajes("sala_agentes", limite)
    return [dict(r) for r in reversed(filas)]


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


# ------------------------------------------------------------ sectores
@app.get("/api/sectores")
def sectores_lista() -> list[dict]:
    """Los 4 sectores (Gerencia, Ventas, Agenda, Facturación) con su último informe."""
    return sectores_agentes.listado(store, sim.empresa.mes)


def _mes_informe(mes: int | None) -> int:
    """El mes pedido o, si no, el último mes cerrado (el mes en curso menos 1)."""
    if mes:
        return int(mes)
    return max(1, sim.empresa.mes - 1)


@app.get("/api/sectores/{sector}")
def sector_detalle(sector: str, mes: int | None = None) -> dict:
    """El informe de un sector (informe + números + historial)."""
    if not sectores_agentes.es_sector(sector):
        raise HTTPException(404, f"Unknown sector: {sector}")
    return sectores_agentes.detalle(store, sector, _mes_informe(mes))


@app.post("/api/sectores/{sector}/generar")
def sector_generar(sector: str, mes: int | None = None) -> dict:
    """Vuelve a generar el informe del sector (IA si está)."""
    if not sectores_agentes.es_sector(sector):
        raise HTTPException(404, f"Unknown sector: {sector}")
    m = _mes_informe(mes)
    usar_ia = not get_config().use_mock
    return sectores_agentes.generar_informe(store, llm, sector, m, usar_ia=usar_ia)


# --------------------------------------------------------- facturación
@app.get("/api/facturacion")
def facturacion(mes: int | None = None) -> dict:
    """Comprobantes SIMULADOS del mes + su auditoría (100% local, sin red)."""
    m = _mes_informe(mes)
    return {
        "mes": m,
        "metricas": sectores_agentes.metricas_de_sector(store, m, "facturacion"),
        "facturas": sectores_agentes.facturas_del_mes(m),
        "sello": sello(),
    }


# ------------------------------------------------------------ métricas AMD
@app.get("/api/metricas")
def metricas() -> dict:
    """Panel AMD: latencia, tokens y tokens/segundo del cerebro servido sobre AMD."""
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
         "content": t("You are a telemarketer at Nexus Alarm, an alarm company in "
                      "Buenos Aires (CABA). You speak briefly and kindly.",
                      "Sos teleoperador de Nexus Alarm, empresa de alarmas en CABA. "
                      "Hablás en español rioplatense, corto y amable.")},
        {"role": "user",
         "content": (f"{fila['nombre']} ({fila['telefono']}), {fila['barrio']}, "
                     f"{fila['direccion'] if 'direccion' in fila.keys() else ''}. "
                     + t("Hi, I got your form. What kind of alarm are you interested in?",
                         "Hola, me llegó su formulario. ¿Qué tipo de alarma le interesa?"))},
    ]
    resp = llm.complete(agent="teleoperador", messages=mensajes_llamada,
                        schema=TeleoperadorResponse)
    return {"cliente": fila["nombre"], "barrio": fila["barrio"],
            "telefono": fila["telefono"], "respuesta": resp.model_dump()}


@app.get("/api/objetivos")
def objetivos() -> list[dict]:
    ultimo = max(MESES_TOTALES, sim.empresa.mes)
    return [{"mes": m, "ventas_por_dia": round(ventas_objetivo_del_mes(m), 1),
             "tecnicos": tecnicos_objetivo_del_mes(m)} for m in range(1, ultimo + 1)]


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
