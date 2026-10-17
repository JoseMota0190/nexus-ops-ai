/**
 * El menú lateral (☰). Muestra SOLO los 4 SECTORES de la empresa:
 *
 *   🧾 Gerencia · 📞 Ventas · 📅 Agenda y técnicos · 🧮 Facturación
 *
 * Cada uno abre su informe mensual (lo que produce el agente del sector: AMD
 * analiza, Evolus redacta). Los paneles viejos siguen en el código pero NO se
 * ofrecen acá: la pantalla quedó enfocada en los sectores.
 */

// Espejo de `backend/engine/sectores.py` (por si la lista del motor no llegó
// todavía, el menú igual se dibuja).
export const SECTORES_FALLBACK = [
  { id: "gerente", icono: "🧾", nombre: "Gerencia", color: "azul",
    bajada: "Rumbo, caja y decisiones del mes" },
  { id: "ventas", icono: "📞", nombre: "Ventas · Teleoperadores", color: "verde",
    bajada: "Llamadas, conversión y por qué no compran" },
  { id: "agenda", icono: "📅", nombre: "Agenda y técnicos", color: "violeta",
    bajada: "Turnos, instalaciones y reparto por zona" },
  { id: "facturacion", icono: "🧮", nombre: "Facturación", color: "cyan",
    bajada: "Comprobantes simulados y auditoría" },
];

const SEMAFORO = { verde: "🟢", ambar: "🟡", rojo: "🔴" };

// Metadatos para el título de cada caja (los 4 sectores + los paneles viejos
// que siguen vivos en el código aunque ya no se ofrezcan en el menú).
export const META_PANELES = [
  ...SECTORES_FALLBACK.map((s) => ({ id: s.id, icono: s.icono, titulo: s.nombre })),
  { id: "sala", icono: "🗣️", titulo: "Sala de Agentes" },
  { id: "kpis", icono: "📊", titulo: "KPIs del negocio" },
  { id: "dia", icono: "📅", titulo: "Detalle del día corrido" },
  { id: "llamadas", icono: "📞", titulo: "Telégrafo de llamadas" },
  { id: "motivos", icono: "💬", titulo: "Motivos: por qué no se vende" },
  { id: "gerencia", icono: "🧾", titulo: "Reunión mensual de gerencia" },
  { id: "evolucion", icono: "📈", titulo: "Evolución mes a mes" },
  { id: "mapa", icono: "🗺️", titulo: "Mapa de CABA" },
  { id: "escenario", icono: "⚙️", titulo: "¿Qué pasa si…?" },
  { id: "agente", icono: "🤖", titulo: "Escuchar una llamada del agente" },
  { id: "amd", icono: "🔧", titulo: "Panel AMD" },
];

export default function MenuLateral({
  abierto,
  panelActivo,
  onAbrir,
  onCerrar,
  sectores,
}) {
  if (!abierto) return null;
  const lista = sectores && sectores.length ? sectores : SECTORES_FALLBACK;

  return (
    <>
      <div className="menu-fondo" onClick={onCerrar} />
      <aside className="menu-lateral" role="dialog" aria-label="Menú de sectores">
        <div className="menu-cab">
          <div>
            <div className="menu-titulo">Los 4 sectores</div>
            <div className="menu-bajada">Cada uno con su informe del mes</div>
          </div>
          <button className="menu-x" onClick={onCerrar} aria-label="Cerrar el menú">
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
                      {SEMAFORO[s.semaforo] || "🟢"} Mes {s.mes_reporte}
                    </span>
                  ) : null}
                </b>
                <i>{s.bajada}</i>
              </span>
            </button>
          ))}
        </div>

        <div className="menu-pie">
          Nexus Alarm · empresa ficticia · demo AMD ACT III / lablab.ai · datos
          simulados.
        </div>
      </aside>
    </>
  );
}
