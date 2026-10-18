"""Respuestas mock locales para el modo USE_MOCK=true.

Permiten correr TODO el flujo sin gastar créditos de GPU ni tocar la red. Las
respuestas son realistas y hablan el idioma activo (inglés o español), y respetan
las reglas de negocio simuladas (lead entrante, dirección en CABA, tarifa del kit,
etc.).

En lugar de pedirle al modelo que genere texto libre, acá devolvemos directamente
el JSON que el agente debería producir, para que el flujo sea 100% determinista.

Regla del "actor": la IA habla solo en unas pocas llamadas/charlas (las de la
demo). El volumen (miles de llamadas) lo calcula el programa sin tocar la red.
"""
from __future__ import annotations

import json
import random
from typing import Any

from schemas.teleoperador import Calificacion

from idioma import t

# Barrios reales de CABA para validar/inferir direcciones.
BARRIOS_CABA = [
    "Palermo", "Belgrano", "Caballito", "Flores", "Villa Urquiza",
    "Recoleta", "San Nicolás", "Almagro", "Boedo", "Villa Devoto",
    "Núñez", "Saavedra", "Coghlan", "Barracas", "Liniers",
]

# Palabras que indican urgencia en el mensaje del cliente (inglés y español).
_URGENCIA = ["urgent", "urgente", "robbery", "robo", "broke in", "se metieron",
             "today", "hoy", "now", "ya", "ahora", "tonight", "esta noche",
             "assaulted", "asaltaron"]

# Motivos por los que atienden y no compran (lista fija, decisión del autor).
# Cada motivo lleva su texto en los dos idiomas: (inglés, español).
_MOTIVOS_NO_COMPRA = [
    (("Too expensive for me", "Muy caro para mí"), 0.30),
    (("Already has another security company", "Ya tiene otra empresa de seguridad"), 0.22),
    (("Not interested in an alarm", "No le interesa una alarma"), 0.25),
    (("Not the right time / thinking about it", "No es el momento / lo está pensando"), 0.15),
    (("Wants to ask the family", "Quiere consultar en familia"), 0.08),
]
# Lista canónica (inglés) por compatibilidad.
MOTIVOS_NO_COMPRA = [n[0] for n, _ in _MOTIVOS_NO_COMPRA]

_KITS = ["hogar_basico", "hogar_plus", "comercial"]
_KIT_LABEL = {
    "hogar_basico": ("the Home Basic kit (USD 180)", "el kit Hogar Básico (USD 180)"),
    "hogar_plus": ("the Home Plus kit (USD 320)", "el kit Hogar Plus (USD 320)"),
    "comercial": ("the Commercial kit (USD 550)", "el kit Comercial (USD 550)"),
}
_DIAS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
_HORAS = {"9am": "09:00", "12pm": "12:00", "4pm": "16:00"}


def _dia(dia: int) -> str:
    return t(_DIAS_EN[dia % 6], _DIAS_ES[dia % 6])


def _barrio_de(direccion: str) -> str | None:
    d = direccion.lower()
    for b in BARRIOS_CABA:
        if b.lower() in d:
            return b
    return None


def _es_caba(direccion: str) -> bool:
    d = direccion.lower()
    fuera = ["tigre", "san isidro", "lanús", "avellaneda", "la plata", "morón"]
    if any(f in d for f in fuera):
        return False
    return _barrio_de(d) is not None


