"""Los 4 SECTORES de Nexus Alarm y sus informes mensuales.

Cada sector es una "oficina" del negocio con su propio agente:

    🧾 Gerencia        — rumbo, caja y decisiones (acta del Gerente IA)
    📞 Ventas          — teleoperadores: llamadas, conversión y motivos
    📅 Agenda/técnicos  — turnos, instalaciones y reparto por zona
    🧮 Facturación      — comprobantes simulados y auditoría

Cómo se arma un informe (acordado con el autor):

1. El PROGRAMA junta los NÚMEROS del mes (regla del concurso: no depende del LLM).
2. La IA (AMD) los ANALIZA en modo agéntico y saca los hallazgos.
3. El escritor LOCAL (`engine/redactor.py`) los REDACTA como documento. La demo
   nunca se queda sin informe y no depende de ningún servicio externo.

Los 6 meses precargados se siembran con el redactor LOCAL (instantáneo, sin
créditos). Los meses que corre el dueño en vivo usan la IA real (AMD).

Todo el texto visible habla inglés y español (`engine/idioma.py`): los nombres de
sector, las etiquetas de los números y el informe entero.
"""
from __future__ import annotations

import json
from typing import Any

from llm import LLMClient
from schemas import InformeSector
from store import Store

from idioma import es_espanol, t

from . import redactor
from .business import (
    DIAS_POR_SEMANA,
    INSTALACIONES_POR_TECNICO_DIA,
    META_TECNICOS,
    SEMANAS_POR_MES,
)

# ------------------------------------------------------------------ los 4
# Lo que NO cambia con el idioma (orden, id, ícono y color).
SECTORES: list[dict[str, str]] = [
    {"id": "gerente", "icono": "🧾", "color": "azul"},
    {"id": "ventas", "icono": "📞", "color": "verde"},
    {"id": "agenda", "icono": "📅", "color": "violeta"},
    {"id": "facturacion", "icono": "🧮", "color": "cyan"},
]

_NOMBRE = {
    "gerente": ("Management", "Gerencia"),
    "ventas": ("Sales · Telemarketers", "Ventas · Teleoperadores"),
    "agenda": ("Scheduling & technicians", "Agenda y técnicos"),
    "facturacion": ("Billing", "Facturación"),
}
_BAJADA = {
    "gerente": ("Direction, cash and the month's decisions",
                "Rumbo, caja y las decisiones del mes"),
    "ventas": ("Calls, conversion and why they don't buy",
               "Llamadas, conversión y por qué no compran"),
    "agenda": ("Slots, installs and zone assignment",
               "Turnos, instalaciones y reparto por zona"),
    "facturacion": ("Simulated invoices and auditing",
                    "Comprobantes simulados y auditoría"),
}
_ICONO = {s["id"]: s["icono"] for s in SECTORES}
_COLOR = {s["id"]: s["color"] for s in SECTORES}


def meta_sector(sector_id: str) -> dict[str, str]:
    """Los datos de un sector en el idioma activo (id, ícono, color, nombre, bajada)."""
    return {
        "id": sector_id,
        "icono": _ICONO.get(sector_id, "🗂️"),
        "color": _COLOR.get(sector_id, "azul"),
        "nombre": t(*_NOMBRE.get(sector_id, (sector_id, sector_id))),
        "bajada": t(*_BAJADA.get(sector_id, ("", ""))),
    }


def es_sector(sector: str) -> bool:
    return sector in _NOMBRE


def semanas_del_mes(mes: int) -> tuple[int, int]:
    """Primera y última semana (de las 4) que forman el mes."""
    return (mes - 1) * SEMANAS_POR_MES + 1, mes * SEMANAS_POR_MES


# --------------------------------------------------------------- métricas
def _resumen(store: Store, mes: int) -> dict:
    fila = store.conn.execute(
        "SELECT * FROM resumen_mes WHERE mes = ?", (mes,)).fetchone()
    return dict(fila) if fila else {}


def _decisiones(store: Store, mes: int) -> list[dict]:
    return [dict(r) for r in store.conn.execute(
        "SELECT accion, valor, motivo, aprobada, aviso FROM decisiones_gerente "
        "WHERE mes = ? ORDER BY id", (mes,)).fetchall()]


