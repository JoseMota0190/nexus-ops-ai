"""Comprobantes SIMULADOS y su AUDITORÍA (100% local y determinista).

Genera facturas que *parecen* reales pero les inyecta defectos al azar (Monte
Carlo) y después las AUDITA con reglas: total mal sumado, CUIT inválido, fecha
imposible, IVA mal calculado, ítem descuadrado, importe negativo y campo
faltante. Es "la planilla de Excel que evita errores": un ALGORITMO, no un LLM.

REGLA FIRME: todo comprobante lleva el sello "SIMULADO – SIN VALIDEZ FISCAL".
Esto NO es un ERP ni una factura de verdad.

Determinismo: con la misma `seed` salen SIEMPRE las mismas facturas.

Tipos de error y probabilidad (cada uno se tira por separado, son independientes):

    tipo             prob.   qué rompe
    ---------------------------------------------------------------
    total_mal_sumado  0.20   el TOTAL no coincide con neto + IVA
    cuit_invalido     0.15   el dígito verificador del CUIT está mal
    fecha_invalida    0.12   la fecha no existe (31/02, mes 13, día 00...)
    iva_mal_calculado 0.12   el IVA no es el 21% del neto
    item_descuadrado  0.10   el subtotal no es cantidad × precio unitario
    importe_negativo  0.08   un ítem tiene importe negativo (ruido)
    campo_faltante    0.12   falta un dato obligatorio (razón social, CUIT...)

En promedio ≈ 0.89 errores por factura (la suma de las probabilidades).
"""
from __future__ import annotations

import datetime as _dt
import re
from copy import deepcopy
from typing import Any

import random

from idioma import es_espanol, t

# Sello obligatorio en TODO comprobante simulado (jamás afirmar facturación real).
SELLO_SIMULADO = "SIMULATED – NO FISCAL VALIDITY"
SELLO_SIMULADO_ES = "SIMULADO – SIN VALIDEZ FISCAL"


def sello() -> str:
    """El sello del comprobante, en el idioma activo."""
    return SELLO_SIMULADO_ES if es_espanol() else SELLO_SIMULADO

# Probabilidad de cada defecto (documentada arriba; si cambiás una, actualizá esto).
PROBABILIDADES: dict[str, float] = {
    "total_mal_sumado": 0.20,
    "cuit_invalido": 0.15,
    "fecha_invalida": 0.12,
    "iva_mal_calculado": 0.12,
    "item_descuadrado": 0.10,
    "importe_negativo": 0.08,
    "campo_faltante": 0.12,
}

ALICUOTA_IVA = 0.21
MONEDA = "ARS"

# Emisor ficticio (el sello aclara que no vale fiscalmente).
EMISOR = {"razon_social": "Nexus Alarm S.A.", "cuit": "30-71234567-1"}

# Clientes ficticios de CABA (razón social [+ idioma] + prefijo de CUIT).
CLIENTES = [
    {"razon_social": ("Av. Corrientes 1234 Building Assoc.", "Consorcio Av. Corrientes 1234"), "prefijo": 30},
    {"razon_social": ("Corner Bar S.R.L.", "Bar de la Esquina S.R.L."), "prefijo": 30},
    {"razon_social": ("Marta Gómez", "Marta Gómez"), "prefijo": 27},
    {"razon_social": ("Ríos Accounting Firm", "Estudio Contable Ríos"), "prefijo": 30},
    {"razon_social": ("Javier Pereyra", "Javier Pereyra"), "prefijo": 20},
    {"razon_social": ("El Trigal Bakery", "Panadería El Trigal"), "prefijo": 33},
    {"razon_social": ("Lucía Fernández", "Lucía Fernández"), "prefijo": 27},
    {"razon_social": ("Belgrano Parking S.A.", "Estacionamiento Belgrano S.A."), "prefijo": 30},
]

# Productos del negocio (kit de alarma + monitoreo + accesorios).
PRODUCTOS = [
    {"descripcion": ("Home Basic Kit", "Kit Hogar Básico"), "precio": 180.0},
    {"descripcion": ("Home Plus Kit", "Kit Hogar Plus"), "precio": 320.0},
    {"descripcion": ("Commercial Kit", "Kit Comercial"), "precio": 550.0},
    {"descripcion": ("Flood sensor", "Sensor de inundación"), "precio": 40.0},
    {"descripcion": ("Zone extender", "Extensor de zona"), "precio": 25.0},
    {"descripcion": ("Monthly monitoring (Plus)", "Monitoreo mensual (Plus)"), "precio": 25.0},
    {"descripcion": ("Annual maintenance", "Mantenimiento anual"), "precio": 60.0},
]

