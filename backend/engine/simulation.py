"""Simulación de los 9 meses: la orquestación de todo (Fases 2-6 y 8).

El ciclo de una semana (lunes a sábados):

    día → se ejecutan las instalaciones agendadas → llegan leads de la web →
    los teleoperadores llaman → se anota atendió/no + motivo → se arma la venta →
    al cerrar la semana se agendan las ventas para la SEMANA SIGUIENTE

Al cerrar el mes: ingresos recurrentes, costos de personal y la REUNIÓN MENSUAL
del Gerente IA. Todo queda guardado en SQLite (se puede parar y seguir).
"""
from __future__ import annotations

import random

from llm import LLMClient
from store import EmpresaRow, Store

from .agenda import agendar_ventas, nombres_para_alta, tecnicos_de, turnos_ocupados
from .business import (
    DIAS_POR_SEMANA,
    MESES_TOTALES,
    MANTENIMIENTO_ANUAL,
    MONITOREO_PROMEDIO,
    SALARIO_OPERADOR_MES,
    SALARIO_TECNICO_MES,
    SEMANAS_POR_MES,
    Empresa,
)
from .calls import costo_leads, simular_dia_de_llamadas
from .gerente import (
    reunion_mensual,
    tecnicos_objetivo_del_mes,
    ventas_objetivo_del_mes,
    ventas_potenciales,
)
from .leads import generar_leads

NOMBRES_OPERADORES = ["Mariana Ríos", "Pablo Cabrera", "Sofía Duarte",
                      "Esteban Vega", "Carla Sosa", "Iván Ayala", "Nadia Ledesma"]


def mes_de_semana(semana: int) -> int:
    return (semana - 1) // SEMANAS_POR_MES + 1


