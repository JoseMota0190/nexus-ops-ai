import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

/**
 * La SALA DE AGENTES: el cuarto donde los agentes de IA negocian CADA venta
 * del día. El teleoperador cierra la venta y le pide un turno al coordinador de
 * agenda; la agenda elige el día y la hora de la pizarra; y el coordinador de
 * técnicos decide a quién mandar. El PROGRAMA es el árbitro: los agentes eligen
 * de las opciones válidas, nunca inventan un turno.
 *
 * Acá se ve la charla tal cual quedó guardada en la base (lo que realmente dijo
 * el modelo que corre sobre AMD). No es un resumen: es el diálogo, venta por venta.
 */

const AGENTES = {
  operador: { nombre: "Teleoperador", icono: "📞", tono: "op" },
  agenda: { nombre: "Coordinador de agenda", icono: "📅", tono: "ag" },
  tecnicos: { nombre: "Coordinador de técnicos", icono: "🔧", tono: "te" },
};

function agrupar(lineas) {  // Cada conversación arranca cuando habla el teleoperador (proponer la venta).
  const charlas = [];
  let actual = null;
  for (const l of lineas) {
    if (l.remitente === "operador" || !actual) {
      actual = { cliente: l.destinatario, lineas: [] };
      charlas.push(actual);
    }
    actual.lineas.push(l);
  }
  return charlas.reverse(); // la más reciente, arriba
}

export default function SalaAgentes({ estado }) {
  const [lineas, setLineas] = useState(null);
  const [error, setError] = useState(null);
  const [refrescando, setRefrescando] = useState(false);

  const traer = useCallback(async () => {
    setRefrescando(true);
    try {
      const r = await api.sala(120);
      setLineas(r);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setRefrescando(false);
    }
  }, []);

  useEffect(() => {
    traer();
  }, [traer]);

  const enjambre = estado?.enjambre;
  const activo = enjambre ? enjambre.activo : null;

  return (
    <div className="sala">
      <div className="sala-cab">
        <div className="sala-estado">
          {activo === null ? (
            <span className="sala-pill">—</span>
          ) : activo ? (
            <span className="sala-pill sala-on">
              <i className="sala-punto" /> En vivo · negociando venta por venta
            </span>
          ) : (
            <span className="sala-pill sala-off">
              Modo rápido: los días corren sin charla (se prende desde el menú)
            </span>
          )}
        </div>
        <button className="dia-chip" onClick={traer} disabled={refrescando}>
          {refrescando ? "Actualizando…" : "↻ Actualizar"}
        </button>
      </div>

      {error ? (
        <div className="aviso aviso-error">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      ) : null}

      {!lineas ? (
        <div className="sin-datos">Entrando a la sala de agentes…</div>
      ) : lineas.length === 0 ? (
        <div className="sin-datos">
          Todavía no hay charla. Corré un día en <b>modo sala</b> (a partir del mes 7) y
          acá vas a ver a los agentes negociando cada venta.
        </div>
      ) : (
        <div className="sala-charlas">
          {agrupar(lineas).map((ch, i) => (
            <div className="sala-charla" key={i}>
              <div className="sala-cliente">
                <b>{ch.cliente}</b>
                <span>
                  {ch.lineas[0]?.mes !== undefined
                    ? `Mes ${ch.lineas[0].mes} · Semana ${ch.lineas[0].semana}`
                    : ""}
                </span>
              </div>
              {ch.lineas.map((l, j) => {
                const a = AGENTES[l.remitente] ?? { nombre: l.remitente, icono: "🤖", tono: "op" };
                return (
                  <div className={`sala-burbuja sala-${a.tono}`} key={j}>
                    <span className="sala-avatar" title={a.nombre}>
                      {a.icono}
                    </span>
                    <div className="sala-texto">
                      <span className="sala-agente">{a.nombre}</span>
                      <span className="sala-dice">{l.texto}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