_PESOS_CUIT = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
_FECHAS_IMPOSIBLES = [
    "31/02/2026", "00/05/2026", "15/13/2026", "32/01/2026",
    "31/04/2026", "30/02/2026",
]


# --------------------------------------------------------------- CUIT (AFIP)
def cuit_valido(cuit: str) -> bool:
    """Valida un CUIT con el dígito verificador (algoritmo módulo 11)."""
    digitos = [int(c) for c in str(cuit) if c.isdigit()]
    if len(digitos) != 11:
        return False
    suma = sum(d * p for d, p in zip(digitos[:10], _PESOS_CUIT))
    verificador = 11 - (suma % 11)
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    return verificador == digitos[10]


def _cuit_base(prefijo: int, cuerpo: list[int]) -> str:
    digitos = [int(d) for d in str(prefijo).zfill(2)] + cuerpo
    suma = sum(d * p for d, p in zip(digitos, _PESOS_CUIT))
    verificador = 11 - (suma % 11)
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    s = "".join(str(d) for d in digitos + [verificador])
    return f"{s[:2]}-{s[2:10]}-{s[10]}"


def _cuit_valido_random(rng: random.Random, prefijo: int) -> str:
    return _cuit_base(prefijo, [rng.randint(0, 9) for _ in range(8)])


def _romper_cuit(rng: random.Random, cuit: str) -> str:
    """Cambia el dígito verificador: el CUIT queda inválido (hay uno solo válido)."""
    digitos = [int(c) for c in cuit if c.isdigit()]
    digitos[10] = (digitos[10] + rng.randint(1, 9)) % 10
    s = "".join(str(d) for d in digitos)
    return f"{s[:2]}-{s[2:10]}-{s[10]}"


# ------------------------------------------------------------- construcción
def _factura_correcta(rng: random.Random, indice: int) -> dict[str, Any]:
    """Arma un comprobante IMPECABLE (sin errores)."""
    tipo = rng.choices(["A", "B", "C"], weights=[0.50, 0.35, 0.15])[0]
    cliente = rng.choice(CLIENTES)
    items: list[dict[str, Any]] = []
    for _ in range(rng.randint(1, 3)):
        prod = rng.choice(PRODUCTOS)
        cantidad = rng.randint(1, 3)
        precio = prod["precio"]
        items.append({
            "descripcion": t(*prod["descripcion"]),
            "cantidad": cantidad,
            "precio_unitario": precio,
            "subtotal": round(cantidad * precio, 2),
        })
    neto = round(sum(i["subtotal"] for i in items), 2)
    iva = round(neto * ALICUOTA_IVA, 2)
    return {
        "numero": f"{tipo}-{rng.randint(1, 4):05d}-{indice:08d}",
        "tipo": tipo,
        "fecha": f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/2026",
        "razon_social": t(*cliente["razon_social"]),
        "cuit": _cuit_valido_random(rng, cliente["prefijo"]),
        "items": items,
        "neto": neto,
        "iva": iva,
        "total": round(neto + iva, 2),
        "moneda": MONEDA,
        "sello": sello(),
    }


