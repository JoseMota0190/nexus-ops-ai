# Registro de tareas — Nexus Alarm

> Foreman mantiene este archivo. IDs estables (`T-001`, `T-002`…). «En curso» en el registro no implica que un agente esté ejecutándose ahora.
> Objetivo vigente: hackathon Nebius x NVIDIA, track **Best Apps and Agents**, cierre **30/10/2026 10:00 PDT**.

## Resumen

- Completadas: 6
- En revisión: 1
- En curso: 1
- Pendientes: 5
- Bloqueadas: 2

## Completadas

### T-001 — Auditoría de línea base del proyecto

- **Estado:** `DONE` (2026-10-27)
- **Responsable:** Foreman
- **Evidencia:**
  - `pytest -q` → 77 passed (línea base).
  - `opencode debug agents` → 4 agentes de proyecto detectados.
  - Frontend es React 18 + Vite. `README.md` era el de la plantilla multiagente.

### T-003 — Cerebro Nebius + router de modelos Nemotron por agente

- **Estado:** `DONE` (2026-10-27)
- **Responsable:** Implementer + Foreman (remate)
- **Hecho:**
  - `backend/llm/config.py` reescrito: `base_url` a Token Factory, campos `reasoning_model`, `fast_model`, `agent_models` y `model_for(agent)` con precedencia override → tier → global.
  - `backend/llm/client.py`: helper `_modelo(agent)`; caché, métricas y fallback keyed por el modelo real.
  - `backend/llm/metrics.py`: `records()` para el panel.
  - `backend/tests/test_llm.py`: 7 tests del router + 1 de integración modelo↔métrica.
  - `.env.example`, `render.yaml` y `docker-compose.yml` con Nebius + los dos Nemotron.
  - `probar_amd.py` → `probar_nebius.py`, adaptado al router.
- **Evidencia:** `pytest -q` → **85 passed, 1 warning, 28,68 s**. `grep AMD|Radeon|Gemma` en `backend/**/*.py` → vacío.

### T-011 — Observabilidad por modelo

- **Estado:** `DONE` (2026-10-27)
- **Responsable:** Implementer + Foreman
- **Hecho:**
  - `/api/metricas` devuelve `modelo_razonamiento`, `modelo_rapido`, `modelos` por agente y `por_modelo` (calls, tokens, fallbacks, latencia promedio).
  - `FranjaAMD.jsx` → `FranjaNebius.jsx`, con ambos modelos y el conteo de llamadas de cada uno.
  - `.franja-amd*` → `.franja-nebius*` en `styles.css`.
- **Evidencia:** smoke en verde; el chequeo «franja Nemotron siempre visible» pasa.

### T-004 — README del producto

- **Estado:** `DONE` (2026-10-27)
- **Responsable:** Foreman
- **Hecho:** `README.md` reescrito en inglés: problema, producto, agentes, arquitectura, uso de Nebius Token Factory + Nemotron con la tabla del router, observabilidad, quickstart, variables, tests, «What changed during the submission period» y licencia.
- **Hecho:** la doc del equipo multiagente se movió a `docs/EQUIPO.md`.
- **Pendiente menor:** las URLs de demo y video son placeholders hasta el deploy.

### T-005 — Verificación local completa

- **Estado:** `DONE` (2026-10-27)
- **Responsable:** Foreman
- **Evidencia:**
  - Backend `pytest -q` → **85 passed**.
  - Frontend `npm run build` → OK; `npm run smoke` → **0 fallas, 0 errores de consola, 35/35 requests 200**.
- **Hallazgo:** el smoke necesita el backend levantado en `localhost:8000`; sin él la app muestra el aviso de "waking up" y falla entero. No era una regresión.

### T-012 — Barrido de marca AMD → Nebius (parcial)

- **Estado:** `IN_PROGRESS` (2026-10-27)
- **Hecho:** `backend/`, `render.yaml`, `docker-compose.yml`, `frontend/src/**`, `frontend/README.md` y `README.md` limpios.
- **Falta:** `PITCH.md` (14), `SLIDES.md` (11), `entrega/slides.html` (19), `AGENTS.md` (1), y las menciones a AMD en `PLAN.md`/`TASKS.md`/`DECISIONS.md` que son históricas y se dejan como registro.

## En revisión

### T-002 — Configurar el equipo multiagente de OpenCode

- **Estado:** `IN_REVIEW`
- **Pendiente:** reemplazar el modelo inválido del Config Helper (`google/gemini-2.5-flash-image-preview:free`) y probar una delegación real.
- **Nota:** no bloquea el producto ni la entrega.

## Pendientes

### T-010 — Verificación end-to-end con Nemotron real (P0)

- **Responsable:** Usuario + Foreman
- **Dependencias:** **T-013**.
- **Objetivo:** una llamada real a cada tier devuelve JSON validado, con latencia y tokens registrados.
- **Criterio:** evidencia transcripta (modelo, latencia, tokens) y salida de `probar_nebius.py`.

### T-016 — Reescritura de PITCH.md y SLIDES.md para Nebius (P0)

- **Responsable:** Foreman
- **Objetivo:** guion de 3 minutos y slides con la narrativa Nebius/Nemotron/router, sin menciones a AMD.
- **Criterio:** `grep AMD` vacío en el material de entrega.

### T-006 — Despliegue público de la demo (P0)

- **Responsable:** Implementer + Usuario
- **Dependencias:** T-010, credenciales de hosting.
- **Objetivo:** URL pública (Render + Netlify) con las variables de Nebius.
- **Criterio:** URL accesible con el recorrido completo.

### T-007 — Video de demo (≤3 min) (P0)

- **Responsable:** Usuario + Foreman (guion)
- **Dependencias:** T-006, T-016.
- **Criterio:** video público, ≤3 min, con el router de modelos visible.

### T-008 — Envío en Devpost (P0)

- **Responsable:** Usuario
- **Dependencias:** T-004, T-006, T-007.
- **Criterio:** submission enviada antes del 30/10/2026 10:00 PDT.

### T-014 — Tavily: agente investigador de mercado (P2, condicional)

- **Responsable:** Implementer
- **Dependencias:** Fases 0–5 cerradas + API key de Tavily.
- **Criterio:** llamada real a Tavily dentro del flujo del gerente.

## Bloqueadas

### T-013 — Credenciales de Nebius Token Factory

- **Estado:** `BLOCKED`
- **Motivo:** el usuario todavía no tiene cuenta ni API key.
- **Qué hace falta:**
  1. Crear cuenta en https://tokenfactory.nebius.com/
  2. Canjear `NEBIUS-DEVPOST-GLOBAL26` ($25).
  3. Unirse a https://dev.nebius.com/builders ($25 más).
  4. Generar API key y cargarla en `.env` local.
- **Bloquea:** T-010, T-006, T-007, T-008.

### T-015 — Repositorio público con licencia visible

- **Estado:** `BLOCKED`
- **Motivo:** el usuario autorizó **solo commit local**; el push queda pendiente.
- **Nota:** `LICENSE` (MIT) ya existe.

## Formato de tarea

- **ID y título:**
- **Estado:** `PENDING` / `IN_PROGRESS` / `BLOCKED` / `IN_REVIEW` / `DONE`
- **Responsable:** Foreman / Implementer / Reviewer / Config Helper
- **Objetivo:**
- **Archivos o áreas relevantes:**
- **Dependencias:**
- **Criterios de aceptación:**
- **Verificación y evidencia:**
- **Bloqueo o próximo paso:**
