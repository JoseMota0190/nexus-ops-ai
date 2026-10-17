import Logo from "./Logo.jsx";

/**
 * La tira de arriba: la marca y, a la derecha, el botón del menú ☰.
 *
 * A propósito NO muestra números: las métricas viven en los paneles que abre el
 * menú (KPIs, evolución, agenda, mapa…). Así la pantalla de inicio queda limpia.
 */
export default function TiraFin({ usuario, corriendo, onMenu, menuAbierto }) {
  return (
    <header className="tira">
      <div className="tira-marca">
        <Logo tamano={26} />
        <span className="tira-nombre">
          Nexus <b>Alarm</b>
        </span>
      </div>

      <div className="tira-der">
        {corriendo ? (
          <span className="tira-quien" title="Se está corriendo la simulación ahora">
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
          title="Métricas y paneles"
        >
          ☰
        </button>
      </div>
    </header>
  );
}
