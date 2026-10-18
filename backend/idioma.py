"""Idioma activo del motor (inglés / español).

El dueño puede ver el sitio en inglés o en español. El motor genera TODO el texto
que la pantalla muestra (informes de sector, actas del gerente, charlas de los
agentes, facturas simuladas y motivos de llamada). En vez de traducir a mano cada
base de datos, el motor sabe en qué idioma está y escribe ese idioma.

`t(en, es)` es el atajo: devuelve el texto en el idioma activo. Así una misma
línea del programa lleva las dos versiones pegadas y es imposible que se
desincronicen.

Vive en la raíz de `backend/` (y no dentro de `engine/`) para que lo puedan usar
tanto el motor como el cliente LLM sin un ciclo de importación.

Cada idioma tiene su propia base (ver `api.py`): la inglesa y la española. El
botón ES/EN cambia el idioma activo y de qué base se lee.
"""
from __future__ import annotations

IDIOMAS = ("en", "es")

_IDIOMA = "en"


def set_idioma(lang: str) -> str:
    """Fija el idioma activo (cualquier cosa rara cae a inglés)."""
    global _IDIOMA
    _IDIOMA = lang if lang in IDIOMAS else "en"
    return _IDIOMA


def idioma() -> str:
    return _IDIOMA


def es_espanol() -> bool:
    return _IDIOMA == "es"


def t(en: str, es: str) -> str:
    """Texto en el idioma activo: `t("in English", "en español")`."""
    return es if _IDIOMA == "es" else en
