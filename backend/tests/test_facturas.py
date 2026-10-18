"""Tests del AUDITOR de facturas simuladas (`engine/facturas.py`).

100% local, deterministas y sin red: generan comprobantes "con errores" (Monte
Carlo) y comprueban que el lector + la auditoría los detecten por reglas.

Regla firme: TODO comprobante lleva el sello "SIMULATED – NO FISCAL VALIDITY".
"""
import copy
import random
import sys
from pathlib import Path

# Asegura que `backend/` esté en el path para importar paquetes locales.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.facturas import (  # noqa: E402
    PROBABILIDADES,
    SELLO_SIMULADO,
    a_texto,
    comparar,
    contar_errores,
    cuit_valido,
    detectar_errores,
    evaluar_factura,
    evaluar_lote,
    extraer_mock,
    generar_factura,
    generar_facturas,
)


def test_sello_simulado_esta_presente():
    assert "SIMULATED" in SELLO_SIMULADO
    assert "NO FISCAL VALIDITY" in SELLO_SIMULADO


# ============================================================ generación
def test_facturas_deterministas():
    a = generar_facturas(5, seed=7)
    b = generar_facturas(5, seed=7)
    assert a == b
    c = generar_facturas(5, seed=8)
    assert a != c


def test_toda_factura_lleva_el_sello():
    for f in generar_facturas(30, seed=1):
        assert f["sello"] == "SIMULATED – NO FISCAL VALIDITY"
        assert f["documento"]["sello"] == "SIMULATED – NO FISCAL VALIDITY"


def test_tipos_de_error_son_los_documentados():
    conocidos = set(PROBABILIDADES)
    for f in generar_facturas(200, seed=3):
        for e in f["errores"]:
            assert e["tipo"] in conocidos


def test_total_mal_sumado_cuando_aparece():
    for f in generar_facturas(300, seed=5):
        if any(e["tipo"] == "total_mal_sumado" for e in f["errores"]):
            doc = f["documento"]
            assert round(doc["neto"] + doc["iva"], 2) != doc["total"]


def test_cuit_valido_algoritmo():
    # CUIT de prueba bien formado (dígito verificador correcto).
    assert cuit_valido("30-71234567-1")
    assert not cuit_valido("30-71234567-9")
    assert not cuit_valido("123")


def test_cuit_invalido_no_pasa_el_validador():
    for f in generar_facturas(400, seed=6):
        doc = f["documento"]
        tiene_error = any(e["tipo"] == "cuit_invalido" for e in f["errores"])
        if tiene_error:
            assert not cuit_valido(doc["cuit"])
        elif doc["cuit"] is not None:
            assert cuit_valido(doc["cuit"])


def test_campo_faltante_deja_algo_en_none():
    vistas = [f for f in generar_facturas(400, seed=9)
              if any(e["tipo"] == "campo_faltante" for e in f["errores"])]
    assert vistas, "con 400 facturas debe aparecer algún campo faltante"
    for f in vistas:
        assert any(f["documento"][c] is None
                   for c in ("razon_social", "cuit", "fecha", "numero"))


def test_importe_negativo_cuando_aparece():
    vistas = [f for f in generar_facturas(400, seed=11)
              if any(e["tipo"] == "importe_negativo" for e in f["errores"])]
    assert vistas
    for f in vistas:
        assert any(i["subtotal"] < 0 for i in f["documento"]["items"])


def test_monte_carlo_frecuencias_cerca_de_lo_documentado():
    n = 2000
    facturas = generar_facturas(n, seed=123)
    conteo = contar_errores(facturas)
    for tipo, p in PROBABILIDADES.items():
        frecuencia = conteo[tipo] / n
        assert abs(frecuencia - p) < 0.03, f"{tipo}: {frecuencia:.3f} vs {p}"


def test_todos_los_tipos_aparecen():
    conteo = contar_errores(generar_facturas(2000, seed=123))
    for tipo in PROBABILIDADES:
        assert conteo[tipo] > 0, f"nunca apareció el error {tipo}"


def test_a_texto_muestra_sello_y_items():
    f = generar_factura(random.Random(1), 1)
    texto = a_texto(f["documento"])
    assert "SIMULATED – NO FISCAL VALIDITY" in texto
    assert "TOTAL:" in texto
    assert "Nexus Alarm" in texto


# ==================================================== lector y precisión
def test_lector_local_ida_y_vuelta():
    correcto = generar_facturas(1, seed=1)[0]["correcto"]
    leido = extraer_mock(a_texto(correcto))
    for campo in ("numero", "tipo", "fecha", "razon_social", "cuit",
                  "items", "neto", "iva", "total", "moneda"):
        assert leido[campo] == correcto[campo], campo


