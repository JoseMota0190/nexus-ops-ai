# Plan del proyecto — Nexus Alarm

> Objetivo, alcance y fases. El estado operativo vive en `TASKS.md`; las decisiones estructurales en `DECISIONS.md`.

## 1. Ficha

- **Nombre:** `nexus-ops-ai` — **Nexus Alarm**.
- **Problema que resuelve:** una empresa de alarmas y monitoreo opera con datos dispersos (sectores, técnicos, agenda, facturación, leads, llamadas). Nexus Alarm es un gemelo digital que simula esa operación y permite evaluar decisiones y reportes generados con LLM sobre un escenario reproducible.
- **Usuarios objetivo:** dueños y responsables de operaciones de empresas de seguridad/monitoreo; jurados de hackathon que necesitan ver un producto completo y no un prototipo.
- **MVP actual (ya implementado):** backend FastAPI con motor de simulación, persistencia SQLite, API bilingüe ES/EN, cliente LLM único (mock por defecto, cualquier proveedor OpenAI-compatible) y frontend React/Vite.
- **Fuera de alcance:** integración con sistemas reales de alarmas, autenticación avanzada, multitenencia, pagos.
- **Restricciones:** código existente que se readapta (no se reescribe); plazo del hackathon; credenciales fuera del repositorio.

## 2. Objetivo externo: hackathon Nebius x NVIDIA

- **Evento:** Nebius x NVIDIA Global AI Hackathon (Devpost 30790).
- **Cierre:** 30/10/2026 10:00 PDT (≈ 14:00 ART). **Quedan ~3 días** desde el 27/10/2026.
- **Requisito duro:** correr sobre **Nebius Token Factory** o **Nebius AI Cloud** y usar al menos un **modelo open source de NVIDIA** (Nemotron).
- **Track elegido:** *Best Apps and Agents* (decidido 2026-10-27, ver `DECISIONS.md` D-005).
  - Encaje: el track pide «a workflow that runs itself»; el producto es exactamente eso.
  - Descartados: *Coding and Agentic Engineering* (pide agentes que escriben/corren/testean código; no es el producto), *Personal AI* (pide stack NemoClaw/OpenShell/Hermes; no lo usamos), *Physical AI* (exige 1 minuto de hardware robótico real).
  - **Estructura de premios (dato duro):** ganar un track da un Jetson Orin Nano, **no dinero**. El efectivo ($20k / $10k / $6k) es Grand Prize / 2º / 3º y compite entre todos los tracks. Conclusión: importa estar entre los tres mejores del overall, no solo ganar la categoría.
  - **Premio adicional apilable:** *Best Use of Tavily* ($3.000), independiente del track.
- **Entregables:** demo online funcionando, video ≤3 min, repo público con licencia visible, descripción, feedback de herramientas y explicación de qué se actualizó respecto del proyecto previo.

## 3. Estado actual (verificado 2026-10-27)

- Backend probado: `pytest -q` → **77 passed** (20,57 s).
- Frontend: `node_modules` presente; el smoke no se ejecutó en esta sesión.
- Proveedor LLM actual en `.env.example`: AMD Radeon Cloud (hackathon anterior). **No cumple** el requisito de Nebius. Migración en curso (T-003).
- Endpoint verificado de Nebius Token Factory: `https://api.tokenfactory.nebius.com/v1/` (OpenAI-compatible; `/v1/models` exige autenticación).
- IDs Nemotron confirmados en la documentación oficial:
  - Razonamiento: `nvidia/Nemotron-3.5-Super-VL` (vigente).
  - Alto volumen: `nvidia/Nemotron-3_5-Lightning` (vigente).
  - **Deprecan el 09/11/2026** (posteriores al cierre, no afectan el judging): `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` y `nvidia/nemotron-3-super-120b-a12b`.
  - **Ya removido** el 31/08/2026: `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1`. No usar.
- Créditos disponibles: código `NEBIUS-DEVPOST-GLOBAL26` ($25) + Builders Program ($25 adicionales).
- Configuración multiagente creada en `.opencode/agents/` y detectada por OpenCode v2.0.22 (`opencode debug agents`): `foreman`, `implementer`, `reviewer`, `config-helper`.
- `MODEL_SELECTION.md` está `CONFIGURADA`, pero el ID del Config Helper (`google/gemini-2.5-flash-image-preview:free`) **no existe** en el catálogo actual; debe reemplazarse.
- `README.md` corresponde a la plantilla multiagente, no al producto.
- Archivos de config multiagente, `PLAN.md`, `TASKS.md`, `DECISIONS.md` y `entrega/` **no están commiteados**.

## 4. Fases hacia la entrega

> Restricción real: cierre 30/10/2026 14:00 ART. Quedan ~2,5 días.
> Sin la API key de Nebius, la Fase 0 bloquea toda evidencia real. Las Fases 1 y 4 no dependen de la key.

### Fase 0 — Credenciales Nebius (bloqueante, la hace el usuario)

