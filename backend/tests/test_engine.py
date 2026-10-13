"""Tests del motor determinista: reloj, leads, asignación y Monte Carlo."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import (
    velocidad, SimClock, generar_leads, LeadsConfig,
    asignar_visita, nuevos_tecnicos, simular_historial, ZONAS, distancia_aprox,
)
from engine.zones import zona_por_nombre


def test_velocidad_x120():
    # 8 h (480 min = 28800 s) en 240 s => x120
    assert velocidad(480, 240) == 120.0


def test_reloj_avanza_y_termina():
    c = SimClock(minutos_por_jornada=480)
    assert c.hora_label == "08:00"
    c.avanzar(480)
    assert c.terminada
    assert c.hora_label == "16:00"


def test_leads_deterministas_con_misma_semilla():
    cfg = LeadsConfig()
    a = generar_leads(cfg, random.Random(7), dia=1)
    b = generar_leads(cfg, random.Random(7), dia=1)
    assert [l.id for l in a] == [l.id for l in b]
    assert [l.barrio for l in a] == [l.barrio for l in b]
    # ordenados por minuto de llegada
    assert all(a[i].minuto_llegada <= a[i + 1].minuto_llegada for i in range(len(a) - 1))


def test_leads_en_rango_volumen():
    cfg = LeadsConfig(leads_por_dia_min=200, leads_por_dia_max=250)
    leads = generar_leads(cfg, random.Random(3), dia=2)
    assert 200 <= len(leads) <= 250


def test_asignacion_respeta_capacidad():
    cfg = LeadsConfig(leads_por_dia_min=150, leads_por_dia_max=150)
    leads = generar_leads(cfg, random.Random(11), dia=5)
    tecnicos = nuevos_tecnicos(10)
    asignadas = 0
    for lead in leads:
        if lead.en_no_llamar:
            continue
        if random.Random(hash(lead.id) % 10000).random() < 0.2:
            tec, vis = asignar_visita(lead, tecnicos, visitas_por_tecnico=3)
            if vis is not None:
                asignadas += 1
    # Nadie debe superar 3 visitas.
    assert all(t.visitas_hoy <= 3 for t in tecnicos)


def test_distancia_simetrica():
    p = zona_por_nombre("Palermo")
    b = zona_por_nombre("Belgrano")
    assert abs(distancia_aprox(p, b) - distancia_aprox(b, p)) < 1e-6


def test_montecarlo_9_meses():
    h = simular_historial(dias=270, semilla=42)
    assert len(h.dias) == 270
    assert h.total_leads > 0
    assert h.total_visitas > 0
    meses = h.por_mes()
    assert len(meses) >= 8  # ~9 meses
    # Conversión diaria en rango plausible
    for d in h.dias[:50]:
        assert 0 <= d.conversion_pct <= 100


if __name__ == "__main__":
    test_velocidad_x120()
    test_reloj_avanza_y_termina()
    test_leads_deterministas_con_misma_semilla()
    test_leads_en_rango_volumen()
    test_asignacion_respeta_capacidad()
    test_distancia_simetrica()
    test_montecarlo_9_meses()
    print("OK: 7 tests del motor pasaron.")
