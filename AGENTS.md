# AGENTS.md — nexus-ops-ai (Gemelo Digital de "Nexus Alarm")

> **Este archivo es la fuente de verdad del proyecto.** Cualquier sesión nueva DEBE leerlo
> entero antes de tocar código. Contiene decisiones ya TOMADAS por el autor (no re-preguntar
> lo que está cerrado) y el estado real de avance.

---

## 0. Cómo trabajar con el autor (IMPORTANTE)

- **El autor NO es técnico.** Hablale en criollo, sin jerga. Si algo es complejo, explicalo con
  una historia/analogía. Ej.: la IA es "el gerente simpático que habla"; el algoritmo es "la
  planilla de Excel que evita errores".
- **NO asumir decisiones.** El autor pidió explícitamente que, cuando se razona algo, se le
  vuelva a PREGUNTAR para confirmar. No dar por sentado.
- Máximo **4 preguntas por bloque** (usar la herramienta de preguntas).
- Trabajar en **fases pequeñas y verificables**. Correr el modo mock tras cada cambio.
- **NO subir nada a GitHub** hasta que el autor lo diga. (Aún no autorizado.)
- Ante duda entre "más funciones" y "más estabilidad", elegir estabilidad.

### Proyecto relacionado pero SEPARADO
Hay OTRO proyecto en `Downloads\AGENTS.md` (habitAR / concurso UdeSA "Contar con Datos 2026",
cierra 15 oct 2026). **NO mezclar.** nexus-ops-ai es el hackathon AMD ACT III / lablab.ai
(fase online 12–18 oct 2026). Son dos cosas distintas en la misma máquina.

---

## 1. Qué es el proyecto

Gemelo digital de una empresa ficticia de instalación de alarmas en CABA (**"Nexus Alarm"**).
Un enjambre de agentes IA opera el proceso comercial completo y el dueño ve KPIs y prueba
escenarios "qué pasa si".

- **Prioridad máxima: AMD.** El cerebro corre en modelo abierto servido por **TokenFactory**
  (`notebooks.amd.com/tokenfactory`). Es requisito de elegibilidad. Debe verse en la demo.
- **Evolus (secundario, módulo aislado):** extractor de documentos + workflow de contratos.
- **Google/Gemini: DESCARTADO** por ahora (decisión del autor).

Reglas del track Commerce (lablab.ai):
- NO usar el LLM como único método de pronóstico. Usar Monte Carlo/estadística y explicar el cálculo.
- Mostrar cómo datos del cliente se convierten en recomendación/acción.
- Debe ser un producto que funciona, no solo dashboard ni slides.

---

## 2. Stack (DECIDIDO, no re-preguntar)

- **Backend:** Python 3.10 + FastAPI. **Frontend:** React.
- **Base de datos:** SQLite real (el autor pidió "base de datos de verdad").
- **LLM:** TokenFactory de AMD, compatible OpenAI (`base_url` configurable). Un SOLO cliente.
- **Docker:** Desktop ya instalado (v4.95.0). Falta generar Dockerfile + docker-compose (Fase 9).
- **Licencia:** MIT. **Hosting:** Render (backend) + Netlify (frontend), el sábado.
- **Git identity global ya configurada:** `Jose Mota <JoseMota0190@users.noreply.github.com>`,
  `credential.helper=manager`. GitHub del autor: **JoseMota0190**. Remotos por HTTPS (el
  credential manager guarda el login tras el 1er push → pushes automáticos después).
- OJO: PowerShell tiene **execution policy** que bloquea `.ps1`. Usar `.venv\Scripts\python.exe`
  directo (sin activar) o `.cmd`. Ya funciona así.

---

## 3. EL MODELO DE NEGOCIO (decidido con el autor, NO cambiar sin preguntar)

### Empresa ficticia
- **Nombre:** Nexus Alarm. **Proyecto:** nexus-ops-ai.
- **Productos:** kit Hogar Básico USD 180, Plus USD 320, Comercial USD 550; sensor inundación
  USD 40, extensor de zona USD 25; monitoreo mensual USD 15 (básico) / 25 (plus, con app);
  mantenimiento anual USD 60.

### Operación (el corazón)
- **Arranque (semana 1):** 2 TÉCNICOS + 3 TELEOPERADORES.
- **Cada teleoperador vende 2/día → 6 VENTAS/DÍA en total.**
- **Las ventas NO se instalan el mismo día: se agendan para la SEMANA SIGUIENTE.**
  Por eso los técnicos **empiezan a trabajar recién en la semana 2** (semana 1 = solo ventas).
