import { useEffect, useMemo, useState } from "react";
import { DIAS } from "../format.js";

const W = 720;
const H = 520;
const PAD = { izq: 58, der: 150, arr: 44, aba: 52 };
const COLORES = ["#ff5a36", "#4aa8ff", "#35d39a", "#ffc53d", "#c77dff", "#ff9f6e",
  "#59e0c5", "#ff6fae", "#8ad36a", "#7aa2ff"];

// CABA está a ~34.6° de latitud: 1° de longitud mide 0.823° "de latitud".
const FACTOR_LON = 0.823;

function proyectador(zonas) {
  const puntos = Object.entries(zonas)
    .filter(([, z]) => z && z.lat != null && z.lon != null)
    .map(([, z]) => z);
  if (puntos.length === 0) return null;

  const lats = puntos.map((p) => p.lat);
  const lons = puntos.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const dlat = Math.max(0.001, maxLat - minLat);
  const dlon = Math.max(0.001, maxLon - minLon);

  const dispW = W - PAD.izq - PAD.der;
  const dispH = H - PAD.arr - PAD.aba;
  const mundoW = dlon * FACTOR_LON;
  const mundoH = dlat;
  const k = Math.min(dispW / mundoW, dispH / mundoH);
  const drawW = mundoW * k;
  const drawH = mundoH * k;
  const x0 = PAD.izq + (dispW - drawW) / 2;
  const y0 = PAD.arr + (dispH - drawH) / 2;

  return (lat, lon) => ({
    x: x0 + (lon - minLon) * FACTOR_LON * k,
    y: y0 + (maxLat - lat) * k,
  });
}

