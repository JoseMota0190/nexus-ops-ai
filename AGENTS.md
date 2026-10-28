# Reglas del repositorio — Nexus Alarm (`nexus-ops-ai`)

> Proyecto real (no plantilla). Este archivo describe cómo está construido el producto, cómo se verifica y cómo trabaja el equipo multiagente. Se completa con evidencia comprobada; si un dato no se verificó, se marca como pendiente.

## Ficha del proyecto

- **Nombre:** `nexus-ops-ai` — producto **Nexus Alarm** (gemelo digital de una empresa de alarmas y monitoreo).
- **Objetivo:** simular la operación diaria de una empresa de seguridad (sectores, técnicos, agenda, facturación, leads, llamadas, reportes) y generar análisis y decisiones con agentes LLM, en español e inglés.
- **Stack principal:**
  - Backend: Python + FastAPI + Pydantic + SQLite + `httpx`. Cliente LLM único compatible con OpenAI en `backend/llm/`.
  - Frontend: React 18 + Vite (JavaScript, sin TypeScript).
  - Infra: Docker Compose, `render.yaml`, `netlify.toml`, `nginx.conf`.
  - Pruebas: `pytest` (backend) y `frontend/smoke.mjs` (jsdom).
- **Cómo ejecutar (local, Windows):** `scripts\dev.cmd` levanta backend en `http://localhost:8000` y frontend en `http://localhost:5173`.
  - Backend solo: `cd backend` y `.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000`.
  - Todo con Docker: `docker compose up --build`.
- **Cómo probar:**
  - Backend: `cd backend` y `.venv\Scripts\python.exe -m pytest -q` → **85 passed** (verificado 2026-10-27).
  - Frontend: `cd frontend` y `npm run build` y después `npm run smoke`. **El smoke necesita el backend levantado en `localhost:8000`**: si no está, la app muestra el aviso de "waking up" y la suite falla entera (no es una regresión).
  - En PowerShell, `npm` está bloqueado por la política de ejecución: usar `npm.cmd` o `cmd /c "npm ..."`.
  - Conexión real con el proveedor: `cd backend` y `.venv\Scripts\python.exe tests\probar_nebius.py` (lista los modelos visibles con la key y valida los IDs configurados).
- **Modo por defecto:** `USE_MOCK=true` en `.env` (sin red, sin costo).
  - `USE_MOCK=false` usa Nebius Token Factory con el **router de modelos**:
    - `LLM_BASE_URL` → `https://api.tokenfactory.nebius.com/v1`
    - `LLM_MODEL_REASONING` → `nvidia/Nemotron-3.5-Super-VL` (agentes `gerente` y `sector_*`)
    - `LLM_MODEL_FAST` → `nvidia/Nemotron-3_5-Lightning` (teleoperador, operador, agenda, técnicos, despacho)
    - `LLM_MODEL` → fallback global; `LLM_MODEL_<AGENTE>` → override por agente
    - `LLM_API_KEY` → nunca se commitea
  - La resolución del modelo vive en `LLMConfig.model_for(agent)`; precedencia: override por agente → tier → global → `""` (que el cliente interpreta como `mock`).
  - **IDs deprecados:** `NVIDIA-Nemotron-3-Nano-30B-A3B` y `nemotron-3-super-120b-a12b` salen de Serverless el 09/11/2026; `Llama-3_1-Nemotron-Ultra-253B-v1` ya fue removido el 31/08/2026. No usarlos.
- **Idiomas:** todo el producto es bilingüe ES/EN; hay una base SQLite por idioma y `POST /api/idioma` para alternar.

## Objetivo externo actual: hackathon Nebius x NVIDIA

