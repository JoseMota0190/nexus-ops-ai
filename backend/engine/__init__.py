"""Motor de simulación (SIN LLM): negocio, agenda, técnicos y crecimiento.

Todo es reproducible: se configura con una semilla aleatoria. El LLM no es el
optimizador: calcula lo necesario el programa, la IA explica/decide.
"""
from .zones import ZONAS, distancia_aprox
from .clock import SimClock, velocidad
from .business import (
    Empresa, PRODUCTOS, META_TECNICOS, META_MES, DIAS_POR_SEMANA, SEMANAS_POR_MES,
    MESES_TOTALES, ventas_por_dia, tecnicos_necesarios, elegir_kit, Producto,
)
from .leads import Lead, generar_leads
from .technicians import Tecnico, asignar_visita, Visita, nuevos_tecnicos
from .montecarlo import simular_historial, ResumenHistorial
from .calls import DiaLlamadas, simular_dia_de_llamadas, MOTIVOS_NO_COMPRA
from .agenda import Cita, ResultadoAgenda, agendar_ventas, nombres_para_alta
from .enjambre import (
    Charla, agendar_semana_enjambre, agendar_venta_en_sala, negociar_venta,
    turnos_libres,
)
from .gerente import (
    reunion_mensual, ventas_objetivo_del_mes, tecnicos_objetivo_del_mes,
    ventas_potenciales, validar_decision,
)
from .simulation import Simulacion, mes_de_semana

__all__ = [
    "ZONAS", "distancia_aprox", "SimClock", "velocidad",
    "Lead", "generar_leads",
    "Tecnico", "asignar_visita", "Visita", "nuevos_tecnicos",
    "simular_historial", "ResumenHistorial",
    "Empresa", "PRODUCTOS", "META_TECNICOS", "META_MES",
    "DIAS_POR_SEMANA", "SEMANAS_POR_MES", "MESES_TOTALES",
    "ventas_por_dia", "tecnicos_necesarios", "elegir_kit", "Producto",
    "DiaLlamadas", "simular_dia_de_llamadas", "MOTIVOS_NO_COMPRA",
    "Cita", "ResultadoAgenda", "agendar_ventas", "nombres_para_alta",
    "Charla", "agendar_semana_enjambre", "agendar_venta_en_sala",
    "negociar_venta", "turnos_libres",
    "reunion_mensual", "ventas_objetivo_del_mes", "tecnicos_objetivo_del_mes",
    "ventas_potenciales", "validar_decision",
    "Simulacion", "mes_de_semana",
]
