# Registro de decisiones

Registrar solo decisiones importantes que afecten arquitectura, stack, alcance, persistencia, seguridad o experiencia del usuario.

## D-001 — Equipo multiagente de OpenCode

- **Estado:** Aceptada (2026-10-27).
- **Decisión:** Foreman coordina y delega; Implementer ejecuta; Reviewer revisa en solo lectura; Config Helper resuelve configuración y capturas.
- **Motivo:** separar planificación, cambios y control de calidad, con un canal auxiliar para problemas de entorno.
- **Consecuencias:** no hay dos implementaciones concurrentes sobre los mismos archivos; el Reviewer nunca edita; los modelos se eligen por rol y se guardan en `MODEL_SELECTION.md`.

## D-002 — Ubicación y formato de los agentes

- **Estado:** Aceptada (2026-10-27).
- **Decisión:** definir los agentes como Markdown con frontmatter YAML en `.opencode/agents/`, en lugar de bloques `agent` dentro de `opencode.json`.
- **Motivo:** es la ubicación que OpenCode v2.0.22 detecta como agentes de proyecto; permite mandatos largos y versionado por archivo.
- **Verificación:** `opencode debug agents` lista `foreman`, `implementer`, `reviewer` y `config-helper`, con sus modelos y permisos resueltos.
- **Consecuencias:** `opencode.json` queda solo con `default_agent` y permisos globales; las claves heredadas `bash` y `task` se mapean a `shell` y `subagent` en V2.

## D-003 — Readaptar el proyecto para Nebius x NVIDIA en lugar de reescribirlo

- **Estado:** Aceptada (2026-10-27).
- **Decisión:** conservar el código existente (FastAPI + React + SQLite) y cambiar el proveedor LLM por configuración hacia Nebius Token Factory con un modelo Nemotron.
- **Motivo:** el cliente `backend/llm/client.py` ya habla el protocolo OpenAI (`/chat/completions`), el hackathon exige Nebius + modelo NVIDIA y el plazo es de ~3 días.
- **Consecuencias:** el cambio de proveedor se hace con `LLM_BASE_URL`, `LLM_MODEL` y `LLM_API_KEY`; no se toca el motor de simulación. El modo mock sigue siendo el respaldo para desarrollo y tests.

## D-004 — Reemplazar el modelo del Config Helper

- **Estado:** Pendiente de elección del usuario (2026-10-27).
- **Problema:** el ID configurado `google/gemini-2.5-flash-image-preview:free` no existe en el catálogo actual de OpenRouter; el único de esa familia es `google/gemini-2.5-flash-image`, que es pago y sin tool calling.
- **Decisión propuesta:** asignar un endpoint `:free` con entrada de imágenes y tool calling confirmados; hay 8 candidatos verificados (ver Fase 4).
- **Consecuencias:** hasta elegir, invocar a `config-helper` puede fallar por modelo inexistente.

## D-005 — Track: Best Apps and Agents

- **Estado:** Aceptada (2026-10-27).
- **Decisión:** presentar en *Best Apps and Agents*.
- **Motivo:** el track pide «a workflow that runs itself» y el producto es exactamente eso. Los otros tres no encajan: *Coding and Agentic Engineering* pide agentes que escriben/corren/testean código; *Personal AI* exige el stack NemoClaw/OpenShell/Hermes; *Physical AI* exige un minuto de hardware real operando.
- **Dato que condiciona la estrategia:** el premio por track es un Jetson Orin Nano (hardware), no efectivo. El dinero ($20k/$10k/$6k) es Grand Prize / 2º / 3º y compite entre todos los tracks.
- **Consecuencias:** la prioridad es coherencia y calidad del producto para entrar en el podio general, no ganar una categoría débil. El premio *Best Use of Tavily* ($3.000) es independiente y se apila.

## D-006 — Router de modelos Nemotron por agente

- **Estado:** Aceptada (2026-10-27).
- **Decisión:** en lugar de un único `LLM_MODEL`, resolver el modelo por agente: `LLM_MODEL_REASONING` para `gerente` y `sector_*`; `LLM_MODEL_FAST` para el resto; override opcional `LLM_MODEL_<AGENTE>`; `LLM_MODEL` como fallback.
- **Modelos:** `nvidia/Nemotron-3.5-Super-VL` (razonamiento) y `nvidia/Nemotron-3_5-Lightning` (alto volumen), confirmados en la documentación oficial de Token Factory.
- **Motivo:** el track recomienda explícitamente usar un modelo grande para razonamiento y uno liviano para las llamadas del día a día. Además baja costo y latencia del envío masivo del enjambre.
- **Consecuencias:** la caché y las métricas quedan keyed por el modelo realmente usado; el panel de observabilidad puede mostrar el ahorro. Se descartan IDs deprecados (`Nano-30B-A3B`, `nemotron-3-super-120b-a12b` salen el 09/11/2026) y el ya removido `Llama-3_1-Nemotron-Ultra-253B-v1`.

## D-007 — Estrategia de repositorio: commit local, sin push

- **Estado:** Aceptada (2026-10-27).
- **Decisión:** dejar el trabajo en un commit local limpio; el push y la publicación quedan a decisión del usuario.
- **Motivo:** el requisito del hackathon es un repo público, pero publicar expone historial y configuración; el usuario quiere revisarlo antes.
- **Consecuencias:** T-015 queda bloqueada hasta autorización explícita; la submission de Devpost no puede enviarse sin URL pública.