def _motivos_del_mes(store: Store, mes: int) -> list[dict]:
    venta_cerrada = t("Closed the sale", "Cerró la venta")
    return [dict(r) for r in store.conn.execute(
        "SELECT motivo, COUNT(*) AS n FROM llamadas "
        "WHERE mes = ? AND atendio = 1 AND motivo <> ? "
        "GROUP BY motivo ORDER BY n DESC", (mes, venta_cerrada)).fetchall()]


def _facturacion_lote(mes: int, ventas: int) -> dict:
    """Comprobantes simulados del mes + auditoría (100% local, sin red)."""
    n = max(1, min(50, int(ventas or 1)))
    try:
        from .facturas import evaluar_lote

        lote = evaluar_lote(n, seed=1000 + mes)
        tipos = {t_: d["esperados"] for t_, d in lote["defectos_por_tipo"].items()}
        defecto_top = max(tipos, key=tipos.get) if tipos else ""
        return {
            "comprobantes": n,
            "precision": lote["precision_promedio"],
            "defectos": lote["defectos_totales"],
            "detectados": lote["defectos_detectados"],
            "tasa_deteccion": lote["tasa_deteccion"],
            "defecto_top": defecto_top,
            "defectos_por_tipo": tipos,
        }
    except Exception:  # noqa: BLE001 — nunca frena el informe
        return {"comprobantes": n, "precision": 0.0, "defectos": 0, "detectados": 0,
                "tasa_deteccion": 1.0, "defecto_top": "", "defectos_por_tipo": {}}


def metricas_de_sector(store: Store, mes: int, sector: str) -> dict:
    """Junta, del SQLite, TODOS los números que el informe del sector necesita."""
    r = _resumen(store, mes)
    ini, fin = semanas_del_mes(mes)

    def f(clave: str, defecto: float = 0.0) -> float:
        return float(r.get(clave) or defecto)

    llamadas = int(r.get("llamadas") or 0)
    atendidas = int(r.get("atendidas") or 0)
    ventas = int(r.get("ventas") or 0)
    dias = SEMANAS_POR_MES * DIAS_POR_SEMANA
    ingresos = f("ingresos_instalaciones") + f("ingresos_recurrentes")
    costos = f("costos_total")

    if sector == "gerente":
        decisiones = _decisiones(store, mes)
        return {
            "ventas": ventas,
            "ventas_por_dia": round(ventas / dias, 1),
            "ingresos": round(ingresos, 2),
            "costos": round(costos, 2),
            "balance": round(ingresos - costos, 2),
            "caja": round(f("caja"), 2),
            "operadores": int(r.get("operadores") or 0),
            "tecnicos": int(r.get("tecnicos") or 0),
            "mejoras": int(r.get("mejoras") or 0),
            "clientes_activos": int(r.get("clientes_activos") or 0),
            "meta_tecnicos": META_TECNICOS,
            "meta_cumplida": int(r.get("tecnicos") or 0) >= META_TECNICOS,
            "decisiones_total": len(decisiones),
            "decisiones_aprobadas": sum(1 for d in decisiones if d["aprobada"]),
        }

    if sector == "ventas":
        motivos = _motivos_del_mes(store, mes)
        top = motivos[0] if motivos else {"motivo": t("no data", "sin datos"), "n": 0}
        return {
            "leads": int(r.get("leads") or 0),
            "llamadas": llamadas,
            "atendidas": atendidas,
            "ventas": ventas,
            "ventas_por_dia": round(ventas / dias, 1),
            "tasa_respuesta": round(atendidas / llamadas, 3) if llamadas else 0.0,
            "tasa_cierre": round(ventas / atendidas, 3) if atendidas else 0.0,
            "conversion": round(ventas / llamadas, 3) if llamadas else 0.0,
            "top_motivo": top["motivo"],
            "top_motivo_n": int(top["n"]),
            "motivos": motivos[:5],
        }

    if sector == "agenda":
        turnos = [dict(x) for x in store.conn.execute(
            "SELECT turno, COUNT(*) AS n FROM citas WHERE semana >= ? AND semana <= ? "
            "AND estado = 'confirmada' GROUP BY turno ORDER BY n DESC", (ini, fin)).fetchall()]
        barrios = [dict(x) for x in store.conn.execute(
            "SELECT barrio, COUNT(*) AS n FROM citas WHERE semana >= ? AND semana <= ? "
            "AND estado = 'confirmada' GROUP BY barrio ORDER BY n DESC LIMIT 1",
            (ini, fin)).fetchall()]
        return {
            "instalaciones": int(r.get("instalaciones") or 0),
            "sin_capacidad": int(r.get("sin_capacidad") or 0),
            "citas": int(store.contar(
                "citas", "semana >= ? AND semana <= ? AND estado = 'confirmada'", (ini, fin))),
            "turno_top": turnos[0]["turno"] if turnos else "",
            "turno_top_n": int(turnos[0]["n"]) if turnos else 0,
            "turnos": turnos,
            "barrio_top": barrios[0]["barrio"] if barrios else "",
            "barrio_top_n": int(barrios[0]["n"]) if barrios else 0,
            "capacidad_dia": int(r.get("tecnicos") or 0) * INSTALACIONES_POR_TECNICO_DIA,
        }

    # facturacion
    return {**_facturacion_lote(mes, ventas), "ventas": ventas}


