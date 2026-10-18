import { useEffect, useMemo, useState } from "react";
import { diasSemana } from "../format.js";
import { t, useIdioma } from "../i18n.js";
import { BARRIOS_CABA } from "../caba.js";

const W = 720;
const H = 520;
// The panel needs air on the right for the neighborhood labels; the cover is
// centered and clean.
const PAD_PANEL = { izq: 58, der: 150, arr: 44, aba: 52 };
const PAD_PORTADA = { izq: 34, der: 34, arr: 30, aba: 30 };
const COLORES = ["#ff5a36", "#4aa8ff", "#35d39a", "#ffc53d", "#c77dff", "#ff9f6e",
  "#59e0c5", "#ff6fae", "#8ad36a", "#7aa2ff"];

// CABA is at ~34.6° latitude: 1° of longitude measures 0.823° "of latitude".
const FACTOR_LON = 0.823;

// The REAL map of the City: the 48 neighborhoods with their polygons (see src/caba.js).
// We flatten all their points so the drawing's frame always contains them.
const PUNTOS_CABA = [];
for (const barrio of BARRIOS_CABA) {
  for (const anillo of barrio.anillos) {
    for (const [lon, lat] of anillo) PUNTOS_CABA.push([lat, lon]);
  }
}

function proyectador(zonas, extra = [], pad = PAD_PANEL) {
  const puntos = Object.entries(zonas)
    .filter(([, z]) => z && z.lat != null && z.lon != null)
    .map(([, z]) => z);
  // The map (neighborhoods) fits in the frame: that way the drawing is always inside.
  const extras = extra.map(([lat, lon]) => ({ lat, lon }));
  const todos = puntos.concat(extras);
  if (todos.length === 0) return null;

  const lats = todos.map((p) => p.lat);
  const lons = todos.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const dlat = Math.max(0.001, maxLat - minLat);
  const dlon = Math.max(0.001, maxLon - minLon);

  const dispW = W - pad.izq - pad.der;
  const dispH = H - pad.arr - pad.aba;
  const mundoW = dlon * FACTOR_LON;
  const mundoH = dlat;
  const k = Math.min(dispW / mundoW, dispH / mundoH);
  const drawW = mundoW * k;
  const drawH = mundoH * k;
  const x0 = pad.izq + (dispW - drawW) / 2;
  const y0 = pad.arr + (dispH - drawH) / 2;

  return (lat, lon) => ({
    x: x0 + (lon - minLon) * FACTOR_LON * k,
    y: y0 + (maxLat - lat) * k,
  });
}

/**
 * CABA map.
 *
 * Two modes:
 *  - `portada`  → full screen, without a box or titles: it is the BACKGROUND of
 *    the owner's screen. Only the map and a small bar with the days.
 *  - normal     → inside a box with an explanation (the regular panel).
 */
