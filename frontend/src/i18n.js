// The site speaks English and Spanish. This is the ONE place that knows which
// language is active.
//
//   t("in English", "en español")   -> the text in the active language
//   setIdioma("es")                 -> switches everything and re-renders
//   useIdioma()                     -> any component that shows text calls it
//
// English is the default. The chosen language is saved so a reload keeps it.
import { useSyncExternalStore } from "react";

const CLAVE = "nexus_idioma";
let _idioma = "en";
const oyentes = new Set();

function avisar() {
  for (const fn of oyentes) fn();
}

export function getIdioma() {
  return _idioma;
}

export function setIdioma(lang) {
  const l = lang === "es" ? "es" : "en";
  if (l === _idioma) return l;
  _idioma = l;
  try {
    localStorage.setItem(CLAVE, l);
  } catch {
    /* private mode: we just don't remember the choice */
  }
  avisar();
  return l;
}

// Reads the saved choice at boot (before the first render).
export function idiomaGuardado() {
  try {
    const g = localStorage.getItem(CLAVE);
    if (g === "es" || g === "en") _idioma = g;
  } catch {
    /* nothing saved */
  }
  return _idioma;
}

// The shortcut: `t("in English", "en español")`.
export function t(en, es) {
  return _idioma === "es" ? es : en;
}

export function suscribir(fn) {
  oyentes.add(fn);
  return () => oyentes.delete(fn);
}

// A hook so any component re-renders when the language changes.
export function useIdioma() {
  return useSyncExternalStore(suscribir, getIdioma, getIdioma);
}
