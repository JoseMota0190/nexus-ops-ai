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
- **⏸️ RETOMADA (14 oct):** antes de escribir o modificar **cualquier** código, recorrer la
  **checklist del §8** punto por punto junto con el autor. Ver §7 (pausa) y §8 (lista).
- **GitHub:** el autor YA AUTORIZÓ el push cuando toque ("Sí, autorizo cuando toque").
  Antes de subir: renombrar `master` → `main`. Repo debe quedar **PÚBLICO** (es requisito de
  inscripción: public repo + Application URL + Docker + README + video + slides).
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

- **Prioridad máxima: AMD.** El cerebro corre en un modelo abierto servido por **AMD**.
  Es requisito de elegibilidad y debe verse en la demo.
  **Actualización 14 oct:** el portal `notebooks.amd.com/tokenfactory` respondió
  *"Your email is not registered for API key distribution"* → el autor decidió **NO insistir
  más**. El motor pasa a ser **AMD Radeon Cloud** (`developer.amd.com.cn/radeon`).
- **Evolus: QUEDÓ ELIMINADO (18 oct).** El código de evento (`AMDACT3`) cerró y no se consiguió
  workspace → se borró el módulo `backend/evolus/` y `EVOLUS.md`. El **auditor de facturas se
  mantuvo, pero es por reglas** (no usa IA): vive en `backend/engine/facturas.py`.
- **Google/Gemma: YA NO ESTÁ DESCARTADO** (cambio de decisión del autor, 14 oct).
  Google DeepMind entró como partner del hackathon y **Gemma corre sobre GPU de AMD (ROCm)**,
  así que **no viola el requisito de AMD** y además da acceso a un **premio extra de Google**.
  El autor eligió **ir directo a montar Gemma**. Ojo: **Gemma NO está en el catálogo gratis**
  de Radeon Cloud (9 modelos, ninguno Gemma) → hay que **alquilar una instancia GPU y
  desplegarlo con vLLM**. Ver §8 y §9.

Reglas del track Commerce (lablab.ai):
- NO usar el LLM como único método de pronóstico. Usar Monte Carlo/estadística y explicar el cálculo.
- Mostrar cómo datos del cliente se convierten en recomendación/acción.
- Debe ser un producto que funciona, no solo dashboard ni slides.

---

## 2. Stack (DECIDIDO, no re-preguntar)

- **Backend:** Python 3.10 + FastAPI. **Frontend:** React.
- **Base de datos:** SQLite real (el autor pidió "base de datos de verdad").
- **LLM:** un SOLO cliente, compatible con OpenAI (`base_url` configurable). Motor previsto:
  **Gemma servido por AMD** (Radeon Cloud / AMD Developer Cloud). Ver §8.
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
- **Registro de leads:** TODOS los leads entran por la web pidiendo ser llamados.
  **NO hay llamada en frío** (decisión del autor, cerrada). El "No Llame" de AAIP quedó
  FUERA del proyecto — no simularlo, no mencionarlo.
- **Sello ARCA:** el comprobante lleva **"SIMULATED – NO FISCAL VALIDITY"** (inglés) /
  **"SIMULADO – SIN VALIDEZ FISCAL"** (español), según el idioma activo
  (`backend/engine/facturas.py`, función `sello()`). Jamás afirmar facturación real.

---

## 4. LOS AGENTES (quién hace qué y quién decide)

| Personaje | Qué hace | ¿Quién decide? |
|---|---|---|
| **Teleoperador** (×3) | Llama, califica, agenda, anota motivo de fallo | IA **habla** |
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

Repo local en **`C:\Users\josem\projects\nexus-ops-ai`** (rama **`main`**). **Repo PÚBLICO en
GitHub + deploy en vivo ✅** (sesión del 18 oct): `https://nexus-ops-ai.netlify.app` (frontend) y
`https://nexus-ops-ai-backend.onrender.com` (backend). El push queda para el **final** (un solo
push/deploy, así Netlify/Render no redeployan a mitad del trabajo).

