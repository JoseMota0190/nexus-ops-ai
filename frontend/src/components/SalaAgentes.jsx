import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { t, useIdioma } from "../i18n.js";

/**
 * The AGENT ROOM: the room where the AI agents negotiate EVERY sale of the day.
 * The telemarketer closes the sale and asks the scheduling coordinator for a
 * slot; the schedule picks the day and time from the board; and the technician
 * coordinator decides who to send. The PROGRAM is the referee: the agents pick
 * from valid options, they never invent a slot.
 *
 * Here you see the chat exactly as it was stored in the database (what the model
 * running on AMD really said). It is not a summary: it is the dialogue, sale by sale.
 */

function agentes() {
  return {
    operador: { nombre: t("Telemarketer", "Teleoperador"), icono: "📞", tono: "op" },
    agenda: { nombre: t("Scheduling coordinator", "Coordinador de agenda"), icono: "📅", tono: "ag" },
    tecnicos: { nombre: t("Technician coordinator", "Coordinador de técnicos"), icono: "🔧", tono: "te" },
  };
}

function agrupar(lineas) {  // Each conversation starts when the telemarketer speaks (proposing the sale).
  const charlas = [];
  let actual = null;
  for (const l of lineas) {
    if (l.remitente === "operador" || !actual) {
      actual = { cliente: l.destinatario, lineas: [] };
      charlas.push(actual);
    }
    actual.lineas.push(l);
  }
  return charlas.reverse(); // the most recent one, on top
}

export default function SalaAgentes({ estado, refrescoMs = 0 }) {
  useIdioma();
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

  // In the LIVE DAY, the room refreshes itself so the bubbles keep appearing.
  useEffect(() => {
    if (!refrescoMs) return undefined;
    const timer = setInterval(traer, refrescoMs);
    return () => clearInterval(timer);
  }, [traer, refrescoMs]);

  const enjambre = estado?.enjambre;
  const activo = enjambre ? enjambre.activo : null;
  const AGENTES = agentes();

  return (
    <div className="sala">
      <div className="sala-cab">
        <div className="sala-estado">
          {activo === null ? (
            <span className="sala-pill">—</span>
          ) : activo ? (
            <span className="sala-pill sala-on">
              <i className="sala-punto" /> {t("Live · negotiating sale by sale",
                                               "En vivo · negociando venta por venta")}
            </span>
          ) : (
            <span className="sala-pill sala-off">
              {t("Fast mode: the days run without chat (turn it on from the menu)",
                 "Modo rápido: los días corren sin charla (prendelo desde el menú)")}
            </span>
          )}
        </div>
        <button className="dia-chip" onClick={traer} disabled={refrescando}>
          {refrescando ? t("Refreshing…", "Refrescando…") : t("↻ Refresh", "↻ Refrescar")}
        </button>
      </div>

      {error ? (
        <div className="aviso aviso-error">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      ) : null}

      {!lineas ? (
        <div className="sin-datos">{t("Entering the agent room…", "Entrando a la sala de agentes…")}</div>
      ) : lineas.length === 0 ? (
        <div className="sin-datos">
          {t("No chat yet. Run a day in ", "Todavía no hay charla. Corré un día en modo ")}
          <b>{t("live room", "sala en vivo")}</b>
          {t(" mode (from month 7 on) and here you'll see the agents negotiating every sale.",
             " (desde el mes 7) y acá vas a ver a los agentes negociando cada venta.")}
        </div>
      ) : (
        <div className="sala-charlas">
          {agrupar(lineas).map((ch, i) => (
            <div className="sala-charla" key={i}>
              <div className="sala-cliente">
                <b>{ch.cliente}</b>
                <span>
                  {ch.lineas[0]?.mes !== undefined
                    ? t(`Month ${ch.lineas[0].mes} · Week ${ch.lineas[0].semana}`,
                        `Mes ${ch.lineas[0].mes} · Semana ${ch.lineas[0].semana}`)
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
