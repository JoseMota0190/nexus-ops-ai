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
  - Backend: `cd backend` y `.venv\Scripts\python.exe -m pytest -q` → **77 passed** (verificado 2026-10-27).
  - Frontend: `cd frontend` y `npm run smoke`.
- **Modo por defecto:** `USE_MOCK=true` en `.env` (sin red, sin costo). `USE_MOCK=false` usa el proveedor configurado en `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`.
- **Idiomas:** todo el producto es bilingüe ES/EN; hay una base SQLite por idioma y `POST /api/idioma` para alternar.

## Objetivo externo actual: hackathon Nebius x NVIDIA

- **Evento:** Nebius x NVIDIA Global AI Hackathon (Devpost, ID 30790).
- **Cierre de entregas:** 30 de octubre de 2026, 10:00 AM PDT (≈ 14:00 en Argentina).
- **Requisito técnico obligatorio:** la solución debe correr sobre **Nebius Token Factory** o **Nebius AI Cloud** y usar al menos un **modelo open source de NVIDIA** (familia Nemotron).
- **Track objetivo:** *Best Apps and Agents* (producto/agente usable), con opción de *Coding and Agentic Engineering* si la narrativa se orienta al equipo multiagente.
- **Entregables:** demo funcionando (URL), video de ≤3 minutos, repositorio público con licencia open source visible, descripción del proyecto, feedback sobre las herramientas de Nebius y explicación de qué se actualizó si el proyecto ya existía.
- **Implicancia para el código:** el cliente LLM ya es compatible con OpenAI, así que el cambio de proveedor se hace por configuración (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`) apuntando a Token Factory, con un modelo Nemotron. No requiere reescribir la capa LLM.

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

- **Tests backend:** `backend/.venv/Scripts/python.exe -m pytest -q` desde `backend/` (77 tests, 2026-10-27).
- **Smoke frontend:** `npm run smoke` desde `frontend/` (requiere `node_modules`).
- **Build frontend:** `npm run build` desde `frontend/`.
- **Lint/format:** no hay linter ni formateador configurado en el repositorio. No inventar comandos.
- **Comando de desarrollo:** `scripts\dev.cmd` (Windows) o `docker compose up --build`.
- **Estructura importante:**
  - `backend/api.py` — superficie HTTP.
  - `backend/engine/` — simulación (sectores, agenda, facturas, leads, llamadas, enjambre, gerente, redactor, montecarlo).
  - `backend/llm/` — cliente único, modo mock, caché, métricas, prompts.
  - `backend/store.py` — persistencia SQLite.
  - `backend/tests/` — pruebas de API, motor, facturas, enjambre y LLM.
  - `frontend/src/` — interfaz (React), `caba.js` (datos geográficos), `i18n.js` (ES/EN).
  - `.opencode/agents/` — definición de los cuatro agentes.

## Estado de Git y riesgos conocidos

- Archivos de la configuración multiagente (`.opencode/`, `opencode.json`, `MODEL_SELECTION.md`, `PLAN.md`, `TASKS.md`, `DECISIONS.md`) **ya están commiteados** (commit local `9911921`, 2026-10-27). El push al repositorio público sigue pendiente (T-015).
- `README.md` ya es el del producto: problema, arquitectura, uso de Nebius + Nemotron, setup, tests y «What changed during the submission period». La doc del equipo multiagente vive en `docs/EQUIPO.md`.
- `docs/PROMPT_INICIO_PROYECTO.md` y `docs/MODELOS.md` describen la plantilla; no contradicen al producto pero deben leerse como documentación de proceso, no del sistema.
- `.env.example` ya apunta a **Nebius Token Factory** con el router Nemotron (`LLM_MODEL_REASONING` / `LLM_MODEL_FAST`). Migración hecha en T-003 (2026-10-27); falta la verificación con una API key real (T-013).
