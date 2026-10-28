# Prompt para delegar una funcionalidad

Foreman: implementemos la tarea [ID]. Antes de delegarla, confirma su objetivo, criterios de aceptación, dependencias y archivos afectados usando `TASKS.md` y el código existente. Si requiere decisiones de alcance o arquitectura, pregúntame primero.

Delega la implementación a `implementer` con instrucciones concretas. Cuando termine, verifica su informe y solicita una revisión independiente a `reviewer`. No ejecutes dos implementaciones sobre los mismos archivos en paralelo. Si falla, permite un ciclo de corrección acotado y, si sigue bloqueada, registra el motivo y consulta la decisión que falta.

Actualiza `TASKS.md` con la evidencia real. No marques la tarea como completada hasta que los criterios de aceptación y las pruebas relevantes estén verificados. Resume qué cambió, qué pruebas se ejecutaron, los riesgos restantes y el próximo paso.
