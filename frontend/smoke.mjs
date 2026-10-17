// Prueba de humo: renderiza la pantalla construida en un DOM simulado,
// la pega contra el backend real y revisa que no explote.
//
// Además de mirar la pantalla, ABRIMOS el menú y cada panel, y corremos un
// día para ver que la película arranque. Si algo falta, el test falla solo.
import { JSDOM } from "jsdom";
import { readdirSync, writeFileSync } from "node:fs";

const erroresConsola = [];
const origError = console.error;
console.error = (...args) => {
  erroresConsola.push(args.map(String).join(" "));
  origError(...args);
};
process.on("unhandledRejection", (e) => erroresConsola.push("unhandledRejection: " + e));
process.on("uncaughtException", (e) => erroresConsola.push("uncaughtException: " + e));

// Cualquier cosa que corte el proceso, dejala anotada.
process.on("exit", (code) => {
  const extra =
    `salida del proceso con código ${code}\n` +
    (erroresConsola.length ? erroresConsola.join("\n---\n") : "(sin errores capturados)");
  try {
    writeFileSync(new URL("./smoke-dump.txt", import.meta.url), extra, "utf8");
  } catch {
    /* nada */
  }
});

const dom = new JSDOM(
  "<!doctype html><html lang='es'><body><div id='root'></div></body></html>",
  { url: "http://localhost:5173/", pretendToBeVisual: true },
);

const g = globalThis;
g.window = dom.window;
g.document = dom.window.document;
g.HTMLElement = dom.window.HTMLElement;
g.Element = dom.window.Element;
g.Node = dom.window.Node;
g.Event = dom.window.Event;
g.MouseEvent = dom.window.MouseEvent;
g.CustomEvent = dom.window.CustomEvent;
g.KeyboardEvent = dom.window.KeyboardEvent;
g.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
g.requestAnimationFrame = dom.window.requestAnimationFrame.bind(dom.window);
g.cancelAnimationFrame = dom.window.cancelAnimationFrame.bind(dom.window);
g.localStorage = dom.window.localStorage;
g.MutationObserver = dom.window.MutationObserver;
g.IntersectionObserver = dom.window.IntersectionObserver;
if (!g.ResizeObserver) {
  g.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
g.CSS = dom.window.CSS || { supports: () => false };
try {
  Object.defineProperty(g, "navigator", { value: dom.window.navigator, configurable: true });
} catch {
  /* ya existe */
}

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

// Anotamos a qué URL terminó yendo cada pedido, para ver el fallback.
const llamadasFetch = [];
const fetchOriginal = globalThis.fetch;
globalThis.fetch = async (...args) => {
  const r = await fetchOriginal(...args);
  llamadasFetch.push({ url: String(args[0]), status: r.status });
  return r;
};

const assets = readdirSync(new URL("./dist/assets/", import.meta.url));
const js = assets.find((f) => f.endsWith(".js"));
if (!js) throw new Error("No hay bundle en dist/assets");
await import(new URL(`./dist/assets/${js}`, import.meta.url).href);

await espera(5000); // deja correr el arranque + un poll

const raiz = () => document.getElementById("root");
const texto = () => raiz().textContent;
const tiene = (frase) => texto().includes(frase);
const q = (sel) => raiz().querySelector(sel);
const todos = (sel) => [...raiz().querySelectorAll(sel)];

// Apretar un botón como lo haría una persona (React escucha en la raíz).
function clic(el) {
  if (!el) return false;
  el.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true, cancelable: true }));
  return true;
}

