# Prompt de inicio para cada proyecto

Leé `MODEL_SELECTION.md` antes de planificar o tocar el producto.

- Si el estado es `PENDIENTE` o falta un rol, todavía no implementes ni delegues trabajo del producto. Consultá el catálogo actual de OpenRouter y prepará recomendaciones para los cuatro roles: Foreman, Implementer, Reviewer y Config Helper.
- Para cada rol, sugerí diez candidatos fuertes cuando existan diez opciones verificadas. Mostrá nombre, ID exacto, `FREE`/`PAGO`, precio de entrada/salida por millón de tokens (si está publicado), soporte de herramientas y razón breve. Si hay menos de diez que cumplan, muestra todos los verificados y explica por qué.
- Para Config Helper, acepta únicamente un endpoint gratuito vigente y con entrada de imágenes confirmada; prioriza tool calling. Nunca lo configures con un modelo de texto que no admita imágenes.
- Preguntá la prioridad general (costo mínimo, calidad, gratuidad, privacidad o equilibrio) y después solicitá los cuatro IDs exactos que aparecen en `/models`. Verificá IDs y datos con el catálogo actual. No inventes disponibilidad ni pidas la API key.
- Cuando el usuario confirme, poné `model: <ID exacto>` en el frontmatter de los cuatro archivos de agentes, registrá IDs, fecha y verificaciones en `MODEL_SELECTION.md`, marca `CONFIGURADA` y pedí iniciar una sesión nueva para recargar agentes.
- Si `MODEL_SELECTION.md` ya está `CONFIGURADA` y los cuatro IDs coinciden con los cuatro archivos, no repitas la selección cada vez que se abre el proyecto. Solo reabre el paso si un ID está ausente/no disponible o el usuario pide cambiarlo.

Luego lee `AGENTS.md`, `PLAN.md`, `TASKS.md` y `DECISIONS.md`. Inspeccioná el repositorio progresivamente y documentá solo hechos comprobados: objetivo, funciones existentes, tecnologías, estructura, comandos de ejecución/pruebas/lint/build, estado Git y riesgos.

No modifiques el código del producto durante el diagnóstico inicial. Actualizá las fichas usando evidencia real, propone un MVP con fases, tareas, dependencias, responsables, áreas de archivos, criterios de aceptación y pruebas. Indica qué tareas podrían hacerse en paralelo sin conflicto. Espera la aprobación del usuario antes de comenzar cambios de alcance importante.

Si no tenés acceso a búsquedas actuales, indicalo y pedí los datos de `/models`; no inventes un top 10. Para datos de modelos, usa `docs/MODELOS.md`.
