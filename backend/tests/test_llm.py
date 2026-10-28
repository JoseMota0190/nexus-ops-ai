"""Tests del cliente LLM en modo mock: sin red, determinista, JSON validado."""
import random
import sys
from pathlib import Path

# Asegura que `backend/` esté en el path para importar paquetes locales.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import LLMClient, LLMError, get_metrics
from llm.config import LLMConfig, _overrides_por_agente
from schemas import TeleoperadorResponse, DespachoResponse, Calificacion
from schemas.gerente import ReunionGerente


def _client() -> LLMClient:
    return LLMClient(config=LLMConfig(use_mock=True, model="mock"))


def test_teleoperador_urgente_cierra_cita():
    c = _client()
    resp = c.complete(
        agent="teleoperador",
        messages=[{"role": "user", "content": "Urge, se metieron en mi casa en Palermo, ¿pueden venir hoy?"}],
        schema=TeleoperadorResponse,
    )
    assert isinstance(resp, TeleoperadorResponse)
    assert resp.direccion_valida_caba is True
    assert resp.barrio == "Palermo"
    assert resp.calificacion == Calificacion.CALIDO
    assert resp.propone_horario is not None


def test_teleoperador_fuera_de_caba():
    c = _client()
    resp = c.complete(
        agent="teleoperador",
        messages=[{"role": "user", "content": "Soy de Tigre, ¿hacen instalaciones ahí?"}],
        schema=TeleoperadorResponse,
    )
    assert resp.direccion_valida_caba is False
    assert resp.calificacion == Calificacion.FRIELO


def test_despacho_trafico_reasigna():
    c = _client()
    resp = c.complete(
        agent="despacho",
        messages=[{"role": "user", "content": '{"tipo": "trafico", "visita_id": "V-01", "tecnico_asignado": "TEC-03"}'}],
        schema=DespachoResponse,
    )
    assert isinstance(resp, DespachoResponse)
    assert resp.tecnico_sugerido is not None
    assert resp.explicacion


def test_json_invalido_lanza_error():
    from pydantic import BaseModel

    class Estricto(BaseModel):
        campo_imposible: int

    c = _client()
    # Fuerzo un agente mock inexistente para provocar error controlado.
    try:
        c.complete(agent="inexistente", messages=[], schema=Estricto)
        assert False, "debió lanzar LLMError"
    except LLMError:
        pass


def test_metricas_se_registran():
    get_metrics()  # store global
    c = _client()
    c.complete(agent="teleoperador",
               messages=[{"role": "user", "content": "Quiero alarma en Belgrano"}],
               schema=TeleoperadorResponse)
    assert get_metrics().total_calls() > 0


def test_proveedor_caido_no_rompe_la_demo():
    """Si el proveedor real está caído o la key está mal, la demo NO se rompe.

    El cliente cae en la respuesta de respaldo y lo anota en las métricas
    (fallback_calls + errors), sin ocultar el problema.
    """
    from llm.config import LLMConfig as C

    c = LLMClient(config=C(use_mock=False, base_url="http://127.0.0.1:9/v1",
                            api_key="clave-mala", model="no-existe",
                            max_retries=0, timeout_s=0.5))
    antes = get_metrics().summary()
    resp = c.complete(agent="teleoperador",
                      messages=[{"role": "user",
                                 "content": "Quiero una alarma en Colegiales, ¿cuánto sale?"}],
                      schema=TeleoperadorResponse)
    assert isinstance(resp, TeleoperadorResponse)
    despues = get_metrics().summary()
    assert despues.get("fallback_calls", 0) > antes.get("fallback_calls", 0)
    assert despues.get("errors", 0) > antes.get("errors", 0)


# ------------------------------------------------- router de modelos Nebius
# El jurado del hackathon premia un modelo grande para razonar y uno liviano
# para el volumen. Estos tests fijan ese contrato.
def _router(**kw) -> LLMConfig:
    base = dict(use_mock=True, reasoning_model="grande", fast_model="chico")
    base.update(kw)
    return LLMConfig(**base)


def test_router_razonamiento_usa_el_modelo_grande():
    c = _router()
    assert c.model_for("gerente") == "grande"
    assert c.model_for("sector_centro") == "grande"
    assert c.model_for("sector_ventas") == "grande"


def test_router_alto_volumen_usa_el_modelo_rapido():
    c = _router()
    for agente in ("teleoperador", "operador", "agenda", "tecnicos", "despacho"):
        assert c.model_for(agente) == "chico", agente


def test_router_override_por_agente_gana_sobre_el_tier():
    c = _router(agent_models=(("teleoperador", "especial"),))
    assert c.model_for("teleoperador") == "especial"
    assert c.model_for("operador") == "chico"


def test_router_override_sector_aplica_a_todos_los_sectores():
    c = _router(agent_models=(("sector", "solo-sectores"),))
    assert c.model_for("sector_ventas") == "solo-sectores"
    assert c.model_for("sector_agenda") == "solo-sectores"
    # El gerente no es un sector: sigue yendo al tier de razonamiento.
    assert c.model_for("gerente") == "grande"


def test_router_sin_tiers_cae_al_modelo_global():
    c = LLMConfig(use_mock=True, model="unico")
    assert c.model_for("gerente") == "unico"
    assert c.model_for("teleoperador") == "unico"


def test_router_sin_modelos_devuelve_vacio():
    c = LLMConfig(use_mock=True)
    assert c.model_for("gerente") == ""
    assert c.model_for("teleoperador") == ""


def test_overrides_por_agente_ignora_los_tiers(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_GERENTE", "grande-a-mano")
    monkeypatch.setenv("LLM_MODEL_REASONING", "no-es-un-agente")
    monkeypatch.setenv("LLM_MODEL_FAST", "tampoco")
    monkeypatch.setenv("LLM_MODEL", "global-tampoco")
    overrides = dict(_overrides_por_agente())
    assert overrides == {"gerente": "grande-a-mano"}


def test_cliente_registra_el_modelo_que_resolvio_el_router():
    """La métrica guarda el modelo real del agente, no el default."""
    from llm.metrics import MetricsStore

    store = MetricsStore()
    c = LLMClient(config=_router(), metrics=store)
    c.complete(agent="teleoperador",
               messages=[{"role": "user", "content": "Quiero alarma en Belgrano"}],
               schema=TeleoperadorResponse)
    c.complete(agent="gerente",
               messages=[{"role": "user", "content": "Resumí el mes"}],
               schema=ReunionGerente)

    usados = [(r.agent, r.model) for r in store.records()]
    assert ("teleoperador", "chico") in usados
    assert ("gerente", "grande") in usados


if __name__ == "__main__":
    test_teleoperador_urgente_cierra_cita()
    test_teleoperador_fuera_de_caba()
    test_despacho_trafico_reasigna()
    test_json_invalido_lanza_error()
    test_metricas_se_registran()
    test_proveedor_caido_no_rompe_la_demo()
    test_router_razonamiento_usa_el_modelo_grande()
    test_router_alto_volumen_usa_el_modelo_rapido()
    test_router_override_por_agente_gana_sobre_el_tier()
    test_router_override_sector_aplica_a_todos_los_sectores()
    test_router_sin_tiers_cae_al_modelo_global()
    test_router_sin_modelos_devuelve_vacio()
    print("OK: tests del cliente LLM y del router pasaron.")
