"""Genera comprobantes SIMULADOS con errores inyectados (Monte Carlo).

Idea (en criollo): inventamos facturas que *parecen* reales, pero les metemos
defectos al azar a propósito —como llegan en la vida real: un total mal sumado,
un CUIT con un dígito cambiado, una fecha imposible, un campo en blanco—. Después
el extractor intenta leerlas y medimos qué tan bien lo hace.

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

from copy import deepcopy
from typing import Any

import random

from .mock import SELLO_SIMULADO

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

# Clientes ficticios de CABA (razón social + prefijo de CUIT).
CLIENTES = [
    {"razon_social": "Consorcio Av. Corrientes 1234", "prefijo": 30},
    {"razon_social": "Bar La Esquina S.R.L.", "prefijo": 30},
    {"razon_social": "Marta Gómez", "prefijo": 27},
    {"razon_social": "Estudio Contable Ríos", "prefijo": 30},
    {"razon_social": "Javier Pereyra", "prefijo": 20},
    {"razon_social": "Panadería El Trigal", "prefijo": 33},
    {"razon_social": "Lucía Fernández", "prefijo": 27},
    {"razon_social": "Cocheras Belgrano S.A.", "prefijo": 30},
]

# Productos del negocio (kit de alarma + monitoreo + accesorios).
PRODUCTOS = [
    {"descripcion": "Kit Hogar Básico", "precio": 180.0},
    {"descripcion": "Kit Hogar Plus", "precio": 320.0},
    {"descripcion": "Kit Comercial", "precio": 550.0},
    {"descripcion": "Sensor de inundación", "precio": 40.0},
    {"descripcion": "Extensor de zona", "precio": 25.0},
    {"descripcion": "Monitoreo mensual (Plus)", "precio": 25.0},
    {"descripcion": "Mantenimiento anual", "precio": 60.0},
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
            "descripcion": prod["descripcion"],
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
        "razon_social": cliente["razon_social"],
        "cuit": _cuit_valido_random(rng, cliente["prefijo"]),
        "items": items,
        "neto": neto,
        "iva": iva,
        "total": round(neto + iva, 2),
        "moneda": MONEDA,
        "sello": SELLO_SIMULADO,
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
    - `documento`: lo que "lee" el extractor (puede traer defectos).
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
        "sello": SELLO_SIMULADO,
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
        f"Comprobante {val(doc.get('tipo'))} N° {val(doc.get('numero'))}",
        f"Fecha: {val(doc.get('fecha'))}",
        f"Cliente: {val(doc.get('razon_social'))}",
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
        f"Neto: {val(doc.get('neto'))}",
        f"IVA 21%: {val(doc.get('iva'))}",
        f"TOTAL: {val(doc.get('total'))} {val(doc.get('moneda'))}",
        "",
        val(doc.get("sello")),
    ]
    return "\n".join(lineas)


def contar_errores(facturas: list[dict[str, Any]]) -> dict[str, int]:
    """Cuenta cuántas veces apareció cada tipo de error (para /metricas)."""
    conteo: dict[str, int] = {t: 0 for t in PROBABILIDADES}
    for f in facturas:
        for e in f.get("errores", []):
            conteo[e["tipo"]] = conteo.get(e["tipo"], 0) + 1
    return conteo
