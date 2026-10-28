# El equipo multiagente que construyó Nexus Alarm

> Documentación de **proceso**, no del producto. El README del producto está en
> la raíz. Esto explica cómo se trabajó el código, no cómo funciona el sistema.

## Equipo

| Agente | Función | Modelo |
|---|---|---|
| Foreman | Coordina, planifica, delega, mantiene el estado e informa avances | Se elige al inicializar el proyecto; priorizar razonamiento, herramientas y costo razonable |
| Implementer | Implementa tareas acotadas y ejecuta pruebas | Se elige al inicializar; priorizar coding y tool calling |
| Reviewer | Audita cambios y devuelve hallazgos | Se elige al inicializar; lectura solamente |
| Config Helper | Soporte técnico de OpenCode/OpenRouter, errores, configuración y capturas | **Debe ser FREE y aceptar imágenes de entrada**; preferible tool calling |

## Archivos de la configuración

- `opencode.json`: selecciona Foreman como agente predeterminado y define permisos generales; no fija modelos.
- `.opencode/agents/foreman.md`: mandato del coordinador, selección de modelos y delegación.
- `.opencode/agents/implementer.md`: mandato del ejecutor.
- `.opencode/agents/reviewer.md`: mandato del revisor de solo lectura.
- `.opencode/agents/config-helper.md`: soporte técnico; analiza imágenes solo si el modelo asignado tiene visión.
- `AGENTS.md`: reglas generales y normas del equipo.
- `MODEL_SELECTION.md`: guarda los modelos elegidos para este proyecto.
- `PLAN.md`: objetivo, alcance, fases y decisiones de producto.
- `TASKS.md`: tareas, estado, responsables, criterios y evidencia.
- `DECISIONS.md`: decisiones técnicas importantes.

## Cómo se trabaja

1. Se acuerda el plan para cambios importantes antes de tocar código.
2. Foreman delega tareas concretas en `implementer`.
3. Los cambios importantes pasan por `reviewer`, que nunca edita archivos.
4. `@config-helper` se usa para problemas de configuración, errores de entorno o capturas de pantalla.
5. Foreman informa el estado desde `TASKS.md` y distingue una tarea anotada como activa de una sesión que realmente sigue corriendo.
6. Se revisa el diff y las pruebas antes de aceptar un resultado.

## Reglas que se sostienen

- No hay dos implementaciones concurrentes sobre los mismos archivos.
- El revisor tiene `edit: deny`; conserva ese permiso incluso si cambia su modelo.
- Una tarea se marca `DONE` solo con evidencia comprobada, nunca por el informe de un agente.
- Las tareas bloqueadas registran motivo, intento realizado y qué decisión hace falta.

## Nota sobre modelos y costos

Las sugerencias no están codificadas: Foreman consulta el catálogo actual de
OpenRouter cuando hay que seleccionar modelos. La popularidad es una señal, no
una prueba de calidad. Precios, cuotas, modelos gratuitos, soporte de
herramientas y políticas de privacidad cambian.

## Seguridad

- No se guardan claves API, tokens, contraseñas, cookies ni datos personales en el repositorio.
- Los comandos de terminal requieren aprobación de forma predeterminada.
- No se despliega, borra, commitea ni hace push sin autorización explícita.
- Los endpoints gratuitos pueden registrar entradas y salidas o usarlas para mejorar modelos.