export default function MapaCaba({ mapa, cargando, error }) {
  const [diaActivo, setDiaActivo] = useState(0);
  const [corriendo, setCorriendo] = useState(true);

  const zonas = mapa?.zonas ?? {};
  const citas = mapa?.citas ?? [];
  const tecnicos = mapa?.tecnicos ?? [];
  const punto = useMemo(() => proyectador(zonas), [zonas]);

  const porDia = useMemo(() => {
    const cuenta = {};
    for (const c of citas) {
      const d = Number(c.dia);
      if (!cuenta[d]) cuenta[d] = {};
      if (c.barrio) cuenta[d][c.barrio] = (cuenta[d][c.barrio] || 0) + 1;
    }
    return cuenta;
  }, [citas]);

  const totalPorDia = useMemo(() => {
    const t = {};
    for (const c of citas) t[Number(c.dia)] = (t[Number(c.dia)] || 0) + 1;
    return t;
  }, [citas]);

  const diasConCitas = useMemo(
    () => Object.keys(totalPorDia).map(Number).sort((a, b) => a - b),
    [totalPorDia],
  );

  // Pasito automático por los días de la semana.
  useEffect(() => {
    if (!corriendo || diasConCitas.length === 0) return;
    const t = setInterval(() => {
      setDiaActivo((d) => {
        const i = diasConCitas.indexOf(d);
        const siguiente = diasConCitas[(i + 1) % diasConCitas.length];
        return siguiente === undefined ? d : siguiente;
      });
    }, 2600);
    return () => clearInterval(t);
  }, [corriendo, diasConCitas]);

  const citasDeHoy = porDia[diaActivo] || {};
  const totalHoy = totalPorDia[diaActivo] || 0;
  const maxBarrio = Math.max(1, ...Object.values(citasDeHoy));
  const barriosActivos = Object.keys(citasDeHoy).length;

  return (
    <div className="panel panel-ancho">
      <h2 className="panel-titulo">
        <span className="icono">🗺️</span> Mapa de CABA — las visitas del día
      </h2>
      <p className="panel-sub">
        Cada bolita es un barrio: cuanto más grande, más instalaciones se agendaron ahí. Los
        cuadritos son los técnicos y su zona base. Semana {mapa?.semana ?? "—"}.
      </p>

      {error ? <div className="error-caja">{error}</div> : null}
      {!error && cargando && !mapa ? <div className="cargando">Dibujando el mapa…</div> : null}
      {!error && !mapa && !cargando ? (
        <div className="sin-datos">No pude leer el mapa todavía.</div>
      ) : null}

      {mapa ? (
        <>
          <div className="dias">
            {DIAS.map((nombre, i) => (
              <button
                key={nombre}
                className={`dia-chip ${i === diaActivo ? "activo" : ""}`}
                onClick={() => {
                  setDiaActivo(i);
                  setCorriendo(false);
                }}
              >
                {nombre} · {totalPorDia[i] || 0}
              </button>
            ))}
            <button
              className="dia-chip"
              onClick={() => setCorriendo((c) => !c)}
              title="Pausar o reanudar la animación"
            >
              {corriendo ? "⏸ Pausar" : "▶ Reproducir"}
            </button>
          </div>

          <div className="mapa-fila">
            <div>
              <svg
                className="mapa-svg"
                viewBox={`0 0 ${W} ${H}`}
                role="img"
                aria-label="Mapa de CABA con las instalaciones por barrio"
              >
                {punto
                  ? Object.entries(zonas).map(([nombre, z]) => {
                      if (z.lat == null || z.lon == null) return null;
                      const { x, y } = punto(z.lat, z.lon);
                      const n = citasDeHoy[nombre] || 0;
                      const r = n > 0 ? 9 + Math.min(20, (n / maxBarrio) * 20) : 6;
                      const derecha = x < W - 150;
                      return (
                        <g key={nombre}>
                          <circle
                            className="zona-punto"
                            cx={x}
                            cy={y}
                            r={r}
                            fill={n > 0 ? "rgba(255,90,54,0.55)" : "rgba(74,168,255,0.25)"}
                            stroke={n > 0 ? "#ff8a3d" : "#4aa8ff"}
                            strokeWidth="2"
                          />
                          <text
                            className="zona-label"
                            x={derecha ? x + r + 6 : x - r - 6}
                            y={y + 3.5}
                            textAnchor={derecha ? "start" : "end"}
                          >
                            {nombre}
                          </text>
                          {n > 0 ? (
                            <text
                              className="zona-count"
                              x={x}
                              y={y - r - 6}
                              textAnchor="middle"
                            >
                              {n}
                            </text>
                          ) : null}
                        </g>
                      );
                    })
                  : null}

                {punto
                  ? tecnicos.map((t, i) => {
                      const z = zonas[t.zona_base];
                      if (!z) return null;
                      const base = punto(z.lat, z.lon);
                      const color = COLORES[i % COLORES.length];
                      const desplazado = i % 2 === 0 ? 1 : -1;
                      const x = base.x + desplazado * 16;
                      const y = base.y + 26 + (i % 3) * 9;
                      return (
                        <g key={`tec${t.id}`}>
                          <rect
                            x={x - 9}
                            y={y - 9}
                            width="18"
                            height="18"
                            rx="6"
                            fill={color}
                            stroke="#0b1117"
                            strokeWidth="2"
                          />
                          <text
                            x={x}
                            y={y + 4}
                            textAnchor="middle"
                            fontSize="11"
                            fontWeight="800"
                            fill="#0b1117"
                          >
                            {String(t.nombre || "?").trim().charAt(0).toUpperCase()}
                          </text>
                        </g>
                      );
                    })
                  : null}
              </svg>
            </div>

            <div>
              <div className="sub-motivo">Técnicos y su zona base</div>
              <div className="tecnicos-lista">
                {tecnicos.length === 0 ? (
                  <div className="sin-datos">Sin técnicos cargados.</div>
                ) : (
                  tecnicos.map((t, i) => {
                    const hoy = citas.filter(
                      (c) => Number(c.dia) === diaActivo && Number(c.tecnico_id) === Number(t.id),
                    ).length;
                    return (
                      <div className="tecnico" key={t.id}>
                        <span
                          className="inicial"
                          style={{ background: COLORES[i % COLORES.length] }}
                        >
                          {String(t.nombre || "?").trim().charAt(0).toUpperCase()}
                        </span>
                        <span>{t.nombre}</span>
                        <span className="zona">
                          {t.zona_base}
                          <br />
                          {hoy} visita{hoy === 1 ? "" : "s"} hoy
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="mapa-stats">
                <div className="dato">
                  <b>{totalHoy}</b>
                  instalaciones {DIAS[diaActivo].toLowerCase()}
                </div>
                <div className="dato">
                  <b>{barriosActivos}</b>
                  barrios con trabajo
                </div>
                <div className="dato">
                  <b>{mapa.capacidad_dia ?? 0}</b>
                  cupos por día
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