- **Evento:** Nebius x NVIDIA Global AI Hackathon (Devpost, ID 30790).
- **Cierre de entregas:** 30 de octubre de 2026, 10:00 AM PDT (≈ 14:00 en Argentina).
- **Requisito técnico obligatorio:** la solución debe correr sobre **Nebius Token Factory** o **Nebius AI Cloud** y usar al menos un **modelo open source de NVIDIA** (familia Nemotron).
- **Track elegido:** *Best Apps and Agents* (decidido 2026-10-27, ver `DECISIONS.md` D-005). El track pide «a workflow that runs itself» y el producto es exactamente eso. Descartados: *Coding and Agentic Engineering* (pide agentes que escriben/corren/testean código), *Personal AI* (exige el stack NemoClaw/OpenShell/Hermes) y *Physical AI* (exige hardware real operando).
- **Estructura de premios:** ganar un track entrega un Jetson Orin Nano, **no efectivo**. La plata ($20k / $10k / $6k) es Grand Prize / 2º / 3º y compite entre todos los tracks. El premio *Best Use of Tavily* ($3.000) es independiente y se apila.
- **Entregables:** demo funcionando (URL), video de ≤3 minutos, repositorio público con licencia open source visible, descripción del proyecto, feedback sobre las herramientas de Nebius y explicación de qué se actualizó si el proyecto ya existía.
- **Criterios de juicio:** *Technological Implementation*, *Design*, *Potential Impact*, *Quality of the Idea*. Por eso el router de modelos y la observabilidad por modelo no son adorno: responden literalmente al primer criterio.
- **Implicancia para el código:** el cliente LLM es compatible con OpenAI, así que el cambio de proveedor fue configuración (`LLM_BASE_URL`, `LLM_MODEL_REASONING`, `LLM_MODEL_FAST`, `LLM_API_KEY`). No se reescribió la capa LLM ni el motor de simulación.

## Principios de trabajo

- Inspeccionar primero; no asumir estructura, dependencias, versiones ni comandos.
- Priorizar cambios pequeños y coherentes con los patrones existentes.
- No reescribir funcionalidades existentes ni hacer refactors fuera del alcance solicitado.
- Explicar los supuestos cuando falte información; no inventar requisitos.
- Mantener secretos fuera de Git. Nunca incluir claves API, contraseñas, cookies, tokens ni datos personales en el código o en los logs.
- No ejecutar acciones destructivas, migraciones irreversibles, despliegues, commits o push sin autorización explícita.
- Ejecutar pruebas relevantes cuando sea posible y reportar claramente lo que no se pudo verificar.
- Usar `PLAN.md` como objetivo y hoja de ruta; `TASKS.md` como estado operativo; `DECISIONS.md` para decisiones técnicas importantes.

## Selección de modelos por proyecto

- `MODEL_SELECTION.md` guarda la elección vigente de los cuatro roles. Estado actual: `CONFIGURADA` (2026-10-27), con revisión pendiente del Config Helper.
- Si un ID deja de existir en `/models`, el agente que lo usa falla. Verificar antes de asumir que la selección sigue siendo válida.
- Config Helper debe usar un endpoint **gratuito vigente** y con **entrada de imágenes confirmada**; priorizar tool calling.
- Tras un cambio de modelos, actualizar el frontmatter de los cuatro agentes y `MODEL_SELECTION.md`, y pedir una sesión nueva para recargar la configuración.

## Reglas del equipo multiagente

- Foreman coordina, divide el trabajo, delega y verifica. No hace toda la implementación por su cuenta.
- Implementer modifica código solo dentro de la tarea asignada e informa evidencia.
- Reviewer realiza una revisión independiente de solo lectura y nunca modifica archivos.
- Config Helper resuelve consultas de configuración y diagnóstico, puede analizar imágenes si el modelo asignado admite visión y pide autorización antes de editar configuración.
- No ejecutar dos implementaciones concurrentes sobre los mismos archivos.
- No considerar un informe de un agente como prueba suficiente: revisar la evidencia y, cuando sea pertinente, el diff y las pruebas.
- Marcar una tarea como `DONE` solo cuando sus criterios de aceptación estén comprobados.
- Las tareas bloqueadas deben incluir motivo, intento realizado y qué decisión o recurso hace falta.

## Verificación específica del proyecto