- [ ] Crear cuenta en https://tokenfactory.nebius.com/ (Google o GitHub).
- [ ] Canjear `NEBIUS-DEVPOST-GLOBAL26` → $25 de créditos.
- [ ] Entrar al Builders Program (https://dev.nebius.com/builders) → $25 más.
- [ ] Generar API key y ponerla en `.env` local (nunca se commitea).
- [ ] Listar modelos reales: `curl https://api.tokenfactory.nebius.com/v1/models -H "Authorization: Bearer $NEBIUS_API_KEY"` y confirmar los IDs Nemotron.
- **Criterio:** una llamada real a Nemotron devuelve contenido válido, con latencia y tokens registrados.

### Fase 1 — Cerebro Nebius + router de modelos (T-003)

- [ ] `LLM_BASE_URL` → Token Factory; defaults Nemotron en `.env.example`.
- [ ] Configuración por capas: `LLM_MODEL_REASONING` (gerente, informes de sector), `LLM_MODEL_FAST` (teleoperador, operador, agenda, técnicos, despacho) y overrides `LLM_MODEL_<AGENTE>`.
- [ ] Tests del router; suite completa en verde.
- **Criterio:** cada agente sale con el modelo que le corresponde; `USE_MOCK=true` sigue funcionando sin red.

### Fase 2 — Observabilidad visible (diferenciador)

- [ ] `FranjaAMD` → `FranjaNebius`: modelo por agente, tokens, latencia, costo estimado y tasa de fallback (los datos ya existen en `backend/llm/metrics.py`).
- [ ] Endpoint que exponga el mapa agente → modelo y las métricas agregadas.
- **Criterio:** pantalla en vivo que un jurado puede ver en el video y que responde al criterio *Technological Implementation*.

### Fase 3 — Documentación y coherencia de marca

- [ ] README real del producto (setup, arquitectura, variables, tests, sección «How we use Nebius Token Factory + Nemotron», tabla de modelos y del router).
- [ ] Barrido de toda mención AMD/Radeon/Gemma en README, `AGENTS.md`, `PITCH.md`, `SLIDES.md`, `render.yaml`, `docker-compose.yml`, `entrega/` y comentarios de código.
- [ ] Sección obligatoria «What changed during the submission period».
- **Criterio:** `grep -ri "amd\|radeon\|gemma"` no devuelve nada en material de entrega; un tercero levanta el proyecto solo con el README.

### Fase 4 — Demo pública

- [ ] `render.yaml` con env de Nebius; `LLM_API_KEY` cargada solo en el panel del hosting.
- [ ] Frontend en Netlify apuntando al backend público.
- **Criterio:** URL accesible con el recorrido completo. **Requiere autorización explícita del usuario para desplegar.**

### Fase 5 — Video y envío

- [ ] Guion ≤3 min reescrito para Nebius/Nemotron/router.
- [ ] Grabar, subir a YouTube público, completar Devpost.
- **Criterio:** submission enviada antes del 30/10/2026 10:00 PDT.

### Fase 6 — Opcional: Tavily (premio aparte de $3.000)

- [ ] Agente investigador de mercado que enriquezca el informe del gerente con contexto real vía Tavily.
- **Criterio:** llamada real a Tavily en el flujo del gerente. Solo si las Fases 0–5 están cerradas.

### Fuera de alcance por riesgo/plazo

- Fine-tuning de Nemotron y Serverless Jobs: 2–3 días de riesgo cada uno, sin cambiar el veredicto del jurado.


## 5. Criterios globales de aceptación

- [ ] Un jurado puede levantar el proyecto siguiendo el README sin ayuda.
- [ ] La demo usa efectivamente Nebius + un modelo NVIDIA.
- [ ] No hay secretos en el repositorio.
- [ ] `TASKS.md` refleja el estado real y cada tarea cerrada tiene evidencia.
- [ ] El video y la descripción explican qué se actualizó en el período del hackathon.

## 6. Riesgos

- **Tiempo:** ~2,5 días para integración, router, demo, video y formulario.
- **Credenciales Nebius:** el usuario todavía no tiene cuenta. Hasta que exista la API key, no hay evidencia real y la Fase 0 bloquea la verificación end-to-end.
- **Presupuesto:** $50 de créditos ($25 promo + $25 Builders). El motor hace varias llamadas por simulación; el router reduce costo al mandar alto volumen al modelo rápido, pero hay que medir antes de grabar el video.
- **Costo por demo:** si la demo corre con `USE_MOCK=false` y un recorrido largo, los créditos pueden agotarse. Mitigación: caché ya existente en `backend/llm/cache.py` y límites en `.env`.
- **Config Helper inválido:** un agente con un ID inexistente falla al invocarse (no bloquea el producto).

## 7. Decisiones pendientes

- ID definitivo del modelo de razonamiento vs. rápido, a confirmar con `GET /v1/models` de la cuenta real (los defaults ya están fijados en la Fase 1).
- Si se publica el repositorio y cuándo (el usuario autorizó **solo commit local**; push queda pendiente de su decisión).
- Sustituir el modelo inválido del Config Helper en `MODEL_SELECTION.md` (no bloquea el producto).

## 8. Actualización del plan

Solo cambiar alcance, fases o decisiones estructurales con evidencia y explicación. Registrar decisiones importantes en `DECISIONS.md`.
