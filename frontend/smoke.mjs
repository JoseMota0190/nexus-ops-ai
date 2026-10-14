// Prueba de humo: renderiza la pantalla construida en un DOM simulado,
// la pega contra el backend real y revisa que no explote.
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

const texto = document.getElementById("root").textContent;
const tiene = (frase) => texto.includes(frase);

const chequeos = [
  ["arrancó el render", document.getElementById("root").children.length > 0],
  ["cabecera", tiene("Nexus Alarm")],
  ["meta del dueño", tiene("Meta del dueño: 10 técnicos para el mes 9")],
  ["mes/semana", tiene("Mes") && tiene("Semana")],
  ["botón avanzar", tiene("Avanzar 1 mes")],
  ["botón 6 meses", tiene("Correr 6 meses de una")],
  ["botón reiniciar", tiene("Reiniciar")],
  ["KPI ventas por día", tiene("Ventas por día")],
  ["KPI conversión", tiene("Conversión")],
  ["KPI técnicos", tiene("Técnicos activos")],
  ["KPI operadores", tiene("Operadores")],
  ["KPI caja", tiene("Plata en caja")],
  ["KPI clientes", tiene("Clientes activos")],
  ["¿qué pasa si...?", tiene("¿Qué pasa si…?")],
  ["sliders", document.querySelectorAll("input[type=range]").length === 3],
  ["acta / gerencia", tiene("Reunión mensual de gerencia")],
  ["evolución", tiene("Evolución mes a mes")],
  ["telégrafo", tiene("Telégrafo de llamadas")],
  ["motivos", tiene("Motivos: por qué no se vende")],
  ["agente habla", tiene("Escuchar una llamada del agente")],
  ["panel AMD", tiene("TOKENFACTORY") || tiene("TokenFactory")],
  ["mapa", tiene("Mapa de CABA")],
  ["gráfico SVG", document.querySelectorAll("svg").length > 0],
  ["barras del gráfico", document.querySelectorAll("rect").length > 0],
  ["barrios en el mapa", document.querySelectorAll("circle").length > 0],
  ["error amable, sin stack trace", !texto.includes("Traceback") && !texto.includes("NameError")],
  ["gráfico con datos", !!document.querySelector(".grafico-svg")],
  ["telégrafo con filas", document.querySelectorAll("table tbody tr").length > 0],
  ["acta del gerente", !!document.querySelector(".acta")],
  ["motivos con barras", document.querySelectorAll(".barra-motivo").length > 0],
  ["estado pegado al backend", /Mes\s+\d+\s+de\s+9/.test(texto)],
];

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

const raiz = document.getElementById("root").innerHTML;
lineas.push(`\nTamaño del HTML renderizado: ${raiz.length} caracteres`);
const urlsVistas = [...new Set(llamadasFetch.map((l) => l.url.split("?")[0]))];
const exitos = llamadasFetch.filter((l) => l.status === 200).length;
lineas.push(`\nPedidos al backend: ${llamadasFetch.length} · OK 200: ${exitos}`);
lineas.push(`URLs probadas: ${llamadasFetch.map((l) => l.url.replace("http://", "")).slice(0, 6).join(" | ")}`);
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
