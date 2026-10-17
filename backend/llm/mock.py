"""Respuestas mock locales para el modo USE_MOCK=true.

Permiten correr TODO el flujo sin gastar créditos de GPU ni tocar la red. Las
respuestas son realistas y en español, y respetan las reglas de negocio simuladas
(www/lead entrante, dirección en CABA, tarifa del kit, etc.).

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

# Barrios reales de CABA para validar/infierir direcciones.
BARRIOS_CABA = [
    "Palermo", "Belgrano", "Caballito", "Flores", "Villa Urquiza",
    "Recoleta", "San Nicolás", "Almagro", "Boedo", "Villa Devoto",
    "Núñez", "Saavedra", "Coghlan", "Barracas", "Liniers",
]

# Palabras que indican urgencia en el mensaje del cliente.
_URGENCIA = ["urgente", "robo", "se metieron", "hoy", "ya", "ahora",
             "esta noche", "asaltaron", "corrí"]

# Motivos por los que atienden y no compran (lista fija, decisión del autor).
MOTIVOS_NO_COMPRA = [
    ("Muy caro para mí", 0.30),
    ("Ya tiene otra empresa de seguridad", 0.22),
    ("No le interesa tener alarma", 0.25),
    ("No es el momento / lo piensa", 0.15),
    ("Quiere consultar con la familia", 0.08),
]

_KITS = ["hogar_basico", "hogar_plus", "comercial"]
_KIT_LABEL = {
    "hogar_basico": "el kit Hogar Básico (USD 180)",
    "hogar_plus": "el kit Hogar Plus (USD 320)",
    "comercial": "el kit Comercial (USD 550)",
}


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
    """Motivo del 'no', según una lista fija con probabilidades."""
    nombres = [m for m, _ in MOTIVOS_NO_COMPRA]
    pesos = [p for _, p in MOTIVOS_NO_COMPRA]
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
            "reply_text": "Disculpás, no instalamos fuera de CABA. ¿Tenés dirección en la ciudad?",
            "calificacion": Calificacion.FRIELO.value,
            "direccion_valida_caba": False,
            "barrio": None,
            "propone_horario": None,
            "cierra_cita": False,
            "producto": None,
            "motivo_no_compra": "Fuera de nuestra zona de cobertura.",
            "requiere_visita_humana": False,
            "motivo": "Dirección fuera de la cobertura de CABA.",
        }

    if urgente:
        calif = Calificacion.CALIDO
        horario = "Hoy 14:00-16:00"
    elif rng.random() < 0.5:
        calif = Calificacion.TIBIO
        horario = "Mañana 10:00-12:00"
    else:
        calif = Calificacion.FRIELO
        horario = None

    # El cierre depende de la calificación (la tasa real la fija el programa).
    cierra = calif in (Calificacion.CALIDO, Calificacion.TIBIO) and rng.random() < 0.6
    kit = rng.choices(_KITS, weights=[0.45, 0.38, 0.17], k=1)[0]

    if cierra:
        return {
            "reply_text": (
                f"¡Genial! Te anoto {_KIT_LABEL[kit]}. "
                f"Te aviso por WhatsApp cuando tengamos el técnico confirmado."
            ),
            "calificacion": calif.value,
            "direccion_valida_caba": True,
            "barrio": barrio,
            "propone_horario": horario,
            "cierra_cita": True,
            "producto": kit,
            "motivo_no_compra": "",
            "requiere_visita_humana": False,
            "motivo": "Cierre de venta en la llamada.",
        }

    # Lead cálido/tibio pero NO se cerró en la llamada: el calor del lead
    # sigue siendo CALIDO/TIBIO (no NO_COMPRA, que es otra cosa).
    return {
        "reply_text": (
            f"Dejame tu número y te paso la info. {f'Te queda bien {horario}?' if horario else ''}"
        ).strip(),
        "calificacion": calif.value,
        "direccion_valida_caba": True,
        "barrio": barrio,
        "propone_horario": horario,
        "cierra_cita": False,
        "producto": None,
        "motivo_no_compra": "",
        "requiere_visita_humana": True,
        "motivo": "Lead interesado pero no cerró en la llamada.",
    }


_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
_HORAS = {"9am": "09:00", "12pm": "12:00", "4pm": "16:00"}


def operador_mock(exc: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """El teleoperador propone al coordinador de agenda a dónde mandar una venta cerrada."""
    cliente = exc.get("cliente") or "el cliente"
    barrio = exc.get("barrio") or "CABA"
    producto = exc.get("producto") or "una alarma"
    pref = exc.get("preferencia") or {}
    dia = max(0, min(5, int(pref.get("dia", 0) or 0)))
    turno = pref.get("turno") or "9am"
    cuando = {"9am": "a la mañana", "12pm": "al mediodía", "4pm": "a la tarde"}
    return {
        "habla": (f"Cerré la venta de {cliente} ({barrio}) por {producto}. "
                  f"El cliente prefiere el {_DIAS[dia]} "
                  f"{cuando.get(turno, 'a la mañana')}. ¿Me das un turno libre?"),
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
        cliente = ctx.get("cliente") or "el cliente"
        return {
            "turno_propuesto": turno,
            "dia": dia,
            "cierra_acuerdo": True,
            "texto_para_cliente": (
                f"¡Hola! Te confirmo la instalación de tu alarma el {_DIAS[dia]} "
                f"a las {_HORAS.get(turno, '09:00')}. El técnico se presenta en el "
                "horario acordado. ¡Gracias por confiar en Nexus Alarm!"
            ),
            "nota_interna": (f"Turno cerrado para {cliente}: {_DIAS[dia]} {turno}. "
                             "Le paso el reparto al coordinador de técnicos."),
        }

    # Modo viejo: sin pizarra, arma el turno leyendo el texto de la charla.
    ultimo = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    dia = 0
    turno = "9am"
    for k, v in (("lunes", 0), ("martes", 1), ("miércoles", 2), ("jueves", 3),
                 ("viernes", 4), ("sábado", 5)):
        if k in ultimo.lower():
            dia = v
    for k, v in (("4pm", "4pm"), ("tarde", "4pm"), ("mediodía", "12pm"),
                 ("12pm", "12pm"), ("mañana", "9am"), ("9am", "9am")):
        if k in ultimo.lower():
            turno = v
            break
    return {
        "turno_propuesto": turno,
        "dia": dia,
        "cierra_acuerdo": True,
        "texto_para_cliente": (
            f"¡Hola! Te confirmo la instalación de tu alarma el {_DIAS[dia]} a las "
            f"{_HORAS.get(turno, '09:00')}. El técnico se presenta en el horario "
            "acordado. ¡Gracias por confiar en Nexus Alarm!"
        ),
        "nota_interna": f"Turno reservado para la cliente: {turno} del día {dia}.",
    }


def tecnicos_mock(exc: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Coordinador de técnicos: elige a quién mandar entre los candidatos."""
    candidatos = exc.get("candidatos") or []
    barrio = exc.get("barrio") or "la zona"
    elegido = candidatos[0] if candidatos else {"id": "TEC-01", "zona": barrio}
    tid = str(elegido.get("id") or "TEC-01")
    nombre = str(elegido.get("nombre") or tid)
    zona = elegido.get("zona") or barrio
    return {
        "habla": (f"Para {barrio} mando a {nombre}: ya está trabajando en {zona}, así no "
                  "cruza la ciudad de punta a punta. Le dejo la visita en la lista del día."),
        "tecnico_id": tid,
        "explicacion": f"{nombre} cubre {zona} y es el que menos se desvía de su recorrido.",
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
        if linea.upper().startswith("DIRECTIVA="):
            directiva = linea.split("=", 1)[1].strip()
            break

    def num(patron: str, default: int) -> int:
        m = re.search(patron, ultimo)
        return int(float(m.group(1))) if m else default

    tecnicos = num(r"T[ée]cnicos activos:\s*(\d+)", 2)
    tope = num(r"tope de contrataci[oó]n:\s*(\d+)", 10)
    potencia = num(r"Ventas/d[ií]a hoy:\s*(\d+)", 6)
    objetivo_ventas = num(r"objetivo de este mes:\s*(\d+)", 6)
    operadores = num(r"Operadores:\s*(\d+)", 3)
    mejoras = num(r"Mejoras de base/servicio:\s*(\d+)", 0)

    if directiva == "escribe_acta":
        return {
            "decisiones": [],
            "titulo": "Acta de gerencia — mes en curso",
            "resumen": ("Revisé ventas, agenda y caja. Moví lo que hacía falta para "
                        "seguir creciendo sin romper la operación."),
            "presion": "sin novedad",
        }

    if directiva == "mantener":
        return {
            "decisiones": [],
            "titulo": "Acta de gerencia — mes sin cambios",
            "resumen": ("Los números dan bien este mes: no hay que forzar nada. "
                        "Sigo vigilando la agenda y la caja."),
            "presion": "sin novedad",
        }

    if directiva == "falta_tecnicos":
        cantidad = max(1, min(tope - tecnicos, 5))
        decisiones = [{
            "palanca": "contratar_tecnicos",
            "cantidad": cantidad,
            "razon": ("La venta viene sostenida y las instalaciones se nos corren: "
                      "si no sumo manos ahora, el cliente espera dos semanas."),
        }]
        titulo = "Acta de gerencia — sumamos manos a la instalación"
        presion = f"Faltan técnicos para cubrir la agenda (tope: {tope})."

    elif directiva == "falta_ventas":
        # Cuántas llamadas faltan para llegar al objetivo, y cuánto mejora eso.
        tasa = (0.14 + 0.02 * mejoras) * (0.30 + 0.03 * mejoras)
        faltan = max(0, objetivo_ventas - potencia)
        llamadas_nuevas = math.ceil(faltan / tasa) if tasa > 0 else 50
        ops = max(1, min(math.ceil(llamadas_nuevas / 50), 3))
        decisiones = [
            {"palanca": "contratar_operadores", "cantidad": ops,
             "razon": ("Necesito más llamadas para llegar al volumen del mes sin "
                       "frenar la agenda de instalaciones.")},
            {"palanca": "mejorar_conversion", "cantidad": 1,
             "razon": ("Mejoro la base de datos y el servicio del equipo: vende más "
                       "el mismo que llama, y así no crezco solo con gente.")},
        ]
        titulo = "Acta de gerencia — más llamadas y mejor conversión"
        presion = "La venta va corta para el objetivo del mes."

    else:
        decisiones = []
        titulo = "Acta de gerencia — mes en curso"
        presion = "sin novedad"

    return {
        "decisiones": decisiones,
        "titulo": titulo,
        "resumen": ("Miré el tablero del mes y tomé la decisión que mejor encaja "
                    "con la meta del dueño."),
        "presion": presion,
    }


def despacho_mock(exc: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """Simula la respuesta del agente de despacho ante una excepción."""
    tipo = exc.get("tipo", "normal")
    visita = exc.get("visita_id", "?")
    tecnico = exc.get("tecnico_asignado", "?")
    motivos = {
        "trafico": ("reasignar", "Tráfico pesado en la zona; reasigno a un técnico más cercano."),
        "lluvia": ("reprogramar", "Lluvia fuerte; reprogramo para el próximo claro."),
        "cancelacion": ("reasignar", "El cliente canceló; cubro con otro técnico de la zona."),
        "urgencia": ("escalar_urgencia", "Caso urgente: lo escalo y envío al técnico de guardia."),
        "garantia": ("mantener", "Es garantía del mismo instalador; lo mantiene él."),
        "normal": ("mantener", "Sin excepciones; se mantiene el plan."),
    }
    accion, explicacion = motivos.get(tipo, motivos["normal"])
    return {
        "accion": accion,
        "tecnico_sugerido": f"TEC-{rng.randint(1, 10):02d}" if accion == "reasignar" else None,
        "nueva_ventana": "16:00-18:00" if accion == "reprogramar" else None,
        "explicacion": f"Visita {visita} (técnico {tecnico}): {explicacion}",
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