def _inyectar_errores(rng: random.Random, doc: dict[str, Any],
                      correcto: dict[str, Any]) -> list[dict[str, Any]]:
    """Mete defectos al azar en `doc` y devuelve la lista de errores inyectados."""
    errores: list[dict[str, Any]] = []

    def registrar(tipo: str, campo: str, esperado: Any, actual: Any) -> None:
        errores.append({"tipo": tipo, "campo": campo,
                        "esperado": esperado, "en_documento": actual})

    # 1) Total mal sumado.
    if rng.random() < PROBABILIDADES["total_mal_sumado"]:
        delta = rng.choice([-1, 1]) * rng.randint(1, 900)
        doc["total"] = round(correcto["total"] + delta, 2)
        registrar("total_mal_sumado", "total", correcto["total"], doc["total"])

    # 2) CUIT inválido (dígito verificador alterado).
    if rng.random() < PROBABILIDADES["cuit_invalido"]:
        doc["cuit"] = _romper_cuit(rng, correcto["cuit"])
        registrar("cuit_invalido", "cuit", correcto["cuit"], doc["cuit"])

    # 3) Fecha imposible.
    if rng.random() < PROBABILIDADES["fecha_invalida"]:
        doc["fecha"] = rng.choice(_FECHAS_IMPOSIBLES)
        registrar("fecha_invalida", "fecha", correcto["fecha"], doc["fecha"])

    # 4) IVA mal calculado.
    if rng.random() < PROBABILIDADES["iva_mal_calculado"]:
        doc["iva"] = round(correcto["neto"] * rng.choice([0.0, 0.105, 0.19]), 2)
        registrar("iva_mal_calculado", "iva", correcto["iva"], doc["iva"])

    # 5) Ítem desdoblado: el subtotal no es cantidad × precio unitario.
    if rng.random() < PROBABILIDADES["item_descuadrado"]:
        i = rng.randrange(len(doc["items"]))
        doc["items"][i]["precio_unitario"] = round(
            correcto["items"][i]["precio_unitario"] + rng.choice([-1, 1]) * rng.randint(1, 50), 2)
        registrar("item_descuadrado", f"items[{i}].precio_unitario",
                  correcto["items"][i]["precio_unitario"],
                  doc["items"][i]["precio_unitario"])

    # 6) Importe negativo (ruido).
    if rng.random() < PROBABILIDADES["importe_negativo"]:
        j = rng.randrange(len(doc["items"]))
        doc["items"][j]["subtotal"] = -abs(correcto["items"][j]["subtotal"])
        registrar("importe_negativo", f"items[{j}].subtotal",
                  correcto["items"][j]["subtotal"], doc["items"][j]["subtotal"])

    # 7) Campo faltante (va ÚLTIMO, para no pisar los valores ya registrados).
    if rng.random() < PROBABILIDADES["campo_faltante"]:
        campo = rng.choice(["razon_social", "cuit", "fecha", "numero"])
        doc[campo] = None
        registrar("campo_faltante", campo, correcto[campo], None)

    return errores


def generar_factura(rng: random.Random, indice: int = 1) -> dict[str, Any]:
    """Devuelve una factura simulada con sus errores inyectados.

    Campos:
    - `documento`: lo que "lee" el auditor (puede traer defectos).
    - `correcto`:  la versión impecable (referencia para medir precisión).
    - `errores`:   lista de defectos inyectados (con esperado vs. en_documento).
    """
    correcto = _factura_correcta(rng, indice)
    documento = deepcopy(correcto)
    errores = _inyectar_errores(rng, documento, correcto)
    return {
        "id": f"F-{indice:04d}",
        "documento": documento,
        "correcto": correcto,
        "errores": errores,
        "sello": sello(),
    }


def generar_facturas(n: int, seed: int = 42) -> list[dict[str, Any]]:
    """Genera `n` facturas simuladas. Misma `seed` → mismas facturas."""
    rng = random.Random(seed)
    return [generar_factura(rng, i + 1) for i in range(max(0, n))]


def a_texto(doc: dict[str, Any]) -> str:
    """Convierte el documento a texto plano (como se vería la factura)."""
    def val(x: Any) -> str:
        return "—" if x is None else str(x)

    lineas = [
        EMISOR["razon_social"],
        t(f"Invoice {val(doc.get('tipo'))} No. {val(doc.get('numero'))}",
          f"Factura {val(doc.get('tipo'))} N° {val(doc.get('numero'))}"),
        t(f"Date: {val(doc.get('fecha'))}", f"Fecha: {val(doc.get('fecha'))}"),
        t(f"Customer: {val(doc.get('razon_social'))}",
          f"Cliente: {val(doc.get('razon_social'))}"),
        f"CUIT: {val(doc.get('cuit'))}",
        "-" * 44,
    ]
    for it in doc.get("items", []):
        lineas.append(
            f"{val(it.get('descripcion'))} x{val(it.get('cantidad'))} "
            f"@{val(it.get('precio_unitario'))} = {val(it.get('subtotal'))}"
        )
    lineas += [
        "-" * 44,
        t(f"Net: {val(doc.get('neto'))}", f"Neto: {val(doc.get('neto'))}"),
        t(f"VAT 21%: {val(doc.get('iva'))}", f"IVA 21%: {val(doc.get('iva'))}"),
        f"TOTAL: {val(doc.get('total'))} {val(doc.get('moneda'))}",
        "",
        val(doc.get("sello")),
    ]
    return "\n".join(lineas)


