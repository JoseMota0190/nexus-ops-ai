import { num } from "../format.js";
import { t, useIdioma } from "../i18n.js";

/**
 * The AMD STRIP: a thin bar, always visible at the bottom, with the health of
 * the brain (the model running on AMD). It takes no room in the menu: you
 * glance at it while the simulation runs.
 */
export default function FranjaAMD({ metricas }) {
  useIdioma();
  const m = metricas || {};
  const real = m.modo_mock === false;
  const respaldos = m.fallback_calls ?? 0;

  return (
    <div className="franja-amd" role="status"
         aria-label={t("AMD brain status", "Estado del cerebro AMD")}>
      <span className="franja-amd-tag">🧠 AMD</span>
      <span className={`franja-amd-punto ${real ? "on" : "off"}`} />
      <span className="franja-amd-item">
        <b>{m.modelo || "mock"}</b>
      </span>
      <span className="franja-amd-sep" />
      <span className="franja-amd-item">
        {real ? t("online", "en línea") : t("test mode", "modo prueba")}
      </span>
      <span className="franja-amd-sep" />
      <span className="franja-amd-item">
        p50 <b>{num(m.latency_p50_ms ?? 0, 0)} ms</b>
      </span>
      <span className="franja-amd-item">
        p95 <b>{num(m.latency_p95_ms ?? 0, 0)} ms</b>
      </span>
      <span className="franja-amd-item">
        <b>{num(m.tokens_per_s ?? 0, 1)}</b> tok/s
      </span>
      <span className="franja-amd-sep" />
      <span className="franja-amd-item">
        <b>{num(m.total_calls ?? 0)}</b> {t("calls", "llamadas")}
      </span>
      <span className="franja-amd-item">
        {t("fallbacks", "respaldos")} <b>{num(respaldos)}</b>
      </span>
    </div>
  );
}
