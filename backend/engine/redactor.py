"""Local WRITER of the sector reports.

Composes each sector's monthly report from the NUMBERS the program computed
(not from the AI). It is the "fallback writer": it works without internet,
without credits and without AMD, so the demo **never ends up without a report**.

When the real brain (AMD) is available, it analyzes and this module writes the
final document.

It speaks English and Spanish: every user-visible string carries both versions
via `idioma.t(...)`.

Metrics contract (what `engine/sectores.py` builds):

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

from idioma import es_espanol, t

from .facturas import sello

TITULOS = {
    "gerente": ("Management", "Gerencia"),
    "ventas": ("Sales · Telemarketers", "Ventas · Teleoperadores"),
    "agenda": ("Scheduling & technicians", "Agenda y técnicos"),
    "facturacion": ("Billing", "Facturación"),
}

NOMBRE_DEFECTO: dict[str, tuple[str, str]] = {
    "total_mal_sumado": ("total does not add up", "el total no cierra"),
    "cuit_invalido": ("invalid CUIT", "CUIT inválido"),
    "fecha_invalida": ("impossible date", "fecha imposible"),
    "iva_mal_calculado": ("VAT miscalculated", "IVA mal calculado"),
    "item_descuadrado": ("line item out of balance", "ítem descuadrado"),
    "importe_negativo": ("negative amount", "importe negativo"),
    "campo_faltante": ("missing field", "campo faltante"),
}

def titulo_de(sector: str) -> str:
    return t(*TITULOS.get(sector, (sector, sector)))


def nombre_defecto(tipo: str) -> str:
    return t(*NOMBRE_DEFECTO.get(tipo, (tipo, tipo)))


def _fmt(x: Any, dec: int = 0) -> str:
    """Number with thousands separator, in the active language's format."""
    try:
        s = f"{float(x):,.{dec}f}"
    except (TypeError, ValueError):
        return str(x)
    if es_espanol():
        s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return s


def _num(x: Any) -> str:
    return _fmt(x, 0)


def _dec(x: Any) -> str:
    return _fmt(x, 1)


