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
from .enjambre import agendar_semana_enjambre, agendar_venta_en_sala
from .gerente import (
    reunion_mensual,
    tecnicos_objetivo_del_mes,
    ventas_objetivo_del_mes,
    ventas_potenciales,
)
from .leads import generar_leads

NOMBRES_OPERADORES = ["Mariana Ríos", "Pablo Cabrera", "Sofía Duarte",
                      "Esteban Vega", "Carla Sosa", "Iván Ayala", "Nadia Ledesma"]

# Cuántos eventos entran en la "película" del día que reproduce la pantalla.
# Con 3 operadores hay ~150 llamadas/día; con este tope la lista queda liviana
# (máx. ~200 eventos ≈ 40 KB) y la película dura lo mismo siempre.
_TOPE_PELICULA = 120


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
        # Desde qué mes opera el ENJAMBRE (los agentes negocian la agenda). None =
        # nunca. Se prende en la API a partir del mes 7: los primeros 6 meses
        # quedan precargados con el algoritmo rápido.
        self.enjambre_desde: int | None = None
        # Interruptor "modo sala" (con charla) vs "modo rápido" (sin charla).
        self.modo_sala: bool = True
        self._sala_dia: list[dict] = []  # las charlas del día

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

    def _enjambre_on(self) -> bool:
        """¿Los agentes negocian la agenda ahora mismo?"""
        return (self.modo_sala and self.enjambre_desde is not None
                and self.empresa.mes >= self.enjambre_desde)

    def _agendar_en_sala(self, venta_id: int, cliente_id: int, barrio: str,
                         semana: int, dia: int) -> None:
        """Los agentes negocian ESTA venta para la semana que viene, ahí mismo.

        Repartir la negociación (una venta por vez, al cerrarse) evita que todo
        caiga junto el sábado: el trabajo queda parejo a lo largo de la semana.
        """
        cita, charla = agendar_venta_en_sala(
            self.llm, self.store,
            {"id": venta_id, "cliente_id": cliente_id, "barrio": barrio},
            semana + 1, self.rng)
        if cita is None:
            return  # sin capacidad: queda pendiente (es la señal para contratar)
        self.store.agendar_cita(cita.venta_id, cita.cliente_id, cita.barrio,
                                cita.tecnico_id, cita.semana, cita.dia, cita.turno,
                                cita.estado, cita.mensaje)
        e = self.empresa
        self.store.mensaje("whatsapp_cliente", "Nexus Alarm",
                           f"cliente {cita.cliente_id}", cita.mensaje, e.mes, semana, dia)
        for linea in charla.lineas:
            self.store.mensaje("sala_agentes", linea["agente"], charla.cliente,
                               linea["dice"], e.mes, semana, dia)
        self._sala_dia.append(self._charla_dict(charla))
        self._agendadas_dia += 1
        if charla.negociado:
            self._negociados_dia += 1

    @staticmethod
    def _charla_dict(ch) -> dict:
        return {"venta_id": ch.venta_id, "cliente": ch.cliente, "barrio": ch.barrio,
                "dia": ch.dia, "turno": ch.turno, "hora": ch.hora,
                "tecnico_id": ch.tecnico_id, "negociado": ch.negociado,
                "lineas": ch.lineas}

    # ------------------------------------------------------------------ día
    def correr_dia(self) -> dict:
        """Un día de operación entero, guardado en la base de UN SOLO golpe.

        (Agruparlo hace que el arranque pase de 25 s a ~1 s; ver Store.transaction.)
        """
        with self.store.transaction():
            return self._correr_dia()

    def _correr_dia(self) -> dict:
        e = self.empresa
        semana, dia = e.semana, e.dia_semana
        self._sala_dia = []  # se llena con las charlas de las ventas de hoy
        self._agendadas_dia = 0  # ventas que los agentes agendaron hoy en la sala
        self._negociados_dia = 0  # de esas, cuántas con un turno distinto al pedido

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

        # 5) Las ventas se cargan en la base. En modo sala, cada venta se negocia
        #    EN EL MOMENTO: teleoperador -> coordinador de agenda -> técnicos.
        for v in res.ventas_lista:
            cliente_id = por_id[v.lead.id]
            venta_id = self.store.registrar_venta(
                cliente_id, e.mes, semana, dia, v.kit, v.accesorio,
                v.monto, v.plan, v.monitoreo)
            self.store.cambiar_estado_cliente(cliente_id, "vendido")
            self.store.conn.execute(
                "UPDATE llamadas SET venta_id = ? WHERE cliente_id = ? AND semana = ? AND dia = ?",
                (venta_id, cliente_id, semana, dia))
            if self._enjambre_on():
                self._agendar_en_sala(venta_id, cliente_id, v.lead.barrio, semana, dia)

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
            "caja": round(e.caja, 2), "agendadas": agendadas + self._agendadas_dia,
            "turnos_negociados": negociados + self._negociados_dia,
            "motivos_no_compra": res.motivos_no_compra,
            "motivos_no_respuesta": res.motivos_no_respuesta,
            # El "guion" del día: lo que la pantalla reproduce a cámara lenta
            # para que el juez vea la operación pasando llamada por llamada.
            "pelicula": self._pelicula_del_dia(leads, res, citas),
            # La charla del enjambre de hoy (vacía en modo rápido).
            "sala": self._sala_dia,
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
        """Cierra la semana: agenda lo que haya quedado pendiente (el algoritmo).

        En modo SALA, las ventas de la semana ya se fueron negociando de a una al
        cerrarse; acá sólo se rescata el backlog viejo que quedó sin capacidad.
        En modo RÁPIDO, acá se agenda todo junto.
        """
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

    def _pelicula_del_dia(self, leads, res, citas) -> dict:
        """Guion del día para que la pantalla lo reproduzca a cámara lenta.

        No cambia la simulación: es solo el RELATO de lo que ya pasó, ordenado
        por minuto (jornada de 8:00 a 18:00). La instalación va en su turno real
        (9am / 12pm / 4pm) y las llamadas se reparten entre esas horas, para que
        el dueño vea la operación respirando en vez de un número que salta.
        """
        inicio, fin = 30, 570           # 8:30 → 17:30, en minutos desde las 8:00
        minuto_turno = {"9am": 60, "12pm": 240, "4pm": 480}
        eventos: list[dict] = []

        # Las instalaciones de hoy, en su hora.
        for c in citas:
            fila = self.store.conn.execute(
                "SELECT nombre FROM clientes WHERE id = ?", (c["cliente_id"],)).fetchone()
            eventos.append({
                "tipo": "instalacion", "minuto": minuto_turno.get(str(c["turno"]), 300),
                "cliente": fila["nombre"] if fila else "Cliente",
                "barrio": c["barrio"], "turno": c["turno"],
            })

        # Las llamadas, en el orden en que se hicieron a lo largo del día.
        n = min(len(res.estados), _TOPE_PELICULA)
        for i in range(n):
            lead = leads[i]
            op = res.operador_de(i)
            eventos.append({
                "tipo": "llamada",
                "minuto": inicio + (fin - inicio) * i // max(1, n - 1),
                "cliente": lead.nombre, "barrio": lead.barrio,
                "telefono": lead.telefono,
                "operador": NOMBRES_OPERADORES[(op - 1) % len(NOMBRES_OPERADORES)],
                "atendio": res.estados[i] != "perdido",
                "motivo": res.motivo_de(i),
                "venta": res.estados[i] == "vendido",
            })

        # La SALA DE AGENTES: cada voz entra justo después de que se cierra la venta.
        minuto_venta = {ev["cliente"]: ev["minuto"] for ev in eventos
                        if ev["tipo"] == "llamada" and ev.get("venta")}
        for ch in self._sala_dia:
            base = minuto_venta.get(ch["cliente"], fin - 20)
            for k, linea in enumerate(ch["lineas"]):
                eventos.append({
                    "tipo": "charla", "minuto": base + k, "agente": linea["agente"],
                    "dice": linea["dice"], "cliente": ch["cliente"], "barrio": ch["barrio"],
                })

        _orden = {"instalacion": 0, "llamada": 1, "charla": 2}
        eventos.sort(key=lambda ev: (ev["minuto"], _orden.get(ev["tipo"], 1)))
        return {"hora_inicio": 8 * 60, "hora_fin": 18 * 60, "eventos": eventos}

    # ---------------------------------------------------------------- semana
    def correr_semana(self) -> list[dict]:
        dias = []
        for _ in range(DIAS_POR_SEMANA):
            dias.append(self.correr_dia())
        return dias

    # ------------------------------------------------------------------ mes
    def correr_mes(self) -> dict:
        """Corre un mes entero. Sin tope: pasada la meta, la empresa se estabiliza
        (el Gerente deja de contratar sin control) y sigue operando."""
        e = self.empresa
        mes = e.mes

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
        for _ in range(max(0, meses)):
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
            "enjambre": {
                "activo": self._enjambre_on(),
                "desde_mes": self.enjambre_desde,
                "modo_sala": self.modo_sala,
            },
            "kpis": kpis,
        }
