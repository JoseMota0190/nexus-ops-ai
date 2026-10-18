import { useEffect, useRef } from "react";
import { metaPaneles } from "./MenuLateral.jsx";
import { t } from "../i18n.js";

/**
 * The box that sits on top of the map. Pressing the X or the backdrop behind
 * it closes it and takes you back to the map without losing sight of it.
 */
export default function PanelModal({ panel, onCerrar, children }) {
  const caja = useRef(null);

  useEffect(() => {
    if (!panel) return;
    const tecla = (e) => {
      if (e.key === "Escape") onCerrar();
    };
    window.addEventListener("keydown", tecla);
    // Give focus back to the box so Escape always works.
    caja.current?.focus();
    return () => window.removeEventListener("keydown", tecla);
  }, [panel, onCerrar]);

  if (!panel) return null;
  const meta = metaPaneles().find((p) => p.id === panel) ?? { icono: "📄", titulo: panel };

  return (
    <>
      <div className="modal-fondo" onClick={onCerrar} />
      <div
        className="modal"
        role="dialog"
        aria-label={meta.titulo}
        tabIndex={-1}
        ref={caja}
      >
        <div className="modal-cab">
          <h2 className="modal-titulo">
            <span className="icono">{meta.icono}</span> {meta.titulo}
          </h2>
          <button className="menu-x" onClick={onCerrar}
                  aria-label={t("Close the panel", "Cerrar el panel")}>
            ✕
          </button>
        </div>
        <div className="modal-cuerpo">{children}</div>
      </div>
    </>
  );
}
