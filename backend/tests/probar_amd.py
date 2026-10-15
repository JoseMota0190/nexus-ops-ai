"""Prueba de conexión real con AMD. Sin esto, no sabemos si el cerebro anda.

Uso (desde backend/):

    .venv\\Scripts\\python.exe tests\\probar_amd.py

Toma la configuración del archivo `.env` (o del entorno):
    LLM_BASE_URL   endpoint compatible con OpenAI
    LLM_API_KEY    la clave
    LLM_MODEL      el nombre exacto del modelo

Qué hace:
  1. Le pide a la lista de modelos disponibles.
  2. Le manda una pregunta de prueba y mide cuánto tarda.
  3. Le pide una respuesta ESTRUCTURADA (la que usan los agentes de verdad).
     -> El paso 3 es el importante: si el modelo no devuelve JSON válido,
        el agente no puede trabajar aunque la prueba 1 y 2 salgan bien.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm.config import get_config  # noqa: E402


def _verde(t: str) -> str:
    return f"\033[32m{t}\033[0m"


def _rojo(t: str) -> str:
    return f"\033[31m{t}\033[0m"


def _ambar(t: str) -> str:
    return f"\033[33m{t}\033[0m"


def _seguro(t: str) -> str:
    """Recorta caracteres que la consola de Windows no puede escribir.

    El modelo a veces devuelve flechas u otros símbolos; si la consola es
    cp1252, imprimirlos revienta la prueba. Acá los reemplazamos.
    """
    return t.encode("cp1252", "replace").decode("cp1252")


def listar_modelos(base_url: str, key: str) -> list[str] | None:
    import httpx
    try:
        r = httpx.get(f"{base_url}/models",
                      headers={"Authorization": f"Bearer {key}"},
                      timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
        return [m.get("id", "?") for m in data]
    except Exception as e:  # noqa: BLE001
        print(f"  {_ambar('⚠')} no se pudo leer el catálogo: {type(e).__name__}: {e}")
        return None


def main() -> int:
    cfg = get_config()

    print("=" * 66)
    print("PRUEBA DE CONEXIÓN CON AMD")
    print("=" * 66)
    print(f"  endpoint : {cfg.base_url}")
    print(f"  modelo   : {cfg.model or '(sin definir)'}")
    print(f"  clave    : {'sí (' + str(len(cfg.api_key)) + ' caracteres)' if cfg.api_key else _rojo('NO DEFINIDA')}")

    if not cfg.api_key or not cfg.model:
        print(f"\n{_rojo('Faltan datos.')}")
        print("Completá LLM_API_KEY y LLM_MODEL en backend/.env y volvé a correr.")
        return 2

    print("\n--- 1) Lista de modelos ---")
    modelos = listar_modelos(cfg.base_url, cfg.api_key)
    if modelos:
        print(f"  {_verde('OK')} hay {len(modelos)} modelos:")
        for m in modelos:
            marca = " <-- el nuestro" if m == cfg.model else ""
            print(f"     · {m}{marca}")
        if cfg.model not in modelos:
            print(f"\n  {_ambar('⚠')} el modelo '{cfg.model}' NO figura en la lista.")
            print("    ¿Se copió el nombre completo? Pegá el nombre tal cual aparece arriba.")
    else:
        print("  seguimos igual, pero con menos información")

    print("\n--- 2) Pregunta simple ---")
    try:
        import httpx
        t0 = time.perf_counter()
        r = httpx.post(
            f"{cfg.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {cfg.api_key}"},
            json={"model": cfg.model,
                  "messages": [{"role": "user", "content": "Decí 'hola' y nada más."}],
                  "max_tokens": 20, "temperature": 0.2},
            timeout=60,
        )
        dt = (time.perf_counter() - t0) * 1000
        if r.status_code != 200:
            print(_seguro(f"  {_rojo('FALLÓ')} HTTP {r.status_code}: {r.text[:400]}"))
            return 1
        txt = r.json()["choices"][0]["message"]["content"]
        print(_seguro(f"  {_verde('OK')} en {dt:.0f} ms -> {txt.strip()[:120]!r}"))
    except Exception as e:  # noqa: BLE001
        print(_seguro(f"  {_rojo('FALLÓ')} {type(e).__name__}: {e}"))
        return 1

    print("\n--- 3) Respuesta estructurada (la que usan los agentes) ---")
    from llm import LLMClient
    from schemas import TeleoperadorResponse

    cliente = LLMClient()
    try:
        t0 = time.perf_counter()
        resp = cliente.complete(
            agent="teleoperador",
            messages=[{"role": "user",
                       "content": "Hola, soy de Caballito, me robaron y quiero una alarma "
                                  "urgente. ¿Pueden venir esta semana? Mi teléfono 11-5555-1234."}],
            schema=TeleoperadorResponse,
        )
        dt = (time.perf_counter() - t0) * 1000
        print(_seguro(f"  {_verde('OK')} el modelo devolvió JSON válido en {dt:.0f} ms"))
        print(_seguro(f"     barrio     : {resp.barrio}"))
        print(f"     calificación: {resp.calificacion}")
        print(f"     dirección CABA: {resp.direccion_valida_caba}")
    except Exception as e:  # noqa: BLE001
        print(f"  {_rojo('FALLÓ')} el modelo no supo responder en el formato que los agentes")
        print(_seguro(f"     necesitan: {type(e).__name__}: {str(e)[:300]}"))
        print("     Prueba con otro modelo del catálogo (el más grande suele ir mejor).")
        return 1

    print(f"\n{_verde('TODO VERDE')}: el cerebro de AMD responde y habla nuestro idioma.")
    print(f"El panel AMD de la pantalla ahora va a mostrar latencia y tokens de verdad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