# ------------------------------------------- números "en criollo" (pantalla)
def campos_de_sector(sector: str, m: dict) -> list[dict]:
    """Lista lista para mostrar: {etiqueta, valor} con el formato del idioma activo."""
    def num(x: Any) -> str:
        try:
            s = f"{float(x):,.0f}"
        except (TypeError, ValueError):
            return str(x)
        return s.replace(",", ".") if es_espanol() else s

    def usd(x: Any) -> str:
        return "USD " + num(x)

    def pct(x: Any) -> str:
        try:
            return f"{float(x) * 100:.0f}%"
        except (TypeError, ValueError):
            return str(x)

    if sector == "gerente":
        return [
            {"etiqueta": t("Sales of the month", "Ventas del mes"), "valor": num(m.get("ventas"))},
            {"etiqueta": t("Sales per day", "Ventas por día"), "valor": f"{float(m.get('ventas_por_dia') or 0):.1f}".replace(".", "," if es_espanol() else ".")},
            {"etiqueta": t("Revenue", "Ingresos"), "valor": usd(m.get("ingresos"))},
            {"etiqueta": t("Costs", "Costos"), "valor": usd(m.get("costos"))},
            {"etiqueta": t("Result", "Resultado"), "valor": usd(m.get("balance"))},
            {"etiqueta": t("Cash", "Caja"), "valor": usd(m.get("caja"))},
            {"etiqueta": t("Operators", "Operadores"), "valor": num(m.get("operadores"))},
            {"etiqueta": t("Technicians", "Técnicos"), "valor": f"{num(m.get('tecnicos'))}/{num(m.get('meta_tecnicos'))}"},
            {"etiqueta": t("Active clients", "Clientes activos"), "valor": num(m.get("clientes_activos"))},
        ]
    if sector == "ventas":
        return [
            {"etiqueta": t("Leads", "Leads"), "valor": num(m.get("leads"))},
            {"etiqueta": t("Calls", "Llamadas"), "valor": num(m.get("llamadas"))},
            {"etiqueta": t("Answered", "Atendidas"), "valor": num(m.get("atendidas"))},
            {"etiqueta": t("Sales", "Ventas"), "valor": num(m.get("ventas"))},
            {"etiqueta": t("Answer rate", "Tasa de respuesta"), "valor": pct(m.get("tasa_respuesta"))},
            {"etiqueta": t("Close rate", "Tasa de cierre"), "valor": pct(m.get("tasa_cierre"))},
            {"etiqueta": t("Conversion", "Conversión"), "valor": pct(m.get("conversion"))},
        ]
    if sector == "agenda":
        turnos = {"9am": t("9am", "9am"), "12pm": t("12pm", "12pm"), "4pm": t("4pm", "4pm")}
        return [
            {"etiqueta": t("Installs", "Instalaciones"), "valor": num(m.get("instalaciones"))},
            {"etiqueta": t("Booked visits", "Visitas agendadas"), "valor": num(m.get("citas"))},
            {"etiqueta": t("No slot", "Sin turno"), "valor": num(m.get("sin_capacidad"))},
            {"etiqueta": t("Most requested slot", "Turno más pedido"), "valor": turnos.get(str(m.get("turno_top")), m.get("turno_top") or "—")},
            {"etiqueta": t("Busiest area", "Zona más cargada"), "valor": m.get("barrio_top") or "—"},
        ]
    return [
        {"etiqueta": t("Invoices", "Comprobantes"), "valor": num(m.get("comprobantes"))},
        {"etiqueta": t("Read precision", "Precisión de lectura"), "valor": pct(m.get("precision"))},
        {"etiqueta": t("Injected defects", "Defectos inyectados"), "valor": num(m.get("defectos"))},
        {"etiqueta": t("Detected defects", "Defectos detectados"), "valor": num(m.get("detectados"))},
        {"etiqueta": t("Detection rate", "Tasa de detección"), "valor": pct(m.get("tasa_deteccion"))},
    ]


