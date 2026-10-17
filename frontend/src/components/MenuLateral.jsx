/**
 * El menú lateral (☰). Esconde todo el detalle de la pantalla en una lista:
 * cada ítem abre su panel SUPERPUESTO sobre el mapa (el mapa nunca se pierde).
 */

export const PANELES = [
  {
    id: "sala",
    icono: "🗣️",
    titulo: "Sala de Agentes",
    bajada: "Los agentes negocian cada venta en vivo, sobre AMD",
  },
  {
    id: "kpis",
    icono: "📊",
    titulo: "KPIs del negocio",
    bajada: "Ventas, conversión, caja y clientes de un vistazo",
  },
  {
    id: "dia",
    icono: "📅",
    titulo: "Detalle del día corrido",
    bajada: "Lo que hizo la operación el último día a mano",
  },
  {
    id: "llamadas",
    icono: "📞",
    titulo: "Telégrafo de llamadas",
    bajada: "Quién contestó, quién no y por qué",
  },
  {
    id: "motivos",
    icono: "💬",
    titulo: "Motivos: por qué no se vende",
    bajada: "Lo que la gente contesta cuando no compra",
  },
  {
    id: "gerente",
    icono: "🧾",
    titulo: "Reunión mensual de gerencia",
    bajada: "El acta del Gerente IA y sus decisiones",
  },
  {
    id: "evolucion",
    icono: "📈",
    titulo: "Evolución mes a mes",
    bajada: "Ingresos contra costos, y el crecimiento",
  },
  {
    id: "mapa",
    icono: "🗺️",
    titulo: "Mapa de CABA",
    bajada: "Los técnicos y las visitas de la semana, con lista",
  },
  {
    id: "escenario",
    icono: "⚙️",
    titulo: "¿Qué pasa si…?",
    bajada: "Movés las palancas y el programa calcula el resultado",
  },
  {
    id: "agente",
    icono: "🤖",
    titulo: "Escuchar una llamada del agente",
    bajada: "El teleoperador (IA) habla de verdad con un cliente",
  },
  {
    id: "amd",
    icono: "🔧",
    titulo: "Panel AMD",
    bajada: "El cerebro: modelo, latencia y tokens",
  },
];

export default function MenuLateral({ abierto, panelActivo, onAbrir, onCerrar }) {
  if (!abierto) return null;

  return (
    <>
      <div className="menu-fondo" onClick={onCerrar} />
      <aside className="menu-lateral" role="dialog" aria-label="Menú de paneles">
        <div className="menu-cab">
          <div>
            <div className="menu-titulo">Menú</div>
            <div className="menu-bajada">Toda la info de la empresa, a un clic</div>
          </div>
          <button className="menu-x" onClick={onCerrar} aria-label="Cerrar el menú">
            ✕
          </button>
        </div>

        <div className="menu-lista">
          {PANELES.map((p) => (
            <button
              key={p.id}
              className={`menu-item ${panelActivo === p.id ? "activo" : ""}`}
              onClick={() => onAbrir(p.id)}
            >
              <span className="menu-item-icono">{p.icono}</span>
              <span className="menu-item-texto">
                <b>{p.titulo}</b>
                <i>{p.bajada}</i>
              </span>
            </button>
          ))}
        </div>

        <div className="menu-pie">
          Nexus Alarm · empresa ficticia · demo AMD ACT III / lablab.ai · datos simulados.
        </div>
      </aside>
    </>
  );
}
