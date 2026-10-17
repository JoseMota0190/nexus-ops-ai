// Un solo lugar para hablar con el backend.
//
// La URL sale de la variable VITE_API_URL. Si no está puesta, usamos
// http://localhost:8000 y, si ese puerto está ocupado por otra cosa,
// probamos http://127.0.0.1:8000 (mismo motor, distinto nombre).

const CONFIGURADA = import.meta.env.VITE_API_URL;
const BASES = CONFIGURADA
  ? [String(CONFIGURADA).replace(/\/+$/, "")]
  : ["http://localhost:8000", "http://127.0.0.1:8000"];

let baseUsada = null;

export function baseActual() {
  return baseUsada || BASES[0];
}

async function fetchBase(base, ruta, opciones) {
  const respuesta = await fetch(base + ruta, {
    ...opciones,
    headers: { "Content-Type": "application/json", ...(opciones.headers || {}) },
  });
  return respuesta;
}

async function pedir(ruta, opciones = {}) {
  const orden = baseUsada ? [baseUsada, ...BASES.filter((b) => b !== baseUsada)] : BASES;
  let ultimaRespuesta = null;
  let ultimoErrorDeRed = null;

  for (const base of orden) {
    let respuesta;
    try {
      respuesta = await fetchBase(base, ruta, opciones);
    } catch {
      ultimoErrorDeRed = base;
      continue; // este puerto ni contesta: probamos el siguiente
    }
    const tipo = respuesta.headers.get("content-type") || "";
    if (respuesta.status === 404 && !tipo.includes("application/json")) {
      // Ese puerto contesta pero NO es el motor (p. ej. un servidor de archivos
      // colgado en el 8000): lo descartamos y probamos el próximo candidato.
      ultimoErrorDeRed = base;
      continue;
    }
    baseUsada = base;
    ultimaRespuesta = respuesta;
    break;
  }

  if (!ultimaRespuesta) {
    throw new Error(
      "No pude conectar con el motor de la simulación. Revisá que esté corriendo " +
        "(desde la carpeta backend: .\\.venv\\Scripts\\python.exe -m uvicorn api:app --port 8000) " +
        `y que responda en ${ultimoErrorDeRed || BASES[0]}.`,
    );
  }

  const r = ultimaRespuesta;
  if (!r.ok) {
    let detalle = "";
    try {
      const cuerpoJson = await r.json();
      detalle = typeof cuerpoJson?.detail === "string" ? cuerpoJson.detail : "";
    } catch {
      /* el backend no devolvió JSON */
    }
    if (r.status >= 500) {
      throw new Error(
        "El motor tuvo un error al procesar este pedido (no rompe nada, es un error del lado " +
          "del servidor). Si pasa siempre, avisale a quien mantiene el backend.",
      );
    }
    throw new Error(
      detalle || `El motor contestó con un problema (código ${r.status}). Probá de nuevo.`,
    );
  }
  return r.json();
}

function cuerpo(datos) {
  return datos === undefined ? undefined : JSON.stringify(datos);
}

export const api = {
  estado: () => pedir("/api/estado"),
  resumenes: () => pedir("/api/resumenes"),
  llamadas: (limite = 20) => pedir(`/api/llamadas?limite=${limite}`),
  mapa: () => pedir("/api/mapa"),
  metricas: () => pedir("/api/metricas"),
  actas: () => pedir("/api/actas"),
  objetivos: () => pedir("/api/objetivos"),
  sectores: () => pedir("/api/sectores"),
  sectorDetalle: (id, mes) =>
    pedir(`/api/sectores/${id}${mes ? `?mes=${mes}` : ""}`),
  generarSector: (id, mes) =>
    pedir(`/api/sectores/${id}/generar${mes ? `?mes=${mes}` : ""}`, {
      method: "POST",
      body: "{}",
    }),
  facturacion: (mes) => pedir(`/api/facturacion${mes ? `?mes=${mes}` : ""}`),
  evolusSalud: () => pedir("/api/evolus/salud"),

  escenario: (datos) => pedir("/api/escenario", { method: "POST", body: cuerpo(datos) }),
  llamadaEnVivo: () => pedir("/api/llamada_en_vivo", { method: "POST", body: "{}" }),
  avanzarMes: () => pedir("/api/mes", { method: "POST", body: "{}" }),
  avanzarDia: () => pedir("/api/dia", { method: "POST", body: "{}" }),
  diaEnVivo: () => pedir("/api/dia/en-vivo", { method: "POST", body: "{}" }),
  diaEnVivoEstado: () => pedir("/api/dia/en-vivo"),
  correrTodo: (meses = 6) => pedir(`/api/todo?meses=${meses}`, { method: "POST", body: "{}" }),
  reiniciar: () => pedir("/api/reiniciar", { method: "POST", body: "{}" }),
  sala: (limite = 60) => pedir(`/api/sala?limite=${limite}`),
  modo: (rapido) => pedir("/api/modo", { method: "POST", body: cuerpo({ rapido }) }),
};