**✅ Fases 2 a 8 construidas y probadas** (ver detalle de fases más abajo):
- `backend/store.py` — SQLite real (clientes, leads, llamadas, motivos, citas, técnicos,
  decisiones del gerente, actas, resúmenes por día/mes) + `transaction()` que agrupa los
  escritos (arranque 25 s → 3.4 s).
- `backend/engine/business.py` — TODAS las constantes del negocio (precios, sueldos, tasas,
  meta 10 técnicos, leads 180+40/mejora, 50 llamadas/operador, `MESES_AUTOMATICOS = 6`).
- `backend/engine/leads.py` · `calls.py` · `agenda.py` · `technicians.py` · `gerente.py` ·
  `simulation.py` — la operación completa: leads → llamadas con motivo de fallo → agenda
  semanal (lun–sáb, turnos 9/12/16) → reparto de técnicos por algoritmo → reunión mensual
  del Gerente IA con validador + **red de seguridad transparente**.
  El tope de contratación de técnicos usa las **ventas reales** del último mes (no el plan).
- `backend/api.py` — FastAPI completo: estado, resumenes, `/api/mes`, `/api/todo`, `/api/dia`,
  `/api/reiniciar`, actas, llamadas, mensajes, mapa, métricas AMD, `llamada_en_vivo`,
  `objetivos`, `escenario` (sliders). **Al arrancar con la base vacía corre solo los primeros
  6 meses.**
- `frontend/` — pantalla del dueño en React + Vite: **mapa CABA a pantalla completa** con el
  **logo de Nexus** latiendo al centro · **pie** con el cuadro de simulación + la **Sala de
  Agentes** adentro + la **franja AMD** siempre visible · **menú ☰ con los 4 sectores**
  (Management · Sales · Scheduling & technicians · Billing), cada uno con su informe mensual ·
  **botón ES/EN** en el header. `npm run build` compila; `npm run smoke` da **46/46 checks**
  (incluye el cambio de idioma) y **falla si algún pedido del backend no responde 200**.
- `backend/engine/sectores.py` + `redactor.py` — los **4 sectores**: el programa calcula los
  números → **la IA de AMD los analiza** → **el redactor local arma el documento** (sin red ni
  créditos). Los informes quedan en la tabla `reportes_sector`. La siembra de los 6 meses los
  escribe **localmente**.
- `backend/engine/facturas.py` — **auditor de facturas por reglas** (Monte Carlo + detección de
  defectos y su lectura). El sello (`sello()`) es bilingüe. **No usa IA** (era el rol del Evolus
  eliminado).
- `backend/llm/client.py` — **respaldo automático**: si el modelo de AMD falla o devuelve basura,
  se usa la respuesta local y queda anotado como `fallback_calls` (el demo NUNCA se rompe).
- `backend/tests/probar_amd.py` — **herramienta de conexión real**: lista el catálogo de modelos,
  mide latencia y comprueba que el modelo devuelva el **JSON estructurado** que los agentes
  necesitan. Correrla antes de prender el cerebro de verdad.
- `docker-compose.yml` + `backend/Dockerfile` + `frontend/Dockerfile` + `nginx.conf` +
  `render.yaml` + `frontend/netlify.toml` + `scripts/dev.cmd`.
  **Docker verificado de punta a punta el 14 oct** (arranca, siembra 6 meses y el proxy de nginx
  anda). **Ojo:** en las sesiones del 17–18 oct **NO se pudo re-verificar** porque Docker Desktop
  estaba cerrado → queda como pendiente barato para el autor.
- `backend/tests/` — **77 tests**: `test_engine.py` (22), `test_llm.py` (6), `test_api.py` (14),
  `test_enjambre.py` (14), `test_facturas.py` (21) + `mirar_negocio.py`.

**Números verificados** (`mirar_negocio.py`, semilla 42 — los mismos que muestra la app): mes 1 →
6.8 ventas/día, 3 operadores, 2 técnicos. Mes 9 → 30.5 ventas/día, 8 operadores,
**10 técnicos (meta cumplida)**. Ingresos ×8.1 vs costos ×2.7 → **los costos crecen más lento
que las ventas**. (Verificado también que el **modo día a día da EXACTAMENTE los mismos números**
que el modo mes, mes por mes.)

