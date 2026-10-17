"""Tests del motor determinista: negocio, leads, agenda, gerente y simulación."""
import contextlib
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import LLMClient
from llm.config import LLMConfig

from engine import (
    velocidad, SimClock, generar_leads, asignar_visita, nuevos_tecnicos,
    simular_historial, ZONAS, distancia_aprox, Empresa, Simulacion,
    ventas_por_dia, tecnicos_necesarios, tecnicos_objetivo_del_mes,
    ventas_objetivo_del_mes, ventas_potenciales, agendar_ventas,
    reunion_mensual, mes_de_semana,
)
from engine.business import DIAS_POR_SEMANA, META_TECNICOS, SEMANAS_POR_MES, capacidad_tecnico_dia
from engine.agenda import turnos_ocupados, tecnicos_de
from engine.zones import zona_por_nombre
from store import Store


def _llm() -> LLMClient:
    return LLMClient(config=LLMConfig(use_mock=True, model="mock"))


def _sim(tmp: str, semilla: int = 7) -> Simulacion:
    sim = Simulacion(Store(Path(tmp) / "t.db"), _llm(), semilla=semilla)
    sim.inicializar(reiniciar=True)
    return sim


@contextlib.contextmanager
def _sim_en(tmp: str, semilla: int = 7):
    """Simulación en un directorio temporal, cerrando la base al salir."""
    sim = _sim(tmp, semilla)
    try:
        yield sim
    finally:
        sim.store.close()


# --------------------------------------------------------------- reloj / zonas
def test_velocidad_x120():
    assert velocidad(480, 240) == 120.0


def test_reloj_avanza_y_termina():
    c = SimClock(minutos_por_jornada=480)
    assert c.hora_label == "08:00"
    c.avanzar(480)
    assert c.terminada
    assert c.hora_label == "16:00"


def test_distancia_simetrica():
    p = zona_por_nombre("Palermo")
    b = zona_por_nombre("Belgrano")
    assert abs(distancia_aprox(p, b) - distancia_aprox(b, p)) < 1e-6


# ---------------------------------------------------------- negocio decidido
def test_arranque_2_tecnicos_3_operadores():
    e = Empresa()
    assert e.operadores == 3
    assert e.tecnicos == 2
    # Cada teleoperador vende 2/día => 6 ventas/día en total.
    assert ventas_por_dia(e.operadores) == 6
    # 50 llamadas por operador => 150/día.
    assert e.llamadas_por_dia == 150


def test_tecnicos_necesarios_para_meta():
    # 1 técnico = 3 ventas/día (3 turnos x 6 días / 6 ventas por día).
    assert tecnicos_necesarios(6) == 2
    assert tecnicos_necesarios(30) == META_TECNICOS


def test_hoja_de_ruta_6_a_30_ventas():
    assert ventas_objetivo_del_mes(1) == 6.0
    assert ventas_objetivo_del_mes(9) == 30.0
    assert tecnicos_objetivo_del_mes(1) == 2
    assert tecnicos_objetivo_del_mes(9) == META_TECNICOS


def test_arranque_hace_6_ventas_dia():
    e = Empresa()
    assert round(ventas_potenciales(e), 1) == 6.3   # ~6 ventas/día, ~20 atienden
    assert e.tasa_respuesta == 0.14
    assert round(e.llamadas_por_dia * e.tasa_respuesta) == 21


# ----------------------------------------------------------------- leads
def test_leads_deterministas_con_misma_semilla():
    a = generar_leads(random.Random(7), dia=1)
    b = generar_leads(random.Random(7), dia=1)
    assert [l.id for l in a] == [l.id for l in b]
    assert [l.barrio for l in a] == [l.barrio for l in b]
    assert all(a[i].minuto_llegada <= a[i + 1].minuto_llegada for i in range(len(a) - 1))


def test_leads_en_rango_volumen():
    leads = generar_leads(random.Random(3), dia=2, mejoras=0)
    assert len(leads) == 180
    leads4 = generar_leads(random.Random(3), dia=2, mejoras=4)
    assert len(leads4) > len(leads)


def test_leads_tienen_telefono_y_origen_web():
    lead = generar_leads(random.Random(5), dia=1)[0]
    assert lead.telefono.startswith("+54 9 11")
    assert lead.origen == "web"
    assert not hasattr(lead, "en_no_llamar")   # se eliminó: todos piden ser llamados


