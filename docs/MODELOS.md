# Cómo elegir modelos para cada agente

Esta plantilla no contiene modelos preseleccionados ni guarda un top 10 fijo. Los modelos y precios cambian; el listado se prepara con datos actuales de OpenRouter cuando se configura cada copia del proyecto.

## Fuentes actuales que debe consultar Foreman

- Catálogo/uso en programación: https://openrouter.ai/collections/programming
- Modelos gratuitos: https://openrouter.ai/collections/free-models
- Modelos con visión: https://openrouter.ai/collections/vision-models
- Catálogo de gratuitos que reciben imágenes: https://openrouter.ai/models?fmt=cards&input_modalities=image&output_modalities=text&q=free
- Todos los modelos: https://openrouter.ai/models

Usar búsquedas y fichas oficiales actuales, indicar la fecha de consulta y verificar la variante exacta. Las clasificaciones de uso ayudan a descubrir candidatos, pero no equivalen a una prueba objetiva de calidad.

## Requisito: diez opciones por rol

Cuando el usuario pregunte qué modelos puede asignar, y durante la configuración inicial si aún no eligió modelos, mostrar una lista de hasta diez candidatos fuertes para CADA rol antes de pedirle que elija. Si se pueden verificar diez que cumplan los criterios, mostrar diez. Si no hay diez candidatos apropiados/verificables, mostrar todos los que sí los cumplan y explicar por qué hay menos; nunca inventar datos ni degradar los criterios solo para completar diez.

Cada fila debe mostrar:

1. Número/posición y nombre.
2. ID exacto de OpenRouter.
3. Estado **FREE** o **PAGO**, confirmado en la ficha actual.
4. Precio de entrada y salida por millón de tokens en USD, si se publica.
5. Capacidad de llamadas a herramientas (confirmada / no confirmada).
6. Capacidad de imagen cuando sea necesaria.
7. Una razón corta por la que encaja en ese rol.

Un modelo es FREE solo si la ficha del endpoint elegido confirma coste cero para entrada y salida. Si hay una variante con `:free`, comprobar esa variante exacta. Distinguir modelos concretos del router `openrouter/free`, que selecciona dinámicamente entre endpoints gratuitos compatibles.

Al final, pide al usuario escoger el ID exacto disponible en `/models`. El ID de la ficha web debe coincidir con el selector de OpenCode; la ficha web por sí sola no prueba que la versión o proveedor esté disponible en su cuenta.

## Criterios por rol

### Foreman — coordinador

- Planificación de varios pasos, seguimiento de instrucciones, razonamiento y síntesis.
- Uso fiable de herramientas y capacidad para coordinar resultados de subagentes.
- Contexto suficiente y precio manejable para 50–60 mensajes diarios u otras conversaciones frecuentes.
- Equilibrar calidad, latencia y costo; no asumir que el modelo más caro es siempre el mejor.

### Implementer — ejecutor de código

- Programación, depuración, cambios de varios archivos y generación de pruebas.
- Buen tool calling, uso de terminal, seguimiento estricto de alcance y criterios de aceptación.
- Relación costo/calidad; distinguir los modelos gratuitos con límites de proveedor.

### Reviewer — revisor independiente

- Encontrar bugs, regresiones, riesgos de seguridad, problemas de datos, casos límite y pruebas faltantes.
- Razonamiento cuidadoso y capacidad para trabajar de forma independiente al Implementer.
- Mantener `edit: deny` sin importar el modelo elegido.

### Config Helper — soporte y visión

- **Solo endpoints gratuitos vigentes**; este requisito no se negocia.
- **Entrada de imágenes confirmada**, de modo que pueda interpretar capturas de pantalla, imágenes de errores y diagramas adjuntos.
- Priorizar modelos con tool calling para poder investigar archivos y documentación; marcar claramente si esa capacidad está por verificar o no disponible.
- Buen desempeño en diagnóstico técnico, explicación de errores y lectura de configuración.
- No sugerirlo para imágenes si solo admite texto. Si hay menos de diez candidatos gratuitos que reciban imágenes y sean apropiados para un agente conversacional, mostrar los disponibles y explicar la limitación.

## Flujo de selección

1. Foreman lee `MODEL_SELECTION.md`. Si `Estado` es `PENDIENTE`, detiene la implementación del producto.
2. Foreman consulta las fuentes actuales y prepara cuatro tablas de opciones, una por rol, con estado FREE/PAGO visible. Las opciones de Config Helper deben ser gratuitas y multimodales con imágenes.
3. Pregunta si la prioridad general es costo mínimo, calidad, gratuidad, privacidad o equilibrio; después solicita los cuatro IDs elegidos. El usuario puede repetir el mismo modelo para varios roles, excepto que Config Helper debe seguir cumpliendo gratuidad y visión.
4. Antes de guardar, confirma que los IDs elegidos aparecen en `/models`; si no, solicita una alternativa. No pide la API key.
5. Escribe el campo `model:` en los cuatro archivos `.opencode/agents/*.md` y completa `MODEL_SELECTION.md`, con IDs y fecha de consulta.
6. Marca `CONFIGURADA` únicamente si los cuatro agentes están definidos y el modelo Config Helper cumple sus dos requisitos.
7. Pide abrir una sesión nueva/reiniciar OpenCode para recargar los agentes.
8. En sesiones posteriores, no vuelvas a hacer las preguntas si la selección sigue completa y coincide. Solo repite el proceso cuando el usuario lo pida, la selección esté incompleta o un modelo configurado no esté disponible.

## Privacidad y límites

- Un endpoint gratuito puede registrar peticiones o usarlas para mejorar modelos; comprobar la ficha y la política del proveedor antes de enviar datos.
- No adjuntar capturas con API keys, cookies, tokens, contraseñas, datos personales ni secretos del proyecto. Recortar o difuminar esos campos antes de enviar imágenes.
- Si no hay acceso a fuentes actuales, reconocer la limitación. No presentar listas de meses anteriores como si fueran actuales.
