// Number and date formatting, always in the active language.
//
// English uses "1,234.5"; Spanish uses "1.234,5". The backend already formats
// the report text that way, so the screen matches it.
import { getIdioma } from "./i18n.js";

const LOCALES = { en: "en-US", es: "es-AR" };

function locale() {
  return LOCALES[getIdioma()] || LOCALES.en;
}

export function num(valor, decimales = 0) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
  return Number(valor).toLocaleString(locale(), {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  });
}

export function usd(valor, decimales = 0) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
  const n = Number(valor);
  const signo = n < 0 ? "−" : "";
  return `${signo}USD ${num(Math.abs(n), decimales)}`;
}

export function pct(valor, decimales = 1) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
  return `${num(valor, decimales)} %`;
}

const DIAS_POR_IDIOMA = {
  en: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  es: ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
};

export function diasSemana() {
  return DIAS_POR_IDIOMA[getIdioma()] || DIAS_POR_IDIOMA.en;
}

const MESES_POR_IDIOMA = {
  en: ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"],
  es: ["enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
};

export function meses() {
  return MESES_POR_IDIOMA[getIdioma()] || MESES_POR_IDIOMA.en;
}