# ------------------------------------------------------------------ técnicos
def test_asignacion_respeta_capacidad():
    leads = generar_leads(random.Random(11), dia=5)
    tecnicos = nuevos_tecnicos(10)
    asignadas = 0
    for lead in leads[:120]:
        if random.Random(hash(lead.id) % 10000).random() < 0.4:
            _, vis = asignar_visita(lead, tecnicos, visitas_por_tecnico=3)
            if vis is not None:
                asignadas += 1
    assert all(t.visitas_hoy <= 3 for t in tecnicos)
    assert asignadas > 0


# -------------------------------------------------------------------- agenda
def test_agenda_llena_capacidad_sin_excederla():
    ventas = [{"id": i, "cliente_id": i, "barrio": ZONAS[i % len(ZONAS)].nombre}
              for i in range(40)]
    tecnicos = [{"id": 1, "zona": "Palermo"}, {"id": 2, "zona": "Flores"}]
    ocupados = set()
    res = agendar_ventas(ventas, ocupados, tecnicos, semana_objetivo=2,
                         rng=random.Random(3))
    # La capacidad del día fluctúa (2, 3 o 4 por técnico): se agenda hasta llenarla.
    cap_total = sum(capacidad_tecnico_dia(t["id"], (2 - 1) * DIAS_POR_SEMANA + d)
                    for t in tecnicos for d in range(DIAS_POR_SEMANA))
    assert len(res.agendadas) <= cap_total
    assert len(ocupados) == len(res.agendadas)
    # Nunca más instalaciones que la capacidad de ese técnico en ese día.
    por_tecnico_dia: dict[tuple, int] = {}
    for (t, d, _turno) in ocupados:
        por_tecnico_dia[(t, d)] = por_tecnico_dia.get((t, d), 0) + 1
    for (t, d), n in por_tecnico_dia.items():
        assert n <= capacidad_tecnico_dia(t, (2 - 1) * DIAS_POR_SEMANA + d)


def test_la_capacidad_diaria_del_tecnico_fluctua_2_3_4_promedio_3():
    valores = [capacidad_tecnico_dia(t, d) for t in range(1, 9) for d in range(120)]
    assert set(valores) <= {2, 3, 4}
    assert 2.7 <= sum(valores) / len(valores) <= 3.3
    # Estable: mismo técnico + mismo día => mismo número (reparto y ejecución coinciden).
    assert capacidad_tecnico_dia(3, 40) == capacidad_tecnico_dia(3, 40)


def test_agenda_sin_tecnicos_marca_sin_capacidad():
    ventas = [{"id": 1, "cliente_id": 1, "barrio": "Palermo"}]
    res = agendar_ventas(ventas, set(), [], semana_objetivo=2, rng=random.Random(1))
    assert res.sin_capacidad == 1


# ------------------------------------------------------------------- gerente
def test_gerente_valida_decision_imposible():
    from schemas import DecisionGerente
    from engine.gerente import validar_decision
    e = Empresa(tecnicos=10)
    d = DecisionGerente(palanca="contratar_tecnicos", cantidad=1,
                        razon="por las dudas")
    v = validar_decision(d, e, 1_000_000.0, mes=1)
    assert v.ok is False          # la venta no justifica más manos
    assert "no justifica" in v.motivo


def test_gerente_llega_a_10_tecnicos_en_9_meses():
    with tempfile.TemporaryDirectory() as td:
        with _sim_en(td) as sim:
            for mes in range(1, 10):
                out = sim.correr_mes()
                assert out["mes"] == mes
            assert sim.empresa.tecnicos == META_TECNICOS
            assert sim.empresa.ventas_totales > 0
            actas = sim.store.conn.execute(
                "SELECT COUNT(*) FROM actas_gerente").fetchone()[0]
            assert actas == 9


# --------------------------------------------------------------- simulación
def test_un_dia_guarda_todo_en_sqlite():
    with tempfile.TemporaryDirectory() as td:
        with _sim_en(td) as sim:
            r = sim.correr_dia()
            assert r["leads"] > 0
            assert r["llamadas"] > 0
            assert 0 <= r["atendidas"] <= r["llamadas"]
            assert sim.store.contar("clientes") > 0
            assert sim.store.contar("llamadas") == r["llamadas"]


