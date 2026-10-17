# nexus-ops-ai — Gemelo Digital de Nexus Alarm

Gemelo digital de una empresa ficticia de instalación de alarmas en Ciudad de Buenos Aires (CABA).
Un enjambre de agentes IA opera el proceso comercial completo — lead → teleoperador → agenda →
reparto de técnicos → contrato → comprobante — y el dueño ve KPIs en vivo, prueba escenarios
"qué pasa si" y corre los 9 meses del plan.

**Cerebro del sistema: modelo abierto servido sobre infraestructura AMD** (AMD Radeon
Cloud / instancia GPU propia con Gemma + vLLM). La inferencia de los agentes corre en AMD.
**Redactor de los informes: Evolus.**

> **Proyecto de hackathon (AMD Developer Hackathon: ACT III / lablab.ai · track Reinvent Commerce).**
> Todos los números, empresas, llamadas y comprobantes son **SIMULADOS**. No constituyen
> asesoramiento, facturación real ni afirmaciones fiscales. Los comprobantes llevan
> "SIMULADO – SIN VALIDEZ FISCAL". La línea base de comparación es una **estimación**.

---

## La historia que cuenta

Nexus Alarm arranca con **3 teleoperadores y 2 técnicos**: 150 llamadas/día (50 por operador),
~6 ventas al día, que se agendan para la **semana siguiente** de lunes a sábados.

Un **Gerente IA** se reúne cada mes, mira los números, mueve sus tres palancas
(contratar operadores · contratar técnicos · mejorar la conversión de la base de datos)
y decide cuánto crecer. El **programa valida** cada decisión contra las reglas del negocio
(caja, tope de contratación, capacidad) y si el plan queda corto, una **red de seguridad**
lo avisa y lo corrige **en forma transparente** — queda escrito en el acta.

Resultado de la simulación de 9 meses:

| | mes 1 | mes 9 | |
|---|---:|---:|---:|
| Ventas/día | 6.7 | 32.0 | **×4.8** |
| Teleoperadores | 3 | 8 | ×2.7 |
| Técnicos | 2 | **10** | meta alcanzada |
| Ingresos/mes | 36.6 k | 323 k | ×8.8 |
| Costos/mes | 9.1 k | 24.4 k | ×2.7 |

**Los costos crecen más lento que las ventas** (×2.7 vs ×6.4 en ingresos por instalación):
la pregunta del pitch es *"¿cómo vendo 5× más sin poner 5× más operadores?"* — la respuesta es
que el Gerente mejora la conversión además de contratar.

---

## Los 4 sectores (el menú ☰)

El menú ya no es una lista de tableros sueltos: son **4 sectores**, y cada uno **rinde
cuentas solo**. Al cerrar cada mes, el sector **calcula sus números** con el programa, la
**IA de AMD los analiza**, **Evolus redacta el documento** y, si Evolus está apagado o falla,
redacta un **respaldo local**. El informe queda guardado y se puede volver a generar con un clic.

| Sector | Qué mira | Color |
|---|---|---|
| 🧾 **Gerencia** | caja, ingresos, costos, técnicos, decisión del mes | azul |
| 📞 **Ventas** | llamadas, atención, conversión, motivos de fallo | verde |
| 📅 **Agenda y técnicos** | ventas agendadas, instalaciones, turnos, ocupación | violeta |
| 🧮 **Facturación** | comprobantes simulados, precisión del extractor, defectos | cyan |

Los **6 meses precargados** se siembran al instante con el redactor local (sin gastar
créditos ni tocar la red); los meses que corrés en vivo usan la IA y Evolus si están prendidos.

**Transparencia:** cada informe muestra de dónde salió (`🧠 Analizó la IA (AMD)` /
`📝 Redactor local` · `✍️ Redactó Evolus` / `✍️ Redacción local`) y su semáforo 🟢🟡🔴.

---

## Cómo correrlo

### Opción A — Docker (un solo comando) ✅ recomendado

```bash
docker compose up --build
```

- **Pantalla del dueño:** http://localhost:8080
- **API del backend:** http://localhost:8000/api/estado

Arranca en **modo mock** por defecto (no gasta créditos AMD). Para usar el cerebro de
AMD de verdad: copiá `.env.example` a `.env`, poné `USE_MOCK=false` y completá
`LLM_API_KEY` y `LLM_MODEL` (el endpoint de Radeon Cloud ya viene puesto), y volvé a
correr `docker compose up --build`.

La base de datos SQLite vive en el volumen Docker `nexus_data` → **sobrevive a los reinicios**.
Para borrar todo y empezar de cero: `docker compose down -v`.

Si el puerto 8000 u 8080 están ocupados en tu máquina:
`BACKEND_PORT=8010 FRONTEND_PORT=8081 docker compose up --build`.

### Opción B — Sin Docker (desarrollo, Windows)

```powershell
# Backend (usa el venv ya creado, sin activarlo)
cd backend
.venv\Scripts\pip install -r requirements.txt   # primera vez
.venv\Scripts\python.exe -m uvicorn api:app --reload

# Frontend (en otra ventana)
cd frontend
npm install
npm run dev
```

