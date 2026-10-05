# Bitácora de prompts de Marco

Proyecto MESSI. Registros del 5 de octubre de 2026, America/Mexico_City.

Responsable: Marco Antonio Osorio Hernandez. Herramienta utilizada: Codex. Este registro documenta solicitudes reales de esta sesión y su uso; deberá consolidarse con los registros existentes del equipo. No se atribuyen aportaciones a otros integrantes.

## Revisión de aportaciones

**Prompt:** «rtomemos el poyecto d cesar, revisa que es lo que ya hecho cada integrante deel equipo y verifica que ya lo hayan hecho».

**Resultado:** se contrastaron tareas, ramas, historial, PR, archivos y evidencias. Se localizaron aportaciones de Marco, Ismael y Víctor. Se repitieron 59 pruebas, con 58 aprobadas y un fallo esperado. Se reprodujo el entrenamiento y la predicción con datos sintéticos. Se identificaron pendientes de interfaz, documentos, interpretación del entrenamiento y evidencia de Yokio y Salomón.

**Uso:** diagnóstico para decidir las correcciones de integración y mantener separado lo comprobado de lo declarado. La ausencia de archivos no se interpretó como prueba de que un compañero no hubiera trabajado fuera del repositorio.

## Corrección e integración

**Prompt:** «ok entonces corrige mi parte y sube los cambios en base a los errores que hayan salido».

**Resultado:** se integraron las contribuciones ya publicadas de Ismael y Víctor con los cambios locales de MySQL. Se corrigió la confirmación de seguimiento, la conservación de formularios inválidos y los avisos de ancho de tablas. Se adaptaron las pruebas de interacción al contrato de almacenamiento y se añadió comprobación MySQL real en CI. Se actualizaron documento 01, README, estado y evidencia de integración.

**Verificación:** 138 pruebas aprobadas en Windows con Python 3.13.13 y servidor MySQL 8.0.42 aislado; pip check sin incompatibilidades y compilación de Python sin errores. La conexión habitual de .env rechazó el acceso; se conserva como pendiente local explícito.

**Reflexión:** la asistencia de IA produjo cambios y documentación que requieren comprensión del responsable. Una ejecución verde con un fallo esperado no acredita la corrección de ese defecto; ahora la prueba de confirmación debe aprobar normalmente. Las métricas sintéticas tampoco acreditan eficacia escolar. El uso de una base aislada permite verificar la persistencia sin modificar los registros habituales.

El prompt inicial de preparación del esqueleto queda excluido de esta bitácora conforme a la indicación del equipo. No se reconstruyen ni inventan prompts de sesiones anteriores.