**Artefactos de entrega escritos:** `README.md` (que corre), `PITCH.md` (guion del video en
inglés con subtítulos + textos de inscripción) y `SLIDES.md` (9 slides listas para pegar).

**⚠️ Bug ya corregido:** `POST /api/escenario` (los sliders) devolvía **500** por un import
faltante. Ahora hay test que barre todos los GET y prueba ese POST.

**⚠️ El `leads.py` viejo (200–250/día, 8% "No Llame", 10 técnicos fijos) ya fue REARMADO**
al modelo real del §3. No hay que rearmar nada más.

### 🎨 Rebranding + sectores (17 oct) ✅ pusheado

Rama `main`, commits (todo verificado en su momento):

1. **Fase 0** (`b7004b4`) — portada nueva: header con la marca + ☰, **mapa real de CABA** (48
   barrios) a pantalla completa, **logo de Nexus** latiendo al centro, pie de simulación abajo.
   Se agregó `frontend/src/caba.js` y `scripts/build-caba-map.py` (el `ejemplo.png` de referencia
   se borró después, en la limpieza del 18 oct).
2. **Fase 0.5** (`793aead`) — **paleta nueva** (fondo `#060B1F`, panel `#0E1A44`, azul, violeta,
   cyan…) con Montserrat + Inter; el chevron "A" de la marca re-hecho como **SVG** (`Logo.jsx`).
3. **Fase 1** (`4642c77`) — los **4 sectores**. Menú ☰ con **solo** los sectores; cada uno tiene su
   informe del mes (`GET /api/sectores`, `/api/sectores/{id}`, `POST .../generar`,
   `/api/facturacion`). **Franja AMD** abajo siempre visible; **Sala de Agentes** dentro del
   cuadro de simulación.
4. **Fase 2 + docs** (`9b58a40`, `5f90750`) — `README.md` / `PITCH.md` / `SLIDES.md` al menú nuevo
   y al motor AMD real (se sacó "TokenFactory" de todo el código y la doc).
5. **Fix del modo día a día** (`72d8002`) — **bug real encontrado y corregido:** al correr día por
   día, el mes **nunca cerraba** → no había reunión del Gerente ni informes de sector. Ahora
   `correr_dia_completo()` replica el ciclo de `correr_mes`: reunión al **abrir** el mes, cierre
   (ingresos recurrentes, costos e informes) al **cerrarlo**. La inversión del mes se reconstruye
   de las decisiones ya guardadas (un reinicio a mitad de mes no duplica ni pierde nada). Test
   nuevo en `test_engine.py`. Números de los 9 meses **intactos**.

### 🌐 Bilingüe (ES/EN) + limpieza + Evolus afuera (sesión del 18 oct) ⏳ sin pushear

Todo verificado: **77 tests + 46 smoke en verde**. Cambios:

1. **Todo el sitio en INGLÉS** (base) + **botón ES/EN que cambia TODO** al español y vuelve.
   Arquitectura: `backend/idioma.py` (`t("English", "español")`) y `frontend/src/i18n.js`
   (mismo `t`). El backend guarda **una base por idioma**: `data/nexus.db` (inglés) y
   `data/nexus_es.db` (español); `POST /api/idioma` cambia la base y el idioma de una; si hay un
   día en vivo corriendo responde **409** (no corta la demo).
2. **Traducido a ambos idiomas** todo lo que se ve: `redactor.py` (informes de los 4 sectores),
   `sectores.py`, `facturas.py` (sello + comprobantes + auditoría), `calls.py` (motivos de fallo),
   `agenda.py`, `gerente.py` (actas y avisos), `llm/mock.py` (TODOS los diálogos de los agentes),
   `enjambre.py`, `simulation.py`, `api.py`, y todo el frontend (App, menú, paneles, película,
   mapa, sala de agentes, franja AMD). Números formateados según idioma: `1,234.5` (EN) /
   `1.234,5` (ES).
