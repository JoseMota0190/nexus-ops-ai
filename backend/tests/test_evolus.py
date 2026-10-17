"""Tests del módulo Evolus en MODO PRUEBA: sin red, deterministas.

No tocan `api.py` ni la base de datos: levantan una app mínima de prueba y le
enganchan SOLO el router de Evolus.

Regla de oro (del brief): con `EVOLUS_ENABLED=false` el módulo **no toca la
red**. Estos tests lo verifican de verdad: si alguien llama a la red, explota.
"""
import copy
import sys
from pathlib import Path

# Asegura que `backend/` esté en el path para importar paquetes locales.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from evolus.config import DEFAULT_API_BASE, EvolusConfig, get_config  # noqa: E402
from evolus.client import EvolusClient, EvolusError, EvolusMetrics  # noqa: E402
from evolus.extract import (  # noqa: E402
    comparar,
    detectar_errores,
    evaluar_factura,
    evaluar_lote,
)
from evolus.facturas import (  # noqa: E402
    PROBABILIDADES,
    a_texto,
    contar_errores,
    cuit_valido,
    generar_factura,
    generar_facturas,
)
from evolus.mock import extraer_mock  # noqa: E402
from evolus.router import router  # noqa: E402
from evolus.workflow import (  # noqa: E402
    contrato_mock,
    ejecutar_contrato,
    texto_contrato_por_defecto,
)


