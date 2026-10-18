import Logo from "./Logo.jsx";
import { t } from "../i18n.js";

/**
 * The top strip: the brand, the ES/EN language button and, on the right, the ☰
 * menu button.
 *
 * It deliberately shows NO numbers: the metrics live in the panels the menu
 * opens (the 4 sectors). That keeps the home screen clean.
 */
export default function TiraFin({ usuario, corriendo, onMenu, menuAbierto, idioma, onIdioma }) {
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
          <span className="tira-quien"
                title={t("The simulation is running right now",
                         "La simulación está corriendo ahora mismo")}>
            <i className="tira-punto" />
            {corriendo}
          </span>
        ) : usuario ? (
          <span className="tira-usuario" title={t("You are in charge", "Estás al mando")}>
            {usuario}
          </span>
        ) : null}

        <div className="tira-idioma" role="group" aria-label={t("Language", "Idioma")}>
          <button
            className={`idioma-chip ${idioma === "en" ? "activo" : ""}`}
            onClick={() => onIdioma?.("en")}
            title={t("See the site in English", "Ver el sitio en inglés")}
          >
            EN
          </button>
          <button
            className={`idioma-chip ${idioma === "es" ? "activo" : ""}`}
            onClick={() => onIdioma?.("es")}
            title={t("See the site in Spanish", "Ver el sitio en español")}
          >
            ES
          </button>
        </div>

        <button
          className={`tira-menu ${menuAbierto ? "activo" : ""}`}
          onClick={onMenu}
          aria-label={t("Open the panels menu", "Abrir el menú de paneles")}
          title={t("Metrics and panels", "Métricas y paneles")}
        >
          ☰
        </button>
      </div>
    </header>
  );
}