3. **Evolus eliminado del código.** Se borró `backend/evolus/`, `backend/tests/test_evolus.py`,
   `EVOLUS.md` y los docs viejos de `entrega/`. El **auditor de facturas se mantuvo por reglas**
   en `engine/facturas.py` con **21 tests** (`test_facturas.py`).
4. **Limpieza de paneles muertos del frontend**: se borraron 9 componentes que ya no se ofrecían
   (Kpis, Escenario, Evolucion, Acta, Llamadas, AgenteVivo, DetalleDia, MetricasAMD, Cabecera).
5. **⚠️ Bug de traducción corregido:** `gerente.py` mandaba `DIRECTIVE=` pero `mock.py` leía
   `DIRECTIVA=` → el Gerente IA de prueba **nunca leía su directiva**. Ahora `mock.py` lee
   `DIRECTIVE=`.
6. **⚠️ Bug del modo día a día** ya corregido en el commit `72d8002` (ver arriba).

> **Interruptor de la pantalla:** el menú ☰ muestra **solo los 4 sectores**. Si más adelante se
> quiere volver a ofrecer algún panel viejo, alcanza con agregarlo en
> `frontend/src/components/MenuLateral.jsx` (los componentes se borraron; habría que recuperarlos
> de git).

---

## 7. FASES DE CONSTRUCCIÓN

1. ✅ **Hecha:** estructura, cliente LLM mock, motor genérico, tests.
2. ✅ **Hecha:** Base de datos REAL (SQLite) de clientes ficticios (la que "leen" los operadores).
3. ✅ **Hecha:** 3 teleoperadores + registro de llamadas (log sintético) + motivos de fallo.
4. ✅ **Hecha:** Coordinador de agenda + mensajes operador↔coordinador + confirmación al cliente.
5. ✅ **Hecha:** Coordinador de técnicos (reparto calculado por programa, IA explica).
6. ✅ **Hecha:** Gerente IA + reuniones mensuales + crecimiento a 10 técnicos.
7. ✅ **Hecha:** Pantalla del dueño (KPIs, sliders, lead en vivo texto, mapa animado, métricas AMD).
8. ✅ **Hecha:** Simulación por meses (6 solos + 3 a mano, con guardado en SQLite).
9. 🟡 **EN CURSO →** Docker ✅ verificado el 14 oct (re-verificar tras abrir Docker Desktop) ·
   README que corra ✅ · **guion del video en inglés ✅ `PITCH.md`** · **slides ✅ `SLIDES.md`**.
   **Hecho en la sesión del 17 oct:** rebranding completo, 4 sectores con informes, franja AMD,
   fix del cierre mensual día a día. **Hecho el 18 oct:** todo el sitio en inglés + **botón ES/EN**
   que cambia TODO, Evolus eliminado (auditor de facturas por reglas), limpieza de paneles muertos
   (ver §6).
   **Faltan:** deploy final tras el push, grabar el video, subir todo al repo público.
   **Motor de AMD pendiente:** ver **§8** (checklist de retomada).

> **⏸️ RETOMADA.** El 14 oct el trabajo quedó pausado a propósito; el **17–18 oct** se avanzó todo
> lo que no dependía del autor (rebranding + sectores + **bilingüe ES/EN** + limpieza + Evolus
> afuera + fix). **No hay bugs abiertos: 77 tests + 46 smoke en verde.** Al volver, recorrer la
> checklist del §8 (lo que sí depende del autor) y después seguir.

### 📌 PENDIENTE DEL AUTOR (lo que NO puedo hacer yo)

1. **Abrir Docker Desktop** y correr `docker compose up --build` para re-verificar (esta sesión
   no lo pudo hacer porque el Docker estaba cerrado).
2. **`gh auth login`** (punto 2 del §8) → crear el repo **público** y pushear `main`. **Yo ya
   dejé `main` al día y pusheado a `origin`** (el remote ya existe).
