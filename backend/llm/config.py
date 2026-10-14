"""Configuración del cliente LLM leída desde variables de entorno.

Nunca se commitean secretos: todo viene de `.env` (ver `.env.example`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv es opcional en runtime
    pass


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


@dataclass(frozen=True)
class LLMConfig:
    use_mock: bool = True
    # AMD Radeon Cloud: endpoints compatibles con OpenAI, gratis y sin aprobación.
    # Gemma se sirve desde una instancia propia (Dedicated Model API) con la misma clave.
    base_url: str = "https://developer.amd.com.cn/radeon/api/v1"
    api_key: str = ""
    model: str = ""
    max_retries: int = 2  # regla: máx. 2 reintentos
    timeout_s: float = 30.0

    @property
    def needs_network(self) -> bool:
        return not self.use_mock


@lru_cache(maxsize=1)
def get_config() -> LLMConfig:
    return LLMConfig(
        use_mock=_bool("USE_MOCK", True),
        base_url=os.getenv("LLM_BASE_URL",
                           "https://developer.amd.com.cn/radeon/api/v1").rstrip("/"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", ""),
        max_retries=max(0, _int("LLM_MAX_RETRIES", 2)),
        timeout_s=float(os.getenv("LLM_TIMEOUT_S", "30")),
    )
