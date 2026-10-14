# Nexus Alarm — Pantalla del dueño

La pantalla única que ve el dueño de **Nexus Alarm**: los KPIs del negocio, el gráfico
"¿Qué pasa si…?", la evolución mes a mes, el acta del Gerente IA, el telégrafo de llamadas,
el mapa de CABA y el panel de métricas de AMD.

Todo en español, tema oscuro, sin librerías de UI pesadas (los gráficos están dibujados a
mano con SVG).

## Cómo levantarlo

Necesitás dos ventanas (o dos pestañas):

**1) El motor (la simulación)** — desde la carpeta `backend`:

```bat
.\.venv\Scripts\python.exe -m uvicorn api:app --port 8000
```

**2) Esta pantalla** — desde la carpeta `frontend` (OJO: en PowerShell se usa `npm.cmd`):

```bat
npm.cmd install     -- solo la primera vez
npm.cmd run build   -- arma la versión final en dist/
npm.cmd run dev     -- la versión para desarrollo, en http://localhost:5173
```

Si el backend vive en otra máquina o puerto, copiá `.env.example` a `.env` y cambiá
`VITE_API_URL`. Si no está esa variable, se usa `http://localhost:8000`.

## Comandos útiles

| Comando             | Qué hace                                                    |
| ------------------- | ----------------------------------------------------------- |
| `npm.cmd run dev`   | Servidor de desarrollo con recarga al tocar un archivo       |
| `npm.cmd run build` | Genera `dist/` (estático, se puede subir a Netlify)          |
| `npm.cmd run preview` | Sirve el `dist/` como si estuviera publicado               |
| `npm.cmd run smoke` | Prueba automática: renderiza la pantalla contra el backend   |

La prueba `smoke` necesita el backend levantado y el `build` hecho.

## Qué mira cada parte

- **Cabecera**: mes, semana, los botones de la simulación y la barra de la meta
  "10 técnicos para el mes 9".
- **KPIs**: ventas por día (potencial vs objetivo), conversión (contestan / compran),
  técnicos, operadores, caja y clientes activos.
- **¿Qué pasa si…?**: tres sliders que llaman a `POST /api/escenario`. No toca la
  simulación real: es una cuenta al aire.
- **Evolución**: `GET /api/resumenes` → barras de ingresos vs costos y línea de técnicos.
- **Acta del Gerente**: `GET /api/actas` + las decisiones de `GET /api/estado`.
- **Telégrafo**: `GET /api/llamadas` + los motivos de `/api/estado`.
- **El agente habla**: `POST /api/llamada_en_vivo`.
- **Mapa**: `GET /api/mapa`, dibujado con SVG y animado por día de la semana.
- **Panel AMD**: `GET /api/metricas`.

El estado se refresca solo cada 4 segundos (los gráficos y tablas, cada 12).