3. **Claves / cuentas** (puntos 1 y 4 del §8): créditos AMD (GPU para Gemma) y cuentas de Render
   y Netlify.
   → Con esas claves, el cambio es **solo 3 variables de entorno** (`LLM_BASE_URL`, `LLM_MODEL`,
   `USE_MOCK=false`).
4. **Grabar el video** siguiendo `PITCH.md` (ya actualizado) y **armar los slides** con `SLIDES.md`.

**Recorte de emergencia si falta tiempo:** primero el mapa animado, luego extras. NUNCA recortar
AMD, el envío ni el README.

---

## 8. CHECKLIST DE RETOMADA — hacerla 1 a 1 ANTES de seguir desarrollando

> **⚠️ INSTRUCCIÓN PARA LA PRÓXIMA SESIÓN:** el autor pidió que, al volver, se recorra
> **esta lista completa punto por punto ANTES de escribir o modificar cualquier código.**
> NO empezar por tareas nuevas. Primero la lista, después se continúa.
> Trabajo **pausado a propósito** el 14 oct: no hay bug abierto, todo verde (77 tests + 46 smoke).

### 1. 🔴 AMD — créditos de Developer Cloud (es el freno de Gemma)
**Qué mira el autor:** la cuenta AMD con la que se anotó a la hackathon. Buscar en el **correo**
algo de "AMD AI Developer Program" / "AMD Developer Cloud"; en la **página del evento en
lablab.ai** (sponsors o aviso del 12 oct); y en el **Discord de anuncios**.
**Qué busca:** un número — puede aparecer como *créditos*, *saldo*, *$100* o *horas de GPU*.
Ojo con si le pide anotarse a un **"AMD AI League"** (otro participante reportó esa duda y
nadie contestó todavía).
**Qué devuelve:** el **texto exacto** que ve (o foto de pantalla). Si no ve nada → el
asistente le arma una pregunta en inglés para el Discord.
**Qué hace el asistente:** con el saldo, elegir la GPU; sin saldo, escalar por Discord.
**Contexto:** TokenFactory quedó descartado (email no habilitado). **El motor será Gemma en una
instancia GPU propia de AMD con vLLM.** El equipo de la hackathon confirmó en el Discord que los
agentes corren sobre *"your team's OpenAI-compatible endpoint (e.g. **vLLM on AMD Developer
Cloud**)"* → **nuestro plan es exactamente el camino que recomiendan**.
**Sin créditos no hay GPU → no hay Gemma.**
**Decisión ya tomada:** el autor **espera a que esté la GPU de Gemma**. Mientras tanto el
programa corre en **modo simulado** (`USE_MOCK=true`) y **NO** se cambia a ningún modelo
interino. **Frente si los créditos no aparecen:** modelo del catálogo gratis de Radeon Cloud
(corren en GPU de AMD, requisito cumplido) — **no cambiarlo sin preguntarle de nuevo**.
**Riesgo:** Gemma no está en el catálogo gratis; requiere instancia + créditos + mantenerla viva
el día de la demo. El cliente LLM **ya acepta cualquier endpoint compatible con OpenAI** (solo
cambian 3 variables de entorno).
**Ya preparado:** `backend/tests/probar_amd.py` verifica conexión real, latencia y **si el modelo
devuelve el JSON estructurado** que los agentes necesitan. El default de `LLM_BASE_URL` ya apunta
a Radeon Cloud; con la GPU solo se cambia a la URL de la instancia (p. ej. `/spaces/<id>/v1`).

### 2. 🔴 GitHub — `gh auth login` (bloquea la entrega del repo)
- **Qué hace el autor:** en una terminal de Windows correr
  `gh auth login --hostname github.com --git-protocol https --web`,
  pegar el código de 8 letras en el navegador y apretar **Authorize**.
- **Qué hace el asistente:** crear el repo **PÚBLICO** y pushear `main`.
- Su GitHub: **JoseMota0190**. Rama ya renombrada a `main` ✅.

