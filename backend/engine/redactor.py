"""Redactor LOCAL de los informes de sector.

Compone el informe mensual de cada sector a partir de los NÚMEROS que calculó el
programa (no de la IA). Es el "redactor de respaldo": funciona sin internet, sin
créditos y sin AMD, así que la demo **nunca se queda sin informe**.

Cuando el cerebro real (AMD) y el redactor de Evolus están disponibles, escriben
ellos dos (AMD analiza, Evolus redacta). Si alguno falta, escribe este módulo.

Contrato de las métricas (lo que arma `engine/sectores.py`):

  gerente     ventas, ventas_por_dia, ingresos, costos, balance, caja, operadores,
              tecnicos, mejoras, clientes_activos, meta_tecnicos, meta_cumplida,
              decisiones_aprobadas, decisiones_total
  ventas      leads, llamadas, atendidas, ventas, ventas_por_dia, tasa_respuesta,
              tasa_cierre, conversion, top_motivo, top_motivo_n
  agenda      instalaciones, sin_capacidad, citas, turno_top, turno_top_n,
              barrio_top, barrio_top_n, capacidad_dia
  facturacion comprobantes, precision, defectos, detectados, tasa_deteccion,
              defecto_top, defectos_por_tipo
"""
from __future__ import annotations

from typing import Any

TITULOS = {
    "gerente": "Gerencia",
    "ventas": "Ventas · Teleoperadores",
    "agenda": "Agenda y técnicos",
    "facturacion": "Facturación",
}

NOMBRE_DEFECTO: dict[str, str] = {
    "total_mal_sumado": "total mal sumado",
    "cuit_invalido": "CUIT inválido",
    "fecha_invalida": "fecha imposible",
    "iva_mal_calculado": "IVA mal calculado",
    "item_descuadrado": "ítem descuadrado",
    "importe_negativo": "importe negativo",
    "campo_faltante": "campo faltante",
}

SELLO = "SIMULADO – SIN VALIDEZ FISCAL"


def _num(x: Any) -> str:
    """Número con separador de miles (formato argentino: punto)."""
    try:
        return f"{float(x):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(x)


def _usd(x: Any) -> str:
    try:
        return "USD " + f"{float(x):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(x)


def _pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.0f}%"
    except (TypeError, ValueError):
        return str(x)


# ------------------------------------------------------------------ gerente
def _gerente(mes: int, m: dict) -> dict:
    ventas = int(m.get("ventas", 0) or 0)
    vpd = m.get("ventas_por_dia", 0)
    balance = float(m.get("balance", 0) or 0)
    tecnicos = int(m.get("tecnicos", 0) or 0)
    meta = int(m.get("meta_tecnicos", 10) or 10)
    semaforo = "verde" if balance > 0 else ("ambar" if balance > -500 else "rojo")

    hallazgos = [
        {"titulo": "Volumen del mes", "dato": f"{_num(ventas)} ventas",
         "detalle": (f"Se cerraron {_num(ventas)} ventas ({vpd}/día) con "
                     f"{m.get('operadores', 0)} operadores en la calle.")},
        {"titulo": "Resultado económico", "dato": _usd(balance),
         "detalle": (f"Ingresos {_usd(m.get('ingresos', 0))} contra costos "
                     f"{_usd(m.get('costos', 0))}. Caja al cierre: {_usd(m.get('caja', 0))}.")},
    ]
    if tecnicos >= meta:
        hallazgos.append({"titulo": "Meta cumplida", "dato": f"{tecnicos} técnicos",
                          "detalle": f"Se llegó a la meta de {meta} técnicos: el equipo está completo."})
    else:
        hallazgos.append({"titulo": "Camino a la meta", "dato": f"{tecnicos}/{meta} técnicos",
                          "detalle": f"Faltan {meta - tecnicos} técnicos para la meta del mes 9."})

    if balance > 0 and tecnicos < meta:
        recom = ("Sostener el crecimiento: sumar un técnico más y seguir mejorando la "
                 "conversión para no contratar solo gente.")
    elif balance > 0:
        recom = "El negocio está sano: estabilizar, cuidar la caja y mantener la conversión."
    else:
        recom = ("Cuidar la caja este mes: revisar costos de leads y no contratar hasta "
                 "que las ventas cubran el gasto.")

    return {
        "titulo": f"Cierre del mes {mes} — Gerencia",
        "resumen": (f"El mes cerró con {_num(ventas)} ventas ({vpd}/día) y un resultado de "
                    f"{_usd(balance)}. La caja quedó en {_usd(m.get('caja', 0))} con "
                    f"{tecnicos} técnicos trabajando."),
        "hallazgos": hallazgos,
        "recomendacion": recom,
        "semaforo": semaforo,
    }


