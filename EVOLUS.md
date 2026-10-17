# Brief: módulo Evolus para nexus-ops-ai

> **Para la IA que va a construir esto:** leé este archivo completo antes de escribir
> una sola línea de código. Está pensado para que trabajes **en paralelo** a otro
> asistente que está tocando otras partes del repo.

---

## Contexto

Repo: https://github.com/JoseMota0190/nexus-ops-ai (rama `main`).

Gemelo digital de una empresa ficticia de alarmas ("Nexus Alarm") para la hackathon
lablab.ai + AMD. Backend Python 3.10 + FastAPI, frontend React + Vite, SQLite.

**El dueño NO es técnico:** explicá en criollo, sin jerga. Si algo es complejo,
usá una historia o analogía.

**Prioridad máxima:** NO romper nada de lo que ya existe y está probado (36 tests
en verde + un test de humo de la pantalla con 55+ checks). Evolus es una pieza
**adicional y opcional**; la demo principal no puede depender de ella.

Vos construís **SOLO** el módulo Evolus, **EN PARALELO** a otro asistente que está
tocando otras partes del repo. Respetá a rajatabla las reglas de no choque de más
abajo.

---

## Qué es Evolus (docs: https://evolus.ai/en/developers)

Plataforma externa de agentes, workflows y extracción de documentos.

### Endpoints

| Uso | URL | Autenticación |
|---|---|---|
| REST (workflows, extractors, AI Tools, libraries) | `https://api.evolus.ai/api/v1` | headers `X-ApiKey` + `X-Application-Id` (o `X-User-ApiKey`) |
| Chat de agentes (OpenAI-compatible) | `https://api.evolus.ai/v1` | `Authorization: Bearer <key>` · model = `"<applicationId>:<agentId>"` · lista con `GET /v1/models` |
| MCP server | `https://api.evolus.ai/mcp` | mismos headers que REST |
| Workspace del evento (gratis) | https://app.evolus.ai/join/AMDACT3 | creá desde ESE link, nunca desde `app.evolus.ai` derecho |

**Workspace del evento:** 50.000 créditos · 60 req/min · hasta 6 personas ·
válido hasta **15-nov-2026 23:59 hora italiana** · sin tarjeta.

### AI Tools — listos, UN endpoint por tool, NO requieren configurar nada en la UI

```
GET  /api/v1/ai-tools                          catálogo (inputs y opciones)
POST /api/v1/ai-tools/{tool}/run               JSON  { text, secondaryText, options }
POST /api/v1/ai-tools/{tool}/run-media         multipart file (doc o audio/video)
POST /api/v1/ai-tools/{tool}/run-file          sólo `translate` y `anonymize`
```

Tools disponibles: `doc-structure`, `tables`, `translate`, `anonymize`,
`summarize`, `minutes`, `email`, `rewrite`, `simplify`, `sentiment`, `compare`.

Respuesta: `{ tool, output, creditsConsumed, truncated }`.

- Límites: documentos 20 MB · audio/video 100 MB · 120.000 caracteres de texto.
- **Usan créditos de la plataforma** (los 50.000 alcanzan de sobra para una demo).

### Extractor propio (requiere crearlo ANTES en la UI del workspace)

```
POST /api/v1/agents/{AGENT_ID}/json/{EXTRACTOR_ID}/ask-file    multipart file
```

- Devuelve el JSON con **tu esquema** (definido en la UI).
- `?useWebhook=false` si querés la respuesta en el body (sino va al webhook).
- `.../ask-files` para varios documentos en una llamada.
- **Usa créditos.** Encabezados `X-AskFile-Execution-Id` / `X-AskFile-Audit-Id`.

### Workflow (requiere crearlo y ENCENDERLO en la UI; apagado → 409)

```
POST /api/v1/workflows/{workflowId}/execute    multipart: input, file(s), parameters
→ 202 Accepted + { jobId, executionId, ... }   (también en header X-Workflow-Execution-Id)

GET  /api/v1/workflows/{workflowId}/executions/{executionId}
→ polling hasta status: Pending | Running | Completed | Failed
```

- Campos: `input` (texto), `file` (uno o más), `parameters` (JSON plano),
  `callbackUrl` (opcional, manda el resultado a tu URL).
- Nunca mandes secretos como `parameters`: quedan guardados con la ejecución.

### Credenciales

Las genera **el dueño** en la página de **API keys** del workspace:

- `X-ApiKey` → variable `EVOLUS_API_KEY`
- space ID (`X-Application-Id`) → variable `EVOLUS_APPLICATION_ID`

