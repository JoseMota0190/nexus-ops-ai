"""Métricas por llamada LLM: latencia y tokens.

Se registran todas las llamadas (mock y reales) en un solo lugar, para exponerlas
al panel de infraestructura AMD: tokens/s, latencia p50/p95, llamadas totales.
"""
from __future__ import annotations

import statistics
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class CallRecord:
    ts: float
    agent: str
    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    ok: bool
    mock: bool
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MetricsStore:
    """Almacén thread-safe de llamadas. Uno solo por proceso."""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _calls: list[CallRecord] = field(default_factory=list)

    def record(self, rec: CallRecord) -> None:
        with self._lock:
            self._calls.append(rec)

    def total_calls(self) -> int:
        with self._lock:
            return len(self._calls)

    def summary(self) -> dict[str, Any]:
        """Resumen para el panel. Percentiles de latencia y totales de tokens."""
        with self._lock:
            calls = list(self._calls)
        if not calls:
            return {"total_calls": 0}

        lat = sorted(c.latency_ms for c in calls)
        prompt_tk = sum(c.prompt_tokens for c in calls)
        comp_tk = sum(c.completion_tokens for c in calls)
        errors = sum(1 for c in calls if not c.ok)
        mocks = sum(1 for c in calls if c.mock)
        cached = sum(1 for c in calls if c.cached)

        def pct(p: float) -> float:
            if not lat:
                return 0.0
            k = (len(lat) - 1) * p
            f = int(k)
            c2 = min(f + 1, len(lat) - 1)
            if f == c2:
                return round(lat[f], 2)
            return round(lat[f] + (lat[c2] - lat[f]) * (k - f), 2)

        # tokens/s sobre la latencia total de las llamadas reales (no mock, no caché)
        real = [c for c in calls if not c.mock and not c.cached]
        total_s = sum(c.latency_ms for c in real) / 1000.0 if real else 0.0
        tok_s = round((sum(c.completion_tokens for c in real) / total_s), 2) if total_s > 0 else 0.0

        return {
            "total_calls": len(calls),
            "errors": errors,
            "mock_calls": mocks,
            "cached_calls": cached,
            "prompt_tokens": prompt_tk,
            "completion_tokens": comp_tk,
            "latency_p50_ms": pct(0.50),
            "latency_p95_ms": pct(0.95),
            "tokens_per_s": tok_s,
            "mean_latency_ms": round(statistics.fmean(lat), 2) if lat else 0.0,
        }


_store = MetricsStore()


def get_metrics() -> MetricsStore:
    return _store


def now_ms() -> float:
    return time.monotonic() * 1000.0
