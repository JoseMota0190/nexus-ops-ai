import { useEffect, useMemo, useRef, useState } from "react";
import { num, usd } from "../format.js";

const DIA_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const VELOCIDADES = [
  { minutos: 3, etiqueta: "3 min" },
  { minutos: 6, etiqueta: "6 min" },
  { minutos: 9, etiqueta: "9 min" },
];

// Los agentes que hablan en la sala, con su carita y color.
const AGENTES = {
  operador: { nombre: "Teleoperador", icono: "📞" },
  agenda: { nombre: "Agenda", icono: "📅" },
  tecnicos: { nombre: "Técnicos", icono: "🔧" },
  despacho: { nombre: "Despacho", icono: "🚚" },
};

function reloj(minuto) {
  const h = 8 + Math.floor(minuto / 60);
  const m = Math.floor(minuto % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/**
 * La película del día: el mismo día que ya corrió el motor, pero reproducido
 * a cámara lenta para que el dueño (o el juez) vea la operación respirando.
 *
 * El programa calcula TODO al instante; acá solo lo estamos mostrando de a poco.
 */
export default function Pelicula({ dia, velocidadInicial = 3, onTerminar }) {
  const [minutos, setMinutos] = useState(velocidadInicial);
  const [corriendo, setCorriendo] = useState(true);
  const [transcurrido, setTranscurrido] = useState(0); // fracción 0..1
  const inicio = useRef(null);
  const raf = useRef(null);

  const ev = dia?.pelicula?.eventos ?? [];
  const minIni = dia?.pelicula?.hora_inicio ?? 480;
  const minFin = dia?.pelicula?.hora_fin ?? 1080;
  const span = Math.max(1, minFin - minIni);

  // Reinicia la película si cambia el día o la velocidad elegida.
  useEffect(() => {
    inicio.current = null;
    setTranscurrido(0);
    setCorriendo(true);
  }, [dia, minutos]);

  // El reloj: avanza a lo largo de los minutos elegidos.
  useEffect(() => {
    if (!corriendo || !ev.length) return;
    const durMs = minutos * 60 * 1000;
    const paso = (t) => {
      if (inicio.current === null) inicio.current = t;
      const f = Math.min(1, (t - inicio.current) / durMs);
      setTranscurrido(f);
      if (f < 1) raf.current = requestAnimationFrame(paso);
      else setCorriendo(false);
    };
    raf.current = requestAnimationFrame(paso);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [corriendo, minutos, ev.length]);

  const minutoActual = minIni + span * transcurrido;
  const visibles = useMemo(() => ev.filter((e) => e.minuto <= minutoActual), [ev, minutoActual]);

  // Los contadores crecen a medida que pasan los eventos.
  const c = useMemo(() => {
    const t = { llamadas: 0, atendidas: 0, ventas: 0, instalaciones: 0 };
    for (const e of visibles) {
      if (e.tipo === "instalacion") t.instalaciones++;
      else if (e.tipo === "llamada") {
        t.llamadas++;
        if (e.atendio) t.atendidas++;
        if (e.venta) t.ventas++;
      }
    }
    return t;
  }, [visibles]);

  const listos = !corriendo && transcurrido >= 1;

  return (
    <div className="pelicula">
      <div className="pelicula-cab">
        <div className="pelicula-reloj">
          <span className="pelicula-hora">{reloj(Math.min(minutoActual, minFin))}</span>
          <span className="pelicula-fecha">
            {DIA_CORTO[dia.dia] ?? ""} · Semana {dia.semana} · Mes {dia.mes}
          </span>
        </div>

        <div className="pelicula-vel">
          <span className="pelicula-vel-e">Dura</span>
          {VELOCIDADES.map((v) => (
            <button
              key={v.minutos}
              className={`dia-chip ${v.minutos === minutos ? "activo" : ""}`}
              onClick={() => setMinutos(v.minutos)}
            >
              {v.etiqueta}
            </button>
          ))}
          <button className="dia-chip" onClick={() => setCorriendo((x) => !x)}>
            {corriendo ? "⏸ Pausar" : "▶ Seguir"}
          </button>
          {listos ? (
            <button className="dia-chip activo" onClick={() => setTranscurrido(0)}>
              ↺ Otra vez
            </button>
          ) : null}
        </div>
      </div>

      <div className="barra pelicula-barra">
        <i style={{ width: `${transcurrido * 100}%` }} />
      </div>

      <div className="pelicula-contadores">
        <Contador etiqueta="Llamadas" valor={c.llamadas} total={dia.llamadas} />
        <Contador etiqueta="Contestaron" valor={c.atendidas} total={dia.atendidas} />
        <Contador etiqueta="Ventas" valor={c.ventas} total={dia.ventas} tono="positivo" />
        <Contador
          etiqueta="Instalaciones"
          valor={c.instalaciones}
          total={dia.instalaciones}
          tono="ondas"
        />
        <Contador
          etiqueta="Leads del día"
          valor={Math.min(dia.leads, Math.round(dia.leads * transcurrido))}
          total={dia.leads}
        />
        <Contador etiqueta="Caja" valor={usd(dia.caja, 0)} solo />
      </div>

      <div className="pelicula-cinta" role="log" aria-live="polite">
        {visibles.length === 0 ? (
          <div className="sin-datos">Abriendo el local… todavía no suena ningún teléfono.</div>
        ) : (
          visibles
            .slice(-90)
            .reverse()
            .map((e, i) => <Fila key={`${e.tipo}-${e.minuto}-${visibles.length - i}`} e={e} />)
        )}
      </div>

      {listos ? (
        <div className="pelicula-fin">
          <span>✅ Día cerrado: {dia.ventas} ventas · {dia.instalaciones} instalaciones · caja{" "}
            {usd(dia.caja, 0)}</span>
          <button className="boton boton-primario boton-chico" onClick={onTerminar}>
            Ver el resumen
          </button>
        </div>
      ) : null}
    </div>
  );
}

function Contador({ etiqueta, valor, total, tono, solo }) {
  return (
    <div className={`pelicula-contador ${tono ?? ""}`}>
      <span className="pelicula-contador-e">{etiqueta}</span>
      <span className="pelicula-contador-v">
        {valor}
        {!solo && total !== undefined ? <i> / {num(total)}</i> : null}
      </span>
    </div>
  );
}

function Fila({ e }) {
  if (e.tipo === "instalacion") {
    return (
      <div className="cinta-fila cinta-inst">
        <span className="cinta-hora">{reloj(e.minuto)}</span>
        <span className="cinta-ico">🔧</span>
        <span className="cinta-txt">
          <b>Instalación</b> — {e.cliente} en {e.barrio} ({e.turno})
        </span>
      </div>
    );
  }
  if (e.tipo === "charla") {
    const a = AGENTES[e.agente] ?? { nombre: e.agente, icono: "🤖" };
    return (
      <div className={`cinta-fila cinta-charla cinta-charla-${e.agente}`}>
        <span className="cinta-hora">{reloj(e.minuto)}</span>
        <span className="cinta-ico">{a.icono}</span>
        <span className="cinta-txt cinta-burbuja">
          <b>{a.nombre}</b>: {e.dice}
        </span>
      </div>
    );
  }
  return (
    <div className={`cinta-fila ${e.venta ? "cinta-venta" : ""}`}>
      <span className="cinta-hora">{reloj(e.minuto)}</span>
      <span className="cinta-ico">{e.venta ? "🎉" : e.atendio ? "☎" : "📵"}</span>
      <span className="cinta-txt">
        <b>{e.operador}</b> llamó a {e.cliente} ({e.barrio}) —{" "}
        {e.venta ? "¡Cerró la venta!" : e.atendio ? e.motivo : `No contestó (${e.motivo})`}
      </span>
    </div>
  );
}
