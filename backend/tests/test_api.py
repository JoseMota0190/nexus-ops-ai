"""Tests de la API (sin red, con el cliente LLM en modo mock)."""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# La base de prueba va en un directorio temporal, no en la de la demo.
_TD = tempfile.mkdtemp()
os.environ["NEXUS_DB"] = str(Path(_TD) / "api.db")

# Los tests SIEMPRE corren sin red, aunque el `.env` de la máquina tenga AMD
# prendido. Se fija ANTES de importar api (load_dotenv no pisa lo ya seteado).
os.environ["USE_MOCK"] = "true"

from fastapi.testclient import TestClient  # noqa: E402
from api import app  # noqa: E402

client = TestClient(app)

# Arranca de fábrica: los 6 primeros meses se corrigen solos al importar la API,
# así que los tests parten de un reinicio limpio (mes 1).
client.post("/api/reiniciar")


def test_estado_inicial():
    r = client.get("/api/estado")
    assert r.status_code == 200
    d = r.json()
    assert d["operadores"] == 3
    assert d["tecnicos"] == 2
    assert d["meta_tecnicos"] == 10
    assert d["puede_avanzar"] is True


def test_avanzar_mes_devuelve_acta_y_numeros():
    r = client.post("/api/mes")
    assert r.status_code == 200
    d = r.json()
    assert d["mes"] == 1
    assert "acta" in d and d["acta"]["cuerpo"]
    assert d["numeros"]["ventas"] > 0
    assert d["objetivos"]["tecnicos"] == 2


def test_llamada_en_vivo_hace_hablar_a_la_ia():
    r = client.post("/api/llamada_en_vivo")
    assert r.status_code == 200
    d = r.json()
    assert d["respuesta"]["reply_text"]
    assert d["cliente"]


def test_mapa_con_citas_y_zonas():
    client.post("/api/mes")
    d = client.get("/api/mapa").json()
    assert d["zonas"]["Palermo"]["lat"] < 0
    assert d["tecnicos"]
    assert d["capacidad_dia"] > 0


def test_llamadas_y_mensajes_log():
    client.post("/api/dia")
    log = client.get("/api/llamadas?limite=10").json()
    assert isinstance(log, list)
    wa = client.get("/api/mensajes?tipo=whatsapp_cliente").json()
    assert isinstance(wa, list)


def test_metricas_amd():
    d = client.get("/api/metricas").json()
    assert "base_url" in d
    assert "total_calls" in d


def test_objetivos_9_meses():
    d = client.get("/api/objetivos").json()
    assert len(d) == 9
    assert d[0]["ventas_por_dia"] == 6.0
    assert d[8]["tecnicos"] == 10


def test_reiniciar_vuelve_al_inicio():
    client.post("/api/reiniciar")
    d = client.get("/api/estado").json()
    assert d["mes"] == 1
    assert d["tecnicos"] == 2


def test_todos_los_get_de_la_pantalla_responden():
    """Barrido: si la pantalla usa un endpoint, tiene que responder 200."""
    from api import app

    rutas = [r.path for r in app.routes
             if getattr(r, "methods", None) and "GET" in r.methods
             and r.path.startswith("/api")]
    assert len(rutas) >= 8, rutas
    # Las rutas con parámetros necesitan un valor real para probarse.
    valores = {"{sector}": "ventas"}
    for ruta in rutas:
        prueba = ruta
        for param, valor in valores.items():
            prueba = prueba.replace(param, valor)
        resp = client.get(prueba)
        assert resp.status_code == 200, f"{prueba} -> {resp.status_code}: {resp.text[:200]}"


def test_sectores_tienen_informe_mensual():
    """Los 4 sectores responden y traen su informe del mes (aunque sea local)."""
    client.post("/api/reiniciar")
    for _ in range(2):  # deja dos meses cerrados
        client.post("/api/mes")

    lista = client.get("/api/sectores").json()
    assert [s["id"] for s in lista] == ["gerente", "ventas", "agenda", "facturacion"]
    assert all(s["tiene_informe"] for s in lista), lista
    assert lista[0]["mes_reporte"] == 2

    detalle = client.get("/api/sectores/ventas").json()
    assert detalle["tiene_informe"] is True
    assert detalle["titulo"]
    assert detalle["resumen"]
    assert detalle["hallazgos"], "un informe sin hallazgos no sirve"
    assert detalle["campos"], "el panel necesita los números en criollo"
    assert detalle["historial"], "tiene que estar el historial de meses"

    # Regenerar a mano (en mock usa el redactor local, sin red).
    gen = client.post("/api/sectores/gerente/generar")
    assert gen.status_code == 200, gen.text
    assert gen.json()["fuente"] in {"ia", "local"}


def test_facturacion_comprobantes_simulados():
    """La facturación trae comprobantes simulados y su auditoría (sin red)."""
    client.post("/api/mes")
    d = client.get("/api/facturacion").json()
    assert d["sello"] == "SIMULADO – SIN VALIDEZ FISCAL"
    assert d["metricas"]["comprobantes"] >= 1
    assert d["facturas"], "tienen que venir comprobantes de ejemplo"


def test_escenario_sliders_calcula():
    """'¿Qué pasa si…?' — el botón de las palancas no puede devolver error."""
    r = client.post("/api/escenario",
                    json={"operadores": 8, "tecnicos": 6, "mejoras": 3})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ventas_por_dia"] > 0
    assert d["costos_mes"] > 0
    assert "balance_mes" in d
    assert d["meta_cumplida"] is False

    # Con la meta completa, el indicador tiene que encenderse.
    lleno = client.post("/api/escenario",
                        json={"operadores": 8, "tecnicos": 10, "mejoras": 4}).json()
    assert lleno["meta_cumplida"] is True


def test_dia_en_vivo_corre_en_segundo_plano_y_termina():
    """El día en vivo arranca al instante (no bloquea) y al final trae el resultado."""
    client.post("/api/modo", json={"rapido": True})  # en modo rápido el día vuela
    assert client.post("/api/dia/en-vivo").status_code == 200, "tiene que arrancar ya"

    d = None
    for _ in range(400):
        d = client.get("/api/dia/en-vivo").json()
        if d["listo"]:
            break
        time.sleep(0.05)

    assert d and d["listo"], "el día en vivo nunca terminó"
    assert d["error"] is None, d["error"]
    assert d["resultado"] and "pelicula" in d["resultado"]
    assert "progreso" in d


def test_no_se_puede_correr_dos_cosas_juntas():
    """Mientras hay un día en vivo, otro 'correr un día' tiene que rebotar (409)."""
    from api import _DIA, _DIA_LOCK

    with _DIA_LOCK:
        _DIA["corriendo"] = True
    try:
        assert client.post("/api/dia").status_code == 409
        assert client.post("/api/mes").status_code == 409
    finally:
        with _DIA_LOCK:
            _DIA["corriendo"] = False


if __name__ == "__main__":
    test_estado_inicial()
    test_avanzar_mes_devuelve_acta_y_numeros()
    test_llamada_en_vivo_hace_hablar_a_la_ia()
    test_mapa_con_citas_y_zonas()
    test_llamadas_y_mensajes_log()
    test_metricas_amd()
    test_objetivos_9_meses()
    test_reiniciar_vuelve_al_inicio()
    test_todos_los_get_de_la_pantalla_responden()
    test_sectores_tienen_informe_mensual()
    test_facturacion_comprobantes_simulados()
    test_escenario_sliders_calcula()
    test_dia_en_vivo_corre_en_segundo_plano_y_termina()
    test_no_se_puede_correr_dos_cosas_juntas()
    print("OK: 12 tests de la API pasaron.")
