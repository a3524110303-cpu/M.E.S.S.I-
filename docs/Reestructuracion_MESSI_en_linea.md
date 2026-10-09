# Reestructuración de MESSI para uso en línea

Fecha: 9 de octubre de 2026.
Estado: propuesta de arquitectura y migración; no representa un despliegue realizado.

La primera implementación del portal ya está en `web/`. Para conocer las
funciones entregadas, cómo ejecutarlas y las verificaciones realizadas, consulta
`USO_WEB.md` y `VALIDACION_WEB.md`. Este documento conserva el diseño de
referencia; no todas sus etapas futuras están terminadas.

## Problema y objetivo

MESSI debe permitir que un docente registre indicadores desde su equipo, que un estudiante solicite apoyo desde otro y que un tutor consulte y atienda esos casos. Todos deben trabajar sobre registros compartidos, con identidad y permisos verificables.

La implementación actual es un prototipo local: app.py instancia SQLiteStore(database_path()) y la interfaz permite seleccionar el rol. El código EST identifica un registro, no autentica una persona. Instalar el programa en distintos equipos crea bases separadas. Existe MySQLStore, pero cambiar el motor no resuelve por sí mismo la identidad, las asignaciones ni la autorización.

Objetivo reformulado: plataforma web de detección y seguimiento de riesgo académico para una institución, con acceso remoto por cuenta, información compartida y trazabilidad del acompañamiento.

## Arquitectura propuesta

```text
Navegadores: docente, estudiante, tutor y administrador
                       |
                    HTTPS
                       |
          Aplicación web Python / Django
    cuentas y sesiones | permisos | formularios
    indicadores | alertas | solicitudes | seguimiento
                       |
               MySQL / InnoDB
                       |
             respaldos y restauración

La aplicación llama al módulo de inferencia MLP en el servidor.
El entrenamiento se ejecuta por separado; no se dispara al visitar una página.
```

Propuesta: una aplicación Django con páginas renderizadas en el servidor y MySQL. Evitar un frontend y API separados en la primera entrega reduce piezas que mantener. Django aporta cuentas, sesiones, grupos y permisos; el equipo debe implementar además filtros y autorización por registro. MySQL aprovecha la experiencia y el esquema que ya existen en el repositorio, aunque requieren ampliación.

El servidor puede ser una máquina dedicada o alojamiento remoto. Centralizar el servicio es compatible con acceso desde muchas computadoras. Los usuarios acceden por URL; no instalan Python, MySQL ni el modelo. La base recibe conexiones de la aplicación, no de los navegadores.

La instancia de evaluación en internet debe tener HTTPS, configuración de producción, secretos externos al repositorio y almacenamiento persistente. No publicar la interfaz actual con selector de roles como si ya tuviera autenticación.

## Módulos y alcance

| Módulo | Función |
| --- | --- |
| Cuentas | Inicio y cierre de sesión, recuperación de acceso, alta y desactivación por administrador. |
| Organización escolar | Periodos, materias, grupos, inscripciones y asignaciones de docentes y tutores. |
| Indicadores | Captura e importación validada de notas, asistencia y tareas por estudiante, materia y periodo. |
| Riesgo | Inferencia del modelo, versión y fecha del cálculo; alertas pendientes de revisión humana. |
| Solicitudes | Solicitud del estudiante autenticado sin exigir una alerta previa. |
| Acompañamiento | Responsable, acuerdos, próximas acciones, estado y seguimientos del caso. |
| Reportes | Consulta filtrada y exportación limitada al alcance del usuario. |
| Operación | Bitácora de cambios, respaldos, restauración y diagnóstico. |

Primera entrega: una institución, cuatro roles, registro académico, inferencia demostrativa y gestión de casos. Avisos dentro de la plataforma. Correo, integraciones institucionales y operación sin conexión quedan para etapas posteriores.

## Roles y reglas de acceso