- **Siempre lunes a sábados.** Cada técnico: **3 instalaciones/día = 9am, 12pm, 4pm.**
- **Meta mes 9: 10 TÉCNICOS** trabajando.

### Llamadas (volumen)
- **50 llamadas por día POR cada teleoperador → 150 llamadas/día en total.**
- El ritmo **FLUCTÚA pero promedia** esos valores (no es fijo).
- De las llamadas: ~20 atienden (en total), de ahí salen las ventas. Cada intento genera un
  **LOG sintético**: ¿atendió? ¿no? Y si vio la oferta pero no compró → **registrá el MOTIVO**
  ("muy caro", "ya tiene otro", "no le interesa", etc.).

### Crecimiento (lo decide el GERENTE IA)
- El gerente **cada mes** junta métricas, **mejora la BASE DE DATOS y el SERVICIO de los
  teleoperadores** (sube la conversión), y **decide cuándo contratar** más técnicos (de 2 a 10).
- Usa **LAS DOS PALANCAS JUNTAS**: contrata **más operadores** Y los vuelve **más eficientes**.
  El número de operadores **sí sube**, pero **no tanto como suben las ventas** (la eficiencia
  también ayuda) → los costos crecen MÁS LENTO que las ventas. Eso se ve en el gráfico.
- Las "reuniones mensuales" del gerente se **SIMULAN con un agente IA gerente** en la demo.

### Reglas locales simuladas (DECIDIDO incluirlas)
- **Registro "No Llame"** (AAIP, Ley 25.326): ~8% de leads. El teleoperador NO puede hacer
  llamada en frío a esos; solo atender entrada.
- **Sello ARCA:** el comprobante lleva **"SIMULADO – SIN VALIDEZ FISCAL"**. Jamás afirmar
  facturación real. (Evolus NO es ERP ni factura.)

---

## 4. LOS AGENTES (quién hace qué y quién decide)

| Personaje | Qué hace | ¿Quién decide? |
|---|---|---|
| **Teleoperador** (×3) | Llama, califica, agenda, anota motivo de fallo, respeta "No Llame" | IA **habla** |
| **Coordinador de Agenda** | Negocia fecha/hora CON EL OPERADOR por mensajes; tiene la pizarra de turnos libres; cuando acuerdan **escribe al cliente** a confirmar | IA **habla** |
| **Coordinador de Técnicos** | Reparte técnicos por zona | **PROGRAMA calcula, IA EXPLICA** (decidido tras razonar juntos: cumple la regla de no depender solo del LLM y evita repartos imposibles) |
| **Gerente** | Cada mes: métricas, mejora base/servicio, decide contratar | IA **analiza y aconseja** |

**Flujo:** Cliente (SQLite) → Teleoperador (llama, log) → [conversación operador↔coordinador
agenda] → coordinador agenda confirma al cliente → coordinador técnicos reparte (programa).

---

## 5. LA SIMULACIÓN DE LOS 9 MESES (decidido con el autor)

- **6 PRIMEROS MESES: corren SOLOS de un saque.**
- **3 ÚLTIMOS MESES: los corre el AUTOR a su ritmo**, viendo los **NÚMEROS de cada mes**
  (leads, llamadas, ventas, instalaciones, decisiones del gerente). NO necesita ver a los
  agentes hablando, solo números.
- **Cada mes ejecutado queda GUARDADO** (SQLite) → puede parar y seguir después sin perder nada.
- Esto es una herramienta de TESTEO para cazar bugs antes de la demo.

### El cálculo clave del pitch
Para llegar a 10 técnicos (mes 9) hacen falta ~**30 ventas/día** (vs 6 del mes 1). Solo se logra
porque el gerente **sube la conversión**. Pregunta del pitch: *"¿cómo vendo 5× más sin poner
5× más operadores?"*

---

## 6. ESTADO ACTUAL (lo que YA ESTÁ construido y PROBADO)

Repo local en **`C:\Users\josem\Projects\nexus-ops-ai`** (git inicializado, 2 commits:
`80f399a` esqueleto, `ac870ac` motor). **Sin remote, sin push (no autorizado aún).**
Rama en `master` (OJO: pendiente renombrar a `main` antes del push; autor lo decidió pero
aún no se hizo).

