import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { num, usd } from "../format.js";

const MEJORAS = [
  "Sin mejoras",
  "Base de datos más ordenada",
  "Guión de venta mejorado",
  "Base + guion juntos",
  "Capacitación del equipo",
  "Toda la maquinaria puesta",
];

export default function Escenario({ estado }) {
  const [operadores, setOperadores] = useState(estado?.operadores ?? 3);
  const [tecnicos, setTecnicos] = useState(estado?.tecnicos ?? 2);
  const [mejoras, setMejoras] = useState(estado?.mejoras ?? 0);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const timer = useRef(null);
  const primeraCarga = useRef(true);

  // Si cambia el estado real, arrancamos los sliders con sus valores…
  useEffect(() => {
    if (!estado) return;
    if (primeraCarga.current) {
      primeraCarga.current = false;
      setOperadores(estado.operadores ?? 3);
      setTecnicos(estado.tecnicos ?? 2);
      setMejoras(estado.mejoras ?? 0);
    }
  }, [estado]);

  // …y cada vez que se mueve un slider, la planilla recalcula (con un respiro).
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    setCargando(true);
    timer.current = setTimeout(async () => {
      try {
        const r = await api.escenario({ operadores, tecnicos, mejoras });
        setResultado(r);
        setError(null);
      } catch (e) {
        setError(e.message);
      } finally {
        setCargando(false);
      }
    }, 260);
    return () => clearTimeout(timer.current);
  }, [operadores, tecnicos, mejoras]);

  const ing = resultado?.ingresos_mes ?? 0;
  const cos = resultado?.costos_mes ?? 0;
  const total = Math.max(1, ing, cos);
  const balance = resultado?.balance_mes ?? 0;
  const capOk =
    resultado && resultado.falta_capacidad === 0 && resultado.sobra_capacidad >= 0;

  return (
    <div className="panel">
      <h2 className="panel-titulo">
        <span className="icono">🎛️</span> ¿Qué pasa si…?
      </h2>
      <p className="panel-sub">
        El dueño mueve las palancas y la planilla recalcula. Esto es una prueba al aire:
        <strong> no toca la simulación real</strong>.
      </p>

      <div className="slider-fila">
        <div className="slider-top">
          <span className="nombre">Teleoperadores (sueldos)</span>
          <span className="valor">{operadores}</span>
        </div>
        <input
          type="range"
          min="1"
          max="20"
          value={operadores}
          onChange={(e) => setOperadores(Number(e.target.value))}
          aria-label="Cantidad de operadores"
        />
        <div className="slider-pista">
          <span>1</span>
          <span>20</span>
        </div>
      </div>

      <div className="slider-fila">
        <div className="slider-top">
          <span className="nombre">Técnicos instaladores</span>
          <span className="valor">{tecnicos}</span>
        </div>
        <input
          type="range"
          min="1"
          max="12"
          value={tecnicos}
          onChange={(e) => setTecnicos(Number(e.target.value))}
          aria-label="Cantidad de técnicos"
        />
        <div className="slider-pista">
          <span>1</span>
          <span>12</span>
        </div>
      </div>

      <div className="slider-fila">
        <div className="slider-top">
          <span className="nombre">Inversión en mejora y conversión</span>
          <span className="valor">
            {mejoras} · {MEJORAS[mejoras] ?? ""}
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="5"
          value={mejoras}
          onChange={(e) => setMejoras(Number(e.target.value))}
          aria-label="Nivel de mejoras"
        />
        <div className="slider-pista">
          <span>0 (nada)</span>
          <span>5 (todo)</span>
        </div>
      </div>

      {error ? <div className="error-caja">{error}</div> : null}

      {!error && !resultado && cargando ? (
        <div className="cargando">Pidiéndole a la planilla que calcule…</div>
      ) : null}

      {resultado ? (
        <>
          <div className="resultado">
            <div className="caja">
              <div className="k">Ventas por día</div>
              <div className="v ondas">{num(resultado.ventas_por_dia, 1)}</div>
              <div className="n">Con {operadores} operadores y {tecnicos} técnicos</div>
            </div>
            <div className="caja">
              <div className="k">Balance del mes</div>
              <div className={`v ${balance >= 0 ? "positivo" : "negativo"}`}>
                {usd(balance, 0)}
              </div>
              <div className="n">Ingresos menos costos del mes</div>
            </div>
            <div className="caja">
              <div className="k">Ingresos del mes</div>
              <div className="v positivo">{usd(ing, 0)}</div>
              <div className="n">Instalaciones + monitoreo + mantenimiento</div>
            </div>
            <div className="caja">
              <div className="k">Costos del mes</div>
              <div className="v negativo">{usd(cos, 0)}</div>
              <div className="n">Sueldos + leads + mejoras</div>
            </div>
          </div>

          <div className="balance-barra" title="Ingresos vs costos del mes">
            <i className="ing" style={{ width: `${(ing / total) * 100}%` }} />
            <i className="cos" style={{ width: `${(cos / total) * 100}%` }} />
          </div>
          <div className="leyenda">
            <span>
              <span className="punto" style={{ background: "#35d39a" }} />
              Ingresos
            </span>
            <span>
              <span className="punto" style={{ background: "#ff5f6d" }} />
              Costos
            </span>
            <span>
              Capacidad de instalación: {num(resultado.capacidad_instalaciones)} por día
            </span>
          </div>

          <div className={`veredicto ${capOk ? "ok" : "mal"}`}>
            <span>{capOk ? "✅" : "⚠️"}</span>
            <span>
              {capOk ? (
                <>
                  Los técnicos dan abasto: sobran{" "}
                  <strong>{num(resultado.sobra_capacidad)}</strong> turnos por día.
                </>
              ) : (
                <>
                  Faltan manos: hay <strong>{num(resultado.falta_capacidad)}</strong>{" "}
                  instalaciones por día sin técnico que las haga.
                </>
              )}
            </span>
          </div>

          <div className={`veredicto ${resultado.meta_cumplida ? "ok" : "mal"}`}>
            <span>{resultado.meta_cumplida ? "🎯" : "🚧"}</span>
            <span>
              {resultado.meta_cumplida ? (
                <>
                  Con <strong>{tecnicos} técnicos</strong> ya se cumple la meta de 10: el
                  dueño está conforme.
                </>
              ) : (
                <>
                  Para la meta de 10 técnicos todavía faltan{" "}
                  <strong>{num(10 - tecnicos)}</strong>.
                </>
              )}
            </span>
          </div>
        </>
      ) : null}
    </div>
  );
}