export default function MapaCaba({ mapa, cargando, error, portada = false }) {
  useIdioma();
  const DIAS = diasSemana();
  const [diaActivo, setDiaActivo] = useState(0);
  const [corriendo, setCorriendo] = useState(true);

  const zonas = mapa?.zonas ?? {};
  const citas = mapa?.citas ?? [];
  const tecnicos = mapa?.tecnicos ?? [];
  const punto = useMemo(
    () => proyectador(zonas, PUNTOS_CABA, portada ? PAD_PORTADA : PAD_PANEL),
    [zonas, portada],
  );

  // Each neighborhood as an SVG path (only once, unless the frame changes).
  const caminosBarrios = useMemo(() => {
    if (!punto) return [];
    return BARRIOS_CABA.map((barrio) => ({
      nombre: barrio.nombre,
      comuna: barrio.comuna,
      d: barrio.anillos
        .map(
          (anillo) =>
            anillo
              .map(([lon, lat], i) => {
                const { x, y } = punto(lat, lon);
                return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
              })
              .join(" ") + " Z",
        )
        .join(" "),
    }));
  }, [punto]);

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

  // Automatic step through the days of the week.
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

  // The drawing itself (shared by the cover mode and the regular panel).
  const dibujo = (
    <svg
      className="mapa-svg"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={t("CABA map with the installs by neighborhood",
                    "Mapa de CABA con las instalaciones por barrio")}
    >
      <g className="caba-barrios">
        {caminosBarrios.map((b) => (
          <path key={b.nombre} className="caba-barrio" d={b.d}>
            <title>{b.nombre}</title>
          </path>
        ))}
      </g>

      {!portada && punto
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
                  <text className="zona-count" x={x} y={y - r - 6} textAnchor="middle">
                    {n}
                  </text>
                ) : null}
              </g>
            );
          })
        : null}

      {!portada && punto
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
  );

  const chipsDias = (
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
        title={t("Pause or resume the animation", "Pausar o reanudar la animación")}
      >
        {corriendo ? t("⏸ Pause", "⏸ Pausa") : t("▶ Play", "▶ Reproducir")}
      </button>
    </div>
  );

  // --------------------------------------------------- cover mode
  // Home screen: the map fills everything, without a box or titles.
  if (portada) {
    if (error) return <div className="error-caja mapa-portada-aviso">{error}</div>;
    if (!mapa) {
      return (
        <div className="mapa-portada-vacio">
          {cargando ? t("Drawing the map…", "Dibujando el mapa…")
            : t("I couldn't read the map yet.", "Todavía no pude leer el mapa.")}
        </div>
      );
    }
    return (
      <div className="mapa-portada">
        {dibujo}
      </div>
    );
  }

  // ---------------------------------------------------- regular panel mode
  return (
    <div className="panel panel-ancho">
      <h2 className="panel-titulo">
        <span className="icono">🗺️</span> {t("CABA map — the day's visits",
                                            "Mapa de CABA — las visitas del día")}
      </h2>
      <p className="panel-sub">
        {t("Each dot is a neighborhood: the bigger it is, the more installs were booked there. The little squares are the technicians and their base zone.",
           "Cada punto es un barrio: cuanto más grande, más instalaciones se agendaron ahí. Los cuadraditos son los técnicos y su zona base.")}{" "}
        {t("Week", "Semana")} {mapa?.semana ?? "—"}.
      </p>

      {error ? <div className="error-caja">{error}</div> : null}
      {!error && cargando && !mapa ? (
        <div className="cargando">{t("Drawing the map…", "Dibujando el mapa…")}</div>
      ) : null}
      {!error && !mapa && !cargando ? (
        <div className="sin-datos">{t("I couldn't read the map yet.", "Todavía no pude leer el mapa.")}</div>
      ) : null}

      {mapa ? (
        <>
          {chipsDias}

          <div className="mapa-fila">
            <div>{dibujo}</div>

            <div>
              <div className="sub-motivo">{t("Technicians and their base zone",
                                              "Técnicos y su zona base")}</div>
              <div className="tecnicos-lista">
                {tecnicos.length === 0 ? (
                  <div className="sin-datos">{t("No technicians loaded.", "No hay técnicos cargados.")}</div>
                ) : (
                  tecnicos.map((tec, i) => {
                    const hoy = citas.filter(
                      (c) => Number(c.dia) === diaActivo && Number(c.tecnico_id) === Number(tec.id),
                    ).length;
                    return (
                      <div className="tecnico" key={tec.id}>
                        <span
                          className="inicial"
                          style={{ background: COLORES[i % COLORES.length] }}
                        >
                          {String(tec.nombre || "?").trim().charAt(0).toUpperCase()}
                        </span>
                        <span>{tec.nombre}</span>
                        <span className="zona">
                          {tec.zona_base}
                          <br />
                          {hoy} {hoy === 1 ? t("visit today", "visita hoy")
                                          : t("visits today", "visitas hoy")}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="mapa-stats">
                <div className="dato">
                  <b>{totalHoy}</b>
                  {t("installs", "instalaciones")} {DIAS[diaActivo].toLowerCase()}
                </div>
                <div className="dato">
                  <b>{barriosActivos}</b>
                  {t("neighborhoods with work", "barrios con trabajo")}
                </div>
                <div className="dato">
                  <b>{mapa.capacidad_dia ?? 0}</b>
                  {t("slots per day", "turnos por día")}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
