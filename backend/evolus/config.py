"""Configuración del módulo Evolus, leída desde variables de entorno.

Evolus es una pieza **opcional y aislada** del simulador principal. Si está
apagada (`EVOLUS_ENABLED=false`, el default) o si no hay clave, el módulo
trabaja en **MODO PRUEBA** (mock): responde con datos locales, no toca la red
y **jamás rompe la demo**.

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

# Base REST de Evolus (workflows, extractores, AI Tools, libraries).
DEFAULT_API_BASE = "https://api.evolus.ai/api/v1"


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EvolusConfig:
    """Foto inmutable de la configuración de Evolus."""

    enabled: bool = False
    api_base: str = DEFAULT_API_BASE
    api_key: str = ""
    application_id: str = ""
    # Opcionales: si están, se usa el EXTRACTOR PROPIO (creado antes en la UI);
    # si no, se usa la herramienta lista `doc-structure` (no requiere configurar nada).
    agent_id: str = ""
    extractor_id: str = ""
    # Opcional: id del workflow de contratos (creado y ENCENDIDO en la UI).
    workflow_id: str = ""
    # AI Tool de Evolus que usamos para REDACTAR los informes de sector
    # (por defecto "summarize"; se puede cambiar con EVOLUS_REDACTOR_TOOL).
    redactor_tool: str = "summarize"
    max_retries: int = 2  # regla del proyecto: máx. 2 reintentos
    timeout_s: float = 30.0

    @property
    def tiene_clave(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def mock(self) -> bool:
        """True = MODO PRUEBA (no se toca la red).

        Es prueba si está apagado o si no hay clave. Encender Evolus sin clave
        es una configuración a medias: el cliente lo avisa con un error claro
        en vez de mandar pedidos sin credenciales.
        """
        return (not self.enabled) or (not self.tiene_clave)

    @property
    def motivo_mock(self) -> str:
        """Explica EN CRIOLLO por qué se está en modo prueba (para /salud)."""
        if not self.enabled:
            return "Evolus apagado (EVOLUS_ENABLED=false)."
        if not self.tiene_clave:
            return "Evolus prendido pero sin clave (EVOLUS_API_KEY vacía)."
        return ""

    @property
    def needs_network(self) -> bool:
        return not self.mock


@lru_cache(maxsize=1)
def get_config() -> EvolusConfig:
    return EvolusConfig(
        enabled=_bool("EVOLUS_ENABLED", False),
        api_base=os.getenv("EVOLUS_API_BASE", DEFAULT_API_BASE).rstrip("/"),
        api_key=os.getenv("EVOLUS_API_KEY", ""),
        application_id=os.getenv("EVOLUS_APPLICATION_ID", ""),
        agent_id=os.getenv("EVOLUS_AGENT_ID", ""),
        extractor_id=os.getenv("EVOLUS_EXTRACTOR_ID", ""),
        workflow_id=os.getenv("EVOLUS_WORKFLOW_ID", ""),
        redactor_tool=os.getenv("EVOLUS_REDACTOR_TOOL", "summarize"),
    )
