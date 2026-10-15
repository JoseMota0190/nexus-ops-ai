import { DIAS } from "../format.js";

const DIA_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

export default function Cabecera({
  estado,
  cargando,
  ocupado,
  onAvanzar,
  onAvanzarDia,
  onCorrerSeis,
  onReiniciar,
}) {
  const mes = estado?.mes ?? 1;
  const semana = estado?.semana ?? 1;
  const dia = estado?.dia_semana ?? 0;
  const terminado = estado ? !estado.puede_avanzar : false;
  const tecnicos = estado?.tecnicos ?? 0;
  const meta = estado?.meta_tecnicos ?? 10;
  const avance = Math.min(100, Math.round((tecnicos / meta) * 100));

  return (
    <header className="cabecera">
      <div className="cabecera-izq">
        <h1 className="titulo-app">
          Nexus Alarm <span className="destello">— Gemelo Digital</span>
        </h1>
        <div className="subtitulo">
          La pantalla del dueño: los números de tu empresa de alarmas, en vivo.
        </div>
        <div className="reloj">
          <span className="chip">
            Mes <strong>{mes}</strong> de 9
          </span>
          <span className="chip">
            Semana <strong>{semana}</strong>
          </span>
          <span className="chip">
            {DIAS[dia] ?? "—"} <strong>{DIA_CORTO[dia] ?? ""}</strong>
          </span>
          {terminado ? (
            <span className="chip terminado">✔ Simulación terminada</span>
          ) : (
            <span className="chip">En marcha</span>
          )}
        </div>
      </div>

      <div className="meta">
        <div className="meta-fila">
          <span className="meta-titulo">Meta del dueño: 10 técnicos para el mes 9</span>
          <span>
            <strong>{tecnicos}</strong> / {meta}
          </span>
        </div>
        <div className="barra" title={`${tecnicos} de ${meta} técnicos`}>
          <i style={{ width: `${avance}%` }} />
        </div>
        <div className="meta-fila" style={{ marginTop: 6 }}>
          <span>{avance}% de la meta</span>
          <span>{estado ? `${estado.ventas_totales} ventas totales` : ""}</span>
        </div>
      </div>

      <div className="acciones">
        <button
          className="boton boton-primario"
          onClick={onAvanzar}
          disabled={!!ocupado || terminado || cargando}
        >
          {ocupado === "mes" ? "Corriendo el mes…" : "Avanzar 1 mes"}
        </button>
        <button
          className="boton boton-secundario"
          onClick={onAvanzarDia}
          disabled={!!ocupado || terminado || cargando}
          title="Corre un día entero de operación y muestra el detalle abajo"
        >
          {ocupado === "dia" ? "Corriendo el día…" : "Avanzar 1 día"}
        </button>
        <button
          className="boton boton-secundario"
          onClick={onCorrerSeis}
          disabled={!!ocupado || terminado || cargando}
        >
          {ocupado === "seis" ? "Corriendo 6 meses…" : "Correr 6 meses de una"}
        </button>
        <button className="boton boton-fantasma" onClick={onReiniciar} disabled={!!ocupado}>
          Reiniciar
        </button>
      </div>
    </header>
  );
}