# ------------------------------------------------------------- con la IA
_IDIOMA_TXT = {
    "en": "Write everything in ENGLISH.",
    "es": "Escribí todo en ESPAÑOL.",
}


def informe_con_ia(llm: LLMClient, sector: str, mes: int, metricas: dict) -> dict:
    """Le pide al agente del sector que analice los números (modo agéntico).

    Si la IA falla, se cae al redactor LOCAL (nunca rompe).
    """
    meta = meta_sector(sector)
    from idioma import idioma
    idioma_txt = _IDIOMA_TXT.get(idioma(), _IDIOMA_TXT["en"])
    mensajes = [
        {"role": "system",
         "content": (f"You are the agent of the «{meta['nombre']}» sector of Nexus Alarm, "
                     "a fictional alarm company in Buenos Aires (CABA). The PROGRAM already "
                     "computed the month's numbers; you interpret them and write a short, "
                     "clear report for the owner. Do not invent figures that are not in the "
                     f"data. {idioma_txt}")},
        {"role": "user",
         "content": json.dumps({"sector": sector, "nombre": meta["nombre"],
                                "mes": mes, "metricas": metricas},
                               ensure_ascii=False)},
    ]
    try:
        resp = llm.complete(agent=f"sector_{sector}", messages=mensajes,
                            schema=InformeSector)
        d = resp.model_dump()
        base = {
            "titulo": d["titulo"],
            "resumen": d["resumen"],
            "hallazgos": d.get("hallazgos") or [],
            "recomendacion": d["recomendacion"],
            "semaforo": d.get("semaforo") or "verde",
        }
        base["documento"] = redactor.componer_documento(
            sector, mes, base["titulo"], base["resumen"], base["hallazgos"],
            base["recomendacion"])
        return base
    except Exception:  # noqa: BLE001 — el cerebro no respondió: escribe el local
        return redactor.redactar(sector, mes, metricas)


# ------------------------------------------------------------ orquestador
def generar_informe(store: Store, llm: LLMClient | None, sector: str, mes: int, *,
                    usar_ia: bool = True, guardar: bool = True) -> dict:
    """Genera el informe de UN sector para UN mes y (por defecto) lo guarda."""
    metricas = metricas_de_sector(store, mes, sector)
    if usar_ia and llm is not None:
        base = informe_con_ia(llm, sector, mes, metricas)
        # Transparencia: si el cerebro está en modo prueba (mock), el informe NO
        # puede decir que "analizó la IA de AMD". Se marca aparte.
        en_mock = bool(getattr(getattr(llm, "config", None), "use_mock", False))
        fuente = "mock" if en_mock else "ia"
    else:
        base = redactor.redactar(sector, mes, metricas)
        fuente = "local"
    informe = {
        "mes": mes,
        "sector": sector,
        **meta_sector(sector),
        "titulo": base["titulo"],
        "resumen": base["resumen"],
        "hallazgos": base["hallazgos"],
        "recomendacion": base["recomendacion"],
        "semaforo": base.get("semaforo", "verde"),
        "fuente": fuente,
        "redactor": base.get("redactor", "local"),
        "documento": base["documento"],
        "metricas": metricas,
    }
    if guardar:
        store.guardar_reporte_sector(
            mes=mes, sector=sector, titulo=informe["titulo"], resumen=informe["resumen"],
            hallazgos=informe["hallazgos"], recomendacion=informe["recomendacion"],
            semaforo=informe["semaforo"], fuente=informe["fuente"],
            redactor=informe["redactor"], documento=informe["documento"],
            metricas=informe["metricas"])
    return informe


