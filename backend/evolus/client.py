"""Cliente de Evolus: el "teléfono" que habla con la plataforma real.

Reglas del proyecto (igual que el cliente de IA):
- Máx. 2 reintentos y timeout.
- Si Evolus falla o devuelve basura → **no se rompe la demo**: se cae al lector
  LOCAL (modo prueba) y **queda anotado** en las métricas (transparencia, no truco).
- Prender Evolus sin clave es una configuración a medias → error claro.

En modo prueba (apagado o sin clave) NUNCA se toca la red.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from . import mock as _mock
from .config import EvolusConfig, get_config

_log = logging.getLogger("nexus.evolus")
T = TypeVar("T")


class EvolusError(Exception):
    """Error del módulo Evolus (config a medias, red caída o respuesta ilegible)."""


@dataclass
class EvolusCall:
    """Una llamada al módulo, para el panel de transparencia."""

    ts: float
    operacion: str
    ok: bool
    mock: bool
    fallback: bool
    latency_ms: float
    nota: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts, "operacion": self.operacion, "ok": self.ok,
            "mock": self.mock, "fallback": self.fallback,
            "latency_ms": round(self.latency_ms, 2), "nota": self.nota,
        }


@dataclass
class EvolusMetrics:
    """Almacén simple de llamadas (para /metricas y el panel)."""

    _calls: list[EvolusCall] = field(default_factory=list)

    def record(self, call: EvolusCall) -> None:
        self._calls.append(call)

    def total(self) -> int:
        return len(self._calls)

    def summary(self) -> dict[str, Any]:
        return {
            "total_llamadas": len(self._calls),
            "en_prueba": sum(1 for c in self._calls if c.mock),
            "caidas_a_prueba": sum(1 for c in self._calls if c.fallback),
            "errores": sum(1 for c in self._calls if not c.ok),
        }


_metrics = EvolusMetrics()


def get_metrics() -> EvolusMetrics:
    return _metrics


class EvolusClient:
    def __init__(self, config: EvolusConfig | None = None,
                 metrics: EvolusMetrics | None = None) -> None:
        self.config = config or get_config()
        self.metrics = metrics or get_metrics()

    # ------------------------------------------------------------------ API
    def validar(self) -> None:
        """Revisa que la configuración tenga sentido antes de usar la red."""
        if self.config.enabled and not self.config.tiene_clave:
            raise EvolusError(
                "EVOLUS_ENABLED=true pero falta EVOLUS_API_KEY: poné la clave en "
                ".env o dejá EVOLUS_ENABLED=false para trabajar en modo prueba."
            )

    def extraer(self, texto: str) -> dict[str, Any]:
        """Lee un comprobante y devuelve `{datos, mock, fallback, nota}`.

        Nunca rompe: si Evolus real falla, cae al lector local y lo anota.
        """
        self.validar()

        t0 = time.perf_counter()
        if self.config.mock:
            datos = _mock.extraer_mock(texto)
            self._record("extraer", ok=True, mock=True, fallback=False, t0=t0,
                         nota=self.config.motivo_mock)
            return {"datos": datos, "mock": True, "fallback": False,
                    "nota": "Modo prueba: leí localmente, sin tocar la red."}

        try:
            datos = self._extraer_red(texto)
            self._record("extraer", ok=True, mock=False, fallback=False, t0=t0)
            return {"datos": datos, "mock": False, "fallback": False, "nota": ""}
        except EvolusError as e:
            _log.warning("Evolus no respondió (%s) -> lector local", e)
            datos = _mock.extraer_mock(texto)
            self._record("extraer", ok=False, mock=True, fallback=True, t0=t0,
                         nota=str(e))
            return {"datos": datos, "mock": True, "fallback": True,
                    "nota": f"Evolus no respondió ({e}); usé el lector local y quedó anotado."}

    # ------------------------------------------------------------- interno
    def _record(self, operacion: str, ok: bool, mock: bool, fallback: bool,
                t0: float, nota: str = "") -> None:
        self.metrics.record(EvolusCall(
            ts=time.time(), operacion=operacion, ok=ok, mock=mock,
            fallback=fallback, latency_ms=(time.perf_counter() - t0) * 1000.0,
            nota=nota,
        ))

    def _headers(self) -> dict[str, str]:
        h = {"X-ApiKey": self.config.api_key}
        if self.config.application_id:
            h["X-Application-Id"] = self.config.application_id
        return h

    def _extraer_red(self, texto: str) -> dict[str, Any]:
        try:
            import httpx  # noqa: F401  (se usa en los _post_*)
        except ImportError as e:  # pragma: no cover
            raise EvolusError("httpx no instalado; corré `pip install httpx`.") from e

        if self.config.agent_id and self.config.extractor_id:
            salida = self._ask_file(texto)  # extractor propio
        else:
            # Herramienta lista `doc-structure`: no requiere configurar la UI.
            url = f"{self.config.api_base}/ai-tools/doc-structure/run"
            salida = self.post_json(url, {"text": texto, "secondaryText": "",
                                          "options": {}})
            if isinstance(salida, dict) and "output" in salida:
                salida = salida["output"]
        return self._como_datos(salida)

    def _ask_file(self, texto: str) -> Any:
        url = (f"{self.config.api_base}/agents/{self.config.agent_id}"
               f"/json/{self.config.extractor_id}/ask-file")
        return self.post_file(url, {"useWebhook": "false"}, texto)

    def _con_reintentos(self, fn: Callable[[], T], operacion: str) -> T:
        intentos = self.config.max_retries + 1
        ultimo: Exception | None = None
        for _ in range(intentos):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001
                ultimo = e
        raise EvolusError(
            f"Evolus no respondió en {operacion!r} tras {intentos} intentos: {ultimo}"
        )

    def post_json(self, url: str, body: dict[str, Any]) -> Any:
        """POST JSON con reintentos y timeout (reutilizable por el workflow)."""
        import httpx

        def intento() -> Any:
            r = httpx.post(url, headers=self._headers(), json=body,
                           timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.json()

        return self._con_reintentos(intento, "post_json")

    def post_file(self, url: str, params: dict[str, str], texto: str) -> Any:
        import httpx

        def intento() -> Any:
            files = {"file": ("comprobante.txt", texto.encode("utf-8"), "text/plain")}
            r = httpx.post(url, headers=self._headers(), params=params,
                           files=files, timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.json()

        return self._con_reintentos(intento, "post_file")

    def post_multipart(self, url: str, data: dict[str, str],
                       files: dict[str, Any]) -> Any:
        """POST multipart (lo usa el disparo del workflow)."""
        import httpx

        def intento() -> Any:
            r = httpx.post(url, headers=self._headers(), data=data, files=files,
                           timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.json()

        return self._con_reintentos(intento, "workflow_execute")

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """GET JSON (lo usa el polling del workflow)."""
        import httpx

        def intento() -> Any:
            r = httpx.get(url, headers=self._headers(), params=params,
                          timeout=self.config.timeout_s)
            r.raise_for_status()
            return r.json()

        return self._con_reintentos(intento, "workflow_status")

    def _como_datos(self, salida: Any) -> dict[str, Any]:
        """Normaliza la respuesta de Evolus a un diccionario de datos."""
        if isinstance(salida, dict):
            return salida
        if isinstance(salida, str):
            try:
                data = json.loads(salida)
            except json.JSONDecodeError as e:
                raise EvolusError("Evolus devolvió texto que no es JSON válido.") from e
            if isinstance(data, dict):
                return data
        raise EvolusError(
            f"Respuesta de Evolus ilegible ({type(salida).__name__}); se usa el lector local."
        )
