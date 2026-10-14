export default function Acta({ actas, decisiones, cargando, error }) {
  const ultima = actas && actas.length ? actas[actas.length - 1] : null;

  return (
    <div className="panel">
      <h2 className="panel-titulo">
        <span className="icono">📋</span> Reunión mensual de gerencia
      </h2>
      <p className="panel-sub">
        El Gerente IA junta los números del mes, decide qué cambiar y escribe el acta.
      </p>

      {error ? <div className="error-caja">{error}</div> : null}
      {!error && cargando && !ultima ? (
        <div className="cargando">Buscando el último acta…</div>
      ) : null}
      {!error && !cargando && !ultima ? (
        <div className="sin-datos">
          Todavía no hubo reuniones: aparece después del primer mes corrido.
        </div>
      ) : null}

      {ultima ? (
        <div className="acta">
          <div className="acta-mes">Acta del mes {ultima.mes}</div>
          <div className="acta-titulo">{ultima.titulo}</div>
          <div className="acta-cuerpo">{ultima.cuerpo}</div>
          {ultima.meta ? (
            <div className="acta-meta">
              <strong>Meta propuesta:</strong> {ultima.meta}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="sub-motivo" style={{ marginTop: 18 }}>
        Decisiones que tomó
      </div>
      {!decisiones || decisiones.length === 0 ? (
        <div className="sin-datos">Sin decisiones todavía.</div>
      ) : (
        <ul className="lista-decisiones">
          {decisiones.map((d, i) => (
            <li key={`${d.mes}-${d.accion}-${i}`}>
              <div className="dec-cab">
                <span className="etiqueta etiqueta-azul">Mes {d.mes}</span>
                <span>
                  {d.accion}: {d.valor}
                </span>
                <span
                  className={`etiqueta ${d.aprobada ? "etiqueta-verde" : "etiqueta-roja"}`}
                >
                  {d.aprobada ? "Aprobada" : "Descartada"}
                </span>
              </div>
              <div className="dec-motivo">
                {d.motivo}
                {d.aviso ? ` · ${d.aviso}` : ""}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
