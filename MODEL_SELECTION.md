# Selección de modelos de este proyecto

> Selección realizada para este proyecto. Queda guardada aquí.

- **Estado:** CONFIGURADA
- **Fecha de configuración:** 2026-10-27
- **Prioridad:** calidad
- **Fecha de revisión del catálogo:** 2026-10-27 (consultado vía tools.opencode.models)

## Modelos elegidos

- **Foreman:** openrouter/deepseek/deepseek-v4.1-flash-1017 (PAGO - $0.15/$0.6)
- **Implementer:** openrouter/cohere/north-mini-code:free (GRATUITO - $0/$0)
- **Reviewer:** openrouter/recursive/flint-v1.0:free (GRATUITO - $0/$0)
- **Config Helper:** openrouter/google/gemini-2.5-flash-image-preview:free (GRATUITO - $0/$0) — requisito obligatorio: endpoint gratuito vigente y entrada de imágenes confirmada; preferible soporte de herramientas.

## Verificación

- [x] Se revisó el catálogo actual de OpenRouter y se mostraron recomendaciones por rol.
- [x] Los precios/etiquetas FREE o PAGO se verificaron en las fichas actuales.
- [x] Los cuatro IDs elegidos aparecen en `/models`.
- [x] El modelo de Config Helper es gratuito y admite imágenes de entrada (seleccionado por usuario tras verificación en /models).
- [x] Se escribió `model:` en los cuatro archivos de agente.
- [ ] Se inició una sesión nueva después de configurar.

## Observaciones

- No guardar API keys ni otros secretos aquí.
- No copiar el listado de recomendaciones a este archivo: es dinámico y debe volver a consultarse si se piden recomendaciones.
- El precio, el límite, la cuota, el soporte de herramientas y las políticas de datos pueden cambiar.
- `FREE` significa precio cero confirmado en el endpoint seleccionado en la fecha de revisión; no garantiza disponibilidad, cuota ilimitada ni privacidad.
- Para el agente Config Helper, los mensajes que incluyen imágenes requieren un modelo compatible con imágenes. La configuración del agente no agrega visión a un modelo que no la tenga.
