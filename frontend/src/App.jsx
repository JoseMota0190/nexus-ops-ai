import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Cabecera from "./components/Cabecera.jsx";
import Kpis from "./components/Kpis.jsx";
import Escenario from "./components/Escenario.jsx";
import Evolucion from "./components/Evolucion.jsx";
import Acta from "./components/Acta.jsx";
import { LogLlamadas, Motivos } from "./components/Llamadas.jsx";
import AgenteVivo from "./components/AgenteVivo.jsx";
import MetricasAMD from "./components/MetricasAMD.jsx";
import MapaCaba from "./components/MapaCaba.jsx";

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

  // ------------------------------------------------------------- acciones
  async function correr(que, funcion, mensajeOk) {
    if (ocupado) return;
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
    } catch (e) {
      mostrarAviso("error", e.message);
    } finally {
      setOcupado(null);
    }
  }

  const avanzarMes = () =>
    correr("mes", api.avanzarMes, "Listo: el mes se corrió y el Gerente IA dejó su acta.");
  const correrSeis = () =>
    correr("seis", () => api.correrTodo(6), "¡Seis meses corridos de una!");
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

  // --------------------------------------------------------------- pantallas
  if (errEstado && !estado) {
    return (
      <div className="app">
        <Cabecera estado={null} cargando ocupado={ocupado} />
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

  return (
    <div className="app">
      <Cabecera
        estado={estado}
        cargando={cargandoEstado}
        ocupado={ocupado}
        onAvanzar={avanzarMes}
        onCorrerSeis={correrSeis}
        onReiniciar={reiniciar}
      />

      {aviso ? (
        <div className={`aviso aviso-${aviso.tipo}`}>
          <span>{aviso.tipo === "ok" ? "✅" : "⚠️"}</span>
          <span>{aviso.texto}</span>
        </div>
      ) : null}

      {errEstado && estado ? (
        <div className="aviso aviso-info">
          <span>💤</span>
          <span>El motor dejó de responder por un momento: sigo reintentando solo.</span>
        </div>
      ) : null}

      <Kpis estado={estado} />

      <section className="paneles">
        <Escenario estado={estado} />

        <Acta
          actas={actas}
          decisiones={estado?.decisiones ?? []}
          cargando={cargandoPesado}
          error={errPesado.actas}
        />

        <div className="panel panel-ancho">
          <h2 className="panel-titulo">
            <span className="icono">📈</span> Evolución mes a mes
          </h2>
          <p className="panel-sub">
            Ingresos contra costos, y cuántos técnicos hay en cada mes. Se ve que{" "}
            <strong>los costos crecen más despacio que las ventas</strong>.
          </p>
          <Evolucion
            resumenes={resumenes}
            cargando={cargandoPesado}
            error={errPesado.resumenes}
          />
        </div>

        <LogLlamadas
          llamadas={llamadas}
          cargando={cargandoPesado}
          error={errPesado.llamadas}
        />

        <Motivos motivos={estado?.motivos} cargando={cargandoEstado} error={errEstado} />

        <AgenteVivo />

        <MetricasAMD
          metricas={metricas}
          cargando={cargandoPesado}
          error={errPesado.metricas}
        />

        <MapaCaba
          mapa={mapa}
          cargando={cargandoPesado}
          error={errPesado.mapa}
        />
      </section>

      <footer
        style={{
          marginTop: 26,
          color: "#6d8199",
          fontSize: 12.5,
          textAlign: "center",
        }}
      >
        Nexus Alarm · gemelo digital de una empresa ficticia de alarmas en CABA · demo AMD
        ACT III / lablab.ai · datos simulados, sin validez fiscal.
      </footer>
    </div>
  );
}
