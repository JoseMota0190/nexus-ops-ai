import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { getIdioma, setIdioma, t, useIdioma } from "./i18n.js";
import FranjaAMD from "./components/FranjaAMD.jsx";
import SectorPanel from "./components/SectorPanel.jsx";
import MapaCaba from "./components/MapaCaba.jsx";
import Logo from "./components/Logo.jsx";
import TiraFin from "./components/TiraFin.jsx";
import MenuLateral from "./components/MenuLateral.jsx";
import PanelModal from "./components/PanelModal.jsx";
import Pelicula from "./components/Pelicula.jsx";
import SalaAgentes from "./components/SalaAgentes.jsx";

const REFRESCO_ESTADO = 4000; // the "live" status every 4 seconds
const REFRESCO_PESADO = 12000; // charts and tables, more calmly

export default function App() {
  const idioma = useIdioma(); // re-renders the whole screen when it changes
  const [estado, setEstado] = useState(null);
  const [mapa, setMapa] = useState(null);
  const [metricas, setMetricas] = useState(null);
  const [sectores, setSectores] = useState(null);

  const [errEstado, setErrEstado] = useState(null);
  const [errPesado, setErrPesado] = useState({});

  const [cargandoEstado, setCargandoEstado] = useState(true);
  const [cargandoPesado, setCargandoPesado] = useState(true);
  const [ocupado, setOcupado] = useState(null);
  const [aviso, setAviso] = useState(null);

  // The new screen: side menu, open panel and the day's movie.
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [panel, setPanel] = useState(null);
  const [pelicula, setPelicula] = useState(null);
  const [velocidad, setVelocidad] = useState(3);
  const [rapido, setRapido] = useState(false); // switch: fast mode vs live room
  const [enVivo, setEnVivo] = useState(null); // progress of the day running in the background

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
      ["mapa", api.mapa, setMapa],
      ["metricas", api.metricas, setMetricas],
      ["sectores", api.sectores, setSectores],
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

  // Boot + polling: status every 4 s, the heavy stuff every 12 s.
  useEffect(() => {
    vivo.current = true;
    (async () => {
      // Make the backend speak the same language as the screen (it may have been
      // restarted since the last visit). English is a no-op.
      try {
        await api.idioma(getIdioma());
      } catch {
        /* if the engine is down, the normal error path will say so */
      }
      if (vivo.current) await refrescarTodo();
    })();
    const timerEstado = setInterval(traerEstado, REFRESCO_ESTADO);
    const timerPesado = setInterval(traerPesado, REFRESCO_PESADO);
    return () => {
      vivo.current = false;
      clearInterval(timerEstado);
      clearInterval(timerPesado);
      if (avisoTimer.current) clearTimeout(avisoTimer.current);
    };
  }, [refrescarTodo, traerEstado, traerPesado]);

  // The mode switch: the backend decides whether the room is negotiating or not.
  useEffect(() => {
    if (estado?.enjambre) setRapido(estado.enjambre.modo_sala === false);
  }, [estado?.enjambre?.modo_sala]);

  // LIVE DAY: if the room is negotiating, the day runs in the background and here
  // we ask how it is going every 2 s, so the bubbles keep appearing. When it
  // finishes, we open the day's movie (which already carries all the events).
  const hayVivo = enVivo !== null;

  // THE WAITING ROOM: there is a single simulation turn. If somebody else is
  // running it (a day, a month, a language change…), we lock the buttons and show
  // a friendly notice until their turn ends. The status poll (every 4 s) unlocks
  // it on its own, because the backend frees the turn when it finishes. Our own
  // run is never treated as "someone else" (hayVivo / ocupado).
  const trabajoAjeno = !!estado?.turno?.activo && !hayVivo && !ocupado;

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
          mostrarAviso("error", t(`The live day stopped: ${d.error}`,
                                   `El día en vivo se cortó: ${d.error}`));
        } else if (d.resultado) {
          setPelicula(d.resultado);
          if (d.resultado.mes_cerrado) {
            mostrarAviso(
              "ok",
              t(`Month ${d.resultado.mes_cerrado_numero} closed: all 4 sectors filed their report.`,
                `Cerró el mes ${d.resultado.mes_cerrado_numero}: los 4 sectores presentaron su informe.`),
            );
          } else {
            mostrarAviso("ok", t("The day is done: watch the movie to see how it went.",
                                 "Terminó el día: mirá la película para ver cómo fue."));
          }
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

  // ------------------------------------------------------------- actions
  // A full day: the engine solves it instantly and then we REPLAY it in slow
  // motion, so the owner sees the operation breathing.
  async function correrUnDia() {
    if (ocupado || pelicula) return;
    setAviso(null);

    // Live room (month 7 onward): the agents negotiate sale by sale and AMD
    // thinks slowly, so the day runs in the BACKGROUND and we watch it fill up
    // live. The rest is followed by the live-day effect (the one polling every 2 s).
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

    // Fast mode: the day is solved instantly.
    setOcupado("dia");
    try {
      const r = await api.avanzarDia();
      if (r && typeof r === "object" && r.leads !== undefined) {
        setPelicula(r); // starts the movie (if there is no script, it skips it)
      }
      await refrescarTodo();
      if (r?.mes_cerrado) {
        mostrarAviso(
          "ok",
          t(`Month ${r.mes_cerrado_numero} closed: all 4 sectors filed their report.`,
            `Cerró el mes ${r.mes_cerrado_numero}: los 4 sectores presentaron su informe.`),
        );
      }
    } catch (e) {
      mostrarAviso("error", e.message);
    } finally {
      setOcupado(null);
    }
  }

  // The switch: go from "live room" (the agents negotiate every sale) to
  // "fast mode" (the days run without chat) and back.
  async function cambiarModo() {
    if (ocupado || pelicula) return;
    const nuevo = !rapido;
    try {
      await api.modo(nuevo);
      setRapido(nuevo);
      mostrarAviso(
        "ok",
        nuevo
          ? t("Fast mode: the days run without chat (to get far).",
              "Modo rápido: los días corren sin charla (para llegar lejos).")
          : t("Live room: the agents negotiate every sale live.",
              "Sala en vivo: los agentes negocian venta por venta."),
      );
      await refrescarTodo();
    } catch (e) {
      mostrarAviso("error", e.message);
    }
  }

  // The ES/EN button: the backend switches to the base of that language and the
  // whole screen re-renders. It never interrupts a live day.
  async function cambiarIdioma(lang) {
    if (lang === idioma) return;
    try {
      await api.idioma(lang);
      setIdioma(lang);
      await refrescarTodo();
    } catch (e) {
      mostrarAviso("error", e.message);
    }
  }

  function abrirPanel(id) {
    setPanel(id);
    setMenuAbierto(false);
  }

  // The content of each menu panel.
  function contenidoPanel(id) {
    switch (id) {
      // ------------------------------------------------ the 4 SECTORS
      case "gerente":
      case "ventas":
      case "agenda":
      case "facturacion":
        return <SectorPanel sector={id} />;
      default:
        return null;
    }
  }

  // --------------------------------------------------------------- screens
  if (errEstado && !estado) {
    return (
      <div className="app">
        <div className="aviso aviso-info" style={{ marginTop: 18 }}>
          <span>😴</span>
          <span>
            <strong>{t("Waking up the demo…", "Despertando la demo…")}</strong>
            <br />
            {t("The free server takes a few seconds to wake up after a rest. " +
               "This page retries on its own — give it a moment.",
               "El servidor gratuito tarda unos segundos en despertar después de " +
               "un descanso. Esta página reintenta sola: dale un momento.")}
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
        idioma={idioma}
        onIdioma={cambiarIdioma}
        onMenu={() => setMenuAbierto((a) => !a)}
      />

      <main className="escena">
        {/* The CABA map full screen: the BACKGROUND of everything. */}
        <MapaCaba mapa={mapa} cargando={cargandoPesado} error={errPesado.mapa} portada />

        {/* The Nexus logo, breathing at the center of the map. */}
        <div className="logo-centro" aria-hidden="true">
          <div className="logo-caja">
            <Logo tamano={82} className="logo-mark" />
            <div className="logo-nombre">
              NEXUS<span>ALARM</span>
            </div>
            <div className="logo-bajada">{t("Digital twin of the operation",
                                             "Gemelo digital de la operación")}</div>
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
            <span>{t("The engine paused for a moment: I'll keep retrying on my own.",
                     "El motor se tomó un respiro: sigo reintentando solo.")}</span>
          </div>
        ) : null}

        {trabajoAjeno ? (
          <div className="aviso aviso-info aviso-flotante">
            <span>⏳</span>
            <span>{t("Someone is running a simulation right now. Your turn is coming and the buttons unlock on their own.",
                     "Alguien está corriendo una simulación ahora mismo. Ya llega tu turno y los botones se destraban solos.")}</span>
          </div>
        ) : null}
      </main>

      {/* The FOOTER: the simulation box + the Agent Room + the AMD strip. */}
      <footer className="pie">
        <div className="menu-simulacion">
          <button
            className="boton boton-primario"
            onClick={correrUnDia}
            disabled={!!ocupado || !!pelicula || trabajoAjeno}
          >
            {ocupado === "dia" ? t("Running the day…", "Corriendo el día…")
              : t("▶ Run one day", "▶ Correr un día")}
          </button>

          <span className="menu-sim-e">{t("Movie speed", "Velocidad de la película")}</span>
          <div className="menu-sim-vel">
            {[3, 6, 9].map((v) => (
              <button
                key={v}
                className={`dia-chip ${v === velocidad ? "activo" : ""}`}
                onClick={() => setVelocidad(v)}
                disabled={!!pelicula || trabajoAjeno}
              >
                {v} min
              </button>
            ))}
          </div>

          <span className="menu-sim-e">{t("Swarm mode", "Modo enjambre")}</span>
          <button
            className={`boton boton-chico ${rapido ? "boton-fantasma" : "boton-primario"}`}
            onClick={cambiarModo}
            disabled={!!ocupado || !!pelicula || trabajoAjeno}
            title={t("In live room mode, the AI negotiates every sale (from month 7 on)",
                     "En modo sala, la IA negocia cada venta (desde el mes 7)")}
          >
            {rapido ? t("⚡ Fast mode", "⚡ Modo rápido") : t("🗣️ Live room", "🗣️ Sala en vivo")}
          </button>
        </div>

        {/* The AGENT ROOM, inside the same simulation box. */}
        <section className="sim-sala">
          <div className="sim-sala-cab">
            <span className="sim-sala-titulo">{t("🗣️ Live agent room", "🗣️ Sala de agentes en vivo")}</span>
            <span className="sim-sala-nota">
              {t("The agents negotiate every sale on AMD; here you see the chat exactly as it is.",
                 "Los agentes negocian cada venta sobre AMD; acá ves la charla tal cual es.")}
            </span>
          </div>
          <div className="sim-sala-caja">
            <SalaAgentes estado={estado} refrescoMs={6000} />
          </div>
        </section>

        {/* The AMD strip: the pulse of the brain, always in sight. */}
        <FranjaAMD metricas={metricas} />
      </footer>

        {/* The LIVE DAY: while the agents negotiate, we cover the map with the room
            and let the bubbles keep appearing (AMD thinks slowly, ~15 s). */}
        {enVivo ? (
          <div className="vivo-envoltorio">
            <div className="vivo-caja">
              <div className="vivo-cab">
                <span className="sala-pill sala-on">
                  <i className="sala-punto" /> {t("LIVE DAY · the agents are negotiating",
                                                  "DÍA EN VIVO · los agentes están negociando")}
                </span>
                <span className="vivo-progreso">
                  {enVivo.agendadas_hoy > 0
                    ? t(`${enVivo.agendadas_hoy} ${enVivo.agendadas_hoy === 1 ? "sale booked" : "sales booked"} today`,
                        `${enVivo.agendadas_hoy} ${enVivo.agendadas_hoy === 1 ? "venta agendada" : "ventas agendadas"} hoy`)
                    : t("starting the day…", "arrancando el día…")}
                </span>
              </div>
              <p className="vivo-bajada">
                {t("The brain runs on AMD and thinks slowly (about 15 s per agent), so the day builds up little by little. Watch the room fill up.",
                   "El cerebro corre sobre AMD y piensa despacio (unos 15 s por agente), así que el día se arma de a poco. Mirá cómo se llena la sala.")}
              </p>
              <div className="vivo-sala">
                <SalaAgentes estado={estado} refrescoMs={2500} />
              </div>
            </div>
          </div>
        ) : null}

        {/* The day's movie: it covers the map while it plays. */}
        {diaParaPelicula ? (
          <div className="pelicula-envoltorio">
            <Pelicula
              dia={diaParaPelicula}
              velocidadInicial={velocidad}
              onTerminar={() => setPelicula(null)}
            />
          </div>
        ) : null}

      <MenuLateral
        abierto={menuAbierto}
        panelActivo={panel}
        onAbrir={abrirPanel}
        onCerrar={() => setMenuAbierto(false)}
        sectores={sectores}
      />

      <PanelModal panel={panel} onCerrar={() => setPanel(null)}>
        {contenidoPanel(panel)}
      </PanelModal>
    </div>
  );
}