| Rol | Acceso |
| --- | --- |
| Administrador | Cuentas, grupos, periodos y asignaciones; acceso a contenido sensible sólo si se define expresamente. |
| Docente | Indicadores y alertas de sus materias y grupos asignados. No consulta notas privadas de acompañamiento por defecto. |
| Estudiante | Sus indicadores autorizados, solicitudes, acuerdos visibles y estado del apoyo. |
| Tutor | Casos e información necesaria de sus estudiantes asignados. |

El rol proviene de la cuenta autenticada, nunca de un selector libre. El servidor verifica permisos en cada lectura, modificación, importación y exportación. Cambiar un ID o una URL no debe permitir consultar otro alumno. Los códigos escolares son identificadores, no contraseñas. Las notas internas y los acuerdos visibles deben tener campos separados.

## Modelo de datos

Usar migraciones versionadas. No adaptar el esquema con SQL manual en cada instalación.

| Entidad | Relaciones y restricciones principales |
| --- | --- |
| Usuario | Cuenta única, contraseña gestionada por Django, estado activo y grupos de permisos. |
| Estudiante | Usuario asociado y matrícula única dentro de la institución. |
| Periodo | Fechas y estado de captura. |
| Grupo / Materia | Organización del curso y vínculo con periodo. |
| Inscripción | Estudiante + grupo + materia + periodo; combinación única. |
| Asignación docente | Usuario docente vinculado al grupo/materia/periodo. |
| Asignación tutor | Usuario tutor vinculado al estudiante y periodo. |
| Indicador | Inscripción, corte académico, valores validados, autor y versión; registro único por inscripción/corte. |
| Predicción | Versión del indicador, versión del modelo, puntuación, umbral y fecha. |
| Alerta | Predicción origen, responsable, revisión y estado; evitar duplicados del mismo cálculo. |
| Solicitud | Estudiante autenticado, mensaje, fecha y estado. |
| Caso de apoyo | Estudiante, tutor, origen opcional en alerta o solicitud, acuerdo visible, nota interna y estado. |
| Seguimiento | Caso, autor, fecha, avance y siguiente acción. |
| Evento de auditoría | Autor, acción, entidad y fecha; no copiar contraseñas ni textos sensibles a los logs. |

Conservar claves foráneas y transacciones. Si cambia un indicador, marcar el cálculo anterior como desactualizado; conservarlo para trazabilidad. Evitar sobrescribir cambios concurrentes mediante versión del registro y aviso de conflicto. Para solicitudes importadas del prototipo conservar procedencia: no inventar un autor autenticado que antes no existía.

## Flujo de uso

1. El administrador crea cuentas, grupos y asignaciones.
2. El docente inicia sesión desde su dispositivo, elige un grupo autorizado y registra o importa indicadores.
3. La aplicación valida los datos, muestra errores por fila y confirma lo guardado en la base compartida.
4. Al calcular riesgo, el servidor usa el modelo y guarda la versión de los indicadores y del modelo.
5. El tutor consulta alertas de sus estudiantes, revisa cada situación y abre o vincula un caso.
6. El estudiante inicia sesión desde otro dispositivo y puede enviar una solicitud directamente.
7. El tutor registra acuerdos y seguimiento. El estudiante ve la parte que se haya definido como visible.
8. Los usuarios vuelven a entrar y encuentran los mismos registros persistentes.

## Red neuronal y evaluación

Se puede conservar el MLP actual como componente demostrativo, separado de la gestión escolar. Se reutilizan validación de datos e inferencia; la interfaz Streamlit queda como demostración previa y referencia del flujo.

El modelo actual usa tres entradas y ocho neuronas ocultas, entrenado con datos sintéticos. Sus resultados actuales no prueban superioridad: en la prueba sintética obtuvo 68.75 % de exactitud frente a 87.5 % de la regla de nota menor a seis y 100 % de la regresión logística. Esto tampoco acredita rendimiento de esos métodos con alumnos reales.

La plataforma debe seguir funcionando si no se dispone del modelo: solicitudes y seguimiento continúan, y el sistema informa que no pudo calcular riesgo. Las alertas no determinan automáticamente sanciones ni decisiones académicas.