def test_comparar_iguales_da_precision_1():
    doc = generar_facturas(1, seed=1)[0]["correcto"]
    comp = comparar(doc, copy.deepcopy(doc))
    assert comp["precision"] == 1.0
    assert comp["coincidencias"] == comp["total_campos"]


def test_comparar_un_campo_distinto_baja_la_precision():
    doc = generar_facturas(1, seed=1)[0]["correcto"]
    otro = copy.deepcopy(doc)
    otro["total"] = round(otro["total"] + 100, 2)
    comp = comparar(doc, otro)
    assert comp["precision"] < 1.0
    assert comp["por_campo"]["total"] is False
    assert comp["por_campo"]["neto"] is True


def test_detectar_errores_documento_limpio():
    doc = generar_facturas(1, seed=1)[0]["correcto"]
    assert detectar_errores(doc) == []


def test_detectar_errores_detecta_cada_tipo():
    base = generar_facturas(1, seed=1)[0]["correcto"]

    def tipos(doc):
        return {e["tipo"] for e in detectar_errores(doc)}

    d = copy.deepcopy(base)
    d["total"] = round(d["neto"] + d["iva"] + 50, 2)
    assert "total_mal_sumado" in tipos(d)

    d = copy.deepcopy(base)
    digitos = [int(c) for c in d["cuit"] if c.isdigit()]
    digitos[10] = (digitos[10] + 3) % 10
    s = "".join(str(x) for x in digitos)
    d["cuit"] = f"{s[:2]}-{s[2:10]}-{s[10]}"
    assert "cuit_invalido" in tipos(d)

    d = copy.deepcopy(base)
    d["fecha"] = "31/02/2026"
    assert "fecha_invalida" in tipos(d)

    d = copy.deepcopy(base)
    d["razon_social"] = None
    assert "campo_faltante" in tipos(d)

    d = copy.deepcopy(base)
    d["iva"] = 0.0
    assert "iva_mal_calculado" in tipos(d)

    d = copy.deepcopy(base)
    d["items"][0]["precio_unitario"] = round(d["items"][0]["precio_unitario"] + 7, 2)
    assert "item_descuadrado" in tipos(d)

    d = copy.deepcopy(base)
    d["items"][0]["subtotal"] = -abs(d["items"][0]["subtotal"])
    assert "importe_negativo" in tipos(d)


def test_evaluar_factura_sin_campo_faltante_no_falla_ningun_defecto():
    for f in generar_facturas(200, seed=21):
        if any(e["tipo"] == "campo_faltante" for e in f["errores"]):
            continue
        ev = evaluar_factura(f)
        assert ev["errores_fallados"] == [], (f["id"], ev["errores_fallados"])
        assert 0.0 < ev["precision"] <= 1.0


def test_evaluar_factura_precision_100_si_esta_limpia():
    limpias = [f for f in generar_facturas(50, seed=4) if not f["errores"]]
    assert limpias
    for f in limpias:
        assert evaluar_factura(f)["precision"] == 1.0


def test_evaluar_lote_da_numeros_coherentes():
    r = evaluar_lote(120, seed=31)
    assert r["n"] == 120
    assert 0.0 < r["precision_promedio"] <= 1.0
    assert 0.0 <= r["tasa_deteccion"] <= 1.0
    assert r["defectos_detectados"] + r["defectos_fallados"] == r["defectos_totales"]


def test_deteccion_completa_sin_falsas_alarmas():
    """El auditor detecta TODO lo etiquetable y no inventa defectos.

    Único caso legítimo "no etiquetable": si a la factura le tocó un valor
    inválido (CUIT/fecha) Y ADEMÁS que ese campo quede vacío por `campo_faltante`
    — el documento igual se marca defectuoso (campo_faltante), pero ya no hay
    valor inválido que etiquetar.
    """
    for f in generar_facturas(500, seed=11):
        doc = f["documento"]
        esp = {e["tipo"] for e in f["errores"]}
        det = {d["tipo"] for d in detectar_errores(doc)}
        vacios = {e["campo"] for e in f["errores"] if e["tipo"] == "campo_faltante"}

        faltan = set()
        for t in esp - det:
            campo = {"cuit_invalido": "cuit", "fecha_invalida": "fecha"}.get(t)
            if not (campo and campo in vacios):
                faltan.add(t)
        assert not faltan, (f["id"], sorted(faltan))
        if not esp:
            assert det == set(), (f["id"], sorted(det))
