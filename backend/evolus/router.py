"""Rutas HTTP del módulo Evolus (AISLADO del resto).

IMPORTANTE: este router **NO se importa en `api.py`**. Queda deliberadamente
separado para que el simulador principal nunca dependa de Evolus. El dueño lo
conecta cuando quiera, agregando dos líneas (están escritas en `EVOLUS.md`,
sección "Cómo conectar").

Las puertas que expone (se van sumando por fase):

    GET  /api/evolus/salud      estado del módulo (¿prendido? ¿modo prueba?)
    POST /api/evolus/facturas   comprobantes simulados con errores inyectados
    POST /api/evolus/extraer    precisión de extracción (esperado vs. obtenido)
    POST /api/evolus/contratos  dispara el workflow de contrato
    GET  /api/evolus/metricas   agregados de extracción
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from . import extract as _extract
from . import facturas as _facturas
from . import mock as _mock
from . import workflow as _workflow
from .client import EvolusError, get_metrics
from .config import get_config

router = APIRouter(prefix="/api/evolus", tags=["evolus"])


class FacturasRequest(BaseModel):
    """Cuántos comprobantes simulados generar y con qué semilla."""

    n: int = Field(default=1, ge=1, le=50,
                   description="Cuántos comprobantes generar (1 a 50).")
    seed: int = Field(default=42,
                      description="Semilla: la misma semilla da las mismas facturas.")


class ExtraerRequest(BaseModel):
    """Compara lo que se esperaba contra lo que se obtuvo del documento."""

    esperado: dict[str, Any] = Field(description="Datos correctos (referencia).")
    obtenido: dict[str, Any] = Field(description="Datos que salieron del documento.")


class ContratoRequest(BaseModel):
    """Dispara el trámite de contrato (el texto es opcional)."""

    texto: str = Field(default="", description="Texto del contrato (opcional).")
    seed: int = Field(default=42, description="Semilla para el modo prueba.")


@router.get("/salud")
def salud() -> dict:
    """Estado del módulo. Nunca toca la red."""
    cfg = get_config()
    return {
        "enabled": cfg.enabled,
        "mock": cfg.mock,
        "base_url": cfg.api_base,
        "tiene_clave": cfg.tiene_clave,
        **_mock.salud_mock(cfg),
    }


@router.post("/facturas")
def facturas(req: FacturasRequest) -> dict:
    """Comprobantes SIMULADOS con errores inyectados (Monte Carlo).

    Es 100% local y determinista: no toca la red ni gasta créditos de Evolus.
    """
    generadas = _facturas.generar_facturas(req.n, req.seed)
    return {
        "n": req.n,
        "seed": req.seed,
        "sello": _mock.SELLO_SIMULADO,
        "facturas": generadas,
    }


@router.post("/extraer")
def extraer(req: ExtraerRequest) -> dict:
    """Compara `esperado` vs. `obtenido` y detecta defectos en el documento.

    Es 100% local: no toca la red.
    """
    comp = _extract.comparar(req.esperado, req.obtenido)
    return {
        "esperado": req.esperado,
        "obtenido": req.obtenido,
        "precision": comp["precision"],
        "coincidencias": comp["coincidencias"],
        "total_campos": comp["total_campos"],
        "por_campo": comp["por_campo"],
        "errores_detectados": _extract.detectar_errores(req.obtenido),
    }


@router.post("/contratos")
def contratos(req: ContratoRequest) -> dict:
    """Dispara el workflow de contrato y devuelve el resultado final.

    En modo prueba (apagado o sin clave) simula el trámite sin tocar la red.
    """
    try:
        return _workflow.ejecutar_contrato(req.texto or None, seed=req.seed)
    except EvolusError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/metricas")
def metricas(n: int = Query(default=100, ge=1, le=1000,
                            description="Sobre cuántas facturas medir."),
             seed: int = Query(default=42, description="Semilla de la tanda.")) -> dict:
    """Agregados de extracción: precisión, defectos detectados/fallados.

    Es 100% local (modo prueba): no toca la red ni gasta créditos.
    """
    resumen = _extract.evaluar_lote(n, seed)
    resumen["cliente"] = get_metrics().summary()
    return resumen