Van en `.env`. **NUNCA se commitean.**

---

## Qué construir: un módulo AISLADO

**Propósito:** extraer datos de documentos (facturas/contratos simulados) y
ejecutar un workflow de contratos, como pieza aparte del simulador principal.

### Archivos NUEVOS solamente

```
backend/evolus/__init__.py
backend/evolus/config.py      EVOLUS_ENABLED, EVOLUS_API_BASE, EVOLUS_API_KEY,
                              EVOLUS_APPLICATION_ID. dataclass frozen.
                              Si no hay clave o EVOLUS_ENABLED=false → modo mock.
backend/evolus/client.py      httpx. Máx 2 reintentos. Timeout. EvolusError tipado.
backend/evolus/mock.py        respuestas offline deterministas (mirá el patrón de
                              backend/llm/mock.py y replicalo).
backend/evolus/facturas.py    genera comprobantes SIMULADOS con sello
                              "SIMULADO – SIN VALIDEZ FISCAL" y les inyecta
                              errores al azar (Monte Carlo): total mal sumado,
                              fecha inválida, campo faltante, CUIT inválido, etc.
                              Documentá probabilidades y tipos de error.
backend/evolus/extract.py     extrae (doc-structure, o el extractor propio si
                              existe) y COMPARA contra lo esperado → precisión
                              por campo + lista de errores detectados/fallados.
backend/evolus/workflow.py    dispara el workflow de contrato + polling de estado.
backend/evolus/router.py      APIRouter de FastAPI. NO importarlo en api.py:
                              dejá las instrucciones en EVOLUS.md, el dueño conecta.
backend/tests/test_evolus.py  DEBE pasar sin red (usa mock).
EVOLUS.md                     cómo configurar, probar, habilitar y conectar.
```

### Comportamiento obligatorio

- **`EVOLUS_ENABLED=false` por defecto** → el módulo responde con mock y
  **JAMÁS rompe la demo**. La demo no puede depender de Evolus.
- Si Evolus falla o devuelve basura → **cae a mock y queda anotado**
  (transparencia, no truco). Mirá el patrón en `backend/llm/client.py`.
- `EVOLUS_ENABLED=true` sin clave → `EvolusError` con mensaje claro.

### Endpoints propios (en `router.py`)

```
GET  /api/evolus/salud      { enabled, mock, base_url, tiene_clave }
POST /api/evolus/facturas   { n } comprobantes simulados con errores inyectados
POST /api/evolus/extraer    { esperado, obtenido, precision, errores_detectados }
POST /api/evolus/contratos  ejecuta workflow de contrato
GET  /api/evolus/metricas   agregados de extracción
```

### Tests (sin red)

- Generación de facturas con errores (verificá tipos y probabilidades).
- Comparación de precisión esperado vs. obtenido.
- El router responde 200 en modo mock.
- `EVOLUS_ENABLED=false` **no toca la red**.

### Opcional (sólo si sobra tiempo)

`frontend/src/components/EvolusPanel.jsx` como componente **NUEVO**.
**NO** importarlo en `App.jsx` ni en ningún lado: el dueño lo conecta.

---

## REGLAS DE NO CHOQUE (crítico — otro asistente trabaja a la vez)

**NO edites NINGÚN archivo existente.** Sólo creá los archivos nuevos de arriba.

**Prohibido tocar:**

```
backend/api.py
backend/engine/**
backend/llm/**
backend/store.py
backend/tests/test_engine.py
backend/tests/test_llm.py
backend/tests/test_api.py
.env
.env.example
frontend/src/App.jsx
frontend/src/components/MapaCaba.jsx
frontend/src/components/MenuLateral.jsx
frontend/src/components/PanelModal.jsx
frontend/src/components/Pelicula.jsx
frontend/src/components/TiraFin.jsx
frontend/src/styles.css
frontend/smoke.mjs
render.yaml
netlify.toml
docker-compose.yml
README.md
PITCH.md
SLIDES.md
AGENTS.md
```

**NO hagas `git commit` ni `git push`.** Dejá los archivos y el `EVOLUS.md`;
el dueño commitea cuando todo esté verde.

---

## Criterio de aceptación

- [ ] Los tests pasan **sin red**.
- [ ] `EVOLUS_ENABLED=false` por defecto; **cero** dependencia de Evolus para la demo.
- [ ] **Cero** ediciones a archivos existentes.
- [ ] `EVOLUS.md` (o este mismo archivo) explica: configurar / probar / habilitar / conectar.

---

