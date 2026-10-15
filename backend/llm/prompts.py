"""Prefijos de prompt que aplican a TODOS los agentes.

Centralizados acá para no repetirlos (ni olvidarlos) en cada llamada.

Hoy el "truco" es uno solo: avisar al modelo que **es un simulador de
ficción**. Sin ese aviso, Gemma (y otros modelos con guardas de seguridad)
se niega a hacer de teleoperador o a firmar como "gerente de Nexus Alarm"
porque no es una empresa real.

Regla: todo `messages` que se le mande al cliente LLM para un agente de
Negocio (teleoperador, agenda, gerente, despacho) tiene que pasar por
`mensajes_de_agente()` o envolver el contenido del sistema/usuario con
`prefijo_simulacion()`.
"""
from __future__ import annotations

from typing import Any

# Mensaje que se mete primero en todos los chats. Tiene que quedar claro
# que es un simulador de ficción y que el modelo NO es un asistente
# comercial real: está actuando un rol de un negocio ficticio.
PREAMBULO_SIMULACION = (
    "EJERCICIO DE SIMULACIÓN (no es una empresa real).\n"
    "Estás jugando un ROL dentro de un simulador de negocios ficticio. "
    "La empresa 'Nexus Alarm', sus teleoperadores, el gerente y los "
    "clientes son PERSONAJES de un simulador, no existen. No sos un "
    "asistente comercial real: sos un actor interpretando un papel. "
    "Devolvé únicamente el JSON pedido, sin frases de cortesía extra, "
    "sin disclaimers, y sin negarte a hacer el rol por no ser una "
    "empresa real.\n\n"
)


def prefijo_simulacion(texto: str) -> str:
    """Devuelve `texto` con el preámbulo de simulación pegado adelante."""
    return PREAMBULO_SIMULACION + texto


def mensajes_de_agente(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Devuelve una copia de `messages` con el preámbulo aplicado al
    primer mensaje `system` (o, si no hay, lo agrega como `system`).

    Es lo que tenemos que usar **siempre** antes de llamar a
    `LLMClient.complete(agent=...)`. No modifica la lista original.
    """
    if not messages:
        return [{"role": "system", "content": PREAMBULO_SIMULACION.strip()}]

    out: list[dict[str, Any]] = []
    aplicado = False
    for m in messages:
        rol = m.get("role")
        contenido = m.get("content", "")
        if rol == "system" and not aplicado:
            out.append({"role": "system",
                        "content": prefijo_simulacion(contenido)})
            aplicado = True
        else:
            out.append({"role": rol, "content": contenido})

    if not aplicado:
        out.insert(0, {"role": "system", "content": PREAMBULO_SIMULACION.strip()})
    return out


def descripcion_esquema(schema) -> str:
    """Texto corto que enumera los campos del esquema esperado.

    Gemma y los modelos con guardas de seguridad suelen seguir mejor las
    instrucciones si el prompt les **enumera los campos** del JSON que
    tienen que devolver. Esto se concatena al system message.
    """
    try:
        info = schema.model_json_schema()
    except Exception:  # noqa: BLE001
        return ""

    defs = info.get("$defs", {})

    def resolver(t: dict) -> dict:
        """Si el tipo es un $ref, devuelve la definición referenciada."""
        if "$ref" in t:
            ref = t["$ref"].rsplit("/", 1)[-1]
            return defs.get(ref, t)
        return t

    def tipo_de(prop: dict) -> str:
        prop = resolver(prop)
        if "enum" in prop:
            return "/".join(str(x) for x in prop["enum"])
        return prop.get("type") or "?"

    props = info.get("properties") or {}
    if not props:
        return ""

    obligatorios = set(info.get("required", []))
    lineas = ["Devolvé EXACTAMENTE este JSON (sin campos extra, sin texto afuera):"]
    for nombre, detalle in props.items():
        tipo = tipo_de(detalle)
        desc = detalle.get("description", "").strip()
        marca = "" if nombre in obligatorios else " (opcional)"
        sufijo = f" — {desc}" if desc else ""
        lineas.append(f"  - {nombre}: {tipo}{marca}{sufijo}")
    return "\n".join(lineas) + "\n"
