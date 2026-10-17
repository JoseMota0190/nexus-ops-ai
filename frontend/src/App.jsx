import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Kpis from "./components/Kpis.jsx";
import Escenario from "./components/Escenario.jsx";
import Evolucion from "./components/Evolucion.jsx";
import Acta from "./components/Acta.jsx";
import { LogLlamadas, Motivos } from "./components/Llamadas.jsx";
import AgenteVivo from "./components/AgenteVivo.jsx";
import DetalleDia from "./components/DetalleDia.jsx";
import MetricasAMD from "./components/MetricasAMD.jsx";
import MapaCaba from "./components/MapaCaba.jsx";
import TiraFin from "./components/TiraFin.jsx";
import MenuLateral from "./components/MenuLateral.jsx";
import PanelModal from "./components/PanelModal.jsx";
import Pelicula from "./components/Pelicula.jsx";
import SalaAgentes from "./components/SalaAgentes.jsx";

const REFRESCO_ESTADO = 4000; // el estado "vivo" cada 4 segundos
const REFRESCO_PESADO = 12000; // los gráficos y tablas, más tranqui

export default function App() {
  const [estado, setEstado] = useState(null);
  const [resumenes, setResumenes] = useState([]);
  const [llamadas, setLlamadas] = useState([]);
  const [mapa, setMapa] = useState(null);
  const [metricas, setMetricas] = useState(null);
  const [actas, setActas] = useState([]);

  const [errEstado, setErrEstado] = useState(null);
  const [errPesado, setErrPesado] = useState({});

  const [cargandoEstado, setCargandoEstado] = useState(true);
  const [cargandoPesado, setCargandoPesado] = useState(true);
  const [ocupado, setOcupado] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [detalleDia, setDetalleDia] = useState(null); // resumen del último día corrido

  // La nueva pantalla: menú lateral, panel abierto y la película del día.
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [panel, setPanel] = useState(null);
  const [pelicula, setPelicula] = useState(null);
  const [velocidad, setVelocidad] = useState(3);
  const [rapido, setRapido] = useState(false); // interruptor: modo rápido vs sala
  const [enVivo, setEnVivo] = useState(null); // progreso del día que corre en segundo plano

  const vivo = useRef(true);
  const avisoTimer = useRef(null);

  const mostrarAviso = useCallback((tipo, texto) => {
    setAviso({ tipo, texto });
    if (avisoTimer.current) clearTimeout(avisoTimer.current);
    avisoTimer.current = setTimeout(() => setAviso(null), 7000);
  }, []);

  const traerEstado = useCallback(async () => {
    try {
      const e = await api.estado();
      if (!vivo.current) return;
      setEstado(e);
      setErrEstado(null);
    } catch (e2) {
      if (vivo.current) setErrEstado(e2.message);
    } finally {
      if (vivo.current) setCargandoEstado(false);
    }
  }, []);

  const traerPesado = useCallback(async () => {
    const tareas = [
      ["resumenes", api.resumenes, setResumenes],
      ["llamadas", api.llamadas, setLlamadas],
      ["mapa", api.mapa, setMapa],
      ["metricas", api.metricas, setMetricas],
      ["actas", api.actas, setActas],
    ];
    const errores = {};
    await Promise.all(
      tareas.map(async ([clave, pedir, guardar]) => {
        try {
          const r = await pedir();
          if (!vivo.current) return;
          guardar(r);
        } catch (e) {
          errores[clave] = e.message;
        }
      }),
    );
    if (!vivo.current) return;
    setErrPesado(errores);
    setCargandoPesado(false);
  }, []);

  const refrescarTodo = useCallback(async () => {
    await Promise.all([traerEstado(), traerPesado()]);
  }, [traerEstado, traerPesado]);

  // Arranque + polling: el estado cada 4 s, lo pesado cada 12 s.
  useEffect(() => {
    vivo.current = true;
    refrescarTodo();
    const t1 = setInterval(traerEstado, REFRESCO_ESTADO);
    const t2 = setInterval(traerPesado, REFRESCO_PESADO);
    return () => {
      vivo.current = false;
      clearInterval(t1);
      clearInterval(t2);
      if (avisoTimer.current) clearTimeout(avisoTimer.current);
    };
  }, [refrescarTodo, traerEstado, traerPesado]);

  // El interruptor de modo: el backend manda si la Sala está negociando o no.
  useEffect(() => {
    if (estado?.enjambre) setRapido(estado.enjambre.modo_sala === false);
  }, [estado?.enjambre?.modo_sala]);

  // DÍA EN VIVO: si la Sala está negociando, el día corre en segundo plano y acá
  // preguntamos cómo va cada 2 s, para que las burbujas vayan apareciendo. Cuando
  // termina, abrimos la película del día (que ya trae todos los eventos).
  const hayVivo = enVivo !== null;
  useEffect(() => {
    if (!hayVivo) return undefined;
    let cancelado = false;

    const tic = async () => {
      try {
        const d = await api.diaEnVivoEstado();
        if (cancelado || !vivo.current) return;
        if (d.progreso) setEnVivo(d.progreso);
        if (!d.listo) return;
        cancelado = true;
        setEnVivo(null);
        setOcupado(null);
        if (d.error) {
          mostrarAviso("error", `El día en vivo se cortó: ${d.error}`);
        } else if (d.resultado) {
          setDetalleDia(d.resultado);
          setPelicula(d.resultado);
          mostrarAviso("ok", "El día terminó: mirá cómo lo cuenta la película.");
        }
        await refrescarTodo();
      } catch (e) {
        if (!cancelado && vivo.current) {
          setEnVivo(null);
          setOcupado(null);
          mostrarAviso("error", e.message);
        }
      }
    };

    const t = setInterval(tic, 2000);
    tic();
    return () => {
      cancelado = true;
      clearInterval(t);
    };
  }, [hayVivo, refrescarTodo, mostrarAviso]);

  // ------------------------------------------------------------- acciones
  async function correr(que, funcion, mensajeOk) {
    if (ocupado) return undefined;
    setOcupado(que);
    setAviso(null);
    try {
      const r = await funcion();
      const extra =
        r && typeof r === "object" && r.corridos !== undefined
          ? ` (${r.corridos} ${r.corridos === 1 ? "mes" : "meses"} corridos)`
          : "";
      mostrarAviso("ok", mensajeOk + extra);
      await refrescarTodo();
      return r;
    } catch (e) {
      mostrarAviso("error", e.message);
      return undefined;
    } finally {
      setOcupado(null);
    }
  }

  const avanzarMes = () =>
    correr("mes", api.avanzarMes, "Listo: el mes se corrió y el Gerente IA dejó su acta.");

  // Un día entero: el motor lo resuelve al instante y después lo REPRODUCIMOS
  // a cámara lenta, para que el dueño vea la operación respirando.
  async function correrUnDia() {
    if (ocupado || pelicula) return;
    setAviso(null);

    // Modo sala (mes 7 en adelante): los agentes negocian venta por venta y AMD
    // piensa lento, así que el día corre en SEGUNDO PLANO y lo vemos llenarse en
    // vivo. El resto lo sigue el efecto del día en vivo (el que pregunta cada 2 s).
    if (estado?.enjambre?.activo) {
      setOcupado("dia");
      setEnVivo({ agendadas_hoy: 0, negociados_hoy: 0 });
      try {
        await api.diaEnVivo();
      } catch (e) {
        setEnVivo(null);
        setOcupado(null);
        mostrarAviso("error", e.message);
      }
      return;
    }

    // Modo rápido: el día se resuelve al toque.
    setOcupado("dia");
    try {
      const r = await api.avanzarDia();
      if (r && typeof r === "object" && r.leads !== undefined) {
        setDetalleDia(r);
        setPelicula(r); // arranca la película (si no hay guion, se la salta)
      }
      await refrescarTodo();
    } catch (e) {
      mostrarAviso("error", e.message);
    } finally {
      setOcupado(null);
    }
  }

  const correrSeis = () =>
    correr("seis", () => api.correrTodo(6), "¡Seis meses corridos de una!");

  // El interruptor: pasar de "modo sala" (los agentes negocian cada venta) a
  // "modo rápido" (los días corren sin charla) y viceversa.
  async function cambiarModo() {
    if (ocupado || pelicula) return;
    const nuevo = !rapido;
    try {
      await api.modo(nuevo);
      setRapido(nuevo);
      mostrarAviso(
        "ok",
        nuevo
          ? "Modo rápido: los días corren sin charla (para llegar lejos)."
          : "Modo sala: los agentes negocian cada venta en vivo.",
      );
      await refrescarTodo();
    } catch (e) {
      mostrarAviso("error", e.message);
    }
  }
  const reiniciar = () => {
    if (
      !window.confirm(
        "¿Reiniciar la simulación? Se borran los 9 meses corridos y volvemos al mes 1.",
      )
    ) {
      return;
    }
    correr("reiniciar", api.reiniciar, "Simulación reiniciada: arrancamos de cero.");
  };

  function abrirPanel(id) {
    setPanel(id);
    setMenuAbierto(false);
  }

  // El contenido de cada panel del menú.
  function contenidoPanel(id) {
    switch (id) {
      case "sala":
        return <SalaAgentes estado={estado} />;
      case "kpis":
        return <Kpis estado={estado} />;
      case "dia":
        return <DetalleDia detalle={detalleDia} />;
      case "llamadas":
        return (
          <LogLlamadas llamadas={llamadas} cargando={cargandoPesado} error={errPesado.llamadas} />
        );
      case "motivos":
        return <Motivos motivos={estado?.motivos} cargando={cargandoEstado} error={errEstado} />;
      case "gerente":
        return (
          <Acta
            actas={actas}
            decisiones={estado?.decisiones ?? []}
            cargando={cargandoPesado}
            error={errPesado.actas}
          />
        );
      case "evolucion":
        return (
          <Evolucion
            resumenes={resumenes}
            cargando={cargandoPesado}
            error={errPesado.resumenes}
          />
        );
      case "mapa":
        return <MapaCaba mapa={mapa} cargando={cargandoPesado} error={errPesado.mapa} />;
      case "escenario":
        return <Escenario estado={estado} />;
      case "agente":
        return <AgenteVivo />;
      case "amd":
        return <MetricasAMD metricas={metricas} cargando={cargandoPesado} error={errPesado.metricas} />;
      default:
        return null;
    }
  }

  // --------------------------------------------------------------- pantallas
  if (errEstado && !estado) {
    return (
      <div className="app">
        <div className="aviso aviso-error" style={{ marginTop: 18 }}>
          <span>🚧</span>
          <span>
            <strong>No pude conectar con el motor de la simulación.</strong>
            <br />
            {errEstado}
            <br />
            Fijate de levantarlo con{" "}
            <code>.\.venv\Scripts\python.exe -m uvicorn api:app --port 8000</code> desde la
            carpeta <code>backend</code> y volvé a cargar la página.
          </span>
        </div>
      </div>
    );
  }

  const diaParaPelicula = pelicula?.pelicula?.eventos?.length ? pelicula : null;

  return (
    <div className="portada">
      <TiraFin
        estado={estado}
        cargando={cargandoEstado}
        corriendo={ocupado}
        menuAbierto={menuAbierto}
        onMenu={() => setMenuAbierto((a) => !a)}
      />

      <main className="escena">
        {/* El mapa de CABA a pantalla completa: el FONDO de todo. */}
        <MapaCaba mapa={mapa} cargando={cargandoPesado} error={errPesado.mapa} portada />

        {/* El logo de Nexus, respirando en el centro del mapa. */}
        <div className="logo-centro" aria-hidden="true">
          <div className="logo-caja">
            <div className="logo-nombre">
              NEXUS<span>ALARM</span>
            </div>
            <div className="logo-bajada">Gemelo digital de la operación</div>
          </div>
        </div>

        {aviso ? (
          <div className={`aviso aviso-${aviso.tipo} aviso-flotante`}>
            <span>{aviso.tipo === "ok" ? "✅" : "⚠️"}</span>
            <span>{aviso.texto}</span>
          </div>
        ) : null}

        {errEstado && estado ? (
          <div className="aviso aviso-info aviso-flotante">
            <span>💤</span>
            <span>El motor dejó de responder por un momento: sigo reintentando solo.</span>
          </div>
        ) : null}
      </main>

      {/* El cuadro de simulación: abajo del mapa, lo único que el dueño toca. */}
      <div className="menu-simulacion">
          <button
            className="boton boton-primario"
            onClick={correrUnDia}
            disabled={!!ocupado || !!pelicula}
          >
            {ocupado === "dia" ? "Corriendo el día…" : "▶ Correr un día"}
          </button>

          <span className="menu-sim-e">Velocidad de la película</span>
          <div className="menu-sim-vel">
            {[3, 6, 9].map((v) => (
              <button
                key={v}
                className={`dia-chip ${v === velocidad ? "activo" : ""}`}
                onClick={() => setVelocidad(v)}
                disabled={!!pelicula}
              >
                {v} min
              </button>
            ))}
          </div>

          <span className="menu-sim-e">Modo del enjambre</span>
          <button
            className={`boton boton-chico ${rapido ? "boton-fantasma" : "boton-primario"}`}
            onClick={cambiarModo}
            disabled={!!ocupado || !!pelicula}
            title="En modo sala, la IA negocia cada venta (a partir del mes 7)"
          >
            {rapido ? "⚡ Modo rápido" : "🗣️ Modo sala"}
          </button>
        </div>

        {/* El DÍA EN VIVO: mientras los agentes negocian, tapamos el mapa con la Sala
            y dejamos que las burbujas vayan apareciendo (AMD piensa lento, ~15 s). */}
        {enVivo ? (
          <div className="vivo-envoltorio">
            <div className="vivo-caja">
              <div className="vivo-cab">
                <span className="sala-pill sala-on">
                  <i className="sala-punto" /> DÍA EN VIVO · los agentes están negociando
                </span>
                <span className="vivo-progreso">
                  {enVivo.agendadas_hoy > 0
                    ? `${enVivo.agendadas_hoy} ${enVivo.agendadas_hoy === 1 ? "venta agendada" : "ventas agendadas"} hoy`
                    : "arrancando el día…"}
                </span>
              </div>
              <p className="vivo-bajada">
                El cerebro corre sobre AMD y piensa lento (unos 15 s por agente), así que
                el día se va armando de a poco. Mirá cómo se llena la sala.
              </p>
              <div className="vivo-sala">
                <SalaAgentes estado={estado} refrescoMs={2500} />
              </div>
            </div>
          </div>
        ) : null}

        {/* La película del día: tapa el mapa mientras se reproduce. */}
        {diaParaPelicula ? (
          <div className="pelicula-envoltorio">
            <Pelicula
              dia={diaParaPelicula}
              velocidadInicial={velocidad}
              onTerminar={() => {
                setPelicula(null);
                setPanel("dia");
              }}
            />
          </div>
        ) : null}

      <MenuLateral
        abierto={menuAbierto}
        panelActivo={panel}
        onAbrir={abrirPanel}
        onCerrar={() => setMenuAbierto(false)}
      />

      <PanelModal panel={panel} onCerrar={() => setPanel(null)}>
        {contenidoPanel(panel)}
      </PanelModal>
    </div>
  );
}
