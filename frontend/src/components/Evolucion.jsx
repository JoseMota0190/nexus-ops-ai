import { num, usd } from "../format.js";

const W = 760;
const H = 320;
const ML = 64; // margen izquierdo
const MR = 56; // margen derecho (eje de técnicos)
const MT = 22;
const MB = 48;

function topeBonito(v) {
  if (v <= 0) return 1;
  const magnitud = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / magnitud;
  const bonito = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return bonito * magnitud;
}

export default function Evolucion({ resumenes, cargando, error }) {
  if (error) return <div className="error-caja">{error}</div>;
  if (cargando && (!resumenes || resumenes.length === 0))
    return <div className="cargando">Cargando los meses corridos…</div>;
  if (!resumenes || resumenes.length === 0)
    return (
      <div className="sin-datos">
        Todavía no se corrió ningún mes. Apretá <strong>«Avanzar 1 mes»</strong> o{" "}
        <strong>«Correr 6 meses de una»</strong> y el gráfico empieza a llenarse.
      </div>
    );

  const datos = resumenes.map((r) => ({
    mes: r.mes,
    ingresos: Number(r.ingresos_instalaciones || 0) + Number(r.ingresos_recurrentes || 0),
    costos: Number(r.costos_total || 0),
    tecnicos: Number(r.tecnicos || 0),
    ventas: Number(r.ventas || 0),
  }));

  const maxVal = topeBonito(Math.max(...datos.map((d) => Math.max(d.ingresos, d.costos)), 1));
  const plotW = W - ML - MR;
  const plotH = H - MT - MB;
  const slot = plotW / datos.length;
  const barraW = Math.min(34, slot * 0.34);

  const yDe = (v) => MT + plotH - (v / maxVal) * plotH;
  const yTec = (t) => MT + plotH - (Math.min(10, t) / 10) * plotH;

  const puntos = datos.map((d, i) => {
    const cx = ML + slot * i + slot / 2;
    return `${cx},${yTec(d.tecnicos)}`;
  });

  const grid = [0, 0.25, 0.5, 0.75, 1];

  // ¿Los costos crecen más lento que los ingresos?
  const primero = datos[0];
  const ultimo = datos[datos.length - 1];
  let nota = null;
  if (datos.length >= 2 && primero.ingresos > 0 && primero.costos > 0) {
    const crecIng = ((ultimo.ingresos - primero.ingresos) / primero.ingresos) * 100;
    const crecCos = ((ultimo.costos - primero.costos) / primero.costos) * 100;
    nota = { crecIng, crecCos, desde: primero.mes, hasta: ultimo.mes };
  }

  return (
    <div>
      <svg
        className="grafico-svg"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Ingresos y costos mes a mes con la línea de técnicos"
      >
        {/* rejilla */}
        {grid.map((g) => {
          const y = MT + plotH - g * plotH;
          return (
            <g key={g}>
              <line x1={ML} y1={y} x2={W - MR} y2={y} stroke="#22303f" strokeWidth="1" />
              <text x={ML - 8} y={y + 4} textAnchor="end" fontSize="11" fill="#6d8199">
                {maxVal * g >= 1000
                  ? `${num((maxVal * g) / 1000, 0)}k`
                  : num(maxVal * g, 0)}
              </text>
            </g>
          );
        })}

        {/* eje derecho: técnicos 0..10 */}
        {[0, 5, 10].map((t) => (
          <text
            key={t}
            x={W - MR + 10}
            y={yTec(t) + 4}
            fontSize="11"
            fill="#ffc53d"
          >
            {t}
          </text>
        ))}

        {/* barras */}
        {datos.map((d, i) => {
          const centro = ML + slot * i + slot / 2;
          const xIng = centro - barraW - 3;
          const xCos = centro + 3;
          return (
            <g key={d.mes}>
              <rect
                x={xIng}
                y={yDe(d.ingresos)}
                width={barraW}
                height={Math.max(2, MT + plotH - yDe(d.ingresos))}
                rx="4"
                fill="url(#gradIngreso)"
              />
              <rect
                x={xCos}
                y={yDe(d.costos)}
                width={barraW}
                height={Math.max(2, MT + plotH - yDe(d.costos))}
                rx="4"
                fill="#d8546a"
                opacity="0.9"
              />
              <text
                x={centro}
                y={H - MB + 18}
                textAnchor="middle"
                fontSize="12"
                fill="#9db0c6"
                fontWeight="700"
              >
                Mes {d.mes}
              </text>
              <text
                x={centro}
                y={H - MB + 33}
                textAnchor="middle"
                fontSize="10.5"
                fill="#6d8199"
              >
                {num(d.ventas)} ventas
              </text>
            </g>
          );
        })}

        {/* línea de técnicos */}
        <polyline
          points={puntos.join(" ")}
          fill="none"
          stroke="#ffc53d"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {datos.map((d, i) => (
          <circle
            key={`t${d.mes}`}
            cx={ML + slot * i + slot / 2}
            cy={yTec(d.tecnicos)}
            r="4.5"
            fill="#0a0e13"
            stroke="#ffc53d"
            strokeWidth="2.5"
          />
        ))}

        <defs>
          <linearGradient id="gradIngreso" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#35d39a" />
            <stop offset="100%" stopColor="#1fae83" />
          </linearGradient>
        </defs>
      </svg>

      <div className="leyenda">
        <span>
          <span className="punto" style={{ background: "#35d39a" }} />
          Ingresos del mes
        </span>
        <span>
          <span className="punto" style={{ background: "#d8546a" }} />
          Costos del mes
        </span>
        <span>
          <span className="punto" style={{ background: "#ffc53d" }} />
          Técnicos (eje de la derecha)
        </span>
        <span>Caja actual: {usd(resumenes[resumenes.length - 1].caja ?? 0, 0)}</span>
      </div>

      {nota ? (
        <div className="nota-grafico">
          📈 Entre el mes {nota.desde} y el mes {nota.hasta}: los ingresos crecieron{" "}
          <strong>{num(nota.crecIng, 0)}%</strong> mientras los costos crecieron solo{" "}
          <strong>{num(nota.crecCos, 0)}%</strong>.{" "}
          {nota.crecIng > nota.crecCos
            ? "Los costos suben más despacio que las ventas: por eso el negocio se vuelve más redondo."
            : "Ojo: en este escenario los costos crecieron al mismo ritmo que los ingresos."}
        </div>
      ) : null}
    </div>
  );
}
