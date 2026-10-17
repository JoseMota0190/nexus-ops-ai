"""Workflow de contratos: se dispara el trámite y se sigue su estado.

Idea (en criollo): mandamos el contrato a la plataforma, que nos da un número
de trámite (`executionId`), y después preguntamos "¿ya está?" cada un rato
hasta que responde terminado. Es como mandar un trámite a una ventanilla y
volver a preguntar hasta que salga.

Reglas del proyecto:
- Máx. 2 reintentos y timeout (los maneja el cliente).
- Si Evolus falla → se simula el trámite en modo prueba y **queda anotado**.
- En modo prueba NUNCA se toca la red.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable

from .client import EvolusClient, EvolusError
from .mock import SELLO_SIMULADO

_log = logging.getLogger("nexus.evolus")

ESTADOS = ("Pending", "Running", "Completed", "Failed")
ESTADOS_FINALES = ("Completed", "Failed")

# Cuánto esperamos entre preguntas y cuántas veces preguntamos como máximo.
INTERVALO_S = 1.0
MAX_CONSULTAS = 20

# Plantilla del contrato simulado (cuando no se pasa un texto propio).
CONTRATO_PLANTILLA = """CONTRATO DE INSTALACIÓN Y MONITOREO — NEXUS ALARM (SIMULADO)
Cliente: {cliente}
Domicilio de instalación: {domicilio}
Kit contratado: {kit}
Monitoreo mensual: USD {monitoreo}
Vigencia: 12 meses desde la fecha de firma.
{sello}
"""


def texto_contrato_por_defecto(seed: int = 42) -> str:
    """Arma un texto de contrato simulado para la demo."""
    rng = random.Random(seed)
    from .facturas import CLIENTES

    cliente = rng.choice(CLIENTES)["razon_social"]
    kit = rng.choice(["Hogar Básico", "Hogar Plus", "Comercial"])
    return CONTRATO_PLANTILLA.format(
        cliente=cliente,
        domicilio="Av. Corrientes 1234, CABA",
        kit=kit,
        monitoreo=rng.choice([15, 25]),
        sello=SELLO_SIMULADO,
    )


def _cliente_del_texto(texto: str) -> str | None:
    for linea in texto.splitlines():
        if linea.lower().startswith("cliente:"):
            return linea.split(":", 1)[1].strip() or None
    return None


def contrato_mock(texto: str, seed: int = 42) -> dict[str, Any]:
    """Simula un trámite de contrato COMPLETO, sin tocar la red.

    Determinista: misma entrada (y misma semilla) → mismo resultado.
    """
    rng = random.Random(seed)
    numero = f"CT-{rng.randint(1000, 9999)}"
    monitoreo = rng.choice([15, 25])
    return {
        "estado": "Completed",
        "jobId": f"job-{numero}",
        "executionId": f"exec-{numero}",
        "pasos": ["Pending", "Running", "Completed"],
        "consultas": 2,
        "resultado": {
            "contrato": numero,
            "cliente": _cliente_del_texto(texto),
            "firmado": False,  # se firma fuera de línea; acá solo se procesa
            "kit": rng.choice(["Hogar Básico", "Hogar Plus", "Comercial"]),
            "monitoreo_mensual_usd": monitoreo,
            "clausulas": rng.randint(6, 12),
            "moneda": "USD",
        },
        "mock": True,
        "fallback": False,
        "nota": "Modo prueba: simulé el trámite del contrato sin tocar la red.",
        "sello": SELLO_SIMULADO,
    }


def _esperar_estado(cliente: EvolusClient, workflow_id: str, execution_id: str,
                    intervalo_s: float, max_consultas: int,
                    dormir: Callable[[float], None]) -> tuple[str, list[str], dict[str, Any]]:
    """Pregunta el estado del trámite hasta que termina (o se agota)."""
    url = f"{cliente.config.api_base}/workflows/{workflow_id}/executions/{execution_id}"
    pasos: list[str] = []
    ultimo: dict[str, Any] = {}
    for i in range(max_consultas):
        ultimo = cliente.get_json(url)
        estado = ultimo.get("status", "Running")
        pasos.append(estado)
        if estado in ESTADOS_FINALES:
            return estado, pasos, ultimo
        if i < max_consultas - 1:
            dormir(intervalo_s)
    return "Running", pasos, ultimo


def ejecutar_contrato(texto: str | None = None, *,
                      client: EvolusClient | None = None,
                      seed: int = 42,
                      intervalo_s: float = INTERVALO_S,
                      max_consultas: int = MAX_CONSULTAS,
                      dormir: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """Dispara el workflow de contrato y devuelve el resultado final.

    Nunca rompe: si Evolus real falla, cae al modo prueba y lo anota.
    """
    cliente = client or EvolusClient()
    texto = texto or texto_contrato_por_defecto(seed)
    t0 = time.perf_counter()

    try:
        cliente.validar()
    except EvolusError:
        raise

    if cliente.config.mock:
        salida = contrato_mock(texto, seed)
        cliente._record("contrato", ok=True, mock=True, fallback=False, t0=t0,
                        nota=cliente.config.motivo_mock)
        return salida

    workflow_id = cliente.config.workflow_id
    if not workflow_id:
        # Prendido pero sin workflow configurado: no mandamos un pedido roto.
        raise EvolusError(
            "EVOLUS_ENABLED=true pero falta EVOLUS_WORKFLOW_ID: creá y encendé el "
            "workflow en la UI de Evolus y poné su id en .env."
        )

    try:
        url = f"{cliente.config.api_base}/workflows/{workflow_id}/execute"
        files = {"file": ("contrato.txt", texto.encode("utf-8"), "text/plain")}
        data = {"input": texto, "parameters": "{}"}
        respuesta = cliente.post_multipart(url, data, files)
        execution_id = respuesta.get("executionId") or respuesta.get("jobId")
        if not execution_id:
            raise EvolusError(f"Evolus no devolvió executionId: {respuesta}")
        estado, pasos, ultimo = _esperar_estado(
            cliente, workflow_id, execution_id, intervalo_s, max_consultas, dormir)
        cliente._record("contrato", ok=estado == "Completed", mock=False,
                        fallback=False, t0=t0, nota=f"estado final: {estado}")
        return {
            "estado": estado,
            "jobId": respuesta.get("jobId"),
            "executionId": execution_id,
            "pasos": pasos,
            "consultas": len(pasos),
            "resultado": ultimo.get("output", ultimo),
            "mock": False,
            "fallback": False,
            "nota": "",
            "sello": SELLO_SIMULADO,
        }
    except EvolusError as e:
        _log.warning("Evolus no respondió (%s) -> trámite simulado", e)
        salida = contrato_mock(texto, seed)
        salida["fallback"] = True
        salida["nota"] = (f"Evolus no respondió ({e}); simulé el trámite y quedó anotado.")
        cliente._record("contrato", ok=False, mock=True, fallback=True, t0=t0,
                        nota=str(e))
        return salida
