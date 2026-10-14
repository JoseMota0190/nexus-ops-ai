// Formateo de números a la criolla: pesos, dólares y números con coma decimal.

export function num(valor, decimales = 0) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
  return Number(valor).toLocaleString("es-AR", {
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

export const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];

export const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
