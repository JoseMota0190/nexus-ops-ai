"""Respuestas mock locales para el modo USE_MOCK=true.

Permiten correr TODO el flujo sin gastar créditos de GPU ni tocar la red. Las
respuestas son realistas y en español, y respetan las reglas de negocio simuladas
(Registro "No Llame", validación de dirección en CABA, etc.).

En lugar de pedirle al modelo que genere texto libre, acá devolvemos directamente
el JSON que el agente debería producir, para que el flujo sea 100% determinista.
"""
from __future__ import annotations

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
_URGENCIA = ["urgente", "robo", "se metieron", "hoy", "ya", "ahora", "esta noche", "asaltaron"]


def _barrio_de(direccion: str) -> str | None:
    d = direccion.lower()
    for b in BARRIOS_CABA:
        if b.lower() in d:
            return b
    return None


def _es_caba(direccion: str) -> bool:
    d = direccion.lower()
    fuera = ["tigre", "san isidro", "lanús", "avellaneda", "la plata", "morón", "ituzainó"]
    if any(f in d for f in fuera):
        return False
    return _barrio_de(d) is not None


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
            "en_registro_no_llamar": False,
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

    cierra = calif != Calificacion.FRIELO and rng.random() < 0.7
    return {
        "reply_text": (
            f"¡Perfecto! Tenemos disponibilidad en {barrio or 'CABA'}. "
            f"¿Te queda bien {horario}?" if horario else
            f"Gracias por escribirnos. Te paso info de nuestros kits y te contactamos."
        ),
        "calificacion": calif.value,
        "direccion_valida_caba": True,
        "barrio": barrio,
        "propone_horario": horario,
        "cierra_cita": cierra,
        "en_registro_no_llamar": False,
        "requiere_visita_humana": False,
        "motivo": "Urgencia detectada." if urgente else "Interés estándar.",
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
