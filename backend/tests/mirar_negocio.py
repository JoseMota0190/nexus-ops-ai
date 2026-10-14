"""Inspección rápida: ¿cierra la historia de negocio de 9 meses?"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import LLMClient
from llm.config import LLMConfig
from engine import Simulacion
from store import Store

print(f"{'Mes':>3} {'Vent/día':>8} {'Obj':>5} {'Ops':>4} {'Tec':>4} {'Mej':>4} "
      f"{'Llam':>5} {'Resp%':>6} {'Cierre%':>7} {'Ingresos':>10} {'Costos':>9} {'Caja':>10}")

with tempfile.TemporaryDirectory() as td:
    sim = Simulacion(Store(Path(td) / "nexus.db"),
                     LLMClient(config=LLMConfig(use_mock=True, model="mock")), semilla=42)
    sim.inicializar(reiniciar=True)
    for mes in range(1, 10):
        out = sim.correr_mes()
        n, o = out["numeros"], out["objetivos"]
        print(f"{mes:>3} {n['ventas_por_dia']:>8.1f} {o['ventas_por_dia']:>5.1f} "
              f"{n['operadores']:>4} {n['tecnicos']:>4} {n['mejoras']:>4} "
              f"{n['llamadas']:>5} {n['tasa_respuesta']:>6.1f} {n['tasa_cierre']:>7.1f} "
              f"{n['ingresos']:>10.0f} {n['costos']:>9.0f} {n['caja']:>10.0f}")

    filas = sim.store.resumenes_mes()
    i1, i9 = filas[0], filas[-1]
    vr = i9["ingresos_instalaciones"] / i1["ingresos_instalaciones"]
    cr = i9["costos_total"] / i1["costos_total"]
    print()
    print(f"Ventas (ingreso por instalación) mes 1 -> mes 9: x{vr:.1f}")
    print(f"Costos totales mes 1 -> mes 9:                  x{cr:.1f}")
    print("OK: los costos crecen MÁS LENTO que las ventas." if cr < vr else "PROBLEMA: costos crecen más rápido.")
    print(f"Técnicos finales: {sim.empresa.tecnicos} (meta 10)")
    sim.store.close()
