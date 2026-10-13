"""Caché/replay de respuestas LLM para reproducir la demo sin red.

Clave = hash determinista de (agente, modelo, mensajes). Valor = JSON crudo devuelto
por el modelo. Sirve para: (a) reproducir la demo si falla la red, (b) no gastar
créditos repitiendo las mismas preguntas en desarrollo.

Se guarda en `backend/data/llm_cache.json` (se puede commitear un cache "caliente"
para la demo de respaldo).
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "llm_cache.json"
_lock = threading.Lock()


def _load() -> dict[str, Any]:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict[str, Any]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def key_for(agent: str, model: str, messages: list[dict[str, str]]) -> str:
    payload = json.dumps({"agent": agent, "model": model, "messages": messages},
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def get(agent: str, model: str, messages: list[dict[str, str]]) -> str | None:
    k = key_for(agent, model, messages)
    with _lock:
        return _load().get(k)


def put(agent: str, model: str, messages: list[dict[str, str]], response_text: str) -> None:
    k = key_for(agent, model, messages)
    with _lock:
        data = _load()
        data[k] = response_text
        _save(data)
