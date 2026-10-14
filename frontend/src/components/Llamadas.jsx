import { num } from "../format.js";

function Tabla({ llamadas }) {
  if (!llamadas || llamadas.length === 0) {
    return <div className="sin-datos">Aún no se registró ninguna llamada.</div>;
  }
  return (
    <div className="tabla-wrap">
      <table>
        <thead>
          <tr>
            <th>Cliente</th>
            <th>Barrio</th>
            <th>Contestó</th>
            <th>Motivo</th>
          </tr>
        </thead>
        <tbody>
          {llamadas.map((l) => (
            <tr key={l.id}>
              <td>{l.nombre}</td>
              <td>{l.barrio}</td>
              <td>
                <span className={`pill ${l.atendio ? "pill-si" : "pill-no"}`}>
                  {l.atendio ? "Sí" : "No"}
                </span>
              </td>
              <td>{l.motivo || (l.atendio ? "—" : "Sin dato")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Motivo({ lista, clase }) {
  const max = Math.max(1, ...lista.map((m) => m.n));
  return (
    <>
      {lista.map((m) => (
        <div className="fila-motivo" key={m.motivo}>
          <div className="et">
            <span>{m.motivo}</span>
            <b>{num(m.n)}</b>
          </div>
          <div className={`barra-motivo ${clase}`}>
            <i style={{ width: `${(m.n / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </>
  );
}

export function LogLlamadas({ llamadas, cargando, error }) {
  return (
    <div className="panel">
      <h2 className="panel-titulo">
        <span className="icono">📞</span> Telégrafo de llamadas
      </h2>
      <p className="panel-sub">Los últimos 20 llamados: quién contestó, quién no y por qué.</p>
      {error ? <div className="error-caja">{error}</div> : null}
      {!error && cargando && (!llamadas || llamadas.length === 0) ? (
        <div className="cargando">Leyendo el telégrafo…</div>
      ) : null}
      {!error && !cargando && (!llamadas || llamadas.length === 0) ? (
        <div className="sin-datos">
          Todavía no hay llamadas: corré un mes y el telégrafo se llena.
        </div>
      ) : null}
      {llamadas && llamadas.length > 0 ? <Tabla llamadas={llamadas} /> : null}
    </div>
  );
}

export function Motivos({ motivos, cargando, error }) {
  const noCompra = motivos?.no_compra ?? [];
  const noRespondio = motivos?.no_respondio ?? [];
  const vacio = noCompra.length === 0 && noRespondio.length === 0;

  return (
    <div className="panel">
      <h2 className="panel-titulo">
        <span className="icono">🧾</span> Motivos: por qué no se vende
      </h2>
      <p className="panel-sub">
        Lo que la gente contesta. Acá el Gerente mira para mejorar el servicio.
      </p>

      {error ? <div className="error-caja">{error}</div> : null}
      {!error && cargando && vacio ? <div className="cargando">Juntando motivos…</div> : null}
      {!error && !cargando && vacio ? (
        <div className="sin-datos">Sin motivos registrados todavía.</div>
      ) : null}

      {noCompra.length > 0 ? (
        <div className="bloque-motivo">
          <div className="sub-motivo">Por qué no compran (contestaron)</div>
          <Motivo lista={noCompra} clase="compra" />
        </div>
      ) : null}

      {noRespondio.length > 0 ? (
        <div className="bloque-motivo">
          <div className="sub-motivo">Por qué no contestaron</div>
          <Motivo lista={noRespondio} clase="responde" />
        </div>
      ) : null}
    </div>
  );
}