class Simulacion:
    """Corre la operación mes a mes, guardando cada paso en la base de datos."""

    def __init__(self, store: Store, llm: LLMClient, semilla: int = 42) -> None:
        self.store = store
        self.llm = llm
        self.semilla = semilla
        self.rng = random.Random(semilla)
        self.empresa = Empresa()

    # ------------------------------------------------------------- arranque
    def inicializar(self, reiniciar: bool = False) -> Empresa:
        if reiniciar:
            self.store.reset()
        guardada = self.store.cargar_empresa()
        if guardada is None:
            self.empresa = Empresa()
            self.store.crear_base(
                nombres_clientes=[],
                nombres_operadores=NOMBRES_OPERADORES[: self.empresa.operadores],
                tecnicos=nombres_para_alta(self.empresa.tecnicos),
                mes=1,
            )
            self._guardar()
        else:
            self.empresa = Empresa(
                mes=guardada.mes, semana=guardada.semana,
                dia_semana=guardada.dia_semana, operadores=guardada.operadores,
                tecnicos=guardada.tecnicos, mejoras=guardada.mejoras,
                clientes_activos=guardada.clientes_activos, caja=guardada.caja,
                ventas_totales=guardada.ventas_totales,
            )
        return self.empresa

    def _guardar(self) -> None:
        e = self.empresa
        self.store.guardar_empresa(EmpresaRow(
            mes=e.mes, semana=e.semana, dia_semana=e.dia_semana,
            operadores=e.operadores, tecnicos=e.tecnicos, mejoras=e.mejoras,
            clientes_activos=e.clientes_activos, caja=round(e.caja, 2),
            ventas_totales=e.ventas_totales))

    # ------------------------------------------------------------------ día
    def correr_dia(self) -> dict:
        e = self.empresa
        semana, dia = e.semana, e.dia_semana

        # 1) Instalaciones agendadas para HOY (semana 1 no tiene: arrancan en la 2).
        citas = self.store.instalaciones_de_dia(semana, dia)
        ingresos_instalaciones = 0.0
        for c in citas:
            venta = self.store.conn.execute(
                "SELECT monto_instalacion FROM ventas WHERE id = ?", (c["venta_id"],)
            ).fetchone()
            if venta:
                ingresos_instalaciones += float(venta["monto_instalacion"])
                e.clientes_activos += 1
                e.ventas_totales += 1

        # 2) Llegan leads del formulario web.
        leads = generar_leads(self.rng, dia=semana * DIAS_POR_SEMANA + dia,
                              mejoras=e.mejoras)
        ids = self.store.insertar_leads(leads, e.mes)
        por_id = {leads[i].id: ids[i] for i in range(len(leads))}

        # 3) Los teleoperadores llaman: el PROGRAMA resuelve todo el volumen.
        res = simular_dia_de_llamadas(leads, e, self.rng, semana, dia)

        # 4) Se anota el log (quién atendió, quién no, y el motivo).
        filas_llamadas = []
        for i, estado in enumerate(res.estados):
            lead = leads[i]
            filas_llamadas.append((
                por_id[lead.id], res.operador_de(i), e.mes, semana, dia,
                1 if estado != "perdido" else 0, res.motivo_de(i), None))
            if estado != "vendido":
                self.store.cambiar_estado_cliente(por_id[lead.id], estado)
        self.store.insertar_llamadas(filas_llamadas)

        # 5) Las ventas se cargan en la base.
        for v in res.ventas_lista:
            cliente_id = por_id[v.lead.id]
            venta_id = self.store.registrar_venta(
                cliente_id, e.mes, semana, dia, v.kit, v.accesorio,
                v.monto, v.plan, v.monitoreo)
            self.store.cambiar_estado_cliente(cliente_id, "vendido")
            self.store.conn.execute(
                "UPDATE llamadas SET venta_id = ? WHERE cliente_id = ? AND semana = ? AND dia = ?",
                (venta_id, cliente_id, semana, dia))
            self.store.conn.commit()

        # 6) Costos del día (cada lead que llega cuesta plata de marketing).
        costo = costo_leads(len(leads))
        e.caja += ingresos_instalaciones - costo
        ingresos_hoy = ingresos_instalaciones

        # 7) Al cerrar la semana, se agendan las ventas para la semana siguiente.
        agendadas = 0
        sin_capacidad = 0
        negociados = 0
        if dia == DIAS_POR_SEMANA - 1:
            agendadas, sin_capacidad, negociados = self._cerrar_semana(semana)
        else:
            # Es un indicador (backlog), no un acumulado: se mide al cerrar la semana.
            sin_capacidad = len(self.store.ventas_sin_cita())

        resumen = {
            "semana": semana, "dia": dia, "mes": e.mes,
            "leads": len(leads), "llamadas": res.llamadas,
            "atendidas": res.atendidas, "ventas": res.ventas,
            "instalaciones": len(citas), "sin_capacidad": sin_capacidad,
            "ingresos": round(ingresos_hoy, 2), "costos": round(costo, 2),
            "caja": round(e.caja, 2), "agendadas": agendadas,
            "turnos_negociados": negociados,
            "motivos_no_compra": res.motivos_no_compra,
            "motivos_no_respuesta": res.motivos_no_respuesta,
        }
        self.store.guardar_resumen_dia(
            mes=e.mes, semana=semana, dia=dia, leads=len(leads),
            llamadas=res.llamadas, atendidas=res.atendidas, ventas=res.ventas,
            instalaciones=len(citas), sin_capacidad=sin_capacidad,
            ingresos=round(ingresos_hoy, 2), costos=round(costo, 2),
            caja=round(e.caja, 2))

        # Avanza el reloj.
        if e.dia_semana < DIAS_POR_SEMANA - 1:
            e.dia_semana += 1
        else:
            e.dia_semana = 0
            e.semana += 1
        self._guardar()
        return resumen

    def _cerrar_semana(self, semana: int) -> tuple[int, int, int]:
        """Agenda todas las ventas pendientes para la SEMANA SIGUIENTE."""
        e = self.empresa
        pendientes = self.store.ventas_sin_cita()
        if not pendientes:
            return 0, 0, 0
        objetivo = semana + 1
        ocupados = turnos_ocupados(self.store, objetivo)
        ventas = [{"id": int(v["id"]), "cliente_id": int(v["cliente_id"]),
                   "barrio": v["barrio"]} for v in pendientes]
        tec = tecnicos_de(self.store)
        res = agendar_ventas(ventas, ocupados, tec, objetivo, self.rng)
        for c in res.agendadas:
            self.store.agendar_cita(
                c.venta_id, c.cliente_id, c.barrio, c.tecnico_id, c.semana,
                c.dia, c.turno, c.estado, c.mensaje)
            # Mensaje de confirmación (tipo WhatsApp) al cliente.
            self.store.mensaje("whatsapp_cliente", "Nexus Alarm",
                               f"cliente {c.cliente_id}", c.mensaje,
                               e.mes, c.semana, c.dia)
        return len(res.agendadas), res.sin_capacidad, res.turnos_negociados

    # ---------------------------------------------------------------- semana
    def correr_semana(self) -> list[dict]:
        dias = []
        for _ in range(DIAS_POR_SEMANA):
            dias.append(self.correr_dia())
        return dias

    # ------------------------------------------------------------------ mes
    def correr_mes(self) -> dict:
        e = self.empresa
        mes = e.mes
        if mes > MESES_TOTALES:
            return {"mes": mes, "completado": True}

        # Reunión mensual del Gerente IA (el programa calcula lo que falta;
        # la IA decide cómo llenarlo y escribe el acta).
        reunion = reunion_mensual(self.llm, self.store, e, mes, self.rng)
        self._guardar()

        inicio_semana = e.semana
        for _ in range(SEMANAS_POR_MES):
            if e.semana > (mes - 1) * SEMANAS_POR_MES + SEMANAS_POR_MES:
                break
            self.correr_semana()

        # Cierre del mes: ingresos recurrentes + costos de personal.
        ingreso_recurrente = round(
            e.clientes_activos * (MONITOREO_PROMEDIO + MANTENIMIENTO_ANUAL / 12), 2)
        costo_personal = round(
            e.operadores * SALARIO_OPERADOR_MES + e.tecnicos * SALARIO_TECNICO_MES, 2)
        e.caja += ingreso_recurrente - costo_personal

        filas = self.store.conn.execute(
            """SELECT COUNT(*) AS n, COALESCE(SUM(ingresos),0) AS ing,
                      COALESCE(SUM(costos),0) AS cost, COALESCE(SUM(llamadas),0) AS llam,
                      COALESCE(SUM(atendidas),0) AS ate, COALESCE(SUM(ventas),0) AS ven,
                      COALESCE(SUM(instalaciones),0) AS ins,
                      MAX(sin_capacidad) AS sc,
                      COALESCE(SUM(leads),0) AS leads
               FROM resumen_dia WHERE semana >= ? AND semana <= ?""",
            (inicio_semana, e.semana - 1)).fetchone()

        ingresos_inst = round(float(filas["ing"]), 2)
        costos_leads = round(float(filas["cost"]), 2)
        costos_total = round(costo_personal + costos_leads +
                             float(reunion["inversion"]), 2)

        self.store.guardar_resumen_mes(
            mes=mes, leads=int(filas["leads"]), llamadas=int(filas["llam"]),
            atendidas=int(filas["ate"]), ventas=int(filas["ven"]),
            instalaciones=int(filas["ins"]), sin_capacidad=int(filas["sc"]),
            operadores=e.operadores, tecnicos=e.tecnicos, mejoras=e.mejoras,
            ingresos_instalaciones=ingresos_inst,
            ingresos_recurrentes=ingreso_recurrente,
            costos_personal=costo_personal, costos_leads=costos_leads,
            costos_mejoras=round(float(reunion["inversion"]), 2),
            costos_total=costos_total, caja=round(e.caja, 2),
            clientes_activos=e.clientes_activos)

        # avanza al próximo mes
        e.mes += 1
        self._guardar()

        return {
            "mes": mes,
            "completado": False,
            "acta": reunion["acta"],
            "avisos": reunion["avisos"],
            "decisiones": [
                {"palanca": d.palanca.value, "cantidad": d.cantidad, "razon": d.razon}
                for d in reunion["decisiones"]],
            "numeros": {
                "leads": int(filas["leads"]), "llamadas": int(filas["llam"]),
                "atendidas": int(filas["ate"]), "ventas": int(filas["ven"]),
                "instalaciones": int(filas["ins"]),
                "sin_capacidad": int(filas["sc"]),
                "ventas_por_dia": round(int(filas["ven"]) / (SEMANAS_POR_MES * DIAS_POR_SEMANA), 1),
                "operadores": e.operadores, "tecnicos": e.tecnicos,
                "mejoras": e.mejoras, "caja": round(e.caja, 2),
                "clientes_activos": e.clientes_activos,
                "ingresos": round(ingresos_inst + ingreso_recurrente, 2),
                "costos": costos_total,
                "tasa_respuesta": round(100 * e.tasa_respuesta, 1),
                "tasa_cierre": round(100 * e.tasa_cierre, 1),
            },
            "objetivos": {
                "ventas_por_dia": round(ventas_objetivo_del_mes(mes), 1),
                "tecnicos": tecnicos_objetivo_del_mes(mes),
                "potencial_ventas": round(ventas_potenciales(e), 1),
                "meta_tecnicos": 10,
            },
        }

    def correr_todo(self, meses: int = MESES_TOTALES) -> list[dict]:
        salidas = []
        for _ in range(meses):
            if self.empresa.mes > MESES_TOTALES:
                break
            salidas.append(self.correr_mes())
        return salidas

    # ------------------------------------------------------------- snapshot
    def estado(self) -> dict:
        e = self.empresa
        kpis = self.store.kpis()
        return {
            "mes": e.mes, "semana": e.semana, "dia_semana": e.dia_semana,
            "operadores": e.operadores, "tecnicos": e.tecnicos,
            "mejoras": e.mejoras, "caja": round(e.caja, 2),
            "clientes_activos": e.clientes_activos,
            "ventas_totales": e.ventas_totales,
            "ventas_por_dia_potencial": round(ventas_potenciales(e), 1),
            "ventas_por_dia_objetivo": round(ventas_objetivo_del_mes(e.mes), 1),
            "tecnicos_objetivo": tecnicos_objetivo_del_mes(e.mes),
            "meta_tecnicos": 10,
            "tasa_respuesta": round(100 * e.tasa_respuesta, 1),
            "tasa_cierre": round(100 * e.tasa_cierre, 1),
            "llamadas_por_dia": e.llamadas_por_dia,
            "leads_por_dia": e.leads_por_dia,
            "capacidad_instalaciones": e.capacidad_instalaciones,
            "kpis": kpis,
        }
