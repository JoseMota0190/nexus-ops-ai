"""Tests del cliente LLM en modo mock: sin red, determinista, JSON validado."""
import random
import sys
from pathlib import Path

# Asegura que `backend/` esté en el path para importar paquetes locales.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import LLMClient, LLMError, get_metrics
from llm.config import LLMConfig
from schemas import TeleoperadorResponse, DespachoResponse, Calificacion


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


if __name__ == "__main__":
    test_teleoperador_urgente_cierra_cita()
    test_teleoperador_fuera_de_caba()
    test_despacho_trafico_reasigna()
    test_json_invalido_lanza_error()
    test_metricas_se_registran()
    print("OK: 5 tests del cliente LLM pasaron.")
