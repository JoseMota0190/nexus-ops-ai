"""Diagnóstico de FACTURACIÓN: ¿detecta bien los errores inyectados?

Corre el generador Monte Carlo sobre una tanda grande de comprobantes y mide:

  1. Tasa de detección global (errores inyectados que el extractor encuentra).
  2. Tasa por tipo de defecto (¿hay alguno que se le escape?).
  3. Falsas alarmas: facturas IMPECABLES marcadas como defectuosas.
  4. Precisión de LECTURA en facturas limpias (debería ser 1.0).

Uso:  backend\\.venv\\Scripts\\python.exe backend\\tests\\verificar_facturacion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evolus.extract import detectar_errores, evaluar_factura  # noqa: E402
from evolus.facturas import PROBABILIDADES, generar_facturas  # noqa: E402

N = 5000
SEED = 7

facturas = generar_facturas(N, seed=SEED)

por_tipo = {t: {"esp": 0, "det": 0} for t in PROBABILIDADES}
tot_esp = tot_det = 0
con_defectos = limpios = 0
falsas_alarmas: list[str] = []
fallados: list[tuple[str, list[str]]] = []
enmascarados = 0
precision_limpias_min = 1.0

for f in facturas:
    doc = f["documento"]
    esp = {e["tipo"] for e in f["errores"]}
    det = {d["tipo"] for d in detectar_errores(doc)}
    # Campos que quedaron vacíos por "campo_faltante" (enmascara el valor inválido).
    vacios = {e["campo"] for e in f["errores"] if e["tipo"] == "campo_faltante"}

    if esp:
        con_defectos += 1
        tot_esp += len(esp)
        tot_det += len(esp & det)  # inyectados que SÍ se detectaron
        for t in esp:
            por_tipo[t]["esp"] += 1
            if t in det:
                por_tipo[t]["det"] += 1
        faltan = esp - det
        # Un valor inválido no se puede etiquetar si el campo quedó vacío:
        # el documento IGUAL se detecta como defectuoso (campo_faltante).
        reales = set()
        for t in faltan:
            campo = {"cuit_invalido": "cuit", "fecha_invalida": "fecha"}.get(t)
            if campo and campo in vacios:
                enmascarados += 1
            else:
                reales.add(t)
        if reales:
            fallados.append((f["id"], sorted(reales)))
    else:
        limpios += 1
        if det:
            falsas_alarmas.append(f["id"])
        precision_limpias_min = min(precision_limpias_min, evaluar_factura(f)["precision"])

print("=" * 64)
print(f"DIAGNOSTICO DE FACTURACION  (n={N}, seed={SEED})")
print("=" * 64)
print(f"  facturas con defectos inyectados : {con_defectos}")
print(f"  facturas impecables              : {limpios}")
print()
print(f"  errores inyectados               : {tot_esp}")
print(f"  errores detectados               : {tot_det}")
tasa = (tot_det / tot_esp) if tot_esp else 1.0
print(f"  TASA DE DETECCION                : {tasa * 100:.2f}%")
print()
print("  --- por tipo de defecto ---")
for t in sorted(por_tipo):
    e, d = por_tipo[t]["esp"], por_tipo[t]["det"]
    if e:
        print(f"    {t:<20} {d:>6}/{e:<6}  {d / e * 100:6.2f}%")
print()
print(f"  falsas alarmas (limpias marcadas): {len(falsas_alarmas)}")
print(f"  precision de lectura en limpias  : {precision_limpias_min}")
print(f"  valores invalidos enmascarados   : {enmascarados}")
print(f"    (casos donde el campo igual quedo vacio -> el comprobante se detecta")
print(f"     por 'campo_faltante', aunque no se pueda etiquetar el valor)")
print(f"  inyectados que se escaparon DE VERDAD: {len(fallados)}")

if fallados:
    print("\n  !! ESCAPADOS (primeros 10):")
    for fid, tipos in fallados[:10]:
        print(f"     {fid}: {tipos}")

verde = (not fallados and not falsas_alarmas and precision_limpias_min == 1.0)
print("\n" + ("TODO VERDE: detecta todo lo etiquetable, sin falsas alarmas." if verde
              else "REVISAR: hay algo que no cierra (ver arriba)."))