def contar_errores(facturas: list[dict[str, Any]]) -> dict[str, int]:
    """Cuenta cuántas veces apareció cada tipo de error."""
    conteo: dict[str, int] = {t: 0 for t in PROBABILIDADES}
    for f in facturas:
        for e in f.get("errores", []):
            conteo[e["tipo"]] = conteo.get(e["tipo"], 0) + 1
    return conteo


# ------------------------------------------------------------- lector local
_ITEM_RE = re.compile(
    r"^(?P<desc>.+?)\s+x(?P<cant>-?\d+)\s+@(?P<precio>-?[\d.]+)\s+=\s+(?P<sub>-?[\d.]+)$"
)
_COMP_RE = re.compile(
    r"^(?:Invoice|Factura)\s+(?P<tipo>[A-C])\s+(?:No\.?|N[°º]?)\s*(?P<numero>.*)$")


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

    Es el "lector de respaldo": funciona sin internet y sin depender de ningún
    servicio externo.
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
        if l.startswith("Invoice ") or l.startswith("Factura "):
            m = _COMP_RE.match(l)
            if m:
                datos["tipo"] = m.group("tipo")
                datos["numero"] = _limpiar(m.group("numero"))
        elif l.startswith("Date:") or l.startswith("Fecha:"):
            datos["fecha"] = _limpiar(l.split(":", 1)[1])
        elif l.startswith("Customer:") or l.startswith("Cliente:"):
            datos["razon_social"] = _limpiar(l.split(":", 1)[1])
        elif l.startswith("CUIT:"):
            datos["cuit"] = _limpiar(l.split(":", 1)[1])
        elif l.startswith("Net:") or l.startswith("Neto:"):
            datos["neto"] = _a_float(l.split(":", 1)[1])
        elif l.startswith("VAT") or l.startswith("IVA"):
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


# ------------------------------------------------------------- comparación
CAMPOS = ["numero", "tipo", "fecha", "razon_social", "cuit", "neto", "iva", "total", "items"]

_TOLERANCIA = 1e-6
_FECHA_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


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
            add("campo_faltante", campo,
                t(f"Missing required field '{campo}'.",
                  f"Falta un dato obligatorio: '{campo}'."))

    cuit = doc.get("cuit")
    if cuit not in (None, "") and not cuit_valido(cuit):
        add("cuit_invalido", "cuit",
            t(f"CUIT {cuit} fails the check digit.",
              f"El CUIT {cuit} no pasa el dígito verificador."))

    fecha = doc.get("fecha")
    if fecha not in (None, "") and not _fecha_ok(fecha):
        add("fecha_invalida", "fecha",
            t(f"The date {fecha} does not exist.",
              f"La fecha {fecha} no existe."))

    neto, iva, total = doc.get("neto"), doc.get("iva"), doc.get("total")
    if all(isinstance(x, (int, float)) for x in (neto, iva, total)):
        if abs(round(neto + iva, 2) - total) > 0.01:
            add("total_mal_sumado", "total",
                t(f"The total ({total}) is not net + VAT ({round(neto + iva, 2)}).",
                  f"El total ({total}) no es neto + IVA ({round(neto + iva, 2)})."))
    if all(isinstance(x, (int, float)) for x in (neto, iva)):
        if abs(round(neto * ALICUOTA_IVA, 2) - iva) > 0.01:
            add("iva_mal_calculado", "iva",
                t(f"VAT ({iva}) is not 21% of net ({round(neto * ALICUOTA_IVA, 2)}).",
                  f"El IVA ({iva}) no es el 21% del neto ({round(neto * ALICUOTA_IVA, 2)})."))

    for i, it in enumerate(doc.get("items") or []):
        sub, cant, precio = it.get("subtotal"), it.get("cantidad"), it.get("precio_unitario")
        if all(isinstance(x, (int, float)) for x in (sub, cant, precio)):
            if abs(round(cant * precio, 2) - sub) > 0.01:
                add("item_descuadrado", f"items[{i}]",
                    t(f"Subtotal {sub} ≠ quantity × price ({round(cant * precio, 2)}).",
                      f"El subtotal {sub} ≠ cantidad × precio ({round(cant * precio, 2)})."))
        if isinstance(sub, (int, float)) and sub < 0:
            add("importe_negativo", f"items[{i}]",
                t(f"Negative amount: {sub}.", f"Importe negativo: {sub}."))
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
