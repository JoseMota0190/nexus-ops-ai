import { useState } from "react";
import { api } from "../api.js";

const CALIFICACIONES = {
  calido: { texto: "Cálido — quiere visita ya", clase: "etiqueta-verde" },
  tibio: { texto: "Tibio — interesado", clase: "etiqueta-azul" },
  frio: { texto: "Frío — solo cotiza", clase: "etiqueta-roja" },
  no_compra: { texto: "No compra", clase: "etiqueta-roja" },
};

export default function AgenteVivo() {
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [llamada, setLlamada] = useState(null);

  async function escuchar() {
    setCargando(true);
    setError(null);
    try {
      const r = await api.llamadaEnVivo();
      setLlamada(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  const resp = llamada?.respuesta;
  const calif = resp ? CALIFICACIONES[resp.calificacion] : null;

  return (
    <div className="panel">
      <h2 className="panel-titulo">
        <span className="icono">🎙️</span> El agente habla (en vivo)
      </h2>
      <p className="panel-sub">
        El teleoperador IA llama a un cliente de verdad y le contesta con su propia voz de
        texto. Mirá cómo conversa.
      </p>

      <button
        className="boton boton-primario"
        onClick={escuchar}
        disabled={cargando}
        style={{ width: "100%" }}
      >
        {cargando ? "Llamando…" : "📞 Escuchar una llamada del agente"}
      </button>

      {error ? (
        <div className="error-caja" style={{ marginTop: 12 }}>
          {error}
        </div>
      ) : null}

      <div className="bocadito">
        {cargando ? (
          <>
            <div className="burbuja burbuja-sistema">
              📞 Sonando… (el cerebro está pensando la respuesta)
            </div>
            <div className="burbuja burbuja-sistema tres-dots">
              <span />
              <span />
              <span />
            </div>
          </>
        ) : null}

        {!cargando && !llamada ? (
          <div className="burbuja burbuja-sistema">
            Apretá el botón de arriba para escuchar una llamada de verdad.
          </div>
        ) : null}

        {!cargando && llamada ? (
          <>
            <div className="burbuja burbuja-sistema">
              📞 Llamando a <strong>{llamada.cliente}</strong> — {llamada.barrio}
              {llamada.telefono ? ` · ${llamada.telefono}` : ""}
            </div>
            <div className="burbuja burbuja-cliente">
              <div className="quien">{llamada.cliente} (cliente)</div>
              Hola, me llegó su formulario. ¿Qué tipo de alarma le interesa?
            </div>
            <div className="burbuja burbuja-agente">
              <div className="quien">Agente teleoperador (IA)</div>
              {resp?.reply_text ?? "—"}
            </div>
            {resp ? (
              <div className="ficha-respuesta">
                {calif ? (
                  <span className={`etiqueta ${calif.clase}`}>{calif.texto}</span>
                ) : null}
                {resp.cierra_cita ? (
                  <span className="etiqueta etiqueta-verde">Cerró la visita</span>
                ) : null}
                {resp.producto ? (
                  <span className="etiqueta etiqueta-azul">Kit: {resp.producto}</span>
                ) : null}
                {resp.propone_horario ? (
                  <span className="etiqueta etiqueta-azul">
                    Propone {resp.propone_horario}
                  </span>
                ) : null}
                {!resp.direccion_valida_caba ? (
                  <span className="etiqueta etiqueta-roja">Dirección fuera de CABA</span>
                ) : null}
                {resp.requiere_visita_humana ? (
                  <span className="etiqueta etiqueta-roja">Deriva a un humano</span>
                ) : null}
                {resp.motivo ? (
                  <span className="etiqueta etiqueta-azul">{resp.motivo}</span>
                ) : null}
                {resp.motivo_no_compra ? (
                  <span className="etiqueta etiqueta-roja">{resp.motivo_no_compra}</span>
                ) : null}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
