"""Tests de la Sala de Agentes (el enjambre), en modo mock: sin red, deterministas.

Etapa 1: el VOCABULARIO del enjambre (esquemas) y las respuestas de prueba de
cada agente. Todavía NO se toca la simulación: acá solo verificamos que cada
agente devuelva el JSON correcto y que elija SIEMPRE una opción válida de las
que le pasa el motor (nunca inventa un turno ni un técnico).
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm import LLMClient
from llm.config import LLMConfig
from schemas import (TurnoOperador, TurnoTecnicos, CoordinacionResponse,
                     DespachoResponse)
from engine import Simulacion
from engine.enjambre import (agendar_semana_enjambre, turnos_libres,
                             _turno_valido, _tecnico_valido)
from store import Store


def _client() -> LLMClient:
    return LLMClient(config=LLMConfig(use_mock=True, model="mock"))


def _json(**kw) -> str:
    return json.dumps(kw, ensure_ascii=False)


def test_operador_propone_el_turno_que_prefiere_el_cliente():
    c = _client()
    resp = c.complete(
        agent="operador",
        messages=[{"role": "user", "content": _json(
            cliente="Gómez", barrio="Caballito", producto="kit Hogar Plus",
            preferencia={"dia": 3, "turno": "12pm"})}],
        schema=TurnoOperador,
    )
    assert isinstance(resp, TurnoOperador)
    assert resp.dia_preferido == 3
    assert resp.turno_preferido == "12pm"
    assert "Gómez" in resp.habla


def test_agenda_elige_el_turno_libre_que_pidio_el_cliente():
    c = _client()
    resp = c.complete(
        agent="agenda",
        messages=[{"role": "user", "content": _json(
            cliente="Gómez", barrio="Caballito", dia_preferido=3, turno_preferido="12pm",
            turnos_libres=[{"dia": 3, "turno": "9am"}, {"dia": 3, "turno": "12pm"},
                           {"dia": 4, "turno": "4pm"}])}],
        schema=CoordinacionResponse,
    )
    assert resp.dia == 3 and resp.turno_propuesto == "12pm"
    assert resp.cierra_acuerdo is True
    assert resp.texto_para_cliente


def test_agenda_nunca_inventa_un_turno_fuera_de_la_pizarra():
    c = _client()
    libres = [{"dia": 5, "turno": "4pm"}, {"dia": 2, "turno": "9am"}]
    resp = c.complete(
        agent="agenda",
        messages=[{"role": "user", "content": _json(
            cliente="Pérez", barrio="Flores", dia_preferido=1, turno_preferido="9am",
            turnos_libres=libres)}],
        schema=CoordinacionResponse,
    )
    # No está el martes 9am (su preferencia): elige de la lista, nunca la inventa.
    assert (resp.dia, resp.turno_propuesto) in {(5, "4pm"), (2, "9am")}


def test_tecnicos_elige_entre_los_candidatos():
    c = _client()
    resp = c.complete(
        agent="tecnicos",
        messages=[{"role": "user", "content": _json(
            barrio="Caballito", dia=3, turno="12pm",
            candidatos=[{"id": "TEC-02", "zona": "Caballito"},
                        {"id": "TEC-05", "zona": "Flores"}])}],
        schema=TurnoTecnicos,
    )
    assert resp.tecnico_id == "TEC-02"
    assert resp.explicacion
    assert "Caballito" in resp.habla


def test_despacho_sigue_andando_en_el_enjambre():
    c = _client()
    resp = c.complete(
        agent="despacho",
        messages=[{"role": "user", "content": _json(
            tipo="trafico", visita_id="V-77", tecnico_asignado="TEC-03")}],
        schema=DespachoResponse,
    )
    assert resp.tecnico_sugerido is not None
    assert resp.explicacion


def test_dialogo_completo_de_una_venta_es_coherente():
    """La charla entera: operador -> agenda -> tecnicos, encadenada."""
    c = _client()
    op = c.complete(agent="operador", messages=[{"role": "user", "content": _json(
        cliente="Ruiz", barrio="Belgrano", producto="kit Comercial",
        preferencia={"dia": 2, "turno": "4pm"})}], schema=TurnoOperador)

    ag = c.complete(agent="agenda", messages=[{"role": "user", "content": _json(
        cliente="Ruiz", barrio="Belgrano", dia_preferido=op.dia_preferido,
        turno_preferido=op.turno_preferido,
        turnos_libres=[{"dia": 2, "turno": "4pm"}, {"dia": 2, "turno": "9am"}])}],
        schema=CoordinacionResponse)

    te = c.complete(agent="tecnicos", messages=[{"role": "user", "content": _json(
        barrio="Belgrano", dia=ag.dia, turno=ag.turno_propuesto,
        candidatos=[{"id": "TEC-07", "zona": "Belgrano"}])}], schema=TurnoTecnicos)

    assert (ag.dia, ag.turno_propuesto) in {(2, "4pm"), (2, "9am")}
    assert te.tecnico_id == "TEC-07"


# ------------------------------------------------ el motor de la sala (Etapa 2)
def _nueva_venta(store, nombre: str, barrio: str, semana: int = 1) -> int:
    """Cliente + venta de prueba (barrio real de CABA para el reparto por zona)."""
    cur = store.conn.execute(
        "INSERT INTO clientes (nombre, telefono, barrio, tipo, mes) VALUES (?, ?, ?, ?, ?)",
        (nombre, "11-5555-0000", barrio, "residencial", 1))
    cid = int(cur.lastrowid)
    vid = store.registrar_venta(cid, 1, semana, 0, "hogar_basico", None,
                                180.0, "basico", 15.0)
    store.conn.commit()
    return vid


def test_turnos_libres_excluye_los_ocupados():
    tecnicos = [{"id": 1, "zona": "Palermo"}]
    opciones = turnos_libres(tecnicos, {(1, 0, "9am")}, "Palermo")
    assert opciones, "tiene que quedar lugar"
    assert (0, "9am") not in [(o["dia"], o["turno"]) for o in opciones]


def test_el_programa_arbitra_si_la_ia_inventa_un_turno():
    opciones = [
        {"dia": 0, "turno": "9am", "candidatos": [{"id": 1, "zona": "Palermo"}]},
        {"dia": 1, "turno": "12pm", "candidatos": [{"id": 2, "zona": "Flores"}]},
    ]
    inventado = CoordinacionResponse(turno_propuesto="4pm", dia=4,
                                     cierra_acuerdo=False, texto_para_cliente="hola",
                                     nota_interna="...")
    elegido = _turno_valido(inventado, opciones, {"dia": 1, "turno": "12pm"})
    assert (elegido["dia"], elegido["turno"]) == (1, "12pm")


def test_el_programa_arbitra_si_la_ia_inventa_un_tecnico():
    candidatos = [{"id": 3, "zona": "Palermo"}, {"id": 5, "zona": "Belgrano"}]
    elegido = _tecnico_valido(TurnoTecnicos(habla="x", tecnico_id="99"), candidatos)
    assert elegido == 3


def test_la_sala_agenda_todas_las_ventas_sin_pisar_turnos():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulacion(Store(Path(tmp) / "t.db"), _client(), semilla=7)
        sim.inicializar(reiniciar=True)
        for i in range(5):
            _nueva_venta(sim.store, f"Cliente {i}", "Palermo")

        res, charlas = agendar_semana_enjambre(sim.llm, sim.store, 1, sim.rng)

        assert len(res.agendadas) == 5
        assert res.sin_capacidad == 0
        assert len(charlas) == 5
        # Ningún (técnico, día, turno) se repite.
        slots = [(c.tecnico_id, c.dia, c.turno) for c in res.agendadas]
        assert len(set(slots)) == len(slots)
        # Cada venta pasó por las 3 voces y todas dijeron algo.
        for ch in charlas:
            assert [l["agente"] for l in ch.lineas] == ["operador", "agenda", "tecnicos"]
            assert all(l["dice"] for l in ch.lineas)
        sim.store.close()


def test_el_enjambre_nunca_supera_la_capacidad():
    """Con 2 técnicos hay 36 turnos por semana: 40 ventas dejan 4 sin capacidad."""
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulacion(Store(Path(tmp) / "t.db"), _client(), semilla=3)
        sim.inicializar(reiniciar=True)
        for i in range(40):
            _nueva_venta(sim.store, f"Cliente {i}", "Belgrano")

        res, _ = agendar_semana_enjambre(sim.llm, sim.store, 1, sim.rng)
        assert len(res.agendadas) == 36
        assert res.sin_capacidad == 4
        sim.store.close()


def test_cada_venta_se_negocia_en_el_dia_modo_sala():
    """En modo sala, las ventas se negocian al cerrarse y la charla sale en el día."""
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulacion(Store(Path(tmp) / "t.db"), _client(), semilla=11)
        sim.inicializar(reiniciar=True)
        sim.enjambre_desde = 1
        sim.modo_sala = True
        total = 0
        for _ in range(6):
            dia = sim.correr_dia()
            assert isinstance(dia["sala"], list)
            for ch in dia["sala"]:
                assert [l["agente"] for l in ch["lineas"]] == ["operador", "agenda", "tecnicos"]
            total += len(dia["sala"])
        assert total > 0, "tiene que haber negociado al menos una venta"
        sim.store.close()


def test_modo_rapido_no_negocia_nada():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulacion(Store(Path(tmp) / "t.db"), _client(), semilla=11)
        sim.inicializar(reiniciar=True)
        sim.enjambre_desde = 1
        sim.modo_sala = False  # interruptor en "rápido"
        dias = [sim.correr_dia() for _ in range(6)]
        assert all(len(d["sala"]) == 0 for d in dias)
        sim.store.close()


if __name__ == "__main__":
    test_operador_propone_el_turno_que_prefiere_el_cliente()
    test_agenda_elige_el_turno_libre_que_pidio_el_cliente()
    test_agenda_nunca_inventa_un_turno_fuera_de_la_pizarra()
    test_tecnicos_elige_entre_los_candidatos()
    test_despacho_sigue_andando_en_el_enjambre()
    test_dialogo_completo_de_una_venta_es_coherente()
    test_turnos_libres_excluye_los_ocupados()
    test_el_programa_arbitra_si_la_ia_inventa_un_turno()
    test_el_programa_arbitra_si_la_ia_inventa_un_tecnico()
    test_la_sala_agenda_todas_las_ventas_sin_pisar_turnos()
    test_el_enjambre_nunca_supera_la_capacidad()
    test_cada_venta_se_negocia_en_el_dia_modo_sala()
    test_modo_rapido_no_negocia_nada()
    print("OK: tests de la Sala de Agentes (enjambre) pasaron.")
