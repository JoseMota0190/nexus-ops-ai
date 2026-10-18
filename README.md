# nexus-ops-ai — Nexus Alarm Digital Twin

A digital twin of a fictional home-alarm installation company in Buenos Aires (CABA).
A swarm of AI agents runs the whole sales process — lead → telemarketer → scheduling →
technician dispatch → invoice — while the owner watches live KPIs, tries "what-if"
scenarios and runs the 9 months of the plan.

**The system's brain: an open model served on AMD infrastructure** (AMD Radeon
Cloud / a GPU instance running Gemma + vLLM). The agents' inference runs on AMD.

> **Hackathon project (AMD Developer Hackathon: ACT III / lablab.ai · Reinvent Commerce track).**
> Every number, company, call and invoice is **SIMULATED**. Nothing here is advice, real
> billing or a tax claim. Invoices carry "SIMULATED – NO FISCAL VALIDITY". The comparison
> baseline is an **estimate**.

---

## The story it tells

Nexus Alarm starts with **3 telemarketers and 2 technicians**: 150 calls/day (50 per
operator), ~6 sales a day, booked for the **following week**, Monday to Saturday.

An **AI Manager** meets every month, looks at the numbers, moves its three levers
(hire operators · hire technicians · improve database conversion) and decides how much
to grow. The **program validates** every decision against the business rules (cash,
hiring cap, capacity) and, if the plan falls short, a **safety net** flags it and fixes
it **transparently** — it is written into the minutes.

Result of the 9-month simulation:

| | month 1 | month 9 | |
|---|---:|---:|---:|
| Sales/day | 6.8 | 30.5 | **×4.5** |
| Telemarketers | 3 | 8 | ×2.7 |
| Technicians | 2 | **10** | goal reached |
| Revenue/month | 38.6 k | 313 k | ×8.1 |
| Costs/month | 9.1 k | 24.4 k | ×2.7 |

**Costs grow slower than sales** (×2.7 vs ×5.9 in revenue per install): the
question of the pitch is *"how do I sell 5× more without putting 5× more operators?"* —
the answer is that the Manager improves conversion as well as hiring.

---

## The 4 sectors (the ☰ menu)

The menu is no longer a list of loose dashboards: it is **4 sectors**, and each one
**reports on itself**. When each month closes, the sector **computes its numbers** with
the program, the **AMD AI analyzes them**, and a **local writer** drafts the document
(no internet, no credits, so the demo never runs out of a report). The report is saved
and can be regenerated with one click.

| Sector | What it watches | Color |
|---|---|---|
| 🧾 **Management** | cash, revenue, costs, technicians, the month's decision | blue |
| 📞 **Sales** | calls, answer rate, conversion, reasons for failure | green |
| 📅 **Scheduling & technicians** | bookings, installs, slots, occupancy | violet |
| 🧮 **Billing** | simulated invoices, reader precision, defects | cyan |

The **6 preloaded months** are seeded instantly with the local writer (no credits, no
network); the months you run live use the AMD AI.

**Transparency:** each report shows where it came from (`🧠 Analyzed by the AI (AMD)` /
`📝 Local writer` · `✍️ Written locally`) and its traffic light 🟢🟡🔴.

---

## Bilingual (ES / EN)

**English is the base language.** The **EN / ES** button in the top strip flips the
**whole site** — interface, month labels, sector reports, agent dialogues and the
invoice seal — from English to Spanish and back.

Under the hood the backend keeps **one database per language** (`data/nexus.db` for
English, `data/nexus_es.db` for Spanish), each seeded with the same 6 months. Pressing
the button calls `POST /api/idioma`, which switches the engine's language and swaps the
database in one step; switching never interrupts a live day (it answers `409` while a
day is running). Every string lives in **one place per side**: `backend/idioma.py`
(`t("English", "español")`) and `frontend/src/i18n.js` (`t("English", "español")`).

---

## How to run it

### Option A — Docker (a single command) ✅ recommended

```bash
docker compose up --build
```

- **Owner's screen:** http://localhost:8080
- **Backend API:** http://localhost:8000/api/estado

It starts in **mock mode** by default (no AMD credits spent). To use the real AMD brain:
copy `.env.example` to `.env`, set `USE_MOCK=false` and fill in `LLM_API_KEY` and
`LLM_MODEL` (the Radeon Cloud endpoint is already set), then run
`docker compose up --build` again.

The SQLite database lives in the Docker volume `nexus_data` → **it survives restarts**.
To wipe everything and start over: `docker compose down -v`.

If ports 8000 or 8080 are taken on your machine:
`BACKEND_PORT=8010 FRONTEND_PORT=8081 docker compose up --build`.

### Option B — No Docker (development, Windows)

```powershell
# Backend (uses the venv already created, without activating it)
cd backend
.venv\Scripts\pip install -r requirements.txt   # first time
.venv\Scripts\python.exe -m uvicorn api:app --reload

# Frontend (in another window)
cd frontend
npm install
npm run dev
```