Para evaluar utilidad real: definir el resultado a predecir y el momento de predicción; obtener datos autorizados; separar entrenamiento y evaluación evitando que registros de un mismo alumno se filtren entre conjuntos; comparar con reglas simples; evaluar falsos positivos, falsos negativos y calibración antes de interpretar puntuaciones como probabilidades. Medir también atención y seguimiento de los casos, no sólo exactitud del modelo.

## Migración por entregas

1. Mantener el prototipo y respaldar los registros existentes. Crear la nueva aplicación web en una rama de trabajo.
2. Implementar cuentas, estructura escolar y autorización por asignación; probarla antes de conectar las pantallas académicas.
3. Crear esquema MySQL mediante migraciones; portar captura, solicitudes y seguimiento usando servicios con permisos. Tomar MySQLStore como referencia de operaciones, sin asumir que el adaptador ya resuelve la aplicación web.
4. Incorporar el módulo de inferencia y persistir versiones y estado de revisión.
5. Migrar únicamente los registros necesarios con mapeo revisado de códigos, periodos y responsables. No convertir ejemplos sintéticos en expedientes reales.
6. Desplegar la instancia de evaluación y probar el recorrido desde equipos distintos; comprobar respaldos y restauración.
7. Actualizar README, manuales y guion para reflejar el comportamiento implementado. Retirar afirmaciones de uso institucional que sólo correspondan a funciones planeadas.

No hay un plazo, proveedor ni costo aprobado. Elegir alojamiento y presupuesto después de definir usuarios esperados, concurrencia, disponibilidad y volumen; no afirmar ahorro antes de medir.

## Criterios de aceptación

- Un docente guarda indicadores desde el equipo A y el tutor autorizado los consulta desde el equipo B, con cuentas distintas.
- Un estudiante desde el equipo C envía una solicitud que llega al tutor asignado.
- Una cuenta sin sesión o sin asignación no accede al registro, incluso cambiando URL, identificador o parámetros de exportación.
- Un docente no modifica grupos ajenos; un estudiante no lee expedientes de otros; un tutor no consulta alumnos no asignados.
- Dos ediciones del mismo registro detectan el conflicto y no pierden silenciosamente información.
- Reiniciar el servicio conserva los datos. Restaurar un respaldo recupera registros y relaciones verificadas.
- Cambiar indicadores deja visible que la predicción previa está desactualizada.
- La ausencia del modelo no impide solicitar o registrar apoyo.
- El despliegue usa HTTPS y configuración de producción; usuarios finales no requieren instalar dependencias.
- Se mide latencia, errores y uso de CPU/RAM bajo una carga acordada. El número de usuarios concurrentes soportados se reporta sólo después de probarlo.

## Argumento de viabilidad y recursos

El proyecto tiene utilidad si permite coordinar personas distribuidas y verificar que los casos reciben atención. La instalación local inicial acredita el flujo de una demostración; no acredita todavía acceso institucional compartido.

Optimización de recursos se reformula como un objetivo medible: una instalación mantenida centralmente, navegador como cliente, inferencia pequeña en servidor, entrenamiento fuera de las peticiones, consultas paginadas y cálculos sólo al cambiar indicadores o solicitarlos. Medir costo total de alojamiento, tiempo de mantenimiento, latencia y capacidad concurrente; el acceso web por sí mismo no garantiza ahorro.

SQLite es válido para prototipos y puede servir a sitios web. Su presencia no demuestra inviabilidad. Para esta propuesta se elige MySQL por el manejo central de transacciones y escrituras concurrentes y la base de trabajo existente. El cambio decisivo es la arquitectura compartida con identidad y autorización.

## Fuentes técnicas

- SQLite, usos apropiados y concurrencia: https://www.sqlite.org/whentouse.html
- Django, cuentas, sesiones y permisos: https://docs.djangoproject.com/en/5.2/topics/auth/
- MySQL, transacciones y capacidades de InnoDB: https://dev.mysql.com/doc/refman/8.4/en/innodb-introduction.html
