# Guion de exposición de MESSI web

“MESSI es una plataforma de alerta y acompañamiento escolar. Su propósito es
conectar el registro de indicadores académicos con la solicitud de ayuda y el
seguimiento de los acuerdos de apoyo.

El sistema tiene un servidor central y una base de datos MySQL compartida.
Cada docente, estudiante y tutor entra desde su propio dispositivo mediante
una cuenta. El servidor conserva los registros; cada usuario tiene acceso
únicamente a la información que le corresponde.

Primero, el administrador crea los usuarios, grupos y asignaciones. El docente
registra la calificación del primer parcial, la asistencia y las tareas de sus
estudiantes. Puede capturarlas o importar un archivo de Excel o CSV.

El módulo de red neuronal analiza esos tres indicadores y genera una puntuación
demostrativa para que el docente y el tutor revisen el caso. Por ahora el modelo
está entrenado con datos sintéticos: no afirmamos que prediga con precisión el
resultado de alumnos reales ni que supere a otros métodos.

El estudiante puede pedir apoyo incluso sin una alerta. El tutor recibe su
solicitud, registra un acuerdo y agrega los avances. El estudiante consulta ese
acuerdo y su seguimiento, mientras que las notas privadas quedan restringidas
al tutor asignado.

La viabilidad se demuestra haciendo este recorrido con cuentas separadas sobre
los mismos registros. Publicarlo en internet requiere un alojamiento con HTTPS.
La aplicación y la configuración de despliegue ya están preparadas; la dirección
pública se presentará sólo cuando el sitio esté publicado y comprobado.”

## Recorrido de demostración

1. Docente: entrar → elegir grupo → guardar indicadores → calcular riesgo.
2. Estudiante: entrar desde otra sesión → enviar solicitud.
3. Tutor: entrar → abrir solicitud → registrar acuerdo → guardar seguimiento.
4. Estudiante: actualizar → mostrar acuerdo y avance. La nota interna no aparece.

En un equipo de ensayo, usa tres perfiles de navegador independientes. Para
demostrar uso desde dispositivos distintos, abre la URL del servidor desde los
equipos de la misma red o la dirección HTTPS pública cuando se haya desplegado.

## Respuestas breves

- **¿Por qué un servidor central?** Para que personas en equipos distintos
  consulten la misma información, con cuentas y permisos.
- **¿Por qué MySQL?** Para manejar la información compartida y las operaciones
  concurrentes dentro de esta arquitectura. Cambiar el motor por sí solo no
  proporciona cuentas ni permisos: esas funciones están en la aplicación.
- **¿Qué se verificó?** Permisos, sesiones separadas, cambios simultáneos, el
  flujo de apoyo y recuperación de datos mediante respaldo. Consulta
  `VALIDACION_WEB.md` para los resultados y límites.
- **¿Ya reduce costos?** Es un objetivo por medir. Una instalación central
  facilita el mantenimiento, pero el costo y la capacidad dependen del
  alojamiento y de las pruebas de carga.
