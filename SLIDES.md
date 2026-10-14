# Slides — nexus-ops-ai (contenido listo para pegar)

> **Uso:** copiá cada bloque en una diapositiva. Fondo oscuro (#0E1116), texto claro,
> logo AMD abajo a la derecha. Máximo 4 ideas por slide — lo que está escrito acá ya
> está cortado para eso.
>
> Total: **9 slides**. Con eso alcanza y sobra para el jurado.
> Los datos numéricos salen de `backend/tests/mirar_negocio.py` (son reproducibles).

---

## SLIDE 1 — Título

**nexus-ops-ai**

*The digital twin of Nexus Alarm*

A swarm of AI agents running the full sales operation of a small
security-alarm company in Buenos Aires.

`AMD ACT III · Reinvent Commerce`

---

## SLIDE 2 — El problema

**Every month, the owner places three bets**

- 👥 How many **salespeople**?
- 🔧 How many **technicians**?
- 📊 How much to invest in **better customer data**?

Guess wrong, and you either **lose sales** or **burn cash**.
Small businesses don't need a dashboard — they need a decision.

---

## SLIDE 3 — Qué es

**A digital twin, not a dashboard**

We simulate **9 months** of a real operating rhythm:

- 150 inbound calls a day (3 operators, 50 each)
- Installations scheduled for the **next week**, Monday–Saturday, 3 slots a day
- An **AI manager** that meets every month and decides how to grow

Everything is **persisted**: stop the simulation, come back later, nothing is lost.

---

## SLIDE 4 — Quién habla, quién calcula ⭐

**The rule of the actor: the LLM talks, the program computes**

| | Speaks (LLM on AMD) | Computes (algorithm) |
|---|---|---|
| Salesperson | ✅ qualifies, notes the objection | — |
| Scheduler | ✅ negotiates the slot | free slots |
| Dispatcher | explains | ✅ **zone split + travel cost** |
| Manager | ✅ analyzes, advises | ✅ **validates cash & capacity** |

~40,000 calls are computed. The AI only **acts** on the ~30 shown live.
Fast, cheap, reproducible — and the agents still speak for real.

---

## SLIDE 5 — La demo

**What you see on screen**

- **KPIs** in real time: sales/day, conversion, active technicians, cash
- **"What if…" sliders**: move operators, technicians and conversion investment
- **Animated map of Buenos Aires**: every appointment, by zone
- **Call telegraph**: who answered, who didn't, and *why not*
- **Manager's minutes**: the AI's monthly decision, in plain Spanish

---

## SLIDE 6 — El Gerente IA ⭐

**The AI manager — with a transparent safety net**

Each month it reads the numbers and moves **three levers**:
hire operators · hire technicians · improve conversion.

But the **program validates** every decision: cash, capacity, workload.
Impossible decisions are **rejected and logged**.

If the plan falls short, the safety net says it out loud:

> *"You won't make it at this rate — reconsider."*

The warning goes **into the minutes**. Nothing is cooked.

---

## SLIDE 7 — Los números ⭐

**9 months. Same goal: 10 technicians, no bankruptcy.**

| | Month 1 | Month 9 | |
|---|---:|---:|---:|
| Sales / day | 6.7 | 32.0 | **×4.8** |
| Operators | 3 | 8 | ×2.7 |
| **Technicians** | 2 | **10** | ✅ **goal met** |
| Revenue / month | $36.6k | $323k | **×8.8** |
| Costs / month | $9.1k | $24.4k | ×2.7 |

**Revenue ×8.8 while costs grow ×2.7.**

Sales grow almost 5× with less than 3× the operators —
because the manager improves conversion, not just headcount.

---

## SLIDE 8 — AMD

**The brain runs on AMD TokenFactory**

- Open model served through `notebooks.amd.com/tokenfactory`
- **Every single call measured**: latency p50/p95, tokens, tokens/s — on screen
- If the endpoint fails, the system **degrades gracefully and reports it** in the panel

**The forecast is Monte Carlo, not the language model.**
The model talks. The math decides.

---

## SLIDE 9 — De datos a acción

**From customer data → recommendation → action**

Every objection is logged (`too expensive`, `already has one`, `not interested`).
That is the manager's raw material: it changes the offer, the script and the
hiring plan — month after month.

**A working product:**
`docker compose up --build` → running

Open source (MIT) · Containerized · Web demo · README that runs

`github.com/JoseMota0190/nexus-ops-ai`

---

## Preguntas que va a hacer el jurado (prepará la respuesta)

**¿Por qué no solo un dashboard?**
Because the AI **acts**: it hires, it improves the script, it schedules. The
dashboard is how you watch it, not what it does.

**¿Y si el LLM falla?**
It degrades to a local fallback, it's logged in the panel, and the simulation
keeps running. The business never stops because a model is down.

**¿Los números son reales?**
They are **simulated and reproducible** (fixed seed). The value is the *decision
loop*, not the specific figures. All companies and receipts are fictional.

**¿Dónde está AMD en esto?**
Every agent's reasoning goes through an open model on TokenFactory, with live
latency and token metrics on screen — that's a hard requirement we built for.
