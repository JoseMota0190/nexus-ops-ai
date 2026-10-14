import { num, pct, usd } from "../format.js";

function Tarjeta({ etiqueta, valor, unidad, detalle, barra, children }) {
  return (
    <div className="kpi">
      <div className="kpi-etiqueta">{etiqueta}</div>
      <div className="kpi-valor">
        {valor}
        {unidad ? <span className="unidad"> {unidad}</span> : null}
      </div>
      {barra !== undefined && barra !== null ? (
        <div className="mini-barra">
          <i style={{ width: `${Math.max(0, Math.min(100, barra))}%` }} />
        </div>
      ) : null}
      {detalle ? <div className="kpi-detalle">{detalle}</div> : null}
      {children}
    </div>
  );
}

export default function Kpis({ estado }) {
  if (!estado) {
    return (
      <section className="kpis">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div className="kpi" key={i}>
            <div className="kpi-etiqueta">Cargando…</div>
            <div className="kpi-valor">—</div>
          </div>
        ))}
      </section>
    );
  }

  const potencial = estado.ventas_por_dia_potencial ?? 0;
  const objetivo = estado.ventas_por_dia_objetivo || 1;
  const avance = Math.round((potencial / objetivo) * 100);
  const tecObj = estado.tecnicos_objetivo || 1;

  return (
    <section className="kpis">
      <Tarjeta
        etiqueta="Ventas por día"
        valor={num(potencial, 1)}
        barra={avance}
        detalle={`Potencial de hoy vs objetivo del mes: ${num(objetivo, 1)}/día`}
      />

      <div className="kpi">
        <div className="kpi-etiqueta">Conversión</div>
        <div className="kpi-par">
          <div>
            <div className="mini">Contestan</div>
            <div className="grande ondas">{pct(estado.tasa_respuesta)}</div>
          </div>
          <div>
            <div className="mini">De los que contestan, compran</div>
            <div className="grande positivo">{pct(estado.tasa_cierre)}</div>
          </div>
        </div>
        <div className="kpi-detalle">
          De 100 llamadas, contestan {num(estado.tasa_respuesta, 0)} y de esas compran{" "}
          {num(estado.tasa_respuesta * estado.tasa_cierre / 100, 1)}.
        </div>
      </div>

      <Tarjeta
        etiqueta="Técnicos activos"
        valor={num(estado.tecnicos)}
        unidad={`/ ${tecObj} este mes`}
        barra={(estado.tecnicos / tecObj) * 100}
        detalle={`Meta final: ${estado.meta_tecnicos ?? 10} técnicos para el mes 9`}
      />

      <Tarjeta
        etiqueta="Operadores"
        valor={num(estado.operadores)}
        detalle={`${num(estado.llamadas_por_dia)} llamadas posibles por día · ${num(
          estado.leads_por_dia,
        )} leads/día`}
      />

      <Tarjeta
        etiqueta="Plata en caja"
        valor={usd(estado.caja, 0)}
        detalle={`${num(estado.clientes_activos)} clientes pagando monitoreo`}
      />

      <Tarjeta
        etiqueta="Clientes activos"
        valor={num(estado.clientes_activos)}
        detalle="Los que ya tienen alarma puesta y pagan el monitoreo mensual."
        barra={Math.min(100, (estado.clientes_activos / 400) * 100)}
      />
    </section>
  );
}
