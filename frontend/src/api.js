// One single place to talk to the backend.
//
// The URL comes from VITE_API_URL. If it is not set, we use
// http://localhost:8000 and, if that port is taken by something else,
// we try http://127.0.0.1:8000 (same engine, different name).

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
      continue; // this port does not answer: try the next one
    }
    const tipo = respuesta.headers.get("content-type") || "";
    if (respuesta.status === 404 && !tipo.includes("application/json")) {
      // That port answers but it is NOT the engine (e.g. a file server sitting
      // on 8000): drop it and try the next candidate.
      ultimoErrorDeRed = base;
      continue;
    }
    baseUsada = base;
    ultimaRespuesta = respuesta;
    break;
  }

  if (!ultimaRespuesta) {
    throw new Error(
      "I couldn't reach the simulation engine. Check that it is running " +
        "(from the backend folder: .\\.venv\\Scripts\\python.exe -m uvicorn api:app --port 8000) " +
        `and that it answers on ${ultimoErrorDeRed || BASES[0]}.`,
    );
  }

  const r = ultimaRespuesta;
  if (!r.ok) {
    let detalle = "";
    try {
      const cuerpoJson = await r.json();
      detalle = typeof cuerpoJson?.detail === "string" ? cuerpoJson.detail : "";
    } catch {
      /* the backend did not return JSON */
    }
    if (r.status >= 500) {
      throw new Error(
        "The engine hit an error handling this request (nothing breaks, it is a server-side " +
          "error). If it keeps happening, tell whoever maintains the backend.",
      );
    }
    throw new Error(
      detalle || `The engine answered with a problem (code ${r.status}). Try again.`,
    );
  }
  return r.json();
}

function cuerpo(datos) {
  return datos === undefined ? undefined : JSON.stringify(datos);
}

export const api = {
  estado: () => pedir("/api/estado"),
  mapa: () => pedir("/api/mapa"),
  metricas: () => pedir("/api/metricas"),
  sectores: () => pedir("/api/sectores"),
  sectorDetalle: (id, mes) =>
    pedir(`/api/sectores/${id}${mes ? `?mes=${mes}` : ""}`),
  generarSector: (id, mes) =>
    pedir(`/api/sectores/${id}/generar${mes ? `?mes=${mes}` : ""}`, {
      method: "POST",
      body: "{}",
    }),
  avanzarDia: () => pedir("/api/dia", { method: "POST", body: "{}" }),
  diaEnVivo: () => pedir("/api/dia/en-vivo", { method: "POST", body: "{}" }),
  diaEnVivoEstado: () => pedir("/api/dia/en-vivo"),
  sala: (limite = 60) => pedir(`/api/sala?limite=${limite}`),
  modo: (rapido) => pedir("/api/modo", { method: "POST", body: cuerpo({ rapido }) }),
  idioma: (lang) => pedir("/api/idioma", { method: "POST", body: cuerpo({ lang }) }),
};
