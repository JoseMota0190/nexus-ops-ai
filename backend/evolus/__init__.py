"""Módulo Evolus: extractor de documentos + workflow de contratos.

Pieza **opcional y aislada** del proyecto nexus-ops-ai. Por defecto arranca
apagada y en MODO PRUEBA (mock): responde con datos locales, no toca la red y
nunca rompe la demo principal. Se prende desde `.env` (ver `EVOLUS.md`).

El router NO se conecta solo: lo engancha el dueño cuando quiera.
"""
from .client import EvolusClient, EvolusError, EvolusMetrics, get_metrics
from .config import EvolusConfig, get_config
from .extract import comparar, detectar_errores, evaluar_factura, evaluar_lote
from .facturas import cuit_valido, generar_factura, generar_facturas
from .mock import SELLO_SIMULADO
from .router import router
from .workflow import contrato_mock, ejecutar_contrato, texto_contrato_por_defecto

__all__ = [
    "EvolusConfig", "get_config", "SELLO_SIMULADO", "router",
    "generar_factura", "generar_facturas", "cuit_valido",
    "EvolusClient", "EvolusError", "EvolusMetrics", "get_metrics",
    "comparar", "detectar_errores", "evaluar_factura", "evaluar_lote",
    "ejecutar_contrato", "contrato_mock", "texto_contrato_por_defecto",
]