**Commiteado:**
- `README.md`, `LICENSE` (MIT), `.env.example`, `.gitignore`, `backend/requirements.txt`.
- `backend/llm/` — cliente LLM único (`client.py`) con **modo mock**, **caché/replay**
  (`cache.py`), **métricas** (`metrics.py`: latencia p50/p95, tokens, tokens/s → panel AMD),
  config por env (`config.py`). Mock realista en español (`mock.py`).
- `backend/schemas/` — `TeleoperadorResponse`, `DespachoResponse` (Pydantic, JSON estructurado).
- `backend/engine/` — `zones.py` (15 barrios CABA con coords y peso de demanda), `clock.py`
  (reloj x120 calculado, no hardcodeado), `leads.py` (leads ficticios 200–250/día, semilla,
  ~8% No Llame), `technicians.py` (asignación por algoritmo con traslado), `montecarlo.py`
  (historial largo con agregación por mes).
- `backend/tests/` — **12 tests pasando** (5 LLM + 7 motor). Correr con:
  `cd backend && .venv\Scripts\python.exe tests\test_llm.py` y `...\test_engine.py`.

**⚠️ NOTA:** el motor actual (leads 200–250/día, 10 técnicos fijos) es un ESQUELETO GENÉRICO
anterior a las decisiones del §3. **La Fase 2+ debe REARMARLO** al modelo real: 3 operadores
vendiendo 2 c/u, 2 técnicos arrancando, agenda semanal, gerente que crece a 10 técnicos.
No borrar, adaptar.

---

## 7. FASES DE CONSTRUCCIÓN

1. ✅ **Hecha:** estructura, cliente LLM mock, motor genérico, tests.
2. ⬜ **SIGUIENTE →** Base de datos REAL (SQLite) de clientes ficticios (la que "leen" los operadores).
3. ⬜ 3 teleoperadores + registro de llamadas (log sintético) + motivos de fallo.
4. ⬜ Coordinador de agenda + mensajes operador↔coordinador + confirmación al cliente.
5. ⬜ Coordinador de técnicos (reparto calculado por programa, IA explica).
6. ⬜ Gerente IA + reuniones mensuales + crecimiento a 10 técnicos.
7. ⬜ Pantalla del dueño (KPIs, sliders, lead en vivo texto, mapa animado, métricas AMD).
8. ⬜ Simulación por meses (6 solos + 3 a mano, con guardado en SQLite).
9. ⬜ Docker (Dockerfile + docker-compose), README que corra, video (voz clonada, fallback a
   voz real), pitch en inglés con subtítulos.

**Recorte de emergencia si falta tiempo:** primero el mapa animado, luego extras. NUNCA recortar
AMD, el envío ni el README.

---

## 8. TAREAS EXTERNAS DEL AUTOR (gestiones que le tocan a él)

- **Discord (hoy):** código de evento Evolus · compatibilidad Evolus↔TokenFactory (¿acepta el
  endpoint de TokenFactory o exige vLLM propio?) · hora exacta de cierre domingo · permiso de
  audio con voz clonada en el video.
- **AMD TokenFactory:** abrir notebook, anotar CATÁLOGO de modelos de texto disponibles.
- **Evolus:** cupón **AMDACT3 YA RECLAMADO**. Falta: crear workspace en `app.evolus.ai`,
  conectar modelo, verificar endpoints en la referencia interactiva (AI Tools / Workflows).
- **Hosting:** crear cuenta Render + Netlify (el sábado).

---

## 9. Decisiones CERRADAS (NO volver a preguntar)

Empresa "Nexus Alarm" · proyecto nexus-ops-ai · Python/FastAPI + React · SQLite · MIT ·
TokenFactory · Evolus extractor+workflow aislado · **sin auditor visual** (facturas con errores
Monte Carlo para Evolus) · lead en vivo solo texto · **CON mapa animado** (primer corte si falta
tiempo) · Google descartado · No Llame + ARCA simulados · 2 técnicos + 3 operadores arranque ·
10 técnicos meta mes 9 · lunes a sábados · 3 turnos (9am/12pm/4pm) · ventas semana siguiente ·
50 llamadas/operador/día (150 total, fluctúa) · 6 ventas/día arranque · reparto: programa
calcula + IA explica · gerente IA simulado · 6 meses solos + 3 manuales guardando · voz clonada
con fallback real, slides en inglés · solo fase online · hosting free tier.