### 3. ⚫ Evolus — ELIMINADO (evento cerrado)
El código de evento (`AMDACT3`) ya cerró y no se consiguió workspace → se **borró** el módulo
`backend/evolus/` y `EVOLUS.md`. El **auditor de facturas quedó, pero por reglas** (sin IA):
`backend/engine/facturas.py` (+21 tests en `test_facturas.py`). **No hay nada que hacer acá.**

### 4. 🟢 Hosting — Render + Netlify ✅ YA DEPLOYADO
- **Hecho (18 oct):** `https://nexus-ops-ai.netlify.app` + `https://nexus-ops-ai-backend.onrender.com`.
- **Falta (asistente):** el **push final**; Render y Netlify redeployan solos desde `main`.
  (Render lee `render.yaml`; Netlify usa `frontend/` con la URL del backend en `frontend/netlify.toml`.)

### 5. 🟡 Discord — preguntas todavía sin contestar
Ya mandó la consulta por el bloqueo de TokenFactory. **Faltan:**
- **Créditos de AMD** (ver punto 1): ¿reclamarlos dónde? ¿sirve el "AMD AI League"?
- **¿Radeon Cloud cuenta como "AMD"** para el requisito de elegibilidad?
- Hora exacta de **cierre domingo**.
- Permiso de **audio con voz clonada** en el video.

### 6. 🟢 Pendientes de más adelante
- **Grabar el video** siguiendo `PITCH.md` (inglés + subtítulos).
- **Desplegar Gemma con vLLM** cuando haya GPU → cambiar `LLM_BASE_URL` + `LLM_MODEL` +
  `USE_MOCK=false` → correr `backend/tests/probar_amd.py`.

---

## 9. Decisiones CERRADAS (NO volver a preguntar)

Empresa "Nexus Alarm" · proyecto nexus-ops-ai · Python/FastAPI + React · SQLite · MIT ·
**motor: Gemma servido por AMD** (TokenFactory descartado por bloqueo del email, 14 oct) ·
**esperar a la GPU de Gemma y NO usar modelo interino** (frente si no hay créditos: modelo
gratis del catálogo de Radeon Cloud, que corre sobre GPU de AMD) · **Evolus ELIMINADO (18 oct)**:
el evento cerró; el auditor de facturas **quedó por reglas** (Monte Carlo + detección, sin IA) ·
lead en vivo solo texto · **CON mapa animado**
(primer corte si falta tiempo) · **solo ARCA simulado, NO hay "No Llame"** (todos los leads son de
la web que pide ser llamado, sin llamada en frío) · 2 técnicos + 3 operadores arranque ·
10 técnicos meta mes 9 · lunes a sábados · 3 turnos (9am/12pm/4pm) · ventas semana siguiente ·
50 llamadas/operador/día (150 total, fluctúa) · 6 ventas/día arranque · reparto: programa
calcula + IA explica · gerente IA simulado · 6 meses solos + 3 manuales guardando · voz clonada
con fallback real, slides en inglés · solo fase online · hosting free tier ·
**repo PÚBLICO en GitHub + push autorizado** (renombrar `master` → `main` antes de subir) ·
**menú ☰ = solo los 4 sectores** (Management · Sales · Scheduling & technicians · Billing; los
paneles viejos se **borraron** en la limpieza del 18 oct) · **informe mensual de cada
sector = programa calcula → IA de AMD analiza → redactor local arma el documento** (los 6 meses
precargados se siembran con el redactor local, sin red ni créditos) · **sitio BILINGÜE: inglés por
defecto + botón ES/EN que cambia TODO** (una base SQLite por idioma; `POST /api/idioma`; los textos
viven en `backend/idioma.py` y `frontend/src/i18n.js`) · **franja AMD
al pie, siempre visible** · **Sala de Agentes dentro del cuadro de simulación** · **simulación
solo día a día** (el mes se cierra solo) · mapa CABA real de 48 barrios + logo al centro.

Plan completo y cronograma: `C:\Users\josem\.opencode\plan\nexus-ops-ai-plan.md`.
