"""Cliente LLM único, compatible con OpenAI, con modo mock, caché y métricas.

Punto de entrada único para TODAS las llamadas a modelos. Uso:

    from llm import LLMClient
    from schemas import TeleoperadorResponse

    client = LLMClient()
    resp = client.complete(
        agent="teleoperador",
        messages=[{"role": "user", "content": "..."}],
        schema=TeleoperadorResponse,
    )

Garantías:
- Modo mock sin red ni créditos.
- Salida estructurada: JSON validado contra el esquema Pydantic.
- Máx. 2 reintentos ante JSON inválido + fallback explícito.
- Caché/replay opcional para reproducir la demo sin red.
- Métricas de cada llamada (latencia, tokens) registradas.
"""
from __future__ import annotations

import json
import random
import time
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from . import cache as _cache
from . import mock as _mock
from .config import LLMConfig, get_config
from .metrics import CallRecord, MetricsStore, get_metrics

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Error del cliente LLM (tras agotar reintentos o fallar la red)."""


class LLMClient:
    def __init__(self, config: LLMConfig | None = None,
                 metrics: MetricsStore | None = None,
                 replay: bool = False) -> None:
        self.config = config or get_config()
        self.metrics = metrics or get_metrics()
        self.replay = replay  # si True, solo sirve desde caché (demo sin red)
        self._rng = random.Random(42)  # determinismo en el modo mock

    # ------------------------------------------------------------------ API
    def complete(self, agent: str, messages: list[dict[str, str]],
                 schema: Type[T]) -> T:
        """Devuelve una instancia validada del esquema `schema`."""
        raw = self._raw_complete(agent, messages)
        return self._validate(agent, raw, schema)

    def complete_json(self, agent: str, messages: list[dict[str, str]]) -> str:
        """Solo el JSON crudo (útil para cacheo y debugging)."""
        return self._raw_complete(agent, messages)

    # ------------------------------------------------------------- interno
    def _raw_complete(self, agent: str, messages: list[dict[str, str]]) -> str:
        model = self.config.model or "mock"

        # 1) Caché/replay tiene prioridad (reproducibilidad).
        cached = _cache.get(agent, model, messages)
        if cached is not None:
            self._record(agent, model, 0.0, len(cached), len(cached),
                         ok=True, mock=self.config.use_mock, cached=True)
            return cached

        if self.config.use_mock:
            return self._complete_mock(agent, messages, model)

        if self.replay:
            raise LLMError("replay=True y no hay respuesta en caché para esta consulta.")

        return self._complete_network(agent, messages, model)

    def _complete_mock(self, agent: str, messages: list[dict[str, str]],
                       model: str) -> str:
        t0 = time.perf_counter()
        if agent == "teleoperador":
            data = _mock.teleoperador_mock(messages, self._rng)
        elif agent == "despacho":
            exc = json.loads(messages[-1]["content"])
            data = _mock.despacho_mock(exc, self._rng)
        else:
            raise LLMError(f"Agente mock desconocido: {agent!r}")
        dt = (time.perf_counter() - t0) * 1000.0
        out = json.dumps(data, ensure_ascii=False)
        _cache.put(agent, model, messages, out)
        self._record(agent, model, dt, len(out) // 4, len(out) // 4,
                     ok=True, mock=True, cached=False)
        return out

    def _complete_network(self, agent: str, messages: list[dict[str, str]],
                          model: str) -> str:
        try:
            import httpx
        except ImportError as e:  # pragma: no cover
            raise LLMError("httpx no instalado; corré `pip install httpx`.") from e

        url = f"{self.config.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        body = {"model": model, "messages": messages,
                "temperature": 0.2, "response_format": {"type": "json_object"}}

        attempts = self.config.max_retries + 1
        last_err: Exception | None = None
        for attempt in range(attempts):
            t0 = time.perf_counter()
            try:
                r = httpx.post(url, headers=headers, json=body,
                               timeout=self.config.timeout_s)
                r.raise_for_status()
                payload = r.json()
                dt = (time.perf_counter() - t0) * 1000.0
                choice = payload["choices"][0]["message"]["content"]
                usage = payload.get("usage", {})
                self._record(agent, model, dt,
                             usage.get("prompt_tokens", 0),
                             usage.get("completion_tokens", 0),
                             ok=True, mock=False, cached=False)
                _cache.put(agent, model, messages, choice)
                return choice
            except Exception as e:  # noqa: BLE001
                last_err = e
                self._record(agent, model, (time.perf_counter() - t0) * 1000.0,
                             0, 0, ok=False, mock=False, cached=False)
        raise LLMError(f"Fallo de red en {agent} tras {attempts} intentos: {last_err}")

    def _validate(self, agent: str, raw: str, schema: Type[T]) -> T:
        try:
            return schema.model_validate_json(raw)
        except ValidationError as e:
            # Un reintento de parseo ya está implícito en _complete_network.
            raise LLMError(f"Salida JSON inválida de {agent}: {e}") from e

    def _record(self, agent: str, model: str, latency_ms: float,
                prompt_tk: int, comp_tk: int, ok: bool, mock: bool,
                cached: bool) -> None:
        self.metrics.record(CallRecord(
            ts=time.time(), agent=agent, model=model, latency_ms=latency_ms,
            prompt_tokens=prompt_tk, completion_tokens=comp_tk,
            ok=ok, mock=mock, cached=cached,
        ))
