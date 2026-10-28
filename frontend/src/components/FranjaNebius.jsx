import { num } from "../format.js";
import { t, useIdioma } from "../i18n.js";

/** Nombre corto del modelo, para que entre en una sola línea. */
function corto(id) {
  if (!id) return "mock";
  const ultimo = id.split("/").pop() || id;
  return ultimo.replace(/-VL$/, "").replace(/_/g, " ");
}

/**
 * THE NEMOTRON STRIP: a thin bar, always visible at the bottom, with the health
 * of the brain and the model router. It shows how many calls went to the
 * reasoning model and how many to the fast one, so anyone can see that the
 * expensive model only does the thinking. It takes no room in the menu.
 */
export default function FranjaNebius({ metricas }) {
  useIdioma();
  const m = metricas || {};
  const real = m.modo_mock === false;
  const respaldos = m.fallback_calls ?? 0;
  const porModelo = m.por_modelo || {};
  const llamadasDe = (id) => (id && porModelo[id] ? porModelo[id].calls : 0);

  return (
    <div className="franja-nebius" role="status"
         aria-label={t("Nebius brain status and model routing",
                       "Estado del cerebro Nebius y router de modelos")}>
      <span className="franja-nebius-tag">🧠 NEMOTRON</span>
      <span className={`franja-nebius-punto ${real ? "on" : "off"}`} />
      <span className="franja-nebius-item">
        {real ? t("online", "en línea") : t("test mode", "modo prueba")}
      </span>
      <span className="franja-nebius-sep" />
      <span className="franja-nebius-item" title={m.modelo_razonamiento || "mock"}>
        ⟡ <b>{corto(m.modelo_razonamiento)}</b>
        <em>{num(llamadasDe(m.modelo_razonamiento))}</em>
      </span>
      <span className="franja-nebius-item" title={m.modelo_rapido || "mock"}>
        ⚡ <b>{corto(m.modelo_rapido)}</b>
        <em>{num(llamadasDe(m.modelo_rapido))}</em>
      </span>
      <span className="franja-nebius-sep" />
      <span className="franja-nebius-item">
        p50 <b>{num(m.latency_p50_ms ?? 0, 0)} ms</b>
      </span>
      <span className="franja-nebius-item">
        p95 <b>{num(m.latency_p95_ms ?? 0, 0)} ms</b>
      </span>
      <span className="franja-nebius-item">
        <b>{num(m.tokens_per_s ?? 0, 1)}</b> tok/s
      </span>
      <span className="franja-nebius-sep" />
      <span className="franja-nebius-item">
        <b>{num(m.total_calls ?? 0)}</b> {t("calls", "llamadas")}
      </span>
      <span className="franja-nebius-item">
        {t("fallbacks", "respaldos")} <b>{num(respaldos)}</b>
      </span>
    </div>
  );
}
