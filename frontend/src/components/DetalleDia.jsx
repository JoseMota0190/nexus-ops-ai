import { num, usd, DIAS } from "../format.js";

const DIA_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

function Cifra({ etiqueta, valor, tono, detalle }) {
  return (
    <div className={`kpi ${tono ?? ""}`}>
      <div className="kpi-etiqueta">{etiqueta}</div>
      <div className="kpi-valor">{valor}</div>
      {detalle ? <div className="kpi-detalle">{detalle}</div> : null}
    </div>
  );
}

function MotivosDelDia({ titulo, motivos }) {
  const lista = Object.entries(motivos ?? {})
    .map(([motivo, n]) => ({ motivo, n }))
    .sort((a, b) => b.n - a.n);
  if (lista.length === 0) return null;
  const max = Math.max(1, ...lista.map((m) => m.n));

  return (
    <div className="bloque-motivo">
      <div className="sub-motivo">{titulo}</div>
      {lista.map((m) => (
        <div className="fila-motivo" key={m.motivo}>
          <div className="et">
            <span>{m.motivo}</span>
            <b>{num(m.n)}</b>
          </div>
          <div className="barra-motivo compra">
            <i style={{ width: `${(m.n / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * El detalle de UN día de operación, tal como lo devuelve el backend.
 * Aparece después de apretar "Avanzar 1 día" (lo pidió el autor para que
 * los jueces de la hackathon vean la simulación al detalle).
 */
export default function DetalleDia({ detalle }) {
  if (!detalle) {
    return (
      <div className="panel">
        <h2 className="panel-titulo">
          <span className="icono">📅</span> Un día de la operación, al detalle
        </h2>
        <p className="panel-sub">
          Apretá <strong>«Avanzar 1 día»</strong> acá arriba y este panel te muestra qué pasó
          ese día: cuántos leads entraron, cuántas llamadas se hicieron, cuántas ventas salieron
          y qué se instaló.
        </p>
        <div className="sin-datos">Todavía no se corrió ningún día a mano.</div>
      </div>
    );
  }

  const d = detalle;
  const diaSemana = DIAS[d.dia] ?? "—";
  const corto = DIA_CORTO[d.dia] ?? "";
  const atendidas = num(d.atendidas);
  const noContestaron = Math.max(0, d.llamadas - d.atendidas);
  const margen = d.ingresos - d.costos;

  return (
    <div className="panel panel-ancho">
      <h2 className="panel-titulo">
        <span className="icono">📅</span> Día corrido — {diaSemana} {corto} · Semana{" "}
        {d.semana} · Mes {d.mes}
      </h2>
      <p className="panel-sub">
        Esto es lo que hizo la operación ese día. Cada número viene de la base de datos, no de
        una estimación.
      </p>

      <section className="kpis">
        <Cifra etiqueta="Leads nuevos (formulario web)" valor={num(d.leads)} />
        <Cifra etiqueta="Llamadas hechas" valor={num(d.llamadas)} />
        <Cifra
          etiqueta="Contestaron"
          valor={atendidas}
          detalle={`${noContestaron} no contestaron`}
        />
        <Cifra etiqueta="Ventas cerradas" valor={num(d.ventas)} tono="positivo" />
        <Cifra etiqueta="Instalaciones hechas" valor={num(d.instalaciones)} />
        <Cifra
          etiqueta="Turnos agendados"
          valor={num(d.agendadas)}
          detalle={
            d.turnos_negociados > 0
              ? `${d.turnos_negociados} hubo que renegociar horario`
              : "Sin renegociaciones"
          }
        />
        <Cifra
          etiqueta="Sin capacidad"
          valor={num(d.sin_capacidad)}
          detalle="Ventas esperando turno (se agenda la semana que viene)"
        />
        <Cifra
          etiqueta="Caja del día"
          valor={usd(margen, 0)}
          detalle={`${usd(d.ingresos, 0)} entraron − ${usd(d.costos, 0)} de leads`}
        />
        <Cifra etiqueta="Caja total" valor={usd(d.caja, 0)} />
      </section>

      <div className="motivos" style={{ display: "flex", gap: 22, flexWrap: "wrap" }}>
        <MotivosDelDia titulo="Por qué no compraron (contestaron)" motivos={d.motivos_no_compra} />
        <MotivosDelDia titulo="Por qué no contestaron" motivos={d.motivos_no_respuesta} />
      </div>
    </div>
  );
}