# ------------------------------------------------------------------- ventas
def _ventas(mes: int, m: dict) -> dict:
    llamadas = int(m.get("llamadas", 0) or 0)
    ventas = int(m.get("ventas", 0) or 0)
    conv = m.get("conversion", 0)
    motivo = m.get("top_motivo") or "sin datos"
    semaforo = "verde" if float(conv or 0) >= 0.05 else ("ambar" if float(conv or 0) >= 0.03 else "rojo")

    return {
        "titulo": f"Mes {mes} — Ventas y teleoperadores",
        "resumen": (f"Entraron {_num(m.get('leads', 0))} leads; se hicieron {_num(llamadas)} "
                    f"llamadas y se cerraron {_num(ventas)} ventas ({_pct(conv)} de las llamadas). "
                    f"Atendieron {_num(m.get('atendidas', 0))}."),
        "hallazgos": [
            {"titulo": "Cuánto atienden", "dato": _pct(m.get("tasa_respuesta", 0)),
             "detalle": (f"De cada 100 llamadas, {_pct(m.get('tasa_respuesta', 0))} atendieron. "
                         "Mejorar la base de datos sube este número.")},
            {"titulo": "Cuánto cierran", "dato": _pct(m.get("tasa_cierre", 0)),
             "detalle": (f"De los que atendieron, {_pct(m.get('tasa_cierre', 0))} compraron: "
                         "es la palanca de servicio del equipo.")},
            {"titulo": "Por qué no compran", "dato": f"{_num(m.get('top_motivo_n', 0))} casos",
             "detalle": f"El motivo más repetido fue «{motivo}»."},
        ],
        "recomendacion": ("Concentrar las mejoras en la base de datos (que más gente atienda) y "
                          "en el argumentario contra el motivo más repetido."),
        "semaforo": semaforo,
    }


# ------------------------------------------------------------------- agenda
def _agenda(mes: int, m: dict) -> dict:
    inst = int(m.get("instalaciones", 0) or 0)
    sin_cap = int(m.get("sin_capacidad", 0) or 0)
    semaforo = "rojo" if sin_cap > 0 else "verde"
    turnos = {"9am": "a la mañana", "12pm": "al mediodía", "4pm": "a la tarde"}

    hallazgos = [
        {"titulo": "Instalaciones hechas", "dato": f"{_num(inst)} visitas",
         "detalle": f"Los técnicos completaron {_num(inst)} instalaciones este mes."},
        {"titulo": "Turno más pedido",
         "dato": turnos.get(str(m.get("turno_top")), str(m.get("turno_top")) or "—"),
         "detalle": (f"El horario preferido fue {turnos.get(str(m.get('turno_top')), m.get('turno_top'))} "
                     f"({_num(m.get('turno_top_n', 0))} visitas).")},
        {"titulo": "Zona con más trabajo", "dato": str(m.get("barrio_top") or "—"),
         "detalle": (f"{m.get('barrio_top')} concentró {_num(m.get('barrio_top_n', 0))} visitas: "
                     "ahí conviene tener un técnico cerca.")},
    ]
    if sin_cap > 0:
        hallazgos.append({"titulo": "Quedaron ventas sin turno", "dato": f"{_num(sin_cap)} sin fecha",
                          "detalle": "Hubo más ventas que capacidad de instalación: falta gente."})

    recom = ("Sumar un técnico: hubo ventas esperando turno." if sin_cap > 0
             else "La capacidad alcanza: mantener el reparto por zona y la pizarra de turnos.")

    return {
        "titulo": f"Mes {mes} — Agenda y técnicos",
        "resumen": (f"Se instalaron {_num(inst)} alarmas con {_num(m.get('citas', 0))} visitas agendadas. "
                    + (f"{_num(sin_cap)} ventas quedaron sin turno por falta de capacidad."
                       if sin_cap > 0 else "La agenda se cubrió sin sobresaltos.")),
        "hallazgos": hallazgos,
        "recomendacion": recom,
        "semaforo": semaforo,
    }


