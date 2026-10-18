# PASOS A · B · C — para hacer vos, paso por paso

> Todo en criollo. Cada paso dice **qué hacés** y **qué deberías ver**.
> Si algo no coincide con lo esperado, parás y me avisás.

---

# 🅰️ PASO A — Docker (el respaldo que corre en tu compu)

**Qué es:** hace que la app corra "en cajitas" (contenedores) igual que en un servidor,
sin depender de nada instalado. Es un requisito de la entrega.

### A.1 — Abrí Docker Desktop
1. Buscá en Windows **Docker Desktop** y abrilo (doble clic).
2. **Esperá.** Abajo a la izquierda tiene que decir **`Engine running`** (verde).
   - Puede tardar **hasta 10 minutos** la primera vez. No hagas nada, esperá.
3. Si dice `Starting...`, seguí esperando hasta que diga **`Engine running`**.

### A.2 — Decime "Docker listo"
- **Escribime `Docker listo`** en el chat y **yo corro el comando** y verifico todo.
- (El comando es `docker compose up --build`. Lo corro yo para mirar la salida y avisarte
  si algo falla. No necesitás tipear nada.)

### ✅ Qué debería pasar (yo te lo confirmo)
- Baja y arma las imágenes (unos minutos la primera vez).
- Levanta 2 cajitas: **backend** y **frontend**.
- Siembra los 6 meses y responde.
- Vos podés abrir: **http://localhost:8080** (la pantalla) y **http://localhost:8000/api/estado**.
- Para apagarlo después: en Docker Desktop, botón **Stop**; o yo corro `docker compose down`.

> **Nota:** el `.env` ya tiene `USE_MOCK=false` y la clave de AMD, así que **Docker también
> usa Gemma de verdad**. Si preferís no gastar créditos durante la prueba, avisame y lo pongo
> en modo prueba.

---

# 🅱️ PASO B — Netlify (que el sitio online quede con lo último)

**Qué es:** el sitio online funciona, pero quedó con una versión vieja. Con 3 clics lo
actualizamos. **No es obligatorio**, pero es gratis y recomendable.

1. Entrá a **https://app.netlify.com** con tu cuenta.
2. Elegí el sitio **`nexus-ops-ai`**.
3. Arriba, tocá la pestaña **`Deploys`**.
4. A la derecha, botón **`Trigger deploy`** → elegí **`Clear cache and deploy site`**.
5. **Esperá** ~1–2 minutos. Vas a ver una barra "Building" y después **`Published`**.

### ✅ Qué debería pasar
- El renglón más de arriba queda en **`Published`** con la hora de ahora.
- Recargá **https://nexus-ops-ai.netlify.app** → sigue andando igual.
- **Yo verifico** después que respondió bien y te confirmo.

### ⚠️ Si algo falla
- Netlify **no borra** la versión anterior si algo sale mal: si queda en **`Failed`**,
  el sitio **sigue online** con lo viejo. Avisame y lo miramos.

---

# 🅲 PASO C — Video + Slides

## C.1 — Exportar los slides a PDF (2 minutos)
1. Abrí la carpeta del proyecto y entrá a **`entrega`**.
2. **Doble clic** en **`slides.html`** → se abre en el navegador (se ven las 9 diapositivas).
3. Apretá **Ctrl + P** (Imprimir).
4. En "Destino" (arriba), elegí **`Guardar como PDF`**.
5. En "Diseño", elegí **`Horizontal`** (landscape).
6. En "Márgenes", elegí **`Ninguno`**.
7. Marcá **`Gráficos de fondo`** (importante, si no sale sin colores).
8. Botón **Guardar** → guardalo como **`nexus-ops-ai-slides.pdf`**.

✅ Deberías obtener un PDF de **9 páginas horizontales** con fondo azul oscuro.

## C.2 — Grabar el video (~2:50)
1. Abrí el sitio online: **https://nexus-ops-ai.netlify.app**
2. Prepará la grabación: apretá **Windows + G** (Game Bar, ya viene en Windows) y tocá
   el botón de **grabar**. (Alternativa: OBS si lo tenés.)
3. Seguí el guion de **`PITCH.md`**, escena por escena (está en inglés con subtítulos listos).
4. **Tip para que se vea AMD "pensando" de verdad:** en el sitio, avanzá hasta el **Mes 7**
   y apretá **▶ Correr un día**. Ahí la Sala de Agentes negocia en vivo con el modelo.
5. Objetivo: **~2 minutos 50 segundos**. Si te pasás, recortá la Escena 3.
6. Guardá el archivo como **`nexus-ops-ai-demo.mp4`**.

### ✅ Checklist antes de dar por cerrado el video
- [ ] Se ve el **mapa de Buenos Aires** y el logo latiendo.
- [ ] Se ve la **franja AMD** abajo (latencia/tokens).
- [ ] Se ve el **menú ☰** con los 4 sectores y un informe mensual.
- [ ] Se menciona que **el motor corre en AMD**.

## C.3 — El cover
- Ya está hecho: **`entrega/cover.png`** (1200×630). No hay que hacer nada.

---

# 📮 Después: llenar el formulario
- Los textos exactos (título, descripción corta/larga, tags) están en **`entrega/ENTREGA.md`**.
- Hay que subir: **video**, **slides PDF**, **cover**, **repo** y **Application URL**
  (`https://nexus-ops-ai.netlify.app`).
