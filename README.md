# Nexus Alarm — a digital twin for a security-alarm company

> **Nebius x NVIDIA Global AI Hackathon 2026 — Best Apps and Agents track**
>
> A working simulation of an alarm-and-monitoring company, run by a team of LLM
> agents on **Nebius Token Factory** with **NVIDIA Nemotron** models.

**[Live demo](#) · [3-minute video](#) · [License: MIT](LICENSE)**

---

## The problem

A security-alarm company in Buenos Aires sells a simple thing: someone answers
the phone, a technician installs a sensor, a monthly invoice goes out. The
business is brutally operational — conversion, technician capacity, routing,
cash — and owners make those decisions on gut feeling, after the month is gone.

Hiring three more technicians costs real money. Improving conversion costs
something else. Nobody can A/B test a company.

## The answer

**Nexus Alarm is that company as a digital twin.** It simulates the day-to-day
operation — incoming calls, lead qualification, scheduling, technician dispatch,
invoicing, churn — and puts a team of LLM agents inside the loop. The owner can
run nine months of operations in minutes, watch the agents actually negotiate,
and read a monthly report that explains *why* the numbers moved.

The point is not the dashboard. The point is that the agents make the decisions,
the program checks that those decisions are physically possible (money, shifts,
capacity), and the owner sees the consequence before spending a peso.

### What the agents do

| Agent | Job | Model tier |
|---|---|---|
| Teleoperator | Takes the call, qualifies the lead, proposes a slot | fast |
| Operator | Turns a qualified lead into a booked job | fast |
| Scheduling | Fits jobs into technician availability | fast |
| Technicians | Assigns and reschedules field work | fast |
| Dispatch | Reacts to traffic, no-shows and overruns | fast |
| Manager | Monthly decision: hire, invest in conversion, or hold | reasoning |
| Sector analysts | Monthly report per area (management, sales, scheduling, billing) | reasoning |

The manager is the interesting one: it emits a *decision* (a lever and an
amount), the deterministic engine rejects it if it is impossible, and the agent
gets the rejection back and has to react. No hallucinated hiring spree — the
simulation is the guardrail.

---

## How this uses Nebius Token Factory and NVIDIA Nemotron

Everything runs on **[Nebius Token Factory](https://tokenfactory.nebius.com/)**,
through its OpenAI-compatible endpoint:

```
LLM_BASE_URL=https://api.tokenfactory.nebius.com/v1
```

All model traffic goes through a single client (`backend/llm/client.py`) that
speaks the OpenAI protocol, so the provider is configuration, not code. That is
deliberate: it is what let us move the whole product onto Nebius without
touching the simulation engine.

### Model routing: right-sized inference

The most expensive mistake in an agentic product is sending every trivial call
to a frontier model. Nexus Alarm runs a **router** (`backend/llm/config.py`) that
picks a model per agent:

| Tier | Env var | Model | Used by | Why |
|---|---|---|---|---|
| Reasoning | `LLM_MODEL_REASONING` | `nvidia/Nemotron-3.5-Super-VL` | `gerente`, `sector_*` | A handful of calls a month, but they decide where the money goes |
| Fast | `LLM_MODEL_FAST` | `nvidia/Nemotron-3_5-Lightning` | `teleoperador`, `operador`, `agenda`, `tecnicos`, `despacho` | Dozens of calls per simulated day; latency and cost dominate |

Precedence is `LLM_MODEL_<AGENT>` → tier → `LLM_MODEL` (global fallback), so any
single agent can be pinned to another endpoint without a code change.

### Observability, on screen

Because the router is only useful if you can see it working, `/api/metricas`
aggregates calls, tokens, fallbacks and average latency **per model**, and the
bottom strip of the UI shows both models and how many calls each one took. In a
demo you can watch the volume go to Lightning while Super handles the monthly
meeting.

### Safety nets (not a demo trick)

- **Structured output.** Every call is validated against a Pydantic schema, with
  at most two retries.
- **Explicit fallback.** If the provider fails or returns invalid JSON, the call
  is served by a local deterministic writer and counted as a *fallback* in the
  metrics. The demo never dies, and nothing is hidden: the strip shows the count.
- **Cache.** Real responses are cached and can be replayed, so the demo is
  reproducible and does not burn credits.
- **Mock mode.** `USE_MOCK=true` runs the entire product with no network at all.

---

## Architecture

```
frontend/ (React 18 + Vite)
   │  plain fetch, auto-refresh
   ▼
backend/api.py (FastAPI)
   │
   ├── engine/          deterministic simulation
   │     simulation · agenda · technicians · facturas · leads
   │     calls · enjambre (swarm) · gerente · redactor · montecarlo
   │
   ├── llm/             single OpenAI-compatible client
   │     config (router) · client · prompts · mock · cache · metrics
   │
   └── store.py         SQLite persistence (one database per language)
```

The rule that keeps the demo honest: **the engine decides what is possible; the
LLM decides what to do.** Agents never mutate state directly. Their output is
parsed, validated, checked against business rules, and only then applied.

Everything is **bilingual (Spanish / English)** — UI, agent output and invoices —
with a separate SQLite database per language and `POST /api/idioma` to switch.

---

## Run it locally

### Option A — one command (Docker)

```bash
docker compose up --build
```

- Backend: <http://localhost:8000/api/estado>
- Frontend: <http://localhost:8080>

### Option B — two terminals

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

On Windows PowerShell, `npm.cmd run dev` avoids the execution-policy problem.

### Configuration

Copy `.env.example` to `.env` and fill in the key. `.env` is git-ignored.

| Variable | Purpose |
|---|---|
| `USE_MOCK` | `true` = no network, fully local. Default is `true`, so the app runs out of the box |
| `LLM_BASE_URL` | Nebius Token Factory endpoint |
| `LLM_API_KEY` | Your Token Factory API key (**never committed**) |
| `LLM_MODEL_REASONING` | Reasoning-tier model |
| `LLM_MODEL_FAST` | High-volume model |
| `LLM_MODEL` | Optional global fallback |
| `LLM_MAX_RETRIES` | Retries on invalid JSON (default 2) |
| `LLM_TIMEOUT_S` | Request timeout in seconds |
| `SIM_SEED` | Seed for reproducible simulations |

To check a real connection before a demo:

```bash
cd backend
.venv\Scripts\python.exe tests\probar_nebius.py
```

It lists the models your key can actually see and flags any configured ID that
is not in that list.

---

## Tests

```bash
cd backend
.venv\Scripts\python.exe -m pytest -q        # 85 passed
```

```bash
cd frontend
npm run build && npm run smoke               # renders the real UI against the backend
```

The smoke test boots the built bundle in jsdom against a running backend, opens
every sector panel, runs a simulated day, and switches languages. It needs the
backend on `localhost:8000` and a fresh `npm run build`; if the backend is down
the app shows its "waking up" notice and the suite fails on purpose.

---

## What changed during the submission period

This project existed before the hackathon (it was built for a previous event).
Everything below was done inside the submission window:

1. **Provider migration to Nebius Token Factory.** The LLM layer moved from a
   single-model configuration to a provider-agnostic setup pointing at
   `api.tokenfactory.nebius.com`.
2. **Model router (new).** Per-agent model resolution with tiers and overrides,
   plus 8 new tests covering the precedence rules.
3. **Per-model observability (new).** `/api/metricas` now aggregates by model,
   and the UI strip shows the routing live.
4. **Full rebrand and documentation rewrite**, so the repository describes the
   product that actually exists.
5. **Deployment configuration** for the Nebius endpoint.

The simulation engine, the API surface and the UI were already there; they were
not rewritten — which is the point. The product was built to swap its brain.

---

## License

MIT — see [LICENSE](LICENSE).

The multi-agent development process used to build this project is documented in
[`docs/EQUIPO.md`](docs/EQUIPO.md) and is not part of the product runtime.