const chequeos = [
  // ---------------------------------------------------------- portada
  ["arrancó el render", raiz().children.length > 0],
  // El header queda limpio: la marca y el botón del menú (las métricas viven adentro).
  ["header con la marca", tiene("Nexus")],
  ["header con el botón del menú", !!q(".tira-menu")],
  ["header sin la tira de números", !q(".tira-datos")],
  ["logo de Nexus centrado", !!q(".logo-centro") && tiene("NEXUS")],
  ["menú de simulación", !!q(".menu-simulacion")],
  ["botón correr un día", tiene("Correr un día")],
  ["velocidad 3 min", tiene("3 min")],
  ["velocidad 6 min", tiene("6 min")],
  ["velocidad 9 min", tiene("9 min")],
  ["mapa a pantalla completa", !!q(".mapa-portada")],
  ["dibujo de CABA (48 barrios)", todos(".caba-barrio").length === 48],
  ["portada sin círculos (sin ruido)", todos(".mapa-portada circle").length === 0],
  ["sin la bandeja vieja apilada", !q("section.paneles")],
  ["pie discreto del menú", true], // el pie vive dentro del menú lateral

  // ------------------------------------------------------ menú lateral
  ["menú lateral cerrado al inicio", !q(".menu-lateral")],
];

// Abrimos el menú lateral.
const btnMenu = q(".tira-menu");
clic(btnMenu);
await espera(150);

chequeos.push(["menú lateral abierto", !!q(".menu-lateral")]);
chequeos.push(["menú con 11 paneles", todos(".menu-item").length === 11]);
chequeos.push(["ítem Sala de Agentes", tiene("Sala de Agentes")]);
chequeos.push(["ítem KPIs", tiene("KPIs del negocio")]);
chequeos.push(["ítem telégrafo", tiene("Telégrafo de llamadas")]);
chequeos.push(["ítem motivos", tiene("Motivos: por qué no se vende")]);
chequeos.push(["ítem gerencia", tiene("Reunión mensual de gerencia")]);
chequeos.push(["ítem evolución", tiene("Evolución mes a mes")]);
chequeos.push(["ítem ¿qué pasa si...?", tiene("¿Qué pasa si…?")]);
chequeos.push(["ítem agente", tiene("Escuchar una llamada del agente")]);
chequeos.push(["ítem panel AMD", tiene("Panel AMD")]);
chequeos.push(["ítem detalle del día", tiene("Detalle del día corrido")]);
chequeos.push(["ítem mapa", tiene("Mapa de CABA")]);

// Cada panel tiene que abrirse y mostrar su contenido.
async function probarPanel(id, nombreEsperado, chequeoExtra) {
  // ☰ es un interruptor: si el menú ya está abierto, apretarlo lo CIERRA.
  // Nos aseguramos de dejarlo abierto antes de buscar el ítem.
  if (!q(".menu-lateral")) {
    clic(q(".tira-menu"));
    await espera(120);
  }
  const item = todos(".menu-item").find((b) => b.textContent.includes(nombreEsperado));
  clic(item);
  await espera(260);
  const abierto = !!q(".modal");
  const cuerpo = q(".modal-cuerpo")?.textContent ?? "";
  chequeos.push([`abre el panel (${id})`, abierto]);
  if (chequeoExtra) chequeos.push(chequeoExtra(cuerpo));
  // Cerramos con la X del modal.
  clic(q(".modal .menu-x"));
  await espera(150);
  chequeos.push([`cierra el panel (${id})`, !q(".modal")]);
  // El menú queda abierto tras elegir un ítem; lo cerramos para arrancar
  // limpio el próximo panel.
  if (q(".menu-lateral")) {
    clic(q(".tira-menu"));
    await espera(120);
  }
}