def _client() -> TestClient:
    """App mínima con SOLO el router de Evolus enganchado."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _sin_red(monkeypatch) -> None:
    """Deja la red 'envenenada': cualquier intento de conexión falla el test."""
    def boom(*_args, **_kwargs):
        raise AssertionError("el módulo Evolus tocó la red en modo prueba")

    monkeypatch.setattr(httpx, "post", boom)
    monkeypatch.setattr(httpx, "get", boom)


def test_salud_responde_en_modo_prueba(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    r = _client().get("/api/evolus/salud")
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is False
    assert d["mock"] is True
    assert d["tiene_clave"] is False
    assert d["base_url"] == DEFAULT_API_BASE
    assert d["modo"] == "prueba"


def test_apagado_jamas_toca_la_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    # Varias llamadas seguidas: ninguna debe intentar conectarse.
    cliente = _client()
    for _ in range(3):
        assert cliente.get("/api/evolus/salud").status_code == 200


def test_config_sin_clave_es_modo_prueba():
    cfg = EvolusConfig(enabled=True, api_key="   ")
    assert cfg.tiene_clave is False
    assert cfg.mock is True
    assert cfg.needs_network is False
    assert "sin clave" in cfg.motivo_mock


def test_config_con_clave_quiere_red():
    cfg = EvolusConfig(enabled=True, api_key="clave-de-prueba",
                       application_id="app-123")
    assert cfg.tiene_clave is True
    assert cfg.mock is False
    assert cfg.needs_network is True
    assert cfg.motivo_mock == ""


def test_config_apagada_es_modo_prueba():
    cfg = EvolusConfig(enabled=False, api_key="clave-igual")
    assert cfg.mock is True
    assert "apagado" in cfg.motivo_mock


def test_salud_trae_las_cuatro_claves_pedidas(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    d = _client().get("/api/evolus/salud").json()
    for clave in ("enabled", "mock", "base_url", "tiene_clave"):
        assert clave in d


def test_base_url_por_defecto_es_la_de_evolus(monkeypatch):
    monkeypatch.delenv("EVOLUS_API_BASE", raising=False)
    get_config.cache_clear()
    assert get_config().api_base == "https://api.evolus.ai/api/v1"


def test_sello_simulado_esta_presente():
    from evolus.mock import SELLO_SIMULADO

    assert "SIMULADO" in SELLO_SIMULADO
    assert "SIN VALIDEZ FISCAL" in SELLO_SIMULADO


# ============================================================ FASE 2: facturas
def test_facturas_deterministas():
    a = generar_facturas(5, seed=7)
    b = generar_facturas(5, seed=7)
    assert a == b
    c = generar_facturas(5, seed=8)
    assert a != c


def test_toda_factura_lleva_el_sello():
    for f in generar_facturas(30, seed=1):
        assert f["sello"] == "SIMULADO – SIN VALIDEZ FISCAL"
        assert f["documento"]["sello"] == "SIMULADO – SIN VALIDEZ FISCAL"


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
    f = generar_factura(__import__("random").Random(1), 1)
    texto = a_texto(f["documento"])
    assert "SIMULADO – SIN VALIDEZ FISCAL" in texto
    assert "TOTAL:" in texto
    assert "Nexus Alarm" in texto


def test_endpoint_facturas_responde(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    r = _client().post("/api/evolus/facturas", json={"n": 3})
    assert r.status_code == 200
    d = r.json()
    assert d["n"] == 3
    assert len(d["facturas"]) == 3
    assert d["sello"] == "SIMULADO – SIN VALIDEZ FISCAL"


def test_endpoint_facturas_rechaza_cantidades_invalidas(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    cliente = _client()
    assert cliente.post("/api/evolus/facturas", json={"n": 0}).status_code == 422
    assert cliente.post("/api/evolus/facturas", json={"n": 999}).status_code == 422


def test_endpoint_facturas_no_toca_la_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)
    assert _client().post("/api/evolus/facturas", json={"n": 5}).status_code == 200


# ==================================================== FASE 3: lector y precisión
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


def test_endpoint_extraer_responde(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    doc = generar_facturas(1, seed=1)[0]["correcto"]
    otro = copy.deepcopy(doc)
    otro["total"] = round(otro["total"] + 10, 2)

    r = _client().post("/api/evolus/extraer",
                       json={"esperado": doc, "obtenido": otro})
    assert r.status_code == 200
    d = r.json()
    for clave in ("esperado", "obtenido", "precision", "errores_detectados"):
        assert clave in d
    assert d["precision"] < 1.0
    assert any(e["tipo"] == "total_mal_sumado" for e in d["errores_detectados"])


def test_endpoint_extraer_no_toca_la_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)
    doc = generar_facturas(1, seed=1)[0]["correcto"]
    r = _client().post("/api/evolus/extraer",
                       json={"esperado": doc, "obtenido": doc})
    assert r.status_code == 200
    assert r.json()["precision"] == 1.0


# =========================================================== FASE 3: cliente
def test_cliente_modo_prueba_extrae_sin_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    correcto = generar_facturas(1, seed=1)[0]["correcto"]
    salida = EvolusClient(config=EvolusConfig(), metrics=EvolusMetrics()).extraer(a_texto(correcto))
    assert salida["mock"] is True
    assert salida["fallback"] is False
    assert salida["datos"]["total"] == correcto["total"]


def test_cliente_prendido_sin_clave_lanza_error():
    cliente = EvolusClient(config=EvolusConfig(enabled=True, api_key=""),
                           metrics=EvolusMetrics())
    with pytest.raises(EvolusError):
        cliente.extraer("cualquier cosa")


def test_cliente_cae_a_prueba_cuando_evolus_falla(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("sin red")

    monkeypatch.setattr(httpx, "post", boom)

    metrics = EvolusMetrics()
    cfg = EvolusConfig(enabled=True, api_key="clave", application_id="app",
                       api_base="http://127.0.0.1:9/api/v1",
                       max_retries=0, timeout_s=0.5)
    correcto = generar_facturas(1, seed=1)[0]["correcto"]
    salida = EvolusClient(config=cfg, metrics=metrics).extraer(a_texto(correcto))

    assert salida["fallback"] is True
    assert salida["mock"] is True
    assert salida["nota"]
    assert salida["datos"]["total"] == correcto["total"]
    assert metrics.summary()["caidas_a_prueba"] == 1


# ========================================================== FASE 4: contratos
def test_contrato_mock_determinista():
    a = contrato_mock("Cliente: X", seed=5)
    b = contrato_mock("Cliente: X", seed=5)
    assert a == b
    assert a["estado"] == "Completed"
    assert a["sello"] == "SIMULADO – SIN VALIDEZ FISCAL"


def test_texto_contrato_por_defecto_lleva_sello():
    texto = texto_contrato_por_defecto(seed=1)
    assert "SIMULADO" in texto
    assert "Cliente:" in texto


def test_ejecutar_contrato_modo_prueba_sin_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    r = ejecutar_contrato(client=EvolusClient(config=EvolusConfig(),
                                              metrics=EvolusMetrics()))
    assert r["mock"] is True
    assert r["fallback"] is False
    assert r["estado"] == "Completed"
    assert r["resultado"]["contrato"].startswith("CT-")


def test_ejecutar_contrato_prendido_sin_clave_lanza_error():
    cliente = EvolusClient(config=EvolusConfig(enabled=True, api_key=""),
                           metrics=EvolusMetrics())
    with pytest.raises(EvolusError):
        ejecutar_contrato(client=cliente)


def test_ejecutar_contrato_prendido_sin_workflow_lanza_error():
    cliente = EvolusClient(
        config=EvolusConfig(enabled=True, api_key="k", workflow_id=""),
        metrics=EvolusMetrics())
    with pytest.raises(EvolusError):
        ejecutar_contrato(client=cliente)


def test_ejecutar_contrato_cae_a_prueba_cuando_falla(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("sin red")

    monkeypatch.setattr(httpx, "post", boom)

    metrics = EvolusMetrics()
    cfg = EvolusConfig(enabled=True, api_key="k", workflow_id="wf-1",
                       api_base="http://127.0.0.1:9/api/v1",
                       max_retries=0, timeout_s=0.3)
    r = ejecutar_contrato(client=EvolusClient(config=cfg, metrics=metrics))
    assert r["fallback"] is True
    assert r["mock"] is True
    assert r["nota"]
    assert metrics.summary()["caidas_a_prueba"] == 1


def _cliente_guionado(monkeypatch, estados):
    """Cliente real con la red 'de mentira': dispara y devuelve estados dados."""
    cfg = EvolusConfig(enabled=True, api_key="k", workflow_id="wf-1",
                       api_base="http://127.0.0.1:9/api/v1")
    cliente = EvolusClient(config=cfg, metrics=EvolusMetrics())
    monkeypatch.setattr(cliente, "post_multipart",
                        lambda *a, **k: {"jobId": "job-1", "executionId": "exec-1"})
    serie = iter(estados)
    monkeypatch.setattr(cliente, "get_json", lambda *a, **k: next(serie))
    return cliente


def test_ejecutar_contrato_sigue_el_estado_hasta_completar(monkeypatch):
    cliente = _cliente_guionado(monkeypatch, [
        {"status": "Pending"},
        {"status": "Running"},
        {"status": "Completed", "output": {"contrato": "CT-1", "clausulas": 8}},
    ])
    r = ejecutar_contrato("texto", client=cliente, dormir=lambda _s: None)
    assert r["estado"] == "Completed"
    assert r["pasos"] == ["Pending", "Running", "Completed"]
    assert r["resultado"]["contrato"] == "CT-1"
    assert r["mock"] is False


def test_ejecutar_contrato_estado_fallado(monkeypatch):
    cliente = _cliente_guionado(monkeypatch, [{"status": "Failed"}])
    r = ejecutar_contrato("texto", client=cliente, dormir=lambda _s: None)
    assert r["estado"] == "Failed"


def test_endpoint_contratos_responde_en_modo_prueba(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    r = _client().post("/api/evolus/contratos", json={"seed": 3})
    assert r.status_code == 200
    d = r.json()
    assert d["mock"] is True
    assert d["estado"] == "Completed"


def test_endpoint_contratos_no_toca_la_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)
    r = _client().post("/api/evolus/contratos",
                       json={"texto": "Cliente: Prueba", "seed": 9})
    assert r.status_code == 200
    assert r.json()["resultado"]["cliente"] == "Prueba"


# =========================================================== FASE 5: métricas
def test_endpoint_metricas_responde(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)

    r = _client().get("/api/evolus/metricas?n=50&seed=2")
    assert r.status_code == 200
    d = r.json()
    for clave in ("n", "precision_promedio", "defectos_totales",
                  "defectos_detectados", "defectos_fallados", "tasa_deteccion",
                  "defectos_por_tipo", "cliente"):
        assert clave in d
    assert d["n"] == 50
    assert d["defectos_detectados"] + d["defectos_fallados"] == d["defectos_totales"]
    assert d["defectos_por_tipo"]


def test_endpoint_metricas_rechaza_n_invalido(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    assert _client().get("/api/evolus/metricas?n=0").status_code == 422
    assert _client().get("/api/evolus/metricas?n=100000").status_code == 422


def test_endpoint_metricas_no_toca_la_red(monkeypatch):
    monkeypatch.setenv("EVOLUS_ENABLED", "false")
    get_config.cache_clear()
    _sin_red(monkeypatch)
    assert _client().get("/api/evolus/metricas?n=10").status_code == 200
