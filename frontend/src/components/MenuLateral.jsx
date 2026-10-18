import { t, useIdioma } from "../i18n.js";

/**
 * The side menu (☰). It shows ONLY the 4 SECTORS of the company:
 *
 *   🧾 Management · 📞 Sales · 📅 Scheduling & technicians · 🧮 Billing
 *
 * Each one opens its monthly report (what the sector's agent produces: AMD
 * analyzes the numbers, the writer turns them into a document).
 */

// Mirror of `backend/engine/sectores.py`, in the active language (so if the
// engine list has not arrived yet, the menu still draws correctly).
export function sectoresFallback() {
  return [
    { id: "gerente", icono: "🧾", color: "azul",
      nombre: t("Management", "Gerencia"),
      bajada: t("Direction, cash and the month's decisions",
                "Rumbo, caja y las decisiones del mes") },
    { id: "ventas", icono: "📞", color: "verde",
      nombre: t("Sales · Telemarketers", "Ventas · Teleoperadores"),
      bajada: t("Calls, conversion and why they don't buy",
                "Llamadas, conversión y por qué no compran") },
    { id: "agenda", icono: "📅", color: "violeta",
      nombre: t("Scheduling & technicians", "Agenda y técnicos"),
      bajada: t("Slots, installs and zone assignment",
                "Turnos, instalaciones y reparto por zona") },
    { id: "facturacion", icono: "🧮", color: "cyan",
      nombre: t("Billing", "Facturación"),
      bajada: t("Simulated invoices and auditing",
                "Comprobantes simulados y auditoría") },
  ];
}

export function metaPaneles() {
  return sectoresFallback().map((s) => ({ id: s.id, icono: s.icono, titulo: s.nombre }));
}

const SEMAFORO = { verde: "🟢", ambar: "🟡", rojo: "🔴" };

export default function MenuLateral({
  abierto,
  panelActivo,
  onAbrir,
  onCerrar,
  sectores,
}) {
  useIdioma(); // re-render the menu when the language changes
  if (!abierto) return null;
  const lista = sectores && sectores.length ? sectores : sectoresFallback();

  return (
    <>
      <div className="menu-fondo" onClick={onCerrar} />
      <aside className="menu-lateral" role="dialog"
             aria-label={t("Sectors menu", "Menú de sectores")}>
        <div className="menu-cab">
          <div>
            <div className="menu-titulo">{t("The 4 sectors", "Los 4 sectores")}</div>
            <div className="menu-bajada">{t("Each with its report of the month",
                                            "Cada uno con su informe del mes")}</div>
          </div>
          <button className="menu-x" onClick={onCerrar}
                  aria-label={t("Close the menu", "Cerrar el menú")}>
            ✕
          </button>
        </div>

        <div className="menu-lista">
          {lista.map((s) => (
            <button
              key={s.id}
              className={`menu-item menu-item-sector sector-${s.color} ${
                panelActivo === s.id ? "activo" : ""
              }`}
              onClick={() => onAbrir(s.id)}
            >
              <span className="menu-item-icono">{s.icono}</span>
              <span className="menu-item-texto">
                <b>
                  {s.nombre}
                  {s.tiene_informe ? (
                    <span className="menu-item-mes">
                      {SEMAFORO[s.semaforo] || "🟢"} {t("Month", "Mes")} {s.mes_reporte}
                    </span>
                  ) : null}
                </b>
                <i>{s.bajada}</i>
              </span>
            </button>
          ))}
        </div>

        <div className="menu-pie">
          {t("Nexus Alarm · fictional company · AMD ACT III / lablab.ai demo · simulated data.",
             "Nexus Alarm · empresa ficticia · demo AMD ACT III / lablab.ai · datos simulados.")}
        </div>
      </aside>
    </>
  );
}
