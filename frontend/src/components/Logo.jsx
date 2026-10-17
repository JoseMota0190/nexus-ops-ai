import { useId } from "react";

/**
 * El logo de Nexus: el "chevron A" de la placa (degradado violeta -> azul
 * eléctrico). Es el mismo dibujo en el header y en el centro del mapa.
 */
export default function Logo({ tamano = 26, className = "" }) {
  const id = "nx-" + useId().replace(/:/g, "");
  return (
    <svg
      className={`logo-svg ${className}`}
      width={tamano}
      height={tamano}
      viewBox="0 0 48 48"
      role="img"
      aria-label="Nexus"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7a5af8" />
          <stop offset="100%" stopColor="#2f6bff" />
        </linearGradient>
      </defs>
      <path d="M24 5 L45 43 H33.6 L24 24.6 L14.4 43 H3 Z" fill={`url(#${id})`} />
    </svg>
  );
}
