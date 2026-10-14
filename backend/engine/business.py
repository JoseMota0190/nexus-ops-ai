"""Modelo de negocio de Nexus Alarm (decidido con el autor, ver AGENTS.md §3).

Todo lo que es "cuánto cuesta, cuánto se vende y cuánto gana la gente" vive acá.
No hay números mágicos repartidos por el código: si algo hay que cambiar, se
cambia en este archivo.

Reglas del modelo (cerradas):
- Arranque: 2 TÉCNICOS + 3 TELEOPERADORES.
- Cada teleoperador vende 2/día => 6 VENTAS/DÍA en total.
- Cada teleoperador llama 50/día => 150 llamadas/día (fluctúa).
- De las llamadas ~20 atienden en total; de ahí salen las ventas.
- Ventas se agendan para la SEMANA SIGUIENTE => los técnicos arrancan en semana 2.
- Lunes a sábados. Cada técnico: 3 instalaciones/día (9am, 12pm, 4pm).
- Meta: 10 técnicos trabajando el mes 9 => hacen falta 30 ventas/día.
- El gerente usa DOS palancas juntas: contrata operadores Y los vuelve más
  eficientes => los costos crecen MÁS LENTO que las ventas.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------- productos
# Precios en USD (empresa ficticia, simulada).
PRODUCTOS: dict[str, tuple[str, float]] = {
    "hogar_basico": ("Kit Hogar Básico", 180.0),
    "hogar_plus": ("Kit Hogar Plus", 320.0),
    "comercial": ("Kit Comercial", 550.0),
    "sensor_inundacion": ("Sensor de inundación", 40.0),
    "extensor_zona": ("Extensor de zona", 25.0),
}

# Monitoreo mensual según tipo de plan (ingreso recurrente por cliente activo).
MONITOREO_MENSUAL: dict[str, float] = {"basico": 15.0, "plus": 25.0}
# Promedio ponderado por la mezcla de ventas (45/38/17). Para el P&L mensual.
MONITOREO_PROMEDIO = 20.0
# Mantenimiento anual => se reparte en 12 meses para el P&L mensual.
MANTENIMIENTO_ANUAL = 60.0

# Mezcla de venta: cada venta lleva un kit + accesorios opcionales.
KIT_PRINCIPAL = ("hogar_basico", "hogar_plus", "comercial")
KIT_PESOS = (0.45, 0.38, 0.17)          # pesos de la mezcla
ACCESORIO_PESO = 0.35                    # 35% de las ventas llevan un accesorio

# ------------------------------------------------------------ estructura
OPERADORES_INICIALES = 3
TECNICOS_INICIALES = 2
LLAMADAS_POR_OPERADOR_DIA = 50       # 50 llamadas/día por operador
VENTAS_POR_OPERADOR_DIA = 2          # => 6 ventas/día con 3 operadores
DIAS_POR_SEMANA = 6                  # lunes a sábado
SEMANAS_POR_MES = 4                  # => 9 meses = 36 semanas = 216 días hábiles
MESES_TOTALES = 9
# Los primeros 6 meses corren solos al arrancar; los 3 últimos los mueve el dueño
# con el botón "Avanzar 1 mes" (decisión cerrada con el autor).
MESES_AUTOMATICOS = 6
INSTALACIONES_POR_TECNICO_DIA = 3    # 9am / 12pm / 4pm
TURNO_MANANA = "9am"
TURNO_MEDIO = "12pm"
TURNO_TARDE = "4pm"
TURNOS_DIA = (TURNO_MANANA, TURNO_MEDIO, TURNO_TARDE)
TURNO_HORA = {"9am": "09:00", "12pm": "12:00", "4pm": "16:00"}
DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado")

# Probabilidad de que el cliente no pueda en el turno propuesto (se le ofrece otro).
PROB_NO_PUEDE = 0.12
MAX_INTENTOS_TURNO = 3

# ------------------------------------------------------------- costos
SALARIO_OPERADOR_MES = 700.0
SALARIO_TECNICO_MES = 900.0
# Costo por lead que llega del formulario web (marketing/base de contactos).
COSTO_POR_LEAD = 1.2
# Costo de aplicar UNA mejora de base de datos + servicio (paga el gerente).
COSTO_POR_MEJORA = 900.0

# ------------------------------------------------------- estado inicial
MEJORAS_INICIALES = 0
CAJA_INICIAL = 0.0

# Meta del dueño (VISIBLE en la demo).
META_TECNICOS = 10
META_MES = 9


def ventas_por_dia(operadores: int) -> int:
    """Ventas esperadas al día con N operadores (2 c/u)."""
    return operadores * VENTAS_POR_OPERADOR_DIA


def capacidad_instalaciones_dia(tecnicos: int) -> int:
    """Cuántas instalaciones por día puede hacer el equipo de técnicos."""
    return tecnicos * INSTALACIONES_POR_TECNICO_DIA


def tecnicos_necesarios(ventas_por_dia_objetivo: float) -> int:
    """Técnicos necesarios para cubrir N ventas/día (lunes a sábado).

    Ventas/día * 6 días  ==  técnicos * 3 instalaciones/día * 6 días
    =>  técnicos == ventas/día / 3
    """
    return max(1, int(round(ventas_por_dia_objetivo / INSTALACIONES_POR_TECNICO_DIA)))


def tecnicos_para_meta() -> int:
    """Técnicos que hacen falta para llegar a 10 (meta del dueño)."""
    return tecnicos_necesarios(ventas_por_dia(META_TECNICOS // VENTAS_POR_OPERADOR_DIA))


# -------------------------------------------------------------- tasas
# Las tasas dependen de las mejoras que aplicó el gerente. Sin mejoras: arranque.
def tasa_respuesta(mejoras: int) -> float:
    """Proporción de llamadas que contestan. Mejora la BASE DE DATOS.

    Con 150 llamadas, 0.14 => ~21 atienden (el "~20 atienden" del modelo).
    """
    return min(0.34, 0.14 + 0.02 * mejoras)


def tasa_cierre(mejoras: int) -> float:
    """Proporción de las atendidas que compran. Mejora el SERVICIO."""
    return min(0.58, 0.30 + 0.03 * mejoras)


def leads_por_dia(mejoras: int) -> int:
    """Leads que entran por el formulario web. Mejora la BASE DE DATOS."""
    return 180 + 40 * mejoras


def llamadas_posibles(operadores: int) -> int:
    """Llamadas que se pueden hacer con N operadores (50 c/u)."""
    return operadores * LLAMADAS_POR_OPERADOR_DIA


# --------------------------------------------------------------- empresa
class Producto:
    """Acceso a precios de producto sin repetir el diccionario por el código."""

    @staticmethod
    def precio(nombre: str | None) -> float:
        if not nombre:
            return 0.0
        return PRODUCTOS[nombre][1]

    @staticmethod
    def etiqueta(nombre: str | None) -> str:
        if not nombre:
            return ""
        return PRODUCTOS[nombre][0]

    @staticmethod
    def monitoreo(plan: str) -> float:
        return MONITOREO_MENSUAL.get(plan, MONITOREO_MENSUAL["basico"])


def elegir_kit(rng) -> str:
    """Mezcla de ventas: 45% Hogar Básico, 38% Plus, 17% Comercial."""
    import random
    return rng.choices(list(KIT_PRINCIPAL), weights=list(KIT_PESOS), k=1)[0]


@dataclass
class Empresa:
    """Estado actual de Nexus Alarm (lo que se guarda en SQLite)."""
    mes: int = 1
    semana: int = 1
    dia_semana: int = 0            # 0 = lunes .. 5 = sábado
    operadores: int = OPERADORES_INICIALES
    tecnicos: int = TECNICOS_INICIALES
    mejoras: int = MEJORAS_INICIALES
    clientes_activos: int = 0      # pagan monitoreo
    caja: float = CAJA_INICIAL
    ventas_totales: int = 0
    # histórico para los gráficos
    historial_meses: list[dict] = field(default_factory=list)

    # -------------------------------------------------------- derivados
    @property
    def llamadas_por_dia(self) -> int:
        return llamadas_posibles(self.operadores)

    @property
    def ventas_por_dia_objetivo(self) -> int:
        return ventas_por_dia(self.operadores)

    @property
    def capacidad_instalaciones(self) -> int:
        return capacidad_instalaciones_dia(self.tecnicos)

    @property
    def tasa_respuesta(self) -> float:
        return tasa_respuesta(self.mejoras)

    @property
    def tasa_cierre(self) -> float:
        return tasa_cierre(self.mejoras)

    @property
    def leads_por_dia(self) -> int:
        return leads_por_dia(self.mejoras)

    @property
    def meta_cumplida(self) -> bool:
        return self.tecnicos >= META_TECNICOS

    def clone(self) -> "Empresa":
        return replace(self, historial_meses=list(self.historial_meses))
