"""Cliente LLM único para todo el proyecto.

Un solo punto de entrada compatible con OpenAI (`base_url` configurable) que apunta
a un modelo abierto servido sobre AMD (Radeon Cloud / instancia GPU con Gemma+vLLM).
De acá salen TODAS las llamadas a modelos, para que las métricas se capturen en un
solo lugar.

Modos:
- USE_MOCK=true  -> respuestas locales realistas, sin red ni créditos.
- replay=true    -> sirve desde caché (reproducir demo sin red).

Reglas del proyecto: salida estructurada (JSON validado con Pydantic),
máx. 2 reintentos y fallback explícito.
"""
from .config import LLMConfig, get_config
from .client import LLMClient, LLMError
from .metrics import MetricsStore, get_metrics

__all__ = ["LLMConfig", "get_config", "LLMClient", "LLMError", "MetricsStore", "get_metrics"]
