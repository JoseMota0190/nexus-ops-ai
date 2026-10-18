import { useEffect, useMemo, useRef, useState } from "react";
import { num, usd } from "../format.js";
import { getIdioma, t, useIdioma } from "../i18n.js";

const DIA_CORTO = {
  en: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  es: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"],
};
const VELOCIDADES = [
  { minutos: 3, etiqueta: "3 min" },
  { minutos: 6, etiqueta: "6 min" },
  { minutos: 9, etiqueta: "9 min" },
];

function diaCorto(d) {
  return (DIA_CORTO[getIdioma()] || DIA_CORTO.en)[d] ?? "";
}

// The agents that speak in the room, with their little face and color.
function agentes() {
  return {
    operador: { nombre: t("Telemarketer", "Teleoperador"), icono: "📞" },
    agenda: { nombre: t("Scheduling", "Agenda"), icono: "📅" },
    tecnicos: { nombre: t("Technicians", "Técnicos"), icono: "🔧" },
    despacho: { nombre: t("Dispatch", "Despacho"), icono: "🚚" },
  };
}

function reloj(minuto) {
  const h = 8 + Math.floor(minuto / 60);
  const m = Math.floor(minuto % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/**
 * The day's movie: the same day the engine already ran, but replayed in slow
 * motion so the owner (or the judge) sees the operation breathing.
 *
 * The program computes EVERYTHING instantly; here we are only showing it bit by bit.
 */
export default function Pelicula({ dia, velocidadInicial = 3, onTerminar }) {
  useIdioma();
  const [minutos, setMinutos] = useState(velocidadInicial);
  const [corriendo, setCorriendo] = useState(true);
  const [transcurrido, setTranscurrido] = useState(0); // fraction 0..1
  const inicio = useRef(null);
  const raf = useRef(null);

  const ev = dia?.pelicula?.eventos ?? [];
  const minIni = dia?.pelicula?.hora_inicio ?? 480;
  const minFin = dia?.pelicula?.hora_fin ?? 1080;
  const span = Math.max(1, minFin - minIni);

  // Restarts the movie if the day or the chosen speed changes.
  useEffect(() => {
    inicio.current = null;
    setTranscurrido(0);
    setCorriendo(true);
  }, [dia, minutos]);

  // The clock: it advances over the chosen minutes.
  useEffect(() => {
    if (!corriendo || !ev.length) return;
    const durMs = minutos * 60 * 1000;
    const paso = (time) => {
      if (inicio.current === null) inicio.current = time;
      const f = Math.min(1, (time - inicio.current) / durMs);
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

  // The counters grow as the events go by.
  const c = useMemo(() => {
    const cuenta = { llamadas: 0, atendidas: 0, ventas: 0, instalaciones: 0 };
    for (const e of visibles) {
      if (e.tipo === "instalacion") cuenta.instalaciones++;
      else if (e.tipo === "llamada") {
        cuenta.llamadas++;
        if (e.atendio) cuenta.atendidas++;
        if (e.venta) cuenta.ventas++;
      }
    }
    return cuenta;
  }, [visibles]);

  const listos = !corriendo && transcurrido >= 1;

  return (
    <div className="pelicula">
      <div className="pelicula-cab">
        <div className="pelicula-reloj">
          <span className="pelicula-hora">{reloj(Math.min(minutoActual, minFin))}</span>
          <span className="pelicula-fecha">
            {diaCorto(dia.dia)} · {t("Week", "Semana")} {dia.semana} · {t("Month", "Mes")} {dia.mes}
          </span>
        </div>

        <div className="pelicula-vel">
          <span className="pelicula-vel-e">{t("Length", "Duración")}</span>
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
            {corriendo ? t("⏸ Pause", "⏸ Pausa") : t("▶ Resume", "▶ Seguir")}
          </button>
          {listos ? (
            <button className="dia-chip activo" onClick={() => setTranscurrido(0)}>
              {t("↺ Again", "↺ Otra vez")}
            </button>
          ) : null}
        </div>
      </div>

      <div className="barra pelicula-barra">
        <i style={{ width: `${transcurrido * 100}%` }} />
      </div>

      <div className="pelicula-contadores">
        <Contador etiqueta={t("Calls", "Llamadas")} valor={c.llamadas} total={dia.llamadas} />
        <Contador etiqueta={t("Answered", "Atendidas")} valor={c.atendidas} total={dia.atendidas} />
        <Contador etiqueta={t("Sales", "Ventas")} valor={c.ventas} total={dia.ventas} tono="positivo" />
        <Contador
          etiqueta={t("Installs", "Instalaciones")}
          valor={c.instalaciones}
          total={dia.instalaciones}
          tono="ondas"
        />
        <Contador
          etiqueta={t("Day leads", "Leads del día")}
          valor={Math.min(dia.leads, Math.round(dia.leads * transcurrido))}
          total={dia.leads}
        />
        <Contador etiqueta={t("Cash", "Caja")} valor={usd(dia.caja, 0)} solo />
      </div>

      <div className="pelicula-cinta" role="log" aria-live="polite">
        {visibles.length === 0 ? (
          <div className="sin-datos">
            {t("Opening the shop… no phone is ringing yet.",
               "Abriendo el local… todavía no suena ningún teléfono.")}
          </div>
        ) : (
          visibles
            .slice(-90)
            .reverse()
            .map((e, i) => <Fila key={`${e.tipo}-${e.minuto}-${visibles.length - i}`} e={e} />)
        )}
      </div>

      {listos ? (
        <div className="pelicula-fin">
          <span>✅ {t("Day closed", "Día cerrado")}: {dia.ventas} {t("sales", "ventas")} ·{" "}
            {dia.instalaciones} {t("installs", "instalaciones")} · {t("cash", "caja")}{" "}
            {usd(dia.caja, 0)}</span>
          <button className="boton boton-primario boton-chico" onClick={onTerminar}>
            {t("Close", "Cerrar")}
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
          <b>{t("Install", "Instalación")}</b> — {e.cliente} {t("in", "en")} {e.barrio} ({e.turno})
        </span>
      </div>
    );
  }
  if (e.tipo === "charla") {
    const a = agentes()[e.agente] ?? { nombre: e.agente, icono: "🤖" };
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
        <b>{e.operador}</b> {t("called", "llamó a")} {e.cliente} ({e.barrio}) —{" "}
        {e.venta
          ? t("closed the sale!", "¡cerró la venta!")
          : e.atendio
            ? e.motivo
            : t(`No answer (${e.motivo})`, `Sin respuesta (${e.motivo})`)}
      </span>
    </div>
  );
}