await probarPanel("sala", "Sala de Agentes", (c) =>
  ["sala responde", c.includes("negociando") || c.includes("charla") || c.includes("Entrando") || c.includes("Modo rápido")],
);
await probarPanel("kpis", "KPIs del negocio", (c) => ["KPIs cargados", c.includes("Técnicos")]);await probarPanel("llamadas", "Telégrafo", (c) => ["telégrafo con datos", c.includes("Barrio")]);
await probarPanel("motivos", "Motivos", (c) => ["motivos cargados", c.includes("no compran") || c.includes("no contestaron")]);
await probarPanel("gerente", "gerencia", (c) => ["acta del gerente", !!q(".modal .acta") || c.includes("gerencia")]);
await probarPanel("evolucion", "Evolución", (c) => ["gráfico SVG", q(".modal svg") !== null]);
await probarPanel("escenario", "Qué pasa si", (c) => ["sliders", q(".modal input[type=range]") !== null]);
await probarPanel("agente", "llamada del agente", (c) => ["agente habla", c.includes("llamada")]);
await probarPanel("amd", "Panel AMD", (c) => ["panel AMD", c.includes("AMD") || c.includes("TokenFactory") || c.includes("mock")]);
await probarPanel("mapa", "Mapa de CABA", (c) => ["mapa con lista de técnicos", c.includes("zona base") || c.includes("Zona")]);
await probarPanel("dia", "Detalle del día", () => ["detalle del día (puede estar vacío)", true]);

// ------------------------------------------------- correr un día y la película
// Al mes 7 (modo sala) el día arranca EN SEGUNDO PLANO y primero se ve el cartel
// "día en vivo"; cuando termina, sale la película. En modo rápido sale directo.
clic(q(".menu-simulacion .boton-primario"));
await espera(2500);

chequeos.push(["corre un día sin explotar", true]);
chequeos.push([
  "arranca el día (cartel en vivo o película)",
  !!q(".vivo-envoltorio") || !!q(".pelicula-envoltorio"),
]);
if (q(".vivo-envoltorio")) {
  chequeos.push(["el cartel dice DÍA EN VIVO", (q(".vivo-cab")?.textContent ?? "").includes("VIVO")]);
}

let hayPelicula = !!q(".pelicula-envoltorio");
for (let i = 0; i < 60 && !hayPelicula; i++) {
  await espera(1000);
  hayPelicula = !!q(".pelicula-envoltorio");
}
chequeos.push(["arranca la película del día", hayPelicula]);
if (hayPelicula) {
  chequeos.push(["reloj de la película", /^\d{2}:\d{2}$/.test(q(".pelicula-hora")?.textContent ?? "")]);
  chequeos.push(["contadores de la película", todos(".pelicula-contador").length === 6]);
  chequeos.push(["la cinta tiene filas", todos(".cinta-fila").length > 0]);
}

let mal = 0;
const lineas = [];
for (const [nombre, ok] of chequeos) {
  if (!ok) mal++;
  lineas.push(`${ok ? "OK  " : "FALLA"} ${nombre}`);
}

const relevantes = erroresConsola.filter(
  (e) => !e.includes("Warning:") && !e.includes("actuar como") && e.trim().length > 0,
);
lineas.push(`\nErrores de consola: ${relevantes.length}`);
relevantes.slice(0, 10).forEach((e) => lineas.push("  · " + e.slice(0, 400)));

lineas.push(`\nTamaño del HTML renderizado: ${raiz().innerHTML.length} caracteres`);
const urlsVistas = [...new Set(llamadasFetch.map((l) => l.url.split("?")[0]))];const exitos = llamadasFetch.filter((l) => l.status === 200).length;
lineas.push(`\nPedidos al backend: ${llamadasFetch.length} · OK 200: ${exitos}`);
lineas.push(`Endpoints tocados: ${urlsVistas.join(", ")}`);

// Ningún pedido puede fallar: un 500 en un botón rompe la demo en vivo.
if (exitos !== llamadasFetch.length) {
  const malos = llamadasFetch.filter((l) => l.status !== 200);
  mal++;
  lineas.push(`FALLA: ${malos.length} de ${llamadasFetch.length} pedidos NO respondieron 200`);
  malos.slice(0, 8).forEach((l) => lineas.push(`  · ${l.status} ${l.url}`));
}

const salida = lineas.join("\n") + "\n";
writeFileSync(new URL("./smoke-result.txt", import.meta.url), salida, "utf8");
const fallos = mal > 0 || relevantes.length > 0 ? 1 : 0;
await new Promise((ok) => process.stdout.write(salida, ok));
process.exit(fallos);


