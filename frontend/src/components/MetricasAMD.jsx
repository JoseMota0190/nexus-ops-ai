import { num, pct } from "../format.js";

export default function MetricasAMD({ metricas, cargando, error }) {
  return (
    <div className="panel panel-amd">
      <h2 className="panel-titulo">
        <span className="icono">🧠</span> Cerebro servido por{" "}
        <span className="amd-logo">AMD · TOKENFACTORY</span>
      </h2>
      <p className="panel-sub">
        El modelo abierto que opina en las llamadas y en las reuniones corre en AMD. Estas
        son las métricas de esa conexión.
      </p>

      {error ? <div className="error-caja">{error}</div> : null}
      {!error && cargando && !metricas ? (
        <div className="cargando">Leyendo las métricas del cerebro…</div>
      ) : null}

      {metricas ? (
        <>
          <div className="amd-grid">
            <div className="amd-dato">
              <div className="k">Modelo</div>
              <div className="v chico">{metricas.modelo || "mock"}</div>
            </div>
            <div className="amd-dato">
              <div className="k">Modo</div>
              <div className="v chico">
                {metricas.modo_mock ? "🔴 Modo mock (sin red)" : "🟢 En red (AMD real)"}
              </div>
            </div>
            <div className="amd-dato">
              <div className="k">Llamadas al modelo</div>
              <div className="v">{num(metricas.total_calls ?? 0)}</div>
            </div>
            <div className="amd-dato">
              <div className="k">Latencia p50</div>
              <div className="v">{num(metricas.latency_p50_ms ?? 0, 0)} ms</div>
            </div>
            <div className="amd-dato">
              <div className="k">Latencia p95</div>
              <div className="v">{num(metricas.latency_p95_ms ?? 0, 0)} ms</div>
            </div>
            <div className="amd-dato">
              <div className="k">Tokens por segundo</div>
              <div className="v ondas">{num(metricas.tokens_per_s ?? 0, 1)}</div>
            </div>
          </div>

          <div className="amd-fila">
            <span>
              Tokens de entrada: <strong>{num(metricas.prompt_tokens ?? 0)}</strong>
            </span>
            <span>
              · Salida: <strong>{num(metricas.completion_tokens ?? 0)}</strong>
            </span>
            <span>
              · Errores: <strong>{num(metricas.errors ?? 0)}</strong>
            </span>
            <span>
              · De caché: <strong>{num(metricas.cached_calls ?? 0)}</strong>
            </span>
            <span>
              · Respaldos: <strong>{num(metricas.fallback_calls ?? 0)}</strong>
            </span>
          </div>

          {metricas.base_url ? (
            <div className="amd-fila" style={{ fontSize: 12 }}>
              Endpoint: <code>{metricas.base_url}</code>
            </div>
          ) : null}

          <div className="amd-fila">
            {metricas.modo_mock ? (
              <span className="etiqueta etiqueta-roja">
                Demo sin red — el cerebro responde con guiones simulados
              </span>
            ) : (
              <span className="etiqueta etiqueta-verde">
                Requisito del jurado: el LLM corre sobre AMD (Radeon Cloud / GPU)
              </span>
            )}
            {metricas.total_calls > 0 ? (
              <span className="etiqueta etiqueta-azul">
                {pct(
                  (1 - (metricas.errors ?? 0) / Math.max(1, metricas.total_calls)) * 100,
                  1,
                )}{" "}
                de éxito
              </span>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
