"""Respuestas mock locales del módulo Evolus (MODO PRUEBA).

Permiten correr TODO el módulo sin red, sin clave y sin gastar créditos de
Evolus. Las respuestas son **deterministas**: la misma entrada devuelve
siempre la misma salida (semilla fija), para que la demo sea reproducible.

Esto se parece al "actor de respaldo" del módulo de IA: el programa responde
por su cuenta y no depende de internet para funcionar.
"""
from __future__ import annotations

import re
from typing import Any

from .config import EvolusConfig

# Sello obligatorio en TODO comprobante simulado (jamás afirmar facturación real).
SELLO_SIMULADO = "SIMULADO – SIN VALIDEZ FISCAL"

_ITEM_RE = re.compile(
    r"^(?P<desc>.+?)\s+x(?P<cant>-?\d+)\s+@(?P<precio>-?[\d.]+)\s+=\s+(?P<sub>-?[\d.]+)$"
)
_COMP_RE = re.compile(r"^Comprobante\s+(?P<tipo>[A-C])\s+N[°º]?\s*(?P<numero>.*)$")


def salud_mock(config: EvolusConfig) -> dict[str, Any]:
    """Estado del modo prueba, en criollo, para la puerta `/salud`."""
    return {
        "modo": "prueba" if config.mock else "real",
        "mensaje": (
            "Evolus en modo prueba: respondo con datos locales, sin tocar internet."
            if config.mock
            else "Evolus conectado: los pedidos salen a la red."
        ),
        "motivo": config.motivo_mock,
    }


def _limpiar(valor: Any) -> Any:
    """Convierte los huecos del documento ('—') en None real."""
    v = ("" if valor is None else str(valor)).strip()
    return None if v in {"", "—", "-"} else v


def _a_float(valor: Any) -> float | None:
    v = _limpiar(valor)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def extraer_mock(texto: str) -> dict[str, Any]:
    """Lector LOCAL determinista: convierte el texto de la factura en datos.

    Es el 'lector de respaldo': funciona sin internet y sirve de referencia
    cuando Evolus real no está disponible.
    """
    datos: dict[str, Any] = {
        "numero": None, "tipo": None, "fecha": None, "razon_social": None,
        "cuit": None, "items": [], "neto": None, "iva": None,
        "total": None, "moneda": None,
    }
    for linea in texto.splitlines():
        l = linea.strip()
        if not l:
            continue
        if l.startswith("Comprobante "):
            m = _COMP_RE.match(l)
            if m:
                datos["tipo"] = m.group("tipo")
                datos["numero"] = _limpiar(m.group("numero"))
        elif l.startswith("Fecha:"):
            datos["fecha"] = _limpiar(l.split(":", 1)[1])
        elif l.startswith("Cliente:"):
            datos["razon_social"] = _limpiar(l.split(":", 1)[1])
        elif l.startswith("CUIT:"):
            datos["cuit"] = _limpiar(l.split(":", 1)[1])
        elif l.startswith("Neto:"):
            datos["neto"] = _a_float(l.split(":", 1)[1])
        elif l.startswith("IVA"):
            datos["iva"] = _a_float(l.split(":", 1)[1])
        elif l.startswith("TOTAL:"):
            partes = l.split(":", 1)[1].split()
            datos["total"] = _a_float(partes[0]) if partes else None
            datos["moneda"] = partes[1] if len(partes) > 1 else None
        else:
            m = _ITEM_RE.match(l)
            if m:
                datos["items"].append({
                    "descripcion": m.group("desc"),
                    "cantidad": int(m.group("cant")),
                    "precio_unitario": float(m.group("precio")),
                    "subtotal": float(m.group("sub")),
                })
    return datos