# ✅ CÓMO USAR ESTE MÓDULO (ya construido)

> Todo el módulo vive en `backend/evolus/` y **no toca nada de lo que ya existía**.
> Arranca **apagado** y en **modo prueba**: responde con datos locales, sin internet
> y sin gastar créditos. La demo principal NO depende de Evolus.

## Archivos

```
backend/evolus/config.py     configuración y decisión de "modo prueba"
backend/evolus/mock.py       lector local + respuestas sin internet + sello
backend/evolus/facturas.py   facturas simuladas con errores inyectados (Monte Carlo)
backend/evolus/client.py     "teléfono" a Evolus real (reintentos, timeout, caída segura)
backend/evolus/extract.py    precisión (esperado vs. obtenido) + detección de defectos
backend/evolus/workflow.py   dispara el trámite de contrato + sigue su estado
backend/evolus/router.py     las puertas HTTP (NO se conecta solo)
backend/tests/test_evolus.py 48 pruebas que corren sin red
```

## 1) Probar (sin internet)

```powershell
cd C:\Users\josem\projects\nexus-ops-ai\backend
.venv\Scripts\python.exe -m pytest tests\test_evolus.py -q
```

## 2) Configurar (en `.env`)

Las cuatro básicas **ya están** en `.env.example`:

```env
EVOLUS_ENABLED=false                                  # apagado por defecto
EVOLUS_API_BASE=https://api.evolus.ai/api/v1
EVOLUS_API_KEY=                                       # la genera el dueño en la UI
EVOLUS_APPLICATION_ID=                                # el "space ID"
```

Opcionales (hacen falta **solo** para el extractor propio y el workflow; agregalas al `.env` si los usás):

```env
EVOLUS_AGENT_ID=             # si definís este + EXTRACTOR_ID, se usa el extractor propio
EVOLUS_EXTRACTOR_ID=         #   en vez de la herramienta lista `doc-structure`
EVOLUS_WORKFLOW_ID=          # id del workflow de contratos (creado y ENCENDIDO en la UI)
```

Regla: **si falta la clave o `EVOLUS_ENABLED=false` → modo prueba** (nunca toca la red).
Prender Evolus sin clave (o sin `EVOLUS_WORKFLOW_ID` para contratos) da un **error claro**.

## 3) Habilitar Evolus de verdad

1. Crear el workspace **desde el link oficial del evento** (no entrar derecho a `app.evolus.ai`).
2. Generar la clave y el space ID en la página **API keys** → pegarlas en `.env`.
3. Si vas a usar contratos: crear y **ENCENDER** el workflow en la UI → `EVOLUS_WORKFLOW_ID`.
4. Poner `EVOLUS_ENABLED=true` y reiniciar el backend.

Si algo falla (red caída, respuesta ilegible) → **cae solo al modo prueba y queda anotado**
(en `/api/evolus/metricas`, campo `cliente.caidas_a_prueba`). Transparencia, no truco.

## 4) Conexión a la pantalla (✅ ya conectado)

`router.py` **ya está enchufado** en `backend/api.py` (con `try/except`, así el
simulador nunca se cae si el módulo falta):

```python
from evolus.router import router as evolus_router
app.include_router(evolus_router)
```

Por eso `GET /api/evolus/salud` ya responde. **Además**, Evolus es el **redactor**
de los informes mensuales de los 4 sectores: cuando el mes cierra, el programa
calcula los números → la IA de AMD analiza → **Evolus redacta el documento**. Si
Evolus está apagado o falla, redacta el **respaldo local** (`engine/redactor.py`)
y queda anotado en el informe (`redactor: "evolus"` o `"local"`).

La AI Tool que se usa para redactar se elige con `EVOLUS_REDACTOR_TOOL`
(por defecto `summarize`; también sirven `email`, `minutes`, `rewrite`, `simplify`).

## 5) Las puertas (endpoints)

```
GET  /api/evolus/salud      ¿prendido? ¿modo prueba? (motivo en criollo)
POST /api/evolus/facturas   { n, seed }  → comprobantes simulados con errores
POST /api/evolus/extraer    { esperado, obtenido } → precisión + defectos detectados
POST /api/evolus/contratos  { texto?, seed } → dispara el trámite y sigue el estado
GET  /api/evolus/metricas   ?n&seed → precisión promedio, defectos por tipo, caídas a prueba
```

Todas las respuestas llevan el sello **"SIMULADO – SIN VALIDEZ FISCAL"** donde corresponde.
Evolus **NO es ERP ni factura**: todo es simulado para la demo.

