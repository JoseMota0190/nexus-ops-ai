import { useEffect, useRef } from "react";
import { PANELES } from "./MenuLateral.jsx";

/**
 * La caja que se superpone sobre el mapa. Apretar la X o el fondo de atrás
 * la cierra y volvés al mapa sin haber perdido de vista.
 */
export default function PanelModal({ panel, onCerrar, children }) {
  const caja = useRef(null);

  useEffect(() => {
    if (!panel) return;
    const tecla = (e) => {
      if (e.key === "Escape") onCerrar();
    };
    window.addEventListener("keydown", tecla);
    // Devuelve el foco a la caja para que Escape funcione siempre.
    caja.current?.focus();
    return () => window.removeEventListener("keydown", tecla);
  }, [panel, onCerrar]);

  if (!panel) return null;
  const meta = PANELES.find((p) => p.id === panel) ?? { icono: "📄", titulo: panel };

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
          <button className="menu-x" onClick={onCerrar} aria-label="Cerrar el panel">
            ✕
          </button>
        </div>
        <div className="modal-cuerpo">{children}</div>
      </div>
    </>
  );
}