- **Tests backend:** `backend/.venv/Scripts/python.exe -m pytest -q` desde `backend/` (**85 tests**, 2026-10-27).
- **Smoke frontend:** `npm run build` y después `npm run smoke` desde `frontend/`. Requiere `node_modules` **y el backend levantado en `localhost:8000`**.
- **Build frontend:** `npm run build` desde `frontend/`.
- **Conexión real con el proveedor:** `.venv\Scripts\python.exe tests\probar_nebius.py` desde `backend/`. No es parte de `pytest`: es un diagnóstico manual que necesita key real.
- **Lint/format:** no hay linter ni formateador configurado en el repositorio. No inventar comandos.
- **Comando de desarrollo:** `scripts\dev.cmd` (Windows) o `docker compose up --build`.
- **Estructura importante:**
  - `backend/api.py` — superficie HTTP, incluido `/api/metricas` con el desglose por modelo.
  - `backend/engine/` — simulación (sectores, agenda, facturas, leads, llamadas, enjambre, gerente, redactor, montecarlo).
  - `backend/llm/` — cliente único, **router de modelos (`config.py`)**, modo mock, caché, métricas, prompts.
  - `backend/store.py` — persistencia SQLite.
  - `backend/tests/` — pruebas de API, motor, facturas, enjambre, LLM y router.
  - `frontend/src/` — interfaz (React), `caba.js` (datos geográficos), `i18n.js` (ES/EN), `components/FranjaNebius.jsx` (observabilidad en vivo).
  - `.opencode/agents/` — definición de los cuatro agentes.

## Estado de Git y riesgos conocidos

- Configuración multiagente, `PLAN.md`, `TASKS.md`, `DECISIONS.md` y `docs/` **ya están commiteados** en local (`9911921` y `19d2d65`, 2026-10-27). El push al repositorio público sigue pendiente (T-015) y requiere autorización explícita.
- `README.md` ya es el del producto: problema, arquitectura, uso de Nebius + Nemotron con la tabla del router, quickstart, variables, tests y «What changed during the submission period». La doc del equipo multiagente vive en `docs/EQUIPO.md`.
- `docs/PROMPT_INICIO_PROYECTO.md` y `docs/MODELOS.md` describen la plantilla; no contradicen al producto pero deben leerse como documentación de proceso, no del sistema.
- `.env.example`, `render.yaml` y `docker-compose.yml` ya apuntan a **Nebius Token Factory** con el router Nemotron. Falta la verificación con una API key real (T-013).
- **Material de entrega pendiente de rebrand:** `SLIDES.md` y `entrega/slides.html` (incluye el PDF ya exportado) todavía mencionan AMD. Es lo último que queda de la migración.
- **Riesgo alto — credenciales:** sin cuenta de Nebius con créditos aplicados no hay evidencia real, ni video, ni submission válida. Los créditos del formulario **no se acreditan solos**: el código promo se canjea en la consola (*balance → Top up → With promo code*) y el Builders Program exige verificar el email y reclamar el crédito.
- **Riesgo medio — presupuesto:** el router reduce costo, pero medir antes de grabar. La caché de `backend/llm/cache.py` permite repetir la demo sin gastar.
- **Riesgo bajo — Config Helper:** `MODEL_SELECTION.md` sigue apuntando a un modelo inexistente para ese rol; no afecta al producto ni a la entrega.

## Punto de retorno (2026-10-27, sesión pausada)

Al retomar, el orden es:

1. **Usuario:** aplicar los créditos en Nebius y generar la API key. Cargarla en `backend/.env` con `USE_MOCK=false`.
2. **Foreman:** correr `backend/.venv/Scripts/python.exe tests\probar_nebius.py` desde `backend/`, confirmar los IDs reales y registrar la evidencia en `TASKS.md` (T-010).
3. **Foreman:** rebrandear `SLIDES.md` y `entrega/slides.html` (T-016).
4. **Usuario + Foreman:** deploy público (T-006) y grabación del video (T-007).
5. **Usuario:** submission en Devpost antes del 30/10/2026 10:00 PDT (T-008).

Estado de verificación al pausar: `pytest -q` → 85 passed; `npm run build` → OK; `npm run smoke` → 0 fallas, 35/35 requests 200.
