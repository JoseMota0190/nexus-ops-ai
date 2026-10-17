import { num, usd } from "../format.js";

/**
 * La tira fina de arriba: lo mínimo que el dueño tiene que ver siempre.
 * Mes · técnicos (contra la meta) · ventas por día · plata en caja · clientes.
 * A la derecha, el botón del menú y el chip de quién está manejando la simulación.
 */
export default function TiraFin({ estado, cargando, usuario, corriendo, onMenu, menuAbierto }) {
  const mes = estado?.mes ?? 1;
  const semana = estado?.semana ?? 1;
  const tecnicos = estado?.tecnicos ?? 0;
  const meta = estado?.meta_tecnicos ?? 10;
  const ventas = estado?.ventas_por_dia_potencial ?? 0;
  const caja = estado?.caja ?? 0;
  const clientes = estado?.clientes_activos ?? 0;
  const avance = Math.min(100, Math.round((tecnicos / meta) * 100));

  return (
    <header className="tira">
      <div className="tira-marca">
        <span className="tira-logo">N</span>
        <span className="tira-nombre">
          Nexus <b>Alarm</b>
        </span>
      </div>

      <div className="tira-datos">
        <Dato etiqueta="Mes" valor={cargando ? "—" : String(mes)} />
        <Dato etiqueta="Semana" valor={cargando ? "—" : semana} />
        <Dato
          etiqueta="Técnicos"
          valor={cargando ? "—" : `${tecnicos} / ${meta}`}
          barra={avance}
        />
        <Dato etiqueta="Ventas por día" valor={cargando ? "—" : num(ventas, 1)} />
        <Dato etiqueta="En caja" valor={cargando ? "—" : usd(caja, 0)} />
        <Dato etiqueta="Clientes" valor={cargando ? "—" : num(clientes)} />
      </div>

      <div className="tira-der">
        {corriendo ? (
          <span className="tira-quien" title="Alguien está corriendo la simulación ahora">
            <i className="tira-punto" />
            {corriendo}
          </span>
        ) : usuario ? (
          <span className="tira-usuario" title="Usted está a cargo">
            {usuario}
          </span>
        ) : null}

        <button
          className={`tira-menu ${menuAbierto ? "activo" : ""}`}
          onClick={onMenu}
          aria-label="Abrir el menú de paneles"
          title="Menú"
        >
          ☰
        </button>
      </div>
    </header>
  );
}

function Dato({ etiqueta, valor, barra }) {
  return (
    <div className="tira-dato">
      <span className="tira-dato-e">{etiqueta}</span>
      <span className="tira-dato-v">
        {valor}
        {barra !== undefined && barra !== null ? (
          <i className="tira-barra">
            <b style={{ width: `${Math.max(0, Math.min(100, barra))}%` }} />
          </i>
        ) : null}
      </span>
    </div>
  );
}
