# nexus-ops-ai — Gemelo Digital de Nexus Alarm

Gemelo digital de una empresa ficticia de instalación de alarmas en Ciudad de Buenos Aires (CABA).
Un enjambre de agentes IA opera el proceso comercial completo — lead → teleoperador → agenda →
reparto de técnicos → contrato → comprobante — y el dueño ve KPIs en vivo, prueba escenarios
"qué pasa si" y corre los 9 meses del plan.

**Cerebro del sistema: modelo abierto servido vía TokenFactory sobre infraestructura AMD**
(`notebooks.amd.com/tokenfactory`). La inferencia de los agentes corre en AMD.

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

## Cómo correrlo

### Opción A — Docker (un solo comando) ✅ recomendado

```bash
docker compose up --build
```

- **Pantalla del dueño:** http://localhost:8080
- **API del backend:** http://localhost:8000/api/estado

Arranca en **modo mock** por defecto (no gasta créditos AMD). Para usar el cerebro de
TokenFactory de verdad: copiá `.env.example` a `.env`, poné `USE_MOCK=false` y completá
`LLM_API_KEY` y `LLM_MODEL`, y volvé a correr `docker compose up --build`.

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
.venv\Scripts\python.exe tests\test_engine.py   # 20 tests del motor
.venv\Scripts\python.exe tests\test_llm.py      #  5 tests del cliente LLM
.venv\Scripts\python.exe tests\test_api.py      #  8 tests de la API
.venv\Scripts\python.exe tests\mirar_negocio.py # tablero de los 9 meses

cd ..\frontend
npm run build     # compila
npm run smoke     # 31 checks: render + placa contra el backend real
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
        └── Panel del dueño           KPIs · sliders · escenarios · mapa CABA · métricas AMD
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
  api.py            FastAPI: estado, resumenes, escenarios, mapa, métricas AMD...
  store.py          SQLite (clientes, leads, llamadas, citas, decisiones, actas)
  engine/           business · leads · calls · agenda · technicians · gerente · simulation
  llm/              client (OpenAI-compatible) · mock · cache · metrics
  schemas/          respuestas estructuradas de cada agente (Pydantic)
  tests/            33 tests + mirador de negocio
frontend/           React + Vite: pantalla del dueño
scripts/dev.cmd     levanta backend + frontend en dos ventanas
docker-compose.yml  backend + frontend de un solo comando
render.yaml         Blueprint de Render
```

## Reglas del proyecto

- **Salidas estructuradas:** cada agente devuelve JSON validado con Pydantic
  (máx. 2 reintentos + fallback en modo mock).
- **Un único cliente LLM** compatible con OpenAI (`base_url` configurable) → TokenFactory de AMD.
- **Modo mock y caché/replay** para reproducir la demo sin red.
- **Métricas por llamada** (latencia p50/p95, tokens, tokens/s) expuestas en el panel AMD.
- **Monte Carlo** y estadística para el pronóstico — el LLM nunca es el único método de cálculo.

## Licencia

MIT. Ver `LICENSE`.
