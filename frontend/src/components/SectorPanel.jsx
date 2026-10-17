import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

/**
 * El panel de un SECTOR: muestra el informe que produjo su agente al cerrar el
 * mes (AMD analiza los números, Evolus redacta el documento y, si no está, lo
 * escribe el redactor local). También muestra los números del mes, el historial
 * y —en Facturación— los comprobantes simulados con su auditoría.
 */

const COLORES = {
  azul: "#2f6bff",
  verde: "#2fce8f",
  violeta: "#7a5af8",
  cyan: "#22d3ee",
};

const SEMAFORO = {
  verde: { emoji: "🟢", texto: "todo en orden" },
  ambar: { emoji: "🟡", texto: "ojo con esto" },
  rojo: { emoji: "🔴", texto: "requiere atención" },
};

function Fuente({ informe }) {
  if (!informe?.fuente) return null;
  const ia = informe.fuente === "ia";
  const evolus = informe.redactor === "evolus";
  return (
    <div className="sector-fuentes">
      <span className={`etiqueta ${ia ? "etiqueta-verde" : "etiqueta-azul"}`}>
        {ia ? "🧠 Analizó la IA (AMD)" : "📝 Redactor local"}
      </span>
      <span className={`etiqueta ${evolus ? "etiqueta-violeta" : "etiqueta-azul"}`}>
        {evolus ? "✍️ Redactó Evolus" : "✍️ Redacción local"}
      </span>
    </div>
  );
}

function Facturas({ facturas }) {
  if (!facturas?.length) return null;
  return (
    <div className="sector-bloque">
      <h3 className="sector-sub">Comprobantes simulados y auditoría</h3>
      <p className="sector-nota">
        Facturas generadas con defectos a propósito (Monte Carlo) y leídas por el
        extractor. <b>SIMULADO – SIN VALIDEZ FISCAL.</b>
      </p>
      <div className="facturas-lista">
        {facturas.map((f) => {
          const fallados = f.errores_fallados?.length ?? 0;
          const detectados = f.errores_detectados?.length ?? 0;
          return (
            <div className="factura" key={f.id}>
              <div className="factura-cab">
                <b>{f.obtenido?.numero || f.id}</b>
                <span
                  className={`factura-chip ${
                    fallados === 0 && detectados === 0
                      ? "factura-ok"
                      : detectados > 0
                        ? "factura-alerta"
                        : "factura-ok"
                  }`}
                >
                  {detectados} {detectados === 1 ? "defecto" : "defectos"}
                </span>
              </div>
              <div className="factura-detalle">
                {f.obtenido?.razon_social || "—"} ·{" "}
                {f.obtenido?.total != null ? `Total ${f.obtenido.total}` : "sin total"}
              </div>
              {f.errores_detectados?.length ? (
                <ul className="factura-errores">
                  {f.errores_detectados.slice(0, 3).map((e, i) => (
                    <li key={i}>{e.detalle}</li>
                  ))}
                </ul>
              ) : (
                <div className="factura-ok-texto">Sin defectos detectados.</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function SectorPanel({ sector, mesInicial }) {
  const [informe, setInforme] = useState(null);
  const [mes, setMes] = useState(mesInicial ?? null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [generando, setGenerando] = useState(false);

  const traer = useCallback(async (m) => {
    setCargando(true);
    try {
      const r = await api.sectorDetalle(sector, m);
      setInforme(r);
      setError(null);
      return r;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setCargando(false);
    }
  }, [sector]);

  useEffect(() => {
    if (!sector) return;
    setInforme(null);
    traer(mes);
  }, [sector, mes, traer]);

  async function regenerar() {
    if (generando) return;
    setGenerando(true);
    try {
      await api.generarSector(sector, mes ?? undefined);
      await traer(mes);
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerando(false);
    }
  }

  const color = COLORES[informe?.color] || COLORES.azul;
  if (error && !informe) {
    return (
      <div className="sector" style={{ "--sector": color }}>
        <div className="aviso aviso-error">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      </div>
    );
  }
  if (cargando && !informe) {
    return <div className="cargando">Abriendo el informe del sector…</div>;
  }
  if (!informe) return null;

  const sem = SEMAFORO[informe.semaforo] || SEMAFORO.verde;

  return (
    <div className={`sector sector-${informe.color}`} style={{ "--sector": color }}>
      <div className="sector-cab">
        <span className="sector-icono">{informe.icono}</span>
        <div className="sector-titulo-caja">
          <h2 className="sector-nombre">{informe.nombre}</h2>
          <div className="sector-mes">
            {informe.tiene_informe ? (
              <>
                <span className="sector-semaforo">
                  {sem.emoji} {sem.texto}
                </span>
                <span className="sector-mes-num">Mes {informe.mes}</span>
              </>
            ) : (
              <span className="sector-mes-num">Sin informe del mes {informe.mes}</span>
            )}
          </div>
        </div>
        <button
          className="dia-chip sector-regen"
          onClick={regenerar}
          disabled={generando}
          title="El agente vuelve a analizar y redactar el informe"
        >
          {generando ? "Escribiendo…" : "↻ Regenerar"}
        </button>
      </div>

      <Fuente informe={informe} />

      {!informe.tiene_informe ? (
        <div className="sin-datos">
          Todavía no hay informe de este sector para el mes {informe.mes}. Corré el
          mes y el agente lo escribe solo.
        </div>
      ) : (
        <>
          <h3 className="sector-titulo">{informe.titulo}</h3>
          <p className="sector-resumen">{informe.resumen}</p>

          {informe.campos?.length ? (
            <div className="sector-numeros">
              {informe.campos.map((c) => (
                <div className="sector-dato" key={c.etiqueta}>
                  <div className="k">{c.etiqueta}</div>
                  <div className="v">{c.valor}</div>
                </div>
              ))}
            </div>
          ) : null}

          {informe.hallazgos?.length ? (
            <div className="sector-hallazgos">
              {informe.hallazgos.map((h, i) => (
                <div className="hallazgo" key={i}>
                  <div className="hallazgo-cab">
                    <b>{h.titulo}</b>
                    {h.dato ? <span className="hallazgo-dato">{h.dato}</span> : null}
                  </div>
                  <p>{h.detalle}</p>
                </div>
              ))}
            </div>
          ) : null}

          {informe.recomendacion ? (
            <div className="sector-recomendacion">
              <span className="sector-reco-etq">Recomendación</span>
              <p>{informe.recomendacion}</p>
            </div>
          ) : null}

          {informe.documento ? (
            <details className="sector-doc">
              <summary>Ver el documento completo</summary>
              <pre>{informe.documento}</pre>
            </details>
          ) : null}
        </>
      )}

      {informe.extras?.facturas?.length ? (
        <Facturas facturas={informe.extras.facturas} />
      ) : null}

      {informe.historial?.length ? (
        <div className="sector-bloque">
          <h3 className="sector-sub">Historial de informes</h3>
          <div className="sector-historial">
            {informe.historial.map((h) => (
              <button
                key={h.mes}
                className={`dia-chip ${h.mes === informe.mes ? "activo" : ""}`}
                onClick={() => setMes(h.mes)}
              >
                {(SEMAFORO[h.semaforo] || {}).emoji || "🟢"} Mes {h.mes}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
