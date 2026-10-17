"""Redacción de documentos con Evolus (AI Tools).

Idea (en criollo): el agente de cada sector JUNTA y ANALIZA los números (eso lo
hace AMD), y después Evolus **redacta** el texto final del informe como
documento. Es la parte de "Evolus escribe" del plan.

Reglas del proyecto (iguales al resto del módulo):
- Máx. 2 reintentos y timeout (los maneja el cliente).
- Si Evolus falla o está apagado → se devuelve el texto local tal cual y **queda
  anotado**. La demo nunca se queda sin documento.
- En modo prueba NUNCA se toca la red.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .client import EvolusClient, EvolusError
from .mock import SELLO_SIMULADO

_log = logging.getLogger("nexus.evolus")


def redactar_informe(texto: str, *, sector: str = "", instrucciones: str = "",
                     client: EvolusClient | None = None) -> dict[str, Any]:
    """Pule `texto` como documento con Evolus. Nunca rompe.

    Devuelve `{texto, redactor, mock, fallback, nota}`:
      - `redactor`: "evolus" si lo escribió Evolus, "local" si no.
    """
    cliente = client or EvolusClient()
    cliente.validar()  # config a medias => error claro (no mandamos pedidos rotos)
    t0 = time.perf_counter()

    if cliente.config.mock:
        cliente._record("redactar", ok=True, mock=True, fallback=False, t0=t0,
                        nota=cliente.config.motivo_mock)
        return {"texto": texto, "redactor": "local", "mock": True,
                "fallback": False, "nota": cliente.config.motivo_mock}

    try:
        url = f"{cliente.config.api_base}/ai-tools/{cliente.config.redactor_tool}/run"
        salida = cliente.post_json(url, {
            "text": texto,
            "secondaryText": instrucciones or (
                f"Redactá como informe ejecutivo del sector {sector} de Nexus Alarm "
                "(empresa ficticia). Español rioplatense, claro y corto."),
            "options": {},
        })
        nuevo = _texto_de(salida)
        if not nuevo:
            raise EvolusError("Evolus devolvió un documento vacío.")
        cliente._record("redactar", ok=True, mock=False, fallback=False, t0=t0)
        return {"texto": nuevo, "redactor": "evolus", "mock": False,
                "fallback": False, "nota": ""}
    except Exception as e:  # noqa: BLE001 — Evolus no rompe la demo
        _log.warning("Evolus no redactó (%s) -> redactor local", e)
        cliente._record("redactar", ok=False, mock=True, fallback=True, t0=t0,
                        nota=str(e))
        return {"texto": texto, "redactor": "local", "mock": True, "fallback": True,
                "nota": f"Evolus no respondió ({e}); redacté localmente."}


def _texto_de(salida: Any) -> str:
    """Saca el texto de la respuesta de Evolus (que puede venir anidada)."""
    if isinstance(salida, str):
        return salida.strip()
    if isinstance(salida, dict):
        for clave in ("output", "text", "result", "documento", "summary"):
            valor = salida.get(clave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
            if isinstance(valor, dict) and valor.get("text"):
                return str(valor["text"]).strip()
    return ""


__all__ = ["redactar_informe", "SELLO_SIMULADO"]
