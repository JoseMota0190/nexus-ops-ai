"""Configuración del cliente LLM leída desde variables de entorno.

Nunca se commitean secretos: todo viene de `.env` (ver `.env.example`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv es opcional en runtime
    pass

# Agentes que necesitan razonamiento (informes, decisiones de negocio).
# El resto son llamadas de alto volumen y van al modelo rápido.
_AGENTES_RAZONAMIENTO = frozenset({"gerente"})
_PREFIJOS_RAZONAMIENTO = ("sector_",)
# Variables que NO son overrides por agente (son los tiers).
_RESERVADAS = frozenset({"REASONING", "FAST"})


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _es_razonamiento(agent: str) -> bool:
    """True si el agente necesita el modelo grande."""
    return agent in _AGENTES_RAZONAMIENTO or agent.startswith(_PREFIJOS_RAZONAMIENTO)


def _overrides_por_agente() -> tuple[tuple[str, str], ...]:
    """Lee `LLM_MODEL_<AGENTE>` del entorno (p. ej. `LLM_MODEL_GERENTE`)."""
    out: list[tuple[str, str]] = []
    for clave, valor in os.environ.items():
        if not clave.startswith("LLM_MODEL_"):
            continue
        sufijo = clave[len("LLM_MODEL_"):]
        if not sufijo or sufijo in _RESERVADAS or not valor.strip():
            continue
        out.append((sufijo.lower(), valor.strip()))
    return tuple(sorted(out))


@dataclass(frozen=True)
class LLMConfig:
    use_mock: bool = True
    # Nebius Token Factory: endpoints compatibles con OpenAI.
    base_url: str = "https://api.tokenfactory.nebius.com/v1"
    api_key: str = ""
    # Fallback global si no hay modelo de tier ni override por agente.
    model: str = ""
    # Router: un modelo grande para razonar y uno liviano para el volumen.
    reasoning_model: str = ""
    fast_model: str = ""
    # Overrides explícitos: (nombre de agente, modelo).
    agent_models: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    max_retries: int = 2  # regla: máx. 2 reintentos
    timeout_s: float = 30.0

    @property
    def needs_network(self) -> bool:
        return not self.use_mock

    def model_for(self, agent: str) -> str:
        """Devuelve el modelo que corresponde a cada agente.

        Precedencia:
        1. Override exacto por agente (`LLM_MODEL_<AGENTE>`).
        2. Override `LLM_MODEL_SECTOR`, solo para agentes `sector_*`.
        3. Tier: razonamiento (`gerente`, `sector_*`) o rápido (el resto).
        4. `LLM_MODEL` global.
        5. Cadena vacía (el cliente la interpreta como "mock").
        """
        for nombre, modelo in self.agent_models:
            if nombre == agent:
                return modelo
        if agent.startswith(_PREFIJOS_RAZONAMIENTO):
            for nombre, modelo in self.agent_models:
                if nombre == "sector":
                    return modelo
        tier = self.reasoning_model if _es_razonamiento(agent) else self.fast_model
        return tier or self.model


@lru_cache(maxsize=1)
def get_config() -> LLMConfig:
    return LLMConfig(
        use_mock=_bool("USE_MOCK", True),
        base_url=_str("LLM_BASE_URL",
                      "https://api.tokenfactory.nebius.com/v1").rstrip("/"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=_str("LLM_MODEL"),
        reasoning_model=_str("LLM_MODEL_REASONING"),
        fast_model=_str("LLM_MODEL_FAST"),
        agent_models=_overrides_por_agente(),
        max_retries=max(0, _int("LLM_MAX_RETRIES", 2)),
        timeout_s=float(os.getenv("LLM_TIMEOUT_S", "30")),
    )
