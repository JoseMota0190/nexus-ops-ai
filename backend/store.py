"""Base de datos real (SQLite) de Nexus Alarm.

Es la "agenda de contactos" y el libro mayor del negocio: clientes, llamadas,
ventas, citas, técnicos, resúmenes por día/mes y las decisiones del Gerente IA.
Todo lo que corre la simulación queda acá, así se puede parar y seguir después.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent / "data" / "nexus.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS empresa (
  id                INTEGER PRIMARY KEY CHECK (id = 1),
  mes               INTEGER NOT NULL,
  semana            INTEGER NOT NULL,
  dia_semana        INTEGER NOT NULL,
  operadores        INTEGER NOT NULL,
  tecnicos          INTEGER NOT NULL,
  mejoras           INTEGER NOT NULL,
  clientes_activos  INTEGER NOT NULL,
  caja              REAL    NOT NULL,
  ventas_totales    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS clientes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre      TEXT NOT NULL,
  telefono    TEXT NOT NULL,
  barrio      TEXT NOT NULL,
  tipo        TEXT NOT NULL,
  origen      TEXT NOT NULL DEFAULT 'web',
  estado      TEXT NOT NULL DEFAULT 'nuevo',
  mes         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS operadores (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre  TEXT NOT NULL,
  activo  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tecnicos (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre    TEXT NOT NULL,
  zona_base TEXT NOT NULL,
  activo    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS llamadas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id  INTEGER NOT NULL REFERENCES clientes(id),
  operador_id INTEGER NOT NULL,
  mes         INTEGER NOT NULL,
  semana      INTEGER NOT NULL,
  dia         INTEGER NOT NULL,
  atendio     INTEGER NOT NULL,
  motivo      TEXT    NOT NULL DEFAULT '',
  venta_id    INTEGER
);

CREATE TABLE IF NOT EXISTS ventas (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id        INTEGER NOT NULL REFERENCES clientes(id),
  mes               INTEGER NOT NULL,
  semana            INTEGER NOT NULL,
  dia               INTEGER NOT NULL,
  kit               TEXT NOT NULL,
  accesorio         TEXT,
  monto_instalacion REAL NOT NULL,
  plan              TEXT NOT NULL,
  monitoreo_mensual REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS citas (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  venta_id     INTEGER NOT NULL REFERENCES ventas(id),
  cliente_id   INTEGER NOT NULL REFERENCES clientes(id),
  barrio       TEXT NOT NULL,
  tecnico_id   INTEGER,
  semana       INTEGER NOT NULL,
  dia          INTEGER NOT NULL,
  turno        TEXT NOT NULL,
  estado       TEXT NOT NULL DEFAULT 'confirmada',
  mensaje      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS resumen_dia (
  mes INTEGER NOT NULL, semana INTEGER NOT NULL, dia INTEGER NOT NULL,
  leads INTEGER, llamadas INTEGER, atendidas INTEGER, ventas INTEGER,
  instalaciones INTEGER, sin_capacidad INTEGER,
  ingresos REAL, costos REAL, caja REAL,
  PRIMARY KEY (mes, semana, dia)
);

CREATE TABLE IF NOT EXISTS resumen_mes (
  mes INTEGER PRIMARY KEY,
  leads INTEGER, llamadas INTEGER, atendidas INTEGER, ventas INTEGER,
  instalaciones INTEGER, sin_capacidad INTEGER,
  operadores INTEGER, tecnicos INTEGER, mejoras INTEGER,
  ingresos_instalaciones REAL, ingresos_recurrentes REAL,
  costos_personal REAL, costos_leads REAL, costos_mejoras REAL,
  costos_total REAL, caja REAL, clientes_activos INTEGER
);

CREATE TABLE IF NOT EXISTS decisiones_gerente (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  mes         INTEGER NOT NULL,
  accion      TEXT NOT NULL,
  valor       TEXT NOT NULL,
  motivo      TEXT NOT NULL,
  aprobada    INTEGER NOT NULL,
  aviso       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mensajes (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo         TEXT NOT NULL,
  remitente    TEXT NOT NULL,
  destinatario TEXT NOT NULL,
  texto        TEXT NOT NULL,
  mes          INTEGER NOT NULL,
  semana       INTEGER NOT NULL,
  dia          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS actas_gerente (
  mes     INTEGER PRIMARY KEY,
  titulo  TEXT NOT NULL,
  cuerpo  TEXT NOT NULL,
  meta    TEXT NOT NULL
);
"""


@dataclass
class EmpresaRow:
    mes: int
    semana: int
    dia_semana: int
    operadores: int
    tecnicos: int
    mejoras: int
    clientes_activos: int
    caja: float
    ventas_totales: int


