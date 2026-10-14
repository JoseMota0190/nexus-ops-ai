"""Tests de la API (sin red, con el cliente LLM en modo mock)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# La base de prueba va en un directorio temporal, no en la de la demo.
_TD = tempfile.mkdtemp()
os.environ["NEXUS_DB"] = str(Path(_TD) / "api.db")

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


if __name__ == "__main__":
    test_estado_inicial()
    test_avanzar_mes_devuelve_acta_y_numeros()
    test_llamada_en_vivo_hace_hablar_a_la_ia()
    test_mapa_con_citas_y_zonas()
    test_llamadas_y_mensajes_log()
    test_metricas_amd()
    test_objetivos_9_meses()
    test_reiniciar_vuelve_al_inicio()
    print("OK: 8 tests de la API pasaron.")