O de una: doble clic en **`scripts\dev.cmd`** (abre backend + frontend en dos ventanas).
En PowerShell: `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1`.

Con `USE_MOCK=true` todo el flujo funciona sin llamar a ningún modelo real.

### Pruebas

```powershell
cd backend
# 103 tests en total (motor, LLM, API, enjambre de agentes, Evolus) — corren sin red
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe tests\mirar_negocio.py # tablero de los 9 meses

cd ..\frontend
npm run build     # compila
npm run smoke     # 45 checks: render + placa contra el backend real
```

---

## Publicar (Render + Netlify)

- **Backend → Render:** el archivo `render.yaml` es un Blueprint. En
  [app.onrender.com](https://app.onrender.com) → *New* → *Blueprint* → elegir el repo.
  Render arma el servicio solo (Python, `uvicorn api:app`, chequeo de salud en `/api/estado`).
- **Frontend → Netlify:** en [app.netlify.com](https://app.netlify.com) → *Add new site* →
  importar el repo con *base directory* `frontend`. Netlify lee `frontend/netlify.toml`
  (build `npm run build`, publica `dist`, redirige `/api/*` al backend de Render).
  **Hay que editar la URL del backend adentro de `netlify.toml`** (está marcada con ⬇).
- Los secretos (`LLM_API_KEY`, `LLM_MODEL`) se cargan en el panel de Render. **Nunca** se
  commitean.

## Variables de entorno

Ver `.env.example`. Los secretos **nunca** se commitean.

---

## Arquitectura

```
Motor de eventos (determinista, SIN LLM)
  reloj x120 · leads 180/día (suben con las mejoras de base de datos)
  150 llamadas/día · agenda semanal (lun–sáb, turnos 9/12/16) · Monte Carlo
  reparto de técnicos por algoritmo (costo de traslado por barrio)
  validador del Gerente + red de seguridad transparente
  todo persistido en SQLite (backend/data/nexus.db)
        │
        ├── Teleoperador  (LLM AMD)  califica, agenda y anota el motivo de fallo
        ├── Coordinador de agenda     negocia turno por mensaje y confirma al cliente
        ├── Gerente IA               reunión mensual: métricas → decisión → acta
        └── 4 SECTORES (cierre de mes)
              programa calcula → IA de AMD analiza → Evolus redacta → respaldo local
              informes guardados en SQLite (reportes_sector)
        │
  Pantalla del dueño: mapa CABA + logo · pie de simulación + Sala de agentes +
  franja AMD siempre visible · menú ☰ con los 4 sectores
```

**Regla del actor:** el programa calcula las ~40.000 llamadas de los 9 meses; la IA
"actúa" solo en las ~20-30 llamadas y chats que se muestran en vivo. Así la demo es
rápida, barata y determinista, y aun así los agentes hablan de verdad.

### Agentes y quién decide

| Personaje | Habla (IA) | Decide (programa) |
|---|---|---|
| Teleoperador | ✅ califica y anota el motivo | probabilidad de cierre |
| Coordinador agenda | ✅ negocia turno | turnos libres y vecindad |
| Coordinador técnicos | explica | ✅ reparto por algoritmo |
| Gerente | ✅ analiza y aconseja | ✅ valida caja, tope y capacidad |

### Reglas locales simuladas

- Cada comprobante lleva **"SIMULADO – SIN VALIDEZ FISCAL"** (sello ARCA simulado).
- Evolus (extractor de documentos + workflow de contratos) es un módulo **aislado**.
- **Todas** las llamadas entran por leads de la web que piden ser llamados: no hay llamada en frío.

---

## Estructura del repo

```
backend/
  api.py            FastAPI: estado, resumenes, escenarios, mapa, métricas AMD, sectores...
  store.py          SQLite (clientes, leads, llamadas, citas, decisiones, actas, informes)
  engine/           business · leads · calls · agenda · technicians · gerente · simulation
                    sectores (informes de los 4 sectores) · redactor (respaldo local)
  llm/              client (OpenAI-compatible) · mock · cache · metrics
  evolus/           módulo aislado: extractor de documentos + workflow + redacción
  schemas/          respuestas estructuradas de cada agente (Pydantic)
  tests/            103 tests + mirador de negocio
frontend/           React + Vite: mapa CABA + pie de simulación + 4 sectores
scripts/dev.cmd     levanta backend + frontend en dos ventanas
docker-compose.yml  backend + frontend de un solo comando
render.yaml         Blueprint de Render
```

## Reglas del proyecto

- **Salidas estructuradas:** cada agente devuelve JSON validado con Pydantic
  (máx. 2 reintentos + fallback en modo mock).
- **Un único cliente LLM** compatible con OpenAI (`base_url` configurable) → Radeon Cloud / Gemma sobre GPU de AMD.
- **Evolus** redacta los informes de sector (con respaldo local si está apagado o falla).
- **Modo mock y caché/replay** para reproducir la demo sin red.
- **Métricas por llamada** (latencia p50/p95, tokens, tokens/s) expuestas en el panel AMD.
- **Monte Carlo** y estadística para el pronóstico — el LLM nunca es el único método de cálculo.

## Licencia

MIT. Ver `LICENSE`.
