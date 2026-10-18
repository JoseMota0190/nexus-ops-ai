# ENTREGA — nexus-ops-ai · plan de las últimas 4 horas

> **Buena noticia: casi todo está listo.** El repo es público, la app **ya está online** y el
> modelo corre en **AMD de verdad** (`Gemma-4-31B-IT`). Lo que queda es **video, slides y
> llenar el formulario**. Abajo, hora por hora.

Estado verificado (dom 18, sesión actual):

| Ítem | Estado |
|---|---|
| Repo **público** GitHub | ✅ `github.com/JoseMota0190/nexus-ops-ai` |
| **Application URL** (demo online) | ✅ `https://nexus-ops-ai.netlify.app` |
| Backend online (Render) | ✅ `https://nexus-ops-ai-backend.onrender.com` |
| **AMD de verdad** en la nube | ✅ `modelo=Gemma-4-31B-IT · modo_mock=false · fallbacks=0` |
| 6 meses sembrados en la nube | ✅ |
| 4 sectores visibles en el sitio | ✅ |
| Tests + smoke | ✅ 104 tests · 45 checks |
| `README.md` que corre | ✅ |
| Docker (Dockerfile + compose) | ✅ archivos listos (falta re-verificar con Docker Desktop) |
| Guion del video (inglés + subtítulos) | ✅ `PITCH.md` |
| Slides | ✅ `entrega/slides.html` (exportar a PDF) |
| Cover image | ✅ `entrega/cover.png` (1200×630) |
| Textos del formulario | ✅ abajo |

---

## Cronograma de las 4 horas

### ⏱️ BLOQUE 0 · 0:00–0:10 — Congelar
- **VOS:** nada. Todo lo crítico ya está publicado.
- **YO:** dejo de tocar código (salvo bug grave). Verifico que el sitio siga vivo.

### ⏱️ BLOQUE 1 · 0:10–0:35 — Redeploy con lo último (recomendado, no crítico)
El sitio online anda, pero puede faltarle el último arreglo (el mes cerrando solo en modo día a
día). No hace falta para un video de 3 minutos, pero es barato asegurarlo:
- **Netlify:** `❯ Deploys` → `Trigger deploy` → **`Clear cache and deploy site`**.
- **Render:** `nexus-ops-ai-backend` → `Manual Deploy` → **`Deploy latest commit`**.
- **YO:** verifico que los dos sigan respondiendo 200 después.

### ⏱️ BLOQUE 2 · 0:35–1:15 — Docker de respaldo (requisito de la entrega)
- **VOS:** abrí **Docker Desktop** y esperá a que diga *"Engine running"* (10 min suele tardar).
- **YO:** corro `docker compose up --build` y confirmo que levanta, siembra los 6 meses y el
  proxy de nginx anda. (El 14 oct ya anduvo; solo hay que re-confirmarlo.)

### ⏱️ BLOQUE 3 · 1:15–2:30 — 🎥 Grabar el video (lo más largo)
- **VOS:** grabá con **Win+G** (Game Bar) o **OBS**, siguiendo `PITCH.md` (escena por escena, con
  los textos en inglés y subtítulos ya escritos). Usá la web online; si querés que se vea el
  *"pensando"* del modelo, entrá al **Mes 7+** y apretá **▶ Correr un día** (ahí la Sala de
  Agentes negocia en vivo con AMD).
- **VOS:** duración objetivo **~2:50**. Si salís del tiempo, recortá la Escena 3.
- **YO:** nada (el guion ya está). Si algo del sitio se ve raro, avisame y lo arreglo.

### ⏱️ BLOQUE 4 · 2:30–3:00 — Slides (exportar el PDF)
- **VOS:** doble clic en `entrega\slides.html` → **Ctrl+P** → destino **"Guardar como PDF"** →
  **Horizontal**, márgenes **Ninguno**, **gráficos de fondo ON** → guardar como
  `nexus-ops-ai-slides.pdf`.
- **VOS:** el cover ya está: `entrega\cover.png`.
- **YO:** nada.

### ⏱️ BLOQUE 5 · 3:00–3:45 — 📮 Llenar el formulario en lablab.ai
- **VOS:** pegá los textos de la sección **"Datos de la inscripción"** (abajo).
- Subir: video, slides PDF, cover, repo público, **Application URL**.

### ⏱️ BLOQUE 6 · 3:45–4:00 — Buffer y entregar
- Revisá que los 4 obligatorios estén cargados: **repo + URL + video + slides**.
- **Apurá el botón de enviar/entregar antes del cierre.**

---

## 👍 Lo que NUNCA se recorta (por si falta tiempo)
1. **AMD visible** → ya está (Gemma en la franja AMD abajo).
2. **Application URL** → ya está.
3. **Repo público + README** → ya está.
El video y los slides son obligatorios para el formulario, pero con lo de arriba ya cumplís las
condiciones duras.

---

# Datos de la inscripción (copiar/pegar en lablab.ai)

**Project title:** `nexus-ops-ai — the digital twin of Nexus Alarm`

**Short description:**
> A swarm of AI agents runs the full sales operation of a small alarm-installing
> company in Buenos Aires — calls, scheduling, dispatch and monthly management —
> on an open model served on AMD, with Monte Carlo forecasting.

**Long description:**
> nexus-ops-ai is a digital twin of "Nexus Alarm", a fictional security-alarm
> installer in Buenos Aires. It simulates nine months of operations: 150 inbound
> calls a day, weekly scheduling Monday–Saturday, technician dispatch
> computed by a zone/travel-cost algorithm, and a monthly AI manager that decides
> how to grow from 2 to 10 technicians without running out of cash.
>
> The LLM (open model on AMD infrastructure) speaks and explains; the program
> computes and validates. Forecasting uses Monte Carlo simulation, never the LLM
> alone. Rejection reasons from every call are logged and fed back to the
> manager's monthly review. The business reports to four sectors — management,
> sales, scheduling and billing — and every month the numbers are computed, the
> model analyzes them, and Evolus writes the report (with a local writer as
> fallback). That is how customer data becomes a recommendation and a
> recommendation becomes an action.
>
> Deliverables: public GitHub repo, containerized app (Docker), live web demo,
> README that runs, presentation video and slides.

**Tags:** `ai-agents`, `llm`, `amd`, `digital-twin`, `commerce`, `monte-carlo`, `agents`,
`fastapi`, `react`

**Categoría / track:** Reinvent Commerce

**Repo:** https://github.com/JoseMota0190/nexus-ops-ai
**Application URL:** https://nexus-ops-ai.netlify.app

---

# Preguntas del jurado (respuestas cortas)

- **¿Por qué no solo un dashboard?** Porque la IA **actúa**: contrata, mejora el guion y agenda.
  El tablero es cómo lo mirás, no lo que hace.
- **¿Y si el LLM falla?** Baja a un respaldo local, queda anotado en la franja y la simulación
  sigue. El negocio no se frena porque un modelo se cayó.
- **¿Los números son reales?** Son **simulados y reproducibles** (semilla fija). El valor es el
  *bucle de decisión*, no la cifra exacta. Empresas y comprobantes son ficticios
  ("SIMULADO – SIN VALIDEZ FISCAL").
- **¿Dónde está AMD?** Todo el razonamiento de los agentes pasa por un modelo abierto servido
  sobre AMD, con latencia y tokens en vivo en la franja de abajo. Se ve en la demo.