# -------------------------------------------------------------- facturación
def _facturacion(mes: int, m: dict) -> dict:
    n = int(m.get("comprobantes", 0) or 0)
    defectos = int(m.get("defectos", 0) or 0)
    detectados = int(m.get("detectados", 0) or 0)
    precision = m.get("precision", 0)
    defecto_top = NOMBRE_DEFECTO.get(str(m.get("defecto_top")), str(m.get("defecto_top") or "—"))
    semaforo = "verde" if float(m.get("tasa_deteccion", 1) or 0) >= 0.9 else "ambar"

    return {
        "titulo": f"Mes {mes} — Facturación (simulada)",
        "resumen": (f"Se emitieron {_num(n)} comprobantes SIMULADOS. El lector detectó "
                    f"{_num(detectados)} de {_num(defectos)} defectos inyectados "
                    f"({_pct(m.get('tasa_deteccion', 0))}) con una precisión de lectura de "
                    f"{_pct(precision)}."),
        "hallazgos": [
            {"titulo": "Precisión de lectura", "dato": _pct(precision),
             "detalle": "Qué tan bien se leyeron los campos del comprobante (número, CUIT, total…)."},
            {"titulo": "Defectos detectados", "dato": f"{_num(detectados)}/{_num(defectos)}",
             "detalle": "La auditoría encuentra los errores antes de darlos por buenos."},
            {"titulo": "Defecto más común", "dato": defecto_top,
             "detalle": f"«{defecto_top}» fue el error que más apareció en los comprobantes."},
        ],
        "recomendacion": ("Revisar los comprobantes que la auditoría marcó antes de emitirlos: "
                          "es plata que se pierde por un dígito o un total mal sumado."),
        "semaforo": semaforo,
    }


_REDACTORES = {
    "gerente": _gerente,
    "ventas": _ventas,
    "agenda": _agenda,
    "facturacion": _facturacion,
}


def componer_documento(sector: str, mes: int, titulo: str, resumen: str,
                       hallazgos: list[dict], recomendacion: str) -> str:
    """Arma el texto del informe (lo que después pule Evolus, si está)."""
    nombre = TITULOS.get(sector, sector)
    lineas = [
        f"INFORME DEL SECTOR — {nombre.upper()}",
        f"Nexus Alarm · Mes {mes} · empresa ficticia (datos simulados)",
        "",
        resumen,
        "",
        "Hallazgos:",
    ]
    for h in hallazgos:
        dato = f" ({h.get('dato')})" if h.get("dato") else ""
        lineas.append(f"  • {h.get('titulo')}{dato}: {h.get('detalle')}")
    lineas += ["", f"Recomendación: {recomendacion}"]
    if sector == "facturacion":
        lineas += ["", SELLO]
    return "\n".join(lineas)


def redactar(sector: str, mes: int, metricas: dict) -> dict:
    """Informe completo (dict) escrito localmente para un sector y un mes."""
    fn = _REDACTORES.get(sector, _gerente)
    base = fn(mes, metricas)
    base["documento"] = componer_documento(
        sector, mes, base["titulo"], base["resumen"], base["hallazgos"],
        base["recomendacion"])
    return base