Or in one go: double-click **`scripts\dev.cmd`** (opens backend + frontend in two windows).

With `USE_MOCK=true` the whole flow works without calling any real model.

### Tests

```powershell
cd backend
# 77 tests in total (engine, LLM, API, agent swarm, invoice auditor) — they run without network
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe tests\mirar_negocio.py # the 9-month dashboard

cd ..\frontend
npm run build     # compiles
npm run smoke     # 46 checks: render + screen + ES/EN switch, against the real backend
```

---

## Publishing (Render + Netlify)

- **Backend → Render:** the `render.yaml` file is a Blueprint. In
  [app.onrender.com](https://app.onrender.com) → *New* → *Blueprint* → pick the repo.
  Render builds the service on its own (Python, `uvicorn api:app`, health check on `/api/estado`).
- **Frontend → Netlify:** in [app.netlify.com](https://app.netlify.com) → *Add new site* →
  import the repo with *base directory* `frontend`. Netlify reads `frontend/netlify.toml`
  (build `npm run build`, publishes `dist`, redirects `/api/*` to the Render backend).
  **Edit the backend URL inside `netlify.toml`** (marked with ⬇).
- Secrets (`LLM_API_KEY`, `LLM_MODEL`) are set in the Render panel. They are **never**
  committed.

## Environment variables

See `.env.example`. Secrets are **never** committed.

---

## Architecture

```
Event engine (deterministic, NO LLM)
  clock x120 · leads 180/day (they grow with database improvements)
  150 calls/day · weekly scheduling (Mon–Sat, slots 9/12/16) · Monte Carlo
  technician dispatch by algorithm (travel cost per neighborhood)
  Manager validator + transparent safety net
  everything persisted in SQLite (one database per language)
        │
        ├── Telemarketer   (LLM AMD)  qualifies, books and logs the reason for failure
        ├── Scheduling coordinator    negotiates a slot by message and confirms to the client
        ├── AI Manager                monthly meeting: metrics → decision → minutes
        └── 4 SECTORS (month close)
              program computes → AMD AI analyzes → local writer drafts
              reports saved in SQLite (reportes_sector)
        │
  Owner's screen: CABA map + logo · simulation footer + agent room +
  AMD strip always visible · ☰ menu with the 4 sectors
```

**Actor rule:** the program computes the ~40,000 calls of the 9 months; the AI
"acts" only in the ~20-30 calls and chats shown live. That way the demo is fast, cheap
and deterministic — and the agents still really talk.

### Agents and who decides

| Character | Talks (AI) | Decides (program) |
|---|---|---|
| Telemarketer | ✅ qualifies and logs the reason | closing probability |
| Scheduling coordinator | ✅ negotiates the slot | free slots and proximity |
| Technician coordinator | explains | ✅ dispatch by algorithm |
| Manager | ✅ analyzes and advises | ✅ validates cash, cap and capacity |

### Simulated local rules

- Every invoice carries **"SIMULATED – NO FISCAL VALIDITY"** (simulated ARCA seal).
- The invoice **auditor** is rule-based (Monte Carlo + rule detection): the LLM is never the
  only method of calculation.
- **All** calls come from website leads asking to be called: there is no cold calling.

---

## Repository structure

```
backend/
  api.py            FastAPI: status, summaries, scenarios, map, AMD metrics, sectors, language
  idioma.py         the site's language (English by default, Spanish on demand)
  store.py          SQLite (clients, leads, calls, appointments, decisions, minutes, reports)
  engine/           business · leads · calls · agenda · technicians · gerente · simulation
                    sectores (reports of the 4 sectors) · redactor (local writer) · facturas (auditor)
  llm/              client (OpenAI-compatible) · mock · cache · metrics
  schemas/          structured responses of each agent (Pydantic)
  tests/            77 tests + business inspector
frontend/           React + Vite: CABA map + simulation footer + 4 sectors + ES/EN switch
scripts/dev.cmd     starts backend + frontend in two windows
docker-compose.yml  backend + frontend in a single command
render.yaml         Render Blueprint
```

## Project rules

- **Structured outputs:** every agent returns JSON validated with Pydantic
  (max. 2 retries + mock-mode fallback).
- **A single LLM client** compatible with OpenAI (`base_url` configurable) → Radeon Cloud / Gemma on AMD GPU.
- **Local writer** drafts the sector reports (no external service needed).
- **Bilingual by design:** every user-facing string is a pair `t("English", "español")`
  (`backend/idioma.py` + `frontend/src/i18n.js`); the ES/EN button flips interface,
  reports, agent dialogues and invoices, with one database per language.
- **Mock mode and cache/replay** to reproduce the demo without network.
- **Per-call metrics** (latency p50/p95, tokens, tokens/s) shown in the AMD strip.
- **Monte Carlo** and statistics for forecasting — the LLM is never the only calculation method.

## License

MIT. See `LICENSE`.