def test_semana_agenda_para_la_siguiente():
    with tempfile.TemporaryDirectory() as td:
        with _sim_en(td) as sim:
            sim.correr_semana()
            # Semana 1: no hay instalaciones (los técnicos arrancan en la semana 2)
            assert sim.store.contar("citas") > 0
            citas = sim.store.conn.execute(
                "SELECT DISTINCT semana FROM citas").fetchall()
            assert all(int(c["semana"]) == 2 for c in citas)
            assert sim.empresa.semana == 2


def test_dia_a_dia_cierra_el_mes_solo():
    """El modo día a día (sin botón "Avanzar 1 mes") cierra el mes solo: reunión
    del Gerente al abrir, informe de los 4 sectores e ingresos recurrentes al cerrar."""
    with tempfile.TemporaryDirectory() as td:
        with _sim_en(td) as sim:
            sim.reportes_con_ia = False  # redactor local: sin red, rápido
            cerrado = None
            for _ in range(SEMANAS_POR_MES * DIAS_POR_SEMANA):
                r = sim.correr_dia_completo()
                if r.get("mes_cerrado"):
                    cerrado = r
            assert cerrado is not None
            assert cerrado["mes_cerrado_numero"] == 1
            # Avanzó al mes 2 y el resumen del mes quedó guardado.
            assert sim.empresa.mes == 2
            fila = sim.store.conn.execute(
                "SELECT ventas FROM resumen_mes WHERE mes = 1").fetchone()
            assert fila is not None and fila["ventas"] > 0
            # Los 4 sectores sacaron su informe del mes 1.
            sectores = sim.store.conn.execute(
                "SELECT COUNT(DISTINCT sector) AS n FROM reportes_sector WHERE mes = 1"
            ).fetchone()["n"]
            assert sectores == 4
            # La reunión del Gerente dejó su acta del mes (prueba de que corrió).
            assert sim.store.conn.execute(
                "SELECT COUNT(*) FROM actas_gerente WHERE mes = 1").fetchone()[0] == 1


def test_reiniciar_no_pierde_determinismo():
    with tempfile.TemporaryDirectory() as td:
        a = _sim(td, semilla=11)
        b = _sim(td + "/otro", semilla=11)
        try:
            for _ in range(3):
                a.correr_dia()
                b.correr_dia()
            assert a.empresa.caja == b.empresa.caja
            assert a.store.contar("llamadas") == b.store.contar("llamadas")
        finally:
            a.store.close()
            b.store.close()


def test_montecarlo_9_meses():
    h = simular_historial(dias=9 * SEMANAS_POR_MES * DIAS_POR_SEMANA, semilla=42)
    assert len(h.dias) == 9 * SEMANAS_POR_MES * DIAS_POR_SEMANA
    assert h.total_leads > 0
    assert h.total_visitas > 0
    meses = h.por_mes()
    assert len(meses) >= 8  # ~9 meses
    for d in h.dias[:50]:
        assert 0 <= d.conversion_pct <= 100


def test_mes_de_semana():
    assert mes_de_semana(1) == 1
    assert mes_de_semana(4) == 1
    assert mes_de_semana(5) == 2
    assert mes_de_semana(36) == 9


if __name__ == "__main__":
    test_velocidad_x120()
    test_reloj_avanza_y_termina()
    test_distancia_simetrica()
    test_arranque_2_tecnicos_3_operadores()
    test_tecnicos_necesarios_para_meta()
    test_hoja_de_ruta_6_a_30_ventas()
    test_arranque_hace_6_ventas_dia()
    test_leads_deterministas_con_misma_semilla()
    test_leads_en_rango_volumen()
    test_leads_tienen_telefono_y_origen_web()
    test_asignacion_respeta_capacidad()
    test_agenda_llena_capacidad_sin_excederla()
    test_la_capacidad_diaria_del_tecnico_fluctua_2_3_4_promedio_3()
    test_agenda_sin_tecnicos_marca_sin_capacidad()
    test_gerente_valida_decision_imposible()
    test_un_dia_guarda_todo_en_sqlite()
    test_semana_agenda_para_la_siguiente()
    test_reiniciar_no_pierde_determinismo()
    test_mes_de_semana()
    test_montecarlo_9_meses()
    test_gerente_llega_a_10_tecnicos_en_9_meses()
    print("OK: 20 tests del motor pasaron.")