def generar_informes_mes(store: Store, llm: LLMClient | None, mes: int, *,
                         usar_ia: bool = True) -> list[dict]:
    """Cierra el mes: genera los 4 informes de sector (al cerrarse el mes)."""
    return [generar_informe(store, llm, s["id"], mes, usar_ia=usar_ia)
            for s in SECTORES]


def sembrar_informes(store: Store, hasta_mes: int, *, forzar: bool = False) -> int:
    """Precarga los informes de los meses ya corridos con el redactor LOCAL.

    Es lo que hace que los 6 meses del arranque tengan informe al instante:
    sin AMD, sin esperar. Devuelve cuántos informes escribió.
    """
    escritos = 0
    for mes in range(1, hasta_mes + 1):
        for s in SECTORES:
            if not forzar and store.reporte_sector(mes, s["id"]):
                continue
            generar_informe(store, None, s["id"], mes, usar_ia=False)
            escritos += 1
    return escritos


def asegurar_informes(store: Store) -> int:
    """Rellena los informes que falten para los meses ya resumidos (upgrades)."""
    meses = [int(r["mes"]) for r in store.conn.execute(
        "SELECT DISTINCT mes FROM resumen_mes ORDER BY mes").fetchall()]
    if not meses:
        return 0
    return sembrar_informes(store, max(meses))


# -------------------------------------------------- lo que consume la API
def listado(store: Store, mes_actual: int) -> list[dict]:
    """Los 4 sectores con su último informe, para el menú ☰."""
    salida = []
    for s in SECTORES:
        ultimo = store.ultimo_reporte_sector(s["id"])
        salida.append({
            **meta_sector(s["id"]),
            "mes_reporte": ultimo["mes"] if ultimo else None,
            "titulo": ultimo["titulo"] if ultimo else "",
            "resumen": ultimo["resumen"] if ultimo else "",
            "semaforo": ultimo["semaforo"] if ultimo else "verde",
            "fuente": ultimo["fuente"] if ultimo else "",
            "redactor": ultimo["redactor"] if ultimo else "",
            "tiene_informe": ultimo is not None,
        })
    return salida


def detalle(store: Store, sector: str, mes: int) -> dict:
    """Todo lo que muestra el panel de un sector: informe + números + historial."""
    meta = meta_sector(sector)
    rep = store.reporte_sector(mes, sector)
    historial = [r for r in store.reportes_sector() if r["sector"] == sector]
    return {
        **meta,
        "mes": mes,
        "tiene_informe": rep is not None,
        "titulo": rep["titulo"] if rep else "",
        "resumen": rep["resumen"] if rep else "",
        "hallazgos": rep["hallazgos"] if rep else [],
        "recomendacion": rep["recomendacion"] if rep else "",
        "semaforo": rep["semaforo"] if rep else "verde",
        "fuente": rep["fuente"] if rep else "",
        "redactor": rep["redactor"] if rep else "",
        "documento": rep["documento"] if rep else "",
        "creado": rep["creado"] if rep else "",
        "campos": campos_de_sector(sector, rep["metricas"]) if rep else [],
        "historial": [{"mes": h["mes"], "titulo": h["titulo"], "semaforo": h["semaforo"]}
                      for h in historial],
        "extras": extras_de_sector(store, sector, mes),
    }


def extras_de_sector(store: Store, sector: str, mes: int) -> dict:
    """Datos extra que el panel de cada sector muestra además del informe."""
    if sector == "facturacion":
        return {"facturas": facturas_del_mes(mes)}
    return {}


# ------------------------------------------------------------- facturación
def facturas_del_mes(mes: int, limite: int = 8) -> list[dict]:
    """Comprobantes SIMULADOS del mes (deterministas) con su auditoría."""
    try:
        from .facturas import evaluar_factura, generar_facturas

        lote = generar_facturas(limite, seed=1000 + mes)
        return [evaluar_factura(f) for f in lote]
    except Exception:  # noqa: BLE001
        return []
