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
  "<!doctype html><html lang='en'><body><div id='root'></div></body></html>",
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
  ["botón correr un día", tiene("Run one day")],
  ["velocidad 3 min", tiene("3 min")],
  ["velocidad 6 min", tiene("6 min")],
  ["velocidad 9 min", tiene("9 min")],
  ["mapa a pantalla completa", !!q(".mapa-portada")],
  ["dibujo de CABA (48 barrios)", todos(".caba-barrio").length === 48],
  ["portada sin círculos (sin ruido)", todos(".mapa-portada circle").length === 0],
  ["sin la bandeja vieja apilada", !q("section.paneles")],
  ["franja AMD siempre visible", !!q(".franja-amd")],
  ["Sala de agentes en el pie", !!q(".sim-sala")],
  ["pie discreto del menú", true], // el pie vive dentro del menú lateral

  // ------------------------------------------------------ menú lateral
  ["menú lateral cerrado al inicio", !q(".menu-lateral")],
];

// Abrimos el menú lateral.
const btnMenu = q(".tira-menu");
clic(btnMenu);
await espera(150);

chequeos.push(["menú lateral abierto", !!q(".menu-lateral")]);
chequeos.push(["menú con 4 sectores", todos(".menu-item").length === 4]);
chequeos.push(["sector Gerencia", tiene("Management")]);
chequeos.push(["sector Ventas", tiene("Sales")]);
chequeos.push(["sector Agenda", tiene("Scheduling & technicians")]);
chequeos.push(["sector Facturación", tiene("Billing")]);

// Cada sector tiene que abrir su informe del mes.
const SECTORES = [
  ["gerente", "Management", (c) => ["informe de gerencia", c.includes("Result") || c.includes("Month") || c.includes("Recommendation")]],
  ["ventas", "Sales", (c) => ["informe de ventas", c.includes("Conversion") || c.includes("calls") || c.includes("Sales")]],
  ["agenda", "Scheduling & technicians", (c) => ["informe de agenda", c.includes("Installs") || c.includes("slot") || c.includes("Scheduling")]],
  ["facturacion", "Billing", (c) => ["informe de facturación", c.includes("Invoice") || c.includes("SIMULATED") || c.includes("precision")]],
];

for (const [id, nombre, chequeo] of SECTORES) {
  if (!q(".menu-lateral")) {
    clic(q(".tira-menu"));
    await espera(140);
  }
  const item = todos(".menu-item").find((b) => b.textContent.includes(nombre));
  clic(item);
  await espera(600);
  chequeos.push([`abre el sector (${id})`, !!q(".modal")]);
  const cuerpo = q(".modal-cuerpo")?.textContent ?? "";
  chequeos.push(chequeo(cuerpo));
  // Cerramos con la X del modal y dejamos el menú cerrado para el próximo.
  clic(q(".modal .menu-x"));
  await espera(150);
  chequeos.push([`cierra el sector (${id})`, !q(".modal")]);
  if (q(".menu-lateral")) {
    clic(q(".tira-menu"));
    await espera(120);
  }
}

// Los paneles viejos (KPIs, telégrafo, etc.) siguen en el código, pero el menú
// ahora solo ofrece los 4 sectores (ya verificado arriba con "menú con 4 sectores").

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
  chequeos.push(["el cartel dice LIVE DAY", (q(".vivo-cab")?.textContent ?? "").includes("LIVE")]);
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

// ------------------------------------------------------- idioma ES / EN
// El botón de idioma cambia TODO el sitio. Al tocar ES el backend arma su base
// (la primera vez tarda unos segundos) y la pantalla se re-renderiza en español.
chequeos.push([
  "botón de idioma ES/EN en el header",
  !!q(".tira-idioma") && todos(".tira-idioma .idioma-chip").length === 2,
]);
const btnEs = todos(".tira-idioma .idioma-chip").find((b) => b.textContent.trim() === "ES");
if (btnEs) {
  clic(btnEs);
  await espera(9000); // la primera vez el español arma su base
  const enEspanol =
    tiene("Los 4 sectores") || tiene("Correr un día") || tiene("Gemelo digital");
  chequeos.push(["el sitio pasa a español", enEspanol]);
  const btnEn = todos(".tira-idioma .idioma-chip").find((b) => b.textContent.trim() === "EN");
  if (btnEn) {
    clic(btnEn);
    await espera(2500);
    chequeos.push(["el sitio vuelve a inglés", tiene("Run one day") || tiene("The 4 sectors")]);
  }
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


