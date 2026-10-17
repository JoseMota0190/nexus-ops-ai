"""Extracción y medición: compara lo leído contra lo esperado.

Dos cosas distintas y complementarias:

1. **`comparar`** — fidelidad de LECTURA. Toma dos estructuras (`esperado` y
   `obtenido`) y dice, campo por campo, cuántos coinciden → `precision` (0 a 1).
2. **`detectar_errores`** — CALIDAD del documento. Revisa una factura y devuelve
   la lista de defectos que encuentra (total mal sumado, CUIT inválido, fecha
   imposible, IVA mal, ítem descuadrado, importe negativo, campo faltante).

`evaluar_factura` une las dos: lee la factura con el lector local, la compara
contra la versión impecable y detecta los defectos; además dice cuáles de los
defectos *esperados* quedaron sin detectar (`errores_fallados`).
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any

from .facturas import ALICUOTA_IVA, a_texto, cuit_valido, generar_facturas
from .mock import extraer_mock

# Campos escalares que se comparan uno por uno (+ la lista de ítems).
CAMPOS = ["numero", "tipo", "fecha", "razon_social", "cuit", "neto", "iva", "total", "items"]

_TOLERANCIA = 1e-6
_FECHA_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


# ------------------------------------------------------------- comparación
def _num_igual(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a == b
    try:
        return abs(float(a) - float(b)) <= _TOLERANCIA
    except (TypeError, ValueError):
        return a == b


def _igual(a: Any, b: Any) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_igual(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_igual(a[k], b[k]) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return _num_igual(a, b)
    return a == b


def comparar(esperado: dict[str, Any], obtenido: dict[str, Any]) -> dict[str, Any]:
    """Compara campo por campo y devuelve la precisión (0 a 1)."""
    por_campo = {campo: _igual(esperado.get(campo), obtenido.get(campo))
                 for campo in CAMPOS}
    aciertos = sum(1 for ok in por_campo.values() if ok)
    total = len(CAMPOS)
    return {
        "precision": round(aciertos / total, 4),
        "coincidencias": aciertos,
        "total_campos": total,
        "por_campo": por_campo,
    }


# --------------------------------------------------------------- detección
def _fecha_ok(fecha: Any) -> bool:
    m = _FECHA_RE.match(str(fecha))
    if not m:
        return False
    d, mo, y = (int(x) for x in m.groups())
    try:
        _dt.date(y, mo, d)
        return True
    except ValueError:
        return False


def detectar_errores(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Revisa un comprobante y devuelve la lista de defectos que encuentra."""
    errores: list[dict[str, Any]] = []

    def add(tipo: str, campo: str, detalle: str) -> None:
        errores.append({"tipo": tipo, "campo": campo, "detalle": detalle})

    for campo in ("razon_social", "cuit", "fecha", "numero"):
        if doc.get(campo) in (None, ""):
            add("campo_faltante", campo, f"Falta el dato obligatorio '{campo}'.")

    cuit = doc.get("cuit")
    if cuit not in (None, "") and not cuit_valido(cuit):
        add("cuit_invalido", "cuit", f"El CUIT {cuit} no pasa el dígito verificador.")

    fecha = doc.get("fecha")
    if fecha not in (None, "") and not _fecha_ok(fecha):
        add("fecha_invalida", "fecha", f"La fecha {fecha} no existe.")

    neto, iva, total = doc.get("neto"), doc.get("iva"), doc.get("total")
    if all(isinstance(x, (int, float)) for x in (neto, iva, total)):
        if abs(round(neto + iva, 2) - total) > 0.01:
            add("total_mal_sumado", "total",
                f"El total ({total}) no es neto + IVA ({round(neto + iva, 2)}).")
    if all(isinstance(x, (int, float)) for x in (neto, iva)):
        if abs(round(neto * ALICUOTA_IVA, 2) - iva) > 0.01:
            add("iva_mal_calculado", "iva",
                f"El IVA ({iva}) no es el 21% del neto ({round(neto * ALICUOTA_IVA, 2)}).")

    for i, it in enumerate(doc.get("items") or []):
        sub, cant, precio = it.get("subtotal"), it.get("cantidad"), it.get("precio_unitario")
        if all(isinstance(x, (int, float)) for x in (sub, cant, precio)):
            if abs(round(cant * precio, 2) - sub) > 0.01:
                add("item_descuadrado", f"items[{i}]",
                    f"Subtotal {sub} ≠ cantidad × precio ({round(cant * precio, 2)}).")
        if isinstance(sub, (int, float)) and sub < 0:
            add("importe_negativo", f"items[{i}]", f"Importe negativo: {sub}.")
    return errores


# --------------------------------------------------------- pipeline completo
def evaluar_factura(factura: dict[str, Any]) -> dict[str, Any]:
    """Lee una factura, mide su precisión y detecta sus defectos."""
    documento = factura["documento"]
    correcto = factura["correcto"]
    obtenido = extraer_mock(a_texto(documento))
    comp = comparar(correcto, obtenido)
    detectados = detectar_errores(documento)
    esperados = {e["tipo"] for e in factura.get("errores", [])}
    tipos_detectados = {d["tipo"] for d in detectados}
    return {
        "id": factura.get("id"),
        "esperado": correcto,
        "obtenido": obtenido,
        "precision": comp["precision"],
        "coincidencias": comp["coincidencias"],
        "total_campos": comp["total_campos"],
        "por_campo": comp["por_campo"],
        "errores_detectados": detectados,
        "errores_esperados": sorted(esperados),
        "errores_fallados": sorted(esperados - tipos_detectados),
    }


def evaluar_lote(n: int, seed: int = 42) -> dict[str, Any]:
    """Corre el pipeline sobre `n` facturas y agrega los resultados."""
    facturas = generar_facturas(n, seed)
    evaluaciones = [evaluar_factura(f) for f in facturas]
    total_defectos = sum(len(e["errores_esperados"]) for e in evaluaciones)
    detectados = sum(len(e["errores_esperados"]) - len(e["errores_fallados"])
                     for e in evaluaciones)
    precision_prom = (round(sum(e["precision"] for e in evaluaciones) / n, 4)
                      if n else 0.0)

    por_tipo: dict[str, dict[str, int]] = {}
    for ev in evaluaciones:
        tipos_detectados = set(ev["errores_esperados"]) - set(ev["errores_fallados"])
        for tipo in ev["errores_esperados"]:
            d = por_tipo.setdefault(tipo, {"esperados": 0, "detectados": 0})
            d["esperados"] += 1
            if tipo in tipos_detectados:
                d["detectados"] += 1

    return {
        "n": n,
        "seed": seed,
        "precision_promedio": precision_prom,
        "defectos_totales": total_defectos,
        "defectos_detectados": detectados,
        "defectos_fallados": total_defectos - detectados,
        "tasa_deteccion": (round(detectados / total_defectos, 4)
                           if total_defectos else 1.0),
        "defectos_por_tipo": por_tipo,
    }