def _usd(x: Any) -> str:
    try:
        return "USD " + _fmt(x, 0)
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
    vpd = _dec(m.get("ventas_por_dia", 0))
    balance = float(m.get("balance", 0) or 0)
    tecnicos = int(m.get("tecnicos", 0) or 0)
    meta = int(m.get("meta_tecnicos", 10) or 10)
    semaforo = "verde" if balance > 0 else ("ambar" if balance > -500 else "rojo")

    hallazgos = [
        {"titulo": t("Month volume", "Volumen del mes"),
         "dato": t(f"{_num(ventas)} sales", f"{_num(ventas)} ventas"),
         "detalle": t(
             f"{_num(ventas)} sales were closed ({vpd}/day) with "
             f"{m.get('operadores', 0)} operators in the field.",
             f"Se cerraron {_num(ventas)} ventas ({vpd}/día) con "
             f"{m.get('operadores', 0)} operadores en la calle.")},
        {"titulo": t("Economic result", "Resultado económico"),
         "dato": _usd(balance),
         "detalle": t(
             f"Revenue {_usd(m.get('ingresos', 0))} against costs "
             f"{_usd(m.get('costos', 0))}. Closing cash: {_usd(m.get('caja', 0))}.",
             f"Ingresos {_usd(m.get('ingresos', 0))} contra costos "
             f"{_usd(m.get('costos', 0))}. Caja al cierre: {_usd(m.get('caja', 0))}.")},
    ]
    if tecnicos >= meta:
        hallazgos.append({
            "titulo": t("Goal met", "Meta cumplida"),
            "dato": t(f"{tecnicos} technicians", f"{tecnicos} técnicos"),
            "detalle": t(
                f"Reached the goal of {meta} technicians: the team is complete.",
                f"Se alcanzó la meta de {meta} técnicos: el equipo está completo.")})
    else:
        hallazgos.append({
            "titulo": t("On the way to the goal", "En camino a la meta"),
            "dato": t(f"{tecnicos}/{meta} technicians", f"{tecnicos}/{meta} técnicos"),
            "detalle": t(
                f"{meta - tecnicos} technicians to go for the month-9 goal.",
                f"Faltan {meta - tecnicos} técnicos para la meta del mes 9.")})

    if balance > 0 and tecnicos < meta:
        recom = t(
            "Keep the growth going: add one more technician and keep improving "
            "conversion so we don't grow only by hiring people.",
            "Sostener el crecimiento: sumar un técnico más y seguir mejorando la "
            "conversión para no crecer sólo contratando gente.")
    elif balance > 0:
        recom = t(
            "The business is healthy: stabilize, protect the cash and keep the conversion.",
            "El negocio está sano: estabilizar, cuidar la caja y sostener la conversión.")
    else:
        recom = t(
            "Protect the cash this month: review lead costs and don't hire until "
            "sales cover the spend.",
            "Cuidar la caja este mes: revisar el costo de leads y no contratar hasta "
            "que las ventas cubran el gasto.")

    return {
        "titulo": t(f"Month {mes} close — Management", f"Cierre del mes {mes} — Gerencia"),
        "resumen": t(
            f"The month closed with {_num(ventas)} sales ({vpd}/day) and a result of "
            f"{_usd(balance)}. Cash ended at {_usd(m.get('caja', 0))} with "
            f"{tecnicos} technicians working.",
            f"El mes cerró con {_num(ventas)} ventas ({vpd}/día) y un resultado de "
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
    motivo = m.get("top_motivo") or t("no data", "sin datos")
    semaforo = "verde" if float(conv or 0) >= 0.05 else ("ambar" if float(conv or 0) >= 0.03 else "rojo")

    return {
        "titulo": t(f"Month {mes} — Sales and telemarketers", f"Mes {mes} — Ventas y teleoperadores"),
        "resumen": t(
            f"{_num(m.get('leads', 0))} leads came in; {_num(llamadas)} "
            f"calls were made and {_num(ventas)} sales closed ({_pct(conv)} of the calls). "
            f"{_num(m.get('atendidas', 0))} answered.",
            f"Entraron {_num(m.get('leads', 0))} leads; se hicieron {_num(llamadas)} "
            f"llamadas y se cerraron {_num(ventas)} ventas ({_pct(conv)} de las llamadas). "
            f"{_num(m.get('atendidas', 0))} atendieron."),
        "hallazgos": [
            {"titulo": t("How many answer", "Cuántos atienden"),
             "dato": _pct(m.get("tasa_respuesta", 0)),
             "detalle": t(
                 f"Out of every 100 calls, {_pct(m.get('tasa_respuesta', 0))} answered. "
                 "Improving the database raises this number.",
                 f"De cada 100 llamadas, {_pct(m.get('tasa_respuesta', 0))} atendieron. "
                 "Mejorar la base sube este número.")},
            {"titulo": t("How many close", "Cuántos cierran"),
             "dato": _pct(m.get("tasa_cierre", 0)),
             "detalle": t(
                 f"Of those who answered, {_pct(m.get('tasa_cierre', 0))} bought: "
                 "it is the team's service lever.",
                 f"De los que atendieron, {_pct(m.get('tasa_cierre', 0))} compraron: "
                 "es la palanca del servicio del equipo.")},
            {"titulo": t("Why they don't buy", "Por qué no compran"),
             "dato": t(f"{_num(m.get('top_motivo_n', 0))} cases", f"{_num(m.get('top_motivo_n', 0))} casos"),
             "detalle": t(f"The most repeated reason was «{motivo}».",
                          f"El motivo más repetido fue «{motivo}».")},
        ],
        "recomendacion": t(
            "Focus the improvements on the database (so more people answer) and "
            "on the pitch against the most repeated reason.",
            "Enfocar las mejoras en la base (para que atiendan más) y en el discurso "
            "contra el motivo más repetido."),
        "semaforo": semaforo,
    }


# ------------------------------------------------------------------- agenda
def _agenda(mes: int, m: dict) -> dict:
    inst = int(m.get("instalaciones", 0) or 0)
    sin_cap = int(m.get("sin_capacidad", 0) or 0)
    semaforo = "rojo" if sin_cap > 0 else "verde"
    turnos = {
        "9am": t("in the morning", "por la mañana"),
        "12pm": t("at noon", "al mediodía"),
        "4pm": t("in the afternoon", "por la tarde"),
    }
    turno_legible = turnos.get(str(m.get("turno_top")), str(m.get("turno_top")) or "—")

    hallazgos = [
        {"titulo": t("Installs done", "Instalaciones hechas"),
         "dato": t(f"{_num(inst)} visits", f"{_num(inst)} visitas"),
         "detalle": t(f"The technicians completed {_num(inst)} installs this month.",
                      f"Los técnicos completaron {_num(inst)} instalaciones este mes.")},
        {"titulo": t("Most requested slot", "Turno más pedido"),
         "dato": turno_legible,
         "detalle": t(
             f"The preferred time was {turno_legible} ({_num(m.get('turno_top_n', 0))} visits).",
             f"El horario preferido fue {turno_legible} ({_num(m.get('turno_top_n', 0))} visitas).")},
        {"titulo": t("Busiest area", "Zona más cargada"),
         "dato": str(m.get("barrio_top") or "—"),
         "detalle": t(
             f"{m.get('barrio_top')} concentrated {_num(m.get('barrio_top_n', 0))} visits: "
             "it pays to have a technician nearby.",
             f"{m.get('barrio_top')} concentró {_num(m.get('barrio_top_n', 0))} visitas: "
             "conviene tener un técnico cerca.")},
    ]
    if sin_cap > 0:
        hallazgos.append({
            "titulo": t("Sales left without a slot", "Ventas que quedaron sin turno"),
            "dato": t(f"{_num(sin_cap)} with no date", f"{_num(sin_cap)} sin fecha"),
            "detalle": t(
                "There were more sales than install capacity: we need more people.",
                "Hubo más ventas que capacidad de instalación: hacen falta más manos.")})

    recom = t(
        "Add a technician: there were sales waiting for a slot."
        if sin_cap > 0 else
        "Capacity is enough: keep the zone assignment and the slot board.",
        "Sumar un técnico: hubo ventas esperando turno."
        if sin_cap > 0 else
        "La capacidad alcanza: sostener el reparto por zona y la pizarra de turnos.")

    return {
        "titulo": t(f"Month {mes} — Scheduling & technicians", f"Mes {mes} — Agenda y técnicos"),
        "resumen": t(
            f"{_num(inst)} alarms were installed with {_num(m.get('citas', 0))} visits booked. "
            + (f"{_num(sin_cap)} sales were left without a slot for lack of capacity."
               if sin_cap > 0 else "The schedule was covered without surprises."),
            f"{_num(inst)} alarmas se instalaron con {_num(m.get('citas', 0))} visitas agendadas. "
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
    defecto_top = nombre_defecto(str(m.get("defecto_top") or "")) if m.get("defecto_top") else "—"
    semaforo = "verde" if float(m.get("tasa_deteccion", 1) or 0) >= 0.9 else "ambar"

    return {
        "titulo": t(f"Month {mes} — Billing (simulated)", f"Mes {mes} — Facturación (simulada)"),
        "resumen": t(
            f"{_num(n)} SIMULATED invoices were issued. The reader detected "
            f"{_num(detectados)} of {_num(defectos)} injected defects "
            f"({_pct(m.get('tasa_deteccion', 0))}) with a read precision of "
            f"{_pct(precision)}.",
            f"Se emitieron {_num(n)} comprobantes SIMULADOS. El lector detectó "
            f"{_num(detectados)} de {_num(defectos)} defectos inyectados "
            f"({_pct(m.get('tasa_deteccion', 0))}) con una precisión de lectura de "
            f"{_pct(precision)}."),
        "hallazgos": [
            {"titulo": t("Read precision", "Precisión de lectura"),
             "dato": _pct(precision),
             "detalle": t(
                 "How well the invoice fields were read (number, CUIT, total…).",
                 "Qué tan bien se leyeron los campos del comprobante (número, CUIT, total…).")},
            {"titulo": t("Defects detected", "Defectos detectados"),
             "dato": f"{_num(detectados)}/{_num(defectos)}",
             "detalle": t(
                 "The audit finds the errors before they are taken as good.",
                 "La auditoría encuentra los errores antes de que se tomen como buenos.")},
            {"titulo": t("Most common defect", "Defecto más común"),
             "dato": defecto_top,
             "detalle": t(
                 f"«{defecto_top}» was the error that appeared most in the invoices.",
                 f"«{defecto_top}» fue el error que más apareció en los comprobantes.")},
        ],
        "recomendacion": t(
            "Review the invoices the audit flagged before issuing them: "
            "that is money lost to a digit or a total that does not add up.",
            "Revisar los comprobantes que la auditoría marcó antes de emitirlos: "
            "es plata perdida por un dígito o un total que no cierra."),
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
    """Builds the report text."""
    nombre = titulo_de(sector)
    lineas = [
        t(f"SECTOR REPORT — {nombre.upper()}", f"INFORME DE SECTOR — {nombre.upper()}"),
        t(f"Nexus Alarm · Month {mes} · fictional company (simulated data)",
          f"Nexus Alarm · Mes {mes} · empresa ficticia (datos simulados)"),
        "",
        resumen,
        "",
        t("Findings:", "Hallazgos:"),
    ]
    for h in hallazgos:
        dato = f" ({h.get('dato')})" if h.get("dato") else ""
        lineas.append(f"  • {h.get('titulo')}{dato}: {h.get('detalle')}")
    lineas += ["", t(f"Recommendation: {recomendacion}", f"Recomendación: {recomendacion}")]
    if sector == "facturacion":
        lineas += ["", sello()]
    return "\n".join(lineas)


def redactar(sector: str, mes: int, metricas: dict) -> dict:
    """Full report (dict) written locally for a sector and a month."""
    fn = _REDACTORES.get(sector, _gerente)
    base = fn(mes, metricas)
    base["documento"] = componer_documento(
        sector, mes, base["titulo"], base["resumen"], base["hallazgos"],
        base["recomendacion"])
    return base