def _contexto(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Lee el JSON de contexto que el motor manda en el último mensaje del usuario.

    El enjambre le pasa a cada agente las opciones válidas (turnos libres,
    técnicos candidatos) como un JSON; el agente elige de ahí. Si el último
    mensaje no es JSON (charla en texto libre), devuelve {}.
    """
    ultimo = next((m["content"] for m in reversed(messages)
                   if m.get("role") == "user"), "")
    try:
        data = json.loads(ultimo)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def elegir_motivo(rng: random.Random) -> str:
    """Motivo del 'no', según una lista fija con probabilidades (idioma activo)."""
    nombres = [t(*n) for n, _ in _MOTIVOS_NO_COMPRA]
    pesos = [p for _, p in _MOTIVOS_NO_COMPRA]
    return rng.choices(nombres, weights=pesos, k=1)[0]


def teleoperador_mock(messages: list[dict[str, str]], rng: random.Random) -> dict[str, Any]:
    """Simula la respuesta del teleoperador a partir del último mensaje del cliente."""
    ultimo = next((m["content"] for m in reversed(messages)
                   if m.get("role") == "user"), "").lower()
    direccion = messages[0]["content"] if messages else ""
    barrio = _barrio_de(ultimo) or _barrio_de(direccion)
    valida = _es_caba(ultimo) or _es_caba(direccion)
    urgente = any(u in ultimo for u in _URGENCIA)

    if not valida:
        return {
            "reply_text": t(
                "Sorry, we don't install outside CABA. Do you have an address in the city?",
                "Perdón, no instalamos fuera de CABA. ¿Tenés una dirección en la ciudad?"),
            "calificacion": Calificacion.FRIELO.value,
            "direccion_valida_caba": False,
            "barrio": None,
            "propone_horario": None,
            "cierra_cita": False,
            "producto": None,
            "motivo_no_compra": t("Outside our coverage area.",
                                  "Fuera de nuestra zona de cobertura."),
            "requiere_visita_humana": False,
            "motivo": t("Address outside CABA coverage.",
                        "Dirección fuera de la cobertura de CABA."),
        }

    if urgente:
        calif = Calificacion.CALIDO
        horario = t("Today 14:00-16:00", "Hoy 14:00-16:00")
    elif rng.random() < 0.5:
        calif = Calificacion.TIBIO
        horario = t("Tomorrow 10:00-12:00", "Mañana 10:00-12:00")
    else:
        calif = Calificacion.FRIELO
        horario = None

    # El cierre depende de la calificación (la tasa real la fija el programa).
    cierra = calif in (Calificacion.CALIDO, Calificacion.TIBIO) and rng.random() < 0.6
    kit = rng.choices(_KITS, weights=[0.45, 0.38, 0.17], k=1)[0]

    if cierra:
        return {
            "reply_text": t(
                f"Great! I'll note down {t(*_KIT_LABEL[kit])}. "
                "I'll message you on WhatsApp once the technician is confirmed.",
                f"¡Genial! Anoto {t(*_KIT_LABEL[kit])}. "
                "Te aviso por WhatsApp cuando el técnico quede confirmado."),
            "calificacion": calif.value,
            "direccion_valida_caba": True,
            "barrio": barrio,
            "propone_horario": horario,
            "cierra_cita": True,
            "producto": kit,
            "motivo_no_compra": "",
            "requiere_visita_humana": False,
            "motivo": t("Sale closed on the call.", "Venta cerrada en la llamada."),
        }

    # Lead cálido/tibio pero NO se cerró en la llamada: el calor del lead
    # sigue siendo CALIDO/TIBIO (no NO_COMPRA, que es otra cosa).
    return {
        "reply_text": t(
            f"Leave me your number and I'll send you the info. {f'Does {horario} work for you?' if horario else ''}".strip(),
            f"Dejame tu número y te paso la info. {f'¿Te sirve {horario}?' if horario else ''}".strip()),
        "calificacion": calif.value,
        "direccion_valida_caba": True,
        "barrio": barrio,
        "propone_horario": horario,
        "cierra_cita": False,
        "producto": None,
        "motivo_no_compra": "",
        "requiere_visita_humana": True,
        "motivo": t("Lead interested but didn't close on the call.",
                    "Lead interesado pero no cerró en la llamada."),
    }


def operador_mock(exc: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """El teleoperador propone al coordinador de agenda a dónde mandar una venta cerrada."""
    cliente = exc.get("cliente") or t("the client", "el cliente")
    barrio = exc.get("barrio") or "CABA"
    producto = exc.get("producto") or t("an alarm", "una alarma")
    pref = exc.get("preferencia") or {}
    dia = max(0, min(5, int(pref.get("dia", 0) or 0)))
    turno = pref.get("turno") or "9am"
    cuando = {
        "9am": t("in the morning", "por la mañana"),
        "12pm": t("at noon", "al mediodía"),
        "4pm": t("in the afternoon", "por la tarde"),
    }
    return {
        "habla": t(
            f"I closed the sale for {cliente} ({barrio}) for {producto}. "
            f"The client prefers {_dia(dia)} {cuando.get(turno, 'in the morning')}. "
            "Can you give me a free slot?",
            f"Cerré la venta de {cliente} ({barrio}) por {producto}. "
            f"El cliente prefiere el {_dia(dia)} {cuando.get(turno, 'por la mañana')}. "
            "¿Me das un turno libre?"),
        "dia_preferido": dia,
        "turno_preferido": turno,
    }


def agenda_mock(messages: list[dict[str, str]], rng: random.Random) -> dict[str, Any]:
    """Coordinador de agenda: elige un turno de la pizarra de libres.

    Con contexto del enjambre (JSON con `turnos_libres`) respeta la preferencia
    del cliente y, si no está, elige de la lista (nunca inventa un turno). Sin
    contexto, cae al modo viejo: arma el turno leyendo el texto de la charla.
    """
    ctx = _contexto(messages)
    libres = ctx.get("turnos_libres")
    if libres:
        dia_pref = int(ctx.get("dia_preferido", 0) or 0)
        turno_pref = ctx.get("turno_preferido") or ""
        elegido = next((s for s in libres if s.get("dia") == dia_pref
                        and s.get("turno") == turno_pref), None)
        if elegido is None:
            elegido = next((s for s in libres if s.get("dia") == dia_pref), None)
        if elegido is None:
            elegido = libres[0]
        dia = int(elegido.get("dia", 0))
        turno = str(elegido.get("turno", "9am"))
        cliente = ctx.get("cliente") or t("the client", "el cliente")
        return {
            "turno_propuesto": turno,
            "dia": dia,
            "cierra_acuerdo": True,
            "texto_para_cliente": t(
                f"Hi! I confirm the installation of your alarm on {_dia(dia)} "
                f"at {_HORAS.get(turno, '09:00')}. The technician will show up at the "
                "agreed time. Thanks for trusting Nexus Alarm!",
                f"¡Hola! Confirmo la instalación de tu alarma el {_dia(dia)} "
                f"a las {_HORAS.get(turno, '09:00')}. El técnico se presenta en el "
                "horario acordado. ¡Gracias por confiar en Nexus Alarm!"),
            "nota_interna": t(
                f"Slot closed for {cliente}: {_dia(dia)} {turno}. "
                "I'm passing the assignment to the technician coordinator.",
                f"Turno cerrado para {cliente}: {_dia(dia)} {turno}. "
                "Le paso la asignación al coordinador de técnicos."),
        }

    # Old mode: with no board, build the slot by reading the chat text.
    ultimo = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    dia = 0
    turno = "9am"
    for k, v in (("monday", 0), ("lunes", 0), ("tuesday", 1), ("martes", 1),
                 ("wednesday", 2), ("miércoles", 2), ("miercoles", 2),
                 ("thursday", 3), ("jueves", 3), ("friday", 4), ("viernes", 4),
                 ("saturday", 5), ("sábado", 5), ("sabado", 5)):
        if k in ultimo.lower():
            dia = v
    for k, v in (("4pm", "4pm"), ("afternoon", "4pm"), ("tarde", "4pm"),
                 ("noon", "12pm"), ("mediodía", "12pm"), ("mediodia", "12pm"),
                 ("12pm", "12pm"), ("morning", "9am"), ("mañana", "9am"),
                 ("manana", "9am"), ("9am", "9am")):
        if k in ultimo.lower():
            turno = v
            break
    return {
        "turno_propuesto": turno,
        "dia": dia,
        "cierra_acuerdo": True,
        "texto_para_cliente": t(
            f"Hi! I confirm the installation of your alarm on {_dia(dia)} at "
            f"{_HORAS.get(turno, '09:00')}. The technician will show up at the agreed "
            "time. Thanks for trusting Nexus Alarm!",
            f"¡Hola! Confirmo la instalación de tu alarma el {_dia(dia)} "
            f"a las {_HORAS.get(turno, '09:00')}. El técnico se presenta en el horario "
            "acordado. ¡Gracias por confiar en Nexus Alarm!"),
        "nota_interna": t(
            f"Slot booked for the client: {turno} on day {dia}.",
            f"Turno agendado para el cliente: {turno} el día {dia}."),
    }


def tecnicos_mock(exc: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Coordinador de técnicos: elige a quién mandar entre los candidatos."""
    candidatos = exc.get("candidatos") or []
    barrio = exc.get("barrio") or t("la zona", "la zona")
    elegido = candidatos[0] if candidatos else {"id": "TEC-01", "zona": barrio}
    tid = str(elegido.get("id") or "TEC-01")
    nombre = str(elegido.get("nombre") or tid)
    zona = elegido.get("zona") or barrio
    return {
        "habla": t(
            f"For {barrio} I'm sending {nombre}: they're already working in {zona}, "
            "so they don't cross the city end to end. I'll leave the visit on the day's list.",
            f"Para {barrio} mando a {nombre}: ya está trabajando en {zona}, "
            "así no cruza la ciudad de punta a punta. Dejo la visita en la lista del día."),
        "tecnico_id": tid,
        "explicacion": t(
            f"{nombre} covers {zona} and deviates the least from their route.",
            f"{nombre} cubre {zona} y es el que menos se desvía de su recorrido."),
    }


def gerente_mock(messages: list[dict[str, str]], rng: random.Random) -> dict[str, Any]:
    """Simula la decisión del Gerente IA en su reunión mensual.

    El programa le pasa una DIRECTIVA explícita y los números del mes (el
    programa calcula lo que falta); la IA decide CÓMO llenarlo y por qué, leyendo
    esos números para proponer cantidades coherentes.
    """
    import math
    import re

    ultimo = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    directiva = "decide_libre"
    for linea in ultimo.splitlines():
        if linea.upper().startswith("DIRECTIVE="):
            directiva = linea.split("=", 1)[1].strip()
            break

    def num(patron: str, default: int) -> int:
        m = re.search(patron, ultimo)
        return int(float(m.group(1))) if m else default

    tecnicos = num(r"Active technicians:\s*(\d+)", 2)
    tope = num(r"hiring cap:\s*(\d+)", 10)
    potencia = num(r"Sales/day today:\s*(\d+)", 6)
    objetivo_ventas = num(r"this month's target:\s*(\d+)", 6)
    operadores = num(r"Operators:\s*(\d+)", 3)
    mejoras = num(r"Database/service improvements:\s*(\d+)", 0)

    if directiva == "escribe_acta":
        return {
            "decisiones": [],
            "titulo": t("Management minutes — month in progress",
                        "Acta de gerencia — mes en curso"),
            "resumen": t(
                "I reviewed sales, schedule and cash. I moved what was needed to "
                "keep growing without breaking the operation.",
                "Revisé ventas, agenda y caja. Moví lo necesario para seguir "
                "creciendo sin romper la operación."),
            "presion": t("no news", "sin novedades"),
        }

    if directiva == "mantener":
        return {
            "decisiones": [],
            "titulo": t("Management minutes — month with no changes",
                        "Acta de gerencia — mes sin cambios"),
            "resumen": t(
                "The numbers look good this month: nothing needs forcing. "
                "I keep watching the schedule and the cash.",
                "Los números están bien este mes: no hay que forzar nada. "
                "Sigo mirando la agenda y la caja."),
            "presion": t("no news", "sin novedades"),
        }

    if directiva == "falta_tecnicos":
        cantidad = max(1, min(tope - tecnicos, 5))
        decisiones = [{
            "palanca": "contratar_tecnicos",
            "cantidad": cantidad,
            "razon": t(
                "Sales are holding up and installs are piling up: "
                "if I don't add hands now, the client waits two weeks.",
                "Las ventas se sostienen y las instalaciones se acumulan: "
                "si no sumo manos ahora, el cliente espera dos semanas."),
        }]
        titulo = t("Management minutes — adding hands to installs",
                   "Acta de gerencia — sumando manos para instalar")
        presion = t(f"Not enough technicians to cover the schedule (cap: {tope}).",
                    f"Faltan técnicos para cubrir la agenda (tope: {tope}).")

    elif directiva == "falta_ventas":
        # How many calls are missing to reach the target, and how much that improves.
        tasa = (0.14 + 0.02 * mejoras) * (0.30 + 0.03 * mejoras)
        faltan = max(0, objetivo_ventas - potencia)
        llamadas_nuevas = math.ceil(faltan / tasa) if tasa > 0 else 50
        ops = max(1, min(math.ceil(llamadas_nuevas / 50), 3))
        decisiones = [
            {"palanca": "contratar_operadores", "cantidad": ops,
             "razon": t(
                 "I need more calls to reach the month's volume without "
                 "slowing down the install schedule.",
                 "Necesito más llamadas para llegar al volumen del mes sin "
                 "frenar la agenda de instalaciones.")},
            {"palanca": "mejorar_conversion", "cantidad": 1,
             "razon": t(
                 "I improve the database and the team's service: the same person "
                 "sells more, so I don't grow only by hiring people.",
                 "Mejoro la base y el servicio del equipo: la misma persona vende "
                 "más, así no crezco sólo contratando gente.")},
        ]
        titulo = t("Management minutes — more calls and better conversion",
                   "Acta de gerencia — más llamadas y mejor conversión")
        presion = t("Sales are short of the month's target.",
                    "Las ventas están por debajo de la meta del mes.")

    else:
        decisiones = []
        titulo = t("Management minutes — month in progress",
                   "Acta de gerencia — mes en curso")
        presion = t("no news", "sin novedades")

    return {
        "decisiones": decisiones,
        "titulo": titulo,
        "resumen": t(
            "I looked at the month's dashboard and made the decision that best fits "
            "the owner's goal.",
            "Miré el tablero del mes e hice la decisión que mejor le sirve a la meta "
            "del dueño."),
        "presion": presion,
    }


def despacho_mock(exc: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Simula la respuesta del agente de despacho ante una excepción."""
    tipo = exc.get("tipo", "normal")
    visita = exc.get("visita_id", "?")
    tecnico = exc.get("tecnico_asignado", "?")
    motivos = {
        "trafico": ("reasignar", t("Heavy traffic in the area; I reassign to a closer technician.",
                                   "Tráfico pesado en la zona; reasigno a un técnico más cercano.")),
        "lluvia": ("reprogramar", t("Heavy rain; I reschedule for the next clear window.",
                                    "Lluvia fuerte; reprogramo para la próxima ventana despejada.")),
        "cancelacion": ("reasignar", t("The client cancelled; I cover it with another technician in the area.",
                                       "El cliente canceló; lo cubro con otro técnico de la zona.")),
        "urgencia": ("escalar_urgencia", t("Urgent case: I escalate it and send the on-call technician.",
                                           "Caso urgente: lo escalo y mando al técnico de guardia.")),
        "garantia": ("mantener", t("It is a warranty from the same installer; they keep it.",
                                   "Es una garantía del mismo instalador; la mantiene.")),
        "normal": ("mantener", t("No exceptions; the plan holds.",
                                 "Sin excepciones; el plan se sostiene.")),
    }
    accion, explicacion = motivos.get(tipo, motivos["normal"])
    return {
        "accion": accion,
        "tecnico_sugerido": f"TEC-{rng.randint(1, 10):02d}" if accion == "reasignar" else None,
        "nueva_ventana": "16:00-18:00" if accion == "reprogramar" else None,
        "explicacion": t(f"Visit {visita} (technician {tecnico}): {explicacion}",
                         f"Visita {visita} (técnico {tecnico}): {explicacion}"),
        "urgencia": 5 if tipo == "urgencia" else (3 if accion == "reasignar" else 1),
    }


def informe_sector_mock(messages: list[dict[str, str]],
                        rng: random.Random) -> dict[str, Any]:
    """Informe de sector en modo prueba.

    El motor manda los NÚMEROS del mes como JSON en el último mensaje; acá los
    pasamos por el redactor LOCAL para devolver un informe coherente, sin red ni
    créditos. Es el mismo texto que usaría el respaldo real.
    """
    ctx = _contexto(messages)
    sector = str(ctx.get("sector") or "gerente")
    mes = int(ctx.get("mes") or 1)
    metricas = ctx.get("metricas") or {}

    # Import perezoso: evita un ciclo de importación con el motor.
    from engine.redactor import redactar

    base = redactar(sector, mes, metricas)
    return {
        "titulo": base["titulo"],
        "resumen": base["resumen"],
        "hallazgos": base["hallazgos"],
        "recomendacion": base["recomendacion"],
        "semaforo": base["semaforo"],
    }