class Store:
    """Acceso a la base de datos. Un solo objeto, un solo archivo .db."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI atiende cada petición en un hilo distinto.
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        # Si dos hilos tocan la base a la vez (el día en vivo + la pantalla
        # consultando), que el segundo ESPERE en vez de tirar error.
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._tx = 0  # profundidad de la transacción abierta (ver transaction())

    # ------------------------------------------------------------ helpers
    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self):
        """Agrupa muchos escritos en UN SOLO guardado al disco.

        Guardar cada escritura por separado cuesta ~0.35 ms en Windows (fsync);
        con 6.000 escrituras por mes eso eran 25 segundos de arranque.
        Adentro de este bloque no se guarda nada hasta el final.
        """
        self._tx += 1
        try:
            yield
        except BaseException:
            if self._tx == 1:
                self.conn.rollback()
            raise
        finally:
            self._tx -= 1
        if self._tx == 0:
            self.conn.commit()

    def commit_ahora(self) -> None:
        """Guarda YA lo escrito, aunque estemos dentro de una transacción.

        Se usa en el DÍA EN VIVO: la charla de la Sala de Agentes tiene que verse
        en la pantalla mientras el día sigue corriendo, no recién al final. Es un
        commit parcial (el de cierre se hace igual); si el día se cortara, queda
        lo negociado hasta ahí, que es mejor que nada.
        """
        self.conn.commit()

    def _exec(self, sql: str, params: Iterable[Any] | dict = ()) -> sqlite3.Cursor:
        if isinstance(params, dict):
            cur = self.conn.execute(sql, params)
        else:
            cur = self.conn.execute(sql, tuple(params))
        if self._tx == 0:
            self.conn.commit()
        return cur

    def reset(self) -> None:
        """Borra todas las tablas y rehace el esquema (para reiniciar la demo)."""
        for tabla in ("mensajes", "actas_gerente", "decisiones_gerente",
                      "resumen_mes", "resumen_dia", "citas", "ventas",
                      "llamadas", "clientes", "tecnicos", "operadores", "empresa"):
            self._exec(f"DROP TABLE IF EXISTS {tabla}")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ----------------------------------------------------------- empresa
    def guardar_empresa(self, e: EmpresaRow) -> None:
        self._exec(
            """INSERT INTO empresa (id, mes, semana, dia_semana, operadores, tecnicos,
                   mejoras, clientes_activos, caja, ventas_totales)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 mes=excluded.mes, semana=excluded.semana, dia_semana=excluded.dia_semana,
                 operadores=excluded.operadores, tecnicos=excluded.tecnicos,
                 mejoras=excluded.mejoras, clientes_activos=excluded.clientes_activos,
                 caja=excluded.caja, ventas_totales=excluded.ventas_totales""",
            (e.mes, e.semana, e.dia_semana, e.operadores, e.tecnicos,
             e.mejoras, e.clientes_activos, e.caja, e.ventas_totales))

    def cargar_empresa(self) -> EmpresaRow | None:
        row = self.conn.execute(
            "SELECT mes, semana, dia_semana, operadores, tecnicos, mejoras, "
            "clientes_activos, caja, ventas_totales FROM empresa WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return EmpresaRow(**dict(row))

    # ---------------------------------------------------------- personas
    def crear_base(self, nombres_clientes: list[tuple], nombres_operadores: list[str],
                   tecnicos: list[tuple[str, str]], mes: int = 1) -> None:
        self.conn.executemany(
            "INSERT INTO operadores (nombre) VALUES (?)",
            [(n,) for n in nombres_operadores])
        self.conn.executemany(
            "INSERT INTO tecnicos (nombre, zona_base) VALUES (?, ?)",
            tecnicos)
        self.conn.executemany(
            "INSERT INTO clientes (nombre, telefono, barrio, tipo, mes) VALUES (?, ?, ?, ?, ?)",
            [(n, t, b, ti, mes) for (n, t, b, ti) in nombres_clientes])
        self.conn.commit()

    def alta_operadores(self, n: int, nombres: list[str]) -> None:
        self.conn.executemany("INSERT INTO operadores (nombre) VALUES (?)",
                              [(nombres[i % len(nombres)],) for i in range(n)])
        self.conn.commit()

    def alta_tecnicos(self, n: int, nombres: list[str], zonas: list[str]) -> None:
        self.conn.executemany(
            "INSERT INTO tecnicos (nombre, zona_base) VALUES (?, ?)",
            [(nombres[i % len(nombres)], zonas[i % len(zonas)]) for i in range(n)])
        self.conn.commit()

    def contar(self, tabla: str, donde: str = "1=1", params: Iterable[Any] = ()) -> int:
        cur = self.conn.execute(f"SELECT COUNT(*) FROM {tabla} WHERE {donde}", tuple(params))
        return int(cur.fetchone()[0])

    # ---------------------------------------------------------- llamadas
    def registrar_llamada(self, cliente_id: int, operador_id: int, mes: int,
                          semana: int, dia: int, atendio: bool, motivo: str,
                          venta_id: int | None = None) -> int:
        cur = self._exec(
            """INSERT INTO llamadas (cliente_id, operador_id, mes, semana, dia,
                   atendio, motivo, venta_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cliente_id, operador_id, mes, semana, dia, int(atendio), motivo, venta_id))
        return int(cur.lastrowid)

    def cambiar_estado_cliente(self, cliente_id: int, estado: str) -> None:
        self._exec("UPDATE clientes SET estado = ? WHERE id = ?", (estado, cliente_id))

    def clientes_nuevos(self, limite: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM clientes WHERE estado = 'nuevo' ORDER BY id LIMIT ?",
            (limite,)).fetchall()

    # ------------------------------------------------------------ ventas
    def registrar_venta(self, cliente_id: int, mes: int, semana: int, dia: int,
                        kit: str, accesorio: str | None, monto: float,
                        plan: str, monitoreo: float) -> int:
        cur = self._exec(
            """INSERT INTO ventas (cliente_id, mes, semana, dia, kit, accesorio,
                   monto_instalacion, plan, monitoreo_mensual)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cliente_id, mes, semana, dia, kit, accesorio, monto, plan, monitoreo))
        return int(cur.lastrowid)

    def ventas_de_semana(self, semana: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT v.*, c.barrio, c.nombre FROM ventas v "
            "JOIN clientes c ON c.id = v.cliente_id WHERE v.semana = ? ORDER BY v.id",
            (semana,)).fetchall()

    def ventas_sin_cita(self) -> list[sqlite3.Row]:
        """Ventas todavía sin turno asignado (incluye el backlog de semanas anteriores)."""
        return self.conn.execute(
            "SELECT v.*, c.barrio, c.nombre FROM ventas v "
            "JOIN clientes c ON c.id = v.cliente_id "
            "WHERE v.id NOT IN (SELECT venta_id FROM citas) ORDER BY v.id").fetchall()

    def instalaciones_de_dia(self, semana: int, dia: int) -> list[sqlite3.Row]:
        """Citas que se ejecutan hoy (misma semana y mismo día)."""
        return self.conn.execute(
            "SELECT * FROM citas WHERE semana = ? AND dia = ? AND estado = 'confirmada'",
            (semana, dia)).fetchall()

    def insertar_leads(self, leads: list, mes: int) -> list[int]:
        """Guarda los leads del día en la base de datos (la agenda real)."""
        if not leads:
            return []
        self.conn.executemany(
            "INSERT INTO clientes (nombre, telefono, barrio, tipo, mes) VALUES (?, ?, ?, ?, ?)",
            [(l.nombre, l.telefono, l.barrio, l.tipo, mes) for l in leads])
        self.conn.commit()
        cur = self.conn.execute(
            "SELECT id FROM clientes ORDER BY id DESC LIMIT ?", (len(leads),))
        ids = [int(r["id"]) for r in cur.fetchall()]
        return list(reversed(ids))

    def insertar_llamadas(self, filas: list[tuple]) -> None:
        """Bulk: (cliente_id, operador_id, mes, semana, dia, atendio, motivo, venta_id)."""
        if not filas:
            return
        self.conn.executemany(
            """INSERT INTO llamadas (cliente_id, operador_id, mes, semana, dia,
                   atendio, motivo, venta_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", filas)
        self.conn.commit()

    # ------------------------------------------------------------- citas
    def agendar_cita(self, venta_id: int, cliente_id: int, barrio: str,
                     tecnico_id: int | None, semana: int, dia: int, turno: str,
                     estado: str, mensaje: str) -> int:
        cur = self._exec(
            """INSERT INTO citas (venta_id, cliente_id, barrio, tecnico_id, semana,
                   dia, turno, estado, mensaje) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (venta_id, cliente_id, barrio, tecnico_id, semana, dia, turno, estado, mensaje))
        return int(cur.lastrowid)

    def citas_de_semana(self, semana: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM citas WHERE semana = ? AND estado = 'confirmada' ORDER BY dia, turno",
            (semana,)).fetchall()

    def slots_ocupados(self, semana: int) -> set[tuple[int, int, str]]:
        """(técnico, día, turno) ya ocupados en la semana dada."""
        rows = self.conn.execute(
            "SELECT tecnico_id, dia, turno FROM citas "
            "WHERE semana = ? AND estado = 'confirmada'", (semana,)).fetchall()
        return {(int(r["tecnico_id"]), int(r["dia"]), str(r["turno"])) for r in rows
                if r["tecnico_id"] is not None}

    # --------------------------------------------------------- resúmenes
    def guardar_resumen_dia(self, **kw: Any) -> None:
        self._exec(
            """INSERT INTO resumen_dia (mes, semana, dia, leads, llamadas, atendidas,
                   ventas, instalaciones, sin_capacidad, ingresos, costos, caja)
               VALUES (:mes, :semana, :dia, :leads, :llamadas, :atendidas, :ventas,
                       :instalaciones, :sin_capacidad, :ingresos, :costos, :caja)
               ON CONFLICT(mes, semana, dia) DO UPDATE SET
                 leads=excluded.leads, llamadas=excluded.llamadas,
                 atendidas=excluded.atendidas, ventas=excluded.ventas,
                 instalaciones=excluded.instalaciones, sin_capacidad=excluded.sin_capacidad,
                 ingresos=excluded.ingresos, costos=excluded.costos, caja=excluded.caja""", kw)

    def guardar_resumen_mes(self, **kw: Any) -> None:
        self._exec(
            """INSERT INTO resumen_mes (mes, leads, llamadas, atendidas, ventas,
                   instalaciones, sin_capacidad, operadores, tecnicos, mejoras,
                   ingresos_instalaciones, ingresos_recurrentes, costos_personal,
                   costos_leads, costos_mejoras, costos_total, caja, clientes_activos)
               VALUES (:mes, :leads, :llamadas, :atendidas, :ventas, :instalaciones,
                       :sin_capacidad, :operadores, :tecnicos, :mejoras,
                       :ingresos_instalaciones, :ingresos_recurrentes, :costos_personal,
                       :costos_leads, :costos_mejoras, :costos_total, :caja, :clientes_activos)
               ON CONFLICT(mes) DO UPDATE SET
                 leads=excluded.leads, llamadas=excluded.llamadas, atendidas=excluded.atendidas,
                 ventas=excluded.ventas, instalaciones=excluded.instalaciones,
                 sin_capacidad=excluded.sin_capacidad, operadores=excluded.operadores,
                 tecnicos=excluded.tecnicos, mejoras=excluded.mejoras,
                 ingresos_instalaciones=excluded.ingresos_instalaciones,
                 ingresos_recurrentes=excluded.ingresos_recurrentes,
                 costos_personal=excluded.costos_personal, costos_leads=excluded.costos_leads,
                 costos_mejoras=excluded.costos_mejoras, costos_total=excluded.costos_total,
                 caja=excluded.caja, clientes_activos=excluded.clientes_activos""", kw)

    def resumenes_mes(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM resumen_mes ORDER BY mes").fetchall()

    # -------------------------------------------------------- gerente IA
    def guardar_decision(self, mes: int, accion: str, valor: str, motivo: str,
                         aprobada: bool, aviso: str = "") -> None:
        self._exec(
            """INSERT INTO decisiones_gerente (mes, accion, valor, motivo, aprobada, aviso)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (mes, accion, valor, motivo, int(aprobada), aviso))

    def guardar_acta(self, mes: int, titulo: str, cuerpo: str, meta: str) -> None:
        self._exec(
            """INSERT INTO actas_gerente (mes, titulo, cuerpo, meta) VALUES (?, ?, ?, ?)
               ON CONFLICT(mes) DO UPDATE SET titulo=excluded.titulo,
                 cuerpo=excluded.cuerpo, meta=excluded.meta""",
            (mes, titulo, cuerpo, meta))

    # ---------------------------------------------------------- mensajes
    def mensaje(self, tipo: str, remitente: str, destinatario: str, texto: str,
                mes: int, semana: int, dia: int) -> int:
        cur = self._exec(
            """INSERT INTO mensajes (tipo, remitente, destinatario, texto, mes, semana, dia)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tipo, remitente, destinatario, texto, mes, semana, dia))
        return int(cur.lastrowid)

    def ultimos_mensajes(self, tipo: str, limite: int = 30) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM mensajes WHERE tipo = ? ORDER BY id DESC LIMIT ?",
            (tipo, limite)).fetchall()

    # --------------------------------------------------------------- KPIs
    def kpis(self) -> dict[str, Any]:
        ult = self.conn.execute(
            "SELECT * FROM resumen_mes ORDER BY mes DESC LIMIT 1").fetchone()
        empresa = self.cargar_empresa()
        return {
            "mes": empresa.mes if empresa else 1,
            "semana": empresa.semana if empresa else 1,
            "operadores": empresa.operadores if empresa else 3,
            "tecnicos": empresa.tecnicos if empresa else 2,
            "mejoras": empresa.mejoras if empresa else 0,
            "caja": round(empresa.caja, 2) if empresa else 0.0,
            "clientes_activos": empresa.clientes_activos if empresa else 0,
            "ventas_totales": empresa.ventas_totales if empresa else 0,
            "ultimo_mes": dict(ult) if ult else None,
            "meses": [dict(r) for r in self.resumenes_mes()],
        }
