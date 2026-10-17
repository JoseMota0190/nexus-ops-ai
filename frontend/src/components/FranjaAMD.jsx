import { num } from "../format.js";

/**
 * La FRANJA AMD: una tira finita, siempre visible abajo, con la salud del
 * cerebro (el modelo que corre sobre AMD) y del redactor (Evolus). No ocupa
 * lugar en el menú: se mira de reojo mientras corre la simulación.
 */
export default function FranjaAMD({ metricas, evolus }) {
  const m = metricas || {};
  const real = m.modo_mock === false;
  const respaldos = m.fallback_calls ?? 0;
  const evolusModo = evolus ? (evolus.mock ? "prueba" : "real") : "—";

  return (
    <div className="franja-amd" role="status" aria-label="Estado del cerebro AMD">
      <span className="franja-amd-tag">🧠 AMD</span>
      <span className={`franja-amd-punto ${real ? "on" : "off"}`} />
      <span className="franja-amd-item">
        <b>{m.modelo || "mock"}</b>
      </span>
      <span className="franja-amd-sep" />
      <span className="franja-amd-item">
        {real ? "en red" : "modo prueba"}
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
        <b>{num(m.total_calls ?? 0)}</b> llamadas
      </span>
      <span className="franja-amd-item">
        respaldos <b>{num(respaldos)}</b>
      </span>
      <span className="franja-amd-sep" />
      <span className="franja-amd-item">
        ✍️ Evolus <b>{evolusModo}</b>
      </span>
    </div>
  );
}
