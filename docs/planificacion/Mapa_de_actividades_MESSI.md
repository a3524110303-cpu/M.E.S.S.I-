# Mapa de actividades MESSI Primera entrega

Fecha de preparación 3 de octubre de 2026; reparto actualizado el 5 de octubre de 2026. Proyecto MESSI Alerta y acompañamiento escolar.

El reparto organiza las responsabilidades principales para cerrar la primera entrega, con ocho horas orientativas por integrante. Todos pueden aportar código; cada autor revisa y comprueba sus cambios. Marco coordina la integración y las correcciones, Víctor valida y Salomón concentra la documentación. Ismael conserva datos y modelo, y Yokio la demostración. Las actividades indican el trabajo y la evidencia esperados; su asignación no acredita que estén terminados.

## Roles y carga propuesta

| Integrante | Rol acordado | Próximo aporte técnico | Esfuerzo |
| --- | --- | --- | --- |
| Marco Antonio Osorio Hernandez | Líder técnico y desarrollador | Integración, persistencia y correcciones QA-03 a QA-05 | 8 h |
| Ismael Hernández Jiménez | Investigador y analista | Normalización de datos crudos, Excel y modelo de demostración | 8 h |
| Víctor Manuel Jiménez Suárez | QA y pruebas | Equivalencia de entradas, validaciones, alertas y errores | 8 h |
| Yokio Yosafat Vazquez Carrillo | Vocero principal | Plantilla docente y demostración sin lenguaje técnico | 8 h |
| Salomón Alvarez Gomez | Documentación | Guía de uso, instrucciones y capturas comprobadas | 8 h |

## Cómo mantener un reparto justo

Las ocho horas de cada persona se reparten en cuatro de preparación de su entregable, dos de comprobación y dos de documentación y revisión. En el caso de Salomón, corresponden a elaborar la guía, comprobar sus instrucciones y revisar el material de demostración. Son estimaciones de esfuerzo, no fechas ni compromisos de disponibilidad. La coordinación, la exposición y las pruebas cuentan como trabajo; el número de commits no mide por sí solo la aportación.

Si una tarea supera la estimación o queda bloqueada, Marco facilita su división con el responsable. El equipo acuerda el traslado de trabajo y registra la nueva carga. La función secundaria de cada integrante es la revisión cruzada asignada más adelante; este apoyo conserva los roles acordados y no supone aptitudes que no se han evaluado.

## Punto de partida

El usuario reporta preparados el documento 01 y la bitácora 06. Se conservan como referencias. El cierre de la primera entrega todavía exige comprobar el prototipo, instalar y verificar dependencias, publicar el trabajo acordado y reunir contribuciones reales de los cinco integrantes. Este mensaje de arranque no se agrega a la bitácora.


## Próximas sesiones y dependencias

La fecha acordada de entrega es el 5 de octubre de 2026 durante la clase. Las sesiones siguientes describen la secuencia de trabajo propuesta; su duración puede repartirse en varios encuentros o trabajo individual. Cada tarea comienza cuando estén disponibles sus entradas.

| Sesión | Trabajo y condición de avance | Carga por persona |
| --- | --- | --- |
| 1 | Revisar el esqueleto, acordar formatos de ingreso y criterios de la entrega. Cada integrante confirma su tarea y acceso al repositorio. | 1 h |
| 2 | Construir los módulos en paralelo. Captura, CSV, Excel y datos crudos siguen un contrato común; Marco conecta modelo y almacenamiento. | 3 h |
| 3 | Ejecutar casos normales, inválidos y sin modelo. Corregir los fallos detectados y guardar evidencia real. | 2 h |
| 4 | Revisión cruzada, README, demostración y cierre. Publicar cambios acordados con la autoría de quien los realizó. | 2 h |

## Contrato técnico de la primera versión

- Aplicación local en navegador con Python 3.13 y Streamlit; pandas para datos, openpyxl 3.1.5 para Excel, scikit-learn para la red MLP y MySQL para estudiantes, indicadores, predicciones, solicitudes, apoyos y seguimiento. SQLite se conserva como almacenamiento legado para migración y pruebas. Las versiones instaladas y comprobadas se documentarán en el README.
- La conexión MySQL se configura mediante las variables MESSI_MYSQL_HOST, MESSI_MYSQL_PORT, MESSI_MYSQL_USER, MESSI_MYSQL_PASSWORD y MESSI_MYSQL_DATABASE en un .env local excluido de Git. La aplicación usa una cuenta limitada; la creación del esquema y la migración desde SQLite son operaciones explícitas. Procedimiento: [Base de datos](../base_de_datos.md). El servicio iniciado y las pruebas simuladas no acreditan una conexión real ni una migración completada.
- Inicialmente todos pueden usar la base mediante la cuenta configurada de la aplicación. El administrador conserva el control de cuentas MySQL y puede asignar lectura, edición o bloqueo con scripts/manage_mysql_users.py. El selector de roles de la interfaz sigue siendo una demostración, sin autenticación individual.
- Ingreso docente mediante captura directa, pegado desde Excel, CSV o archivo XLSX. El formato XLS clásico se exporta a XLSX antes de cargarlo. Plantilla docente: data/synthetic/Plantilla_MESSI.xlsx. Las pantallas explican el ingreso con lenguaje sencillo.
- Contrato interno de predicción: id_estudiante, nota_parcial, asistencia y tareas_entregadas. La nota va de 0 a 10; asistencia y tareas son porcentajes de 0 a 100. CSV, XLSX y pegado usan esas cuatro columnas con valores, sin fórmulas. El ID es seudónimo y único.
- La captura directa admite conteos de sesiones asistidas e impartidas y tareas entregadas y solicitadas. record_from_counts en data.py convierte a porcentajes: el total debe superar cero y la cantidad no puede superar el total. No se promete carga de un esquema de conteos desde Excel.
- En data.py, load_csv, load_excel y load_pasted comparten validate_records. Las cuatro vías de ingreso convergen en el mismo contrato y rechazan datos inconsistentes con mensajes que indican qué corregir.
- resultado_final se usa únicamente en entrenamiento: 1 significa reprobado y 0 aprobado. El identificador, la discapacidad y el contexto sensible no son entradas del modelo; sólo se usan los tres indicadores académicos.
- La MLP inicial tiene una capa oculta de ocho neuronas. La demostración usa datos sintéticos; las métricas de esos datos no demuestran eficacia escolar. La alerta requiere revisión humana y el umbral continúa sujeto a validación.
- Solicitar ayuda, registrar un apoyo y dar seguimiento deben funcionar aunque no se haya entrenado o instalado el modelo. Las vistas del prototipo y el alcance de su control de acceso deben explicarse con precisión.

## Orden de desbloqueo

E1 T04 define el contrato de datos. E1 T01 y E1 T13 pueden avanzar con ese acuerdo. E1 T07 y E1 T10 preparan casos a partir del contrato y verifican el sistema integrado cuando esté disponible. E1 T02, T05, T08, T11 y T14 registran resultados; las revisiones T03, T06, T09, T12 y T15 permiten el cierre.


## Actividades de Marco e Ismael

Marco mantiene la integración técnica y apoya la persistencia. Ismael mantiene la investigación, el análisis del caso y los datos. Ambos comparten la preparación del manual del programador para la segunda entrega.

### E1 T01 Integración y persistencia

**Asignación** Responsable Marco. Esfuerzo 4 h. Prioridad P0. Depende de Contrato E1 T04 y estructura inicial.

Integrar captura, pegado, CSV y XLSX con el contrato común de datos, evaluación opcional y vistas; completar MySQL para estudiantes, indicadores, predicciones, solicitudes, apoyos y seguimiento. Preparar configuración local, inicialización explícita del esquema y migración opcional del SQLite anterior de MESSI. Marco atiende las correcciones QA-03 a QA-05 reportadas por Víctor y coordina los cambios de código de todos los integrantes.

**Evidencia** Código integrado, esquema MySQL inicializado y una solicitud con apoyo y seguimiento guardados usando datos de prueba. Si se importa SQLite, registrar conteos comprobados y conservación del original.

**Aceptación** Las vías de ingreso usan la misma validación; indicadores, predicciones y apoyos se recuperan de MySQL al reiniciar; la solicitud funciona sin modelo. Los errores recuperables muestran una explicación útil. La cuenta del runtime no requiere privilegios administrativos ni creación de tablas.

### E1 T02 Comprobación de integración

**Asignación** Responsable Marco. Esfuerzo 2 h. Prioridad P1. Depende de E1 T01 y escenarios E1 T10.

Probar ingreso válido por captura, pegado, CSV y XLSX, modelo ausente, solicitud, apoyo y seguimiento. Revisar instalación y comandos reproducibles con Yokio.

**Evidencia** Comando ejecutado, resultado real y defectos con su corrección o estado pendiente.

**Aceptación** Se reproduce el recorrido local y no se declara funcional un módulo que todavía no se ha ejecutado.

### E1 T03 README y revisión de pruebas

**Asignación** Responsable Marco. Esfuerzo 2 h. Prioridad P1. Depende de E1 T02 y E1 T07.

Documentar instalación, ejecución, límites, arquitectura inicial y licencias o créditos comprobados. Revisar las pruebas de Víctor y coordinar la integración final.

**Evidencia** README actualizado, observaciones de revisión y cambio propio con autoría real.

**Aceptación** Otra persona puede seguir los pasos; los pendientes están visibles y los créditos reflejan recursos efectivamente usados.

### E1 T04 Datos y modelo de demostración

**Asignación** Responsable Ismael. Esfuerzo 4 h. Prioridad P0. Depende de Documento 01 y acuerdo del equipo.

Definir normalización de conteos en captura y contrato de porcentajes para CSV, Excel y pegado; preparar datos sintéticos y la MLP pequeña. Separar variables y etiqueta; plantear comparación con regla de nota y regresión logística.

**Evidencia** Esquema, validadores, CSV y plantilla XLSX sintéticos; entrenamiento reproducible con semilla y separación de datos documentadas.

**Aceptación** Las entradas equivalentes se normalizan igual; los totales son válidos. Ni resultado_final ni el ID son predictores. Las comparaciones pendientes quedan identificadas.

### E1 T05 Validación de datos y del modelo

**Asignación** Responsable Ismael. Esfuerzo 2 h. Prioridad P1. Depende de E1 T04 y dependencias disponibles.

Probar normalización, límites, faltantes, totales inválidos y etiqueta incorrecta. Registrar métricas ejecutadas, matriz de confusión y falsos negativos; evitar mezclar entrenamiento y evaluación.

**Evidencia** Pruebas del esquema, salida real del entrenamiento y métricas o bloqueo de ejecución registrado.

**Aceptación** Las entradas inválidas se rechazan; se explica qué datos produjeron las métricas y no se atribuye validez real a datos sintéticos.

### E1 T06 Fuentes y revisión de integración

**Asignación** Responsable Ismael. Esfuerzo 2 h. Prioridad P1. Depende de E1 T05 y E1 T01.

Documentar origen sintético, variables, limitaciones y fuentes utilizadas. Preparar notas del componente IA para el manual 02 y revisar integración y persistencia con Marco.

**Evidencia** Notas de datos y modelo, revisión registrada y cambio propio con autoría real.

**Aceptación** Se distingue una fuente consultada de un dato inventado para prueba; la revisión detecta cualquier uso de información sensible como predictor.


## Actividades de Víctor y Yokio

Víctor conserva la responsabilidad de QA. Yokio mantiene la exposición y comunicación, con una aportación técnica concreta a los datos de demostración y la comprobación de ejecución.

### E1 T07 Pruebas de datos y alertas

**Asignación** Responsable Víctor. Esfuerzo 4 h. Prioridad P0. Depende de Contrato E1 T04; módulos disponibles.

Implementar casos de equivalencia entre captura, pegado, CSV y XLSX; probar límites, duplicados, totales inválidos, modelo ausente y alertas. Preparar matriz de casos con entradas, resultado esperado y prioridad.

**Evidencia** Pruebas automatizadas y matriz QA trazable a los casos del flujo docente y tutor.

**Aceptación** Entradas equivalentes producen el mismo resultado; se rechazan totales inconsistentes. Los casos incluyen valores 0 y máximos, faltantes y solicitud sin predicción.

### E1 T08 Ejecución de QA y defectos

**Asignación** Responsable Víctor. Esfuerzo 2 h. Prioridad P1. Depende de E1 T07 y sistema integrado.

Ejecutar las pruebas disponibles, reproducir errores y registrar severidad, responsable y estado. Reservar para la entrega 03 sólo los resultados realmente observados.

**Evidencia** Salida de pruebas, matriz con aprobado, falló o no ejecutado, y defectos reproducibles.

**Aceptación** Ningún caso no ejecutado se cuenta como aprobado; los fallos que impiden la demostración tienen corrección comprobada o bloquean el cierre.

### E1 T09 Informe QA y revisión de interfaz

**Asignación** Responsable Víctor. Esfuerzo 2 h. Prioridad P1. Depende de E1 T08 y E1 T13.

Organizar evidencias de todos los módulos para el informe 03 y revalidar las correcciones de Marco, incluidos QA-03 a QA-05, y los cambios de los demás autores. Comprobar con Salomón que las instrucciones coincidan con el comportamiento observado. Preparar el protocolo de observación de una persona ajena para una entrega posterior.

**Evidencia** Índice de evidencias, revisión registrada y cambio propio con autoría real.

**Aceptación** Cada defecto remite a su caso y cada resultado a una ejecución. La futura prueba externa se mantiene pendiente hasta realizarla.

### E1 T10 Escenarios y comprobación de demostración

**Asignación** Responsable Yokio. Esfuerzo 4 h. Prioridad P0. Depende de Contrato E1 T04 y apoyo de Marco.

Preparar ejemplos docentes pequeños en la plantilla Excel y CSV, con ingreso válido e inválido y ayuda sin alerta. Completar una comprobación sencilla de ejecución para repetir la demostración.

**Evidencia** Escenarios y plantilla docente con resultado esperado, más script o procedimiento de comprobación ejecutable.

**Aceptación** Los ejemplos son ficticios y seudónimos; la plantilla se comprende sin vocabulario de programación y el equipo puede repetirla.

### E1 T11 Ensayo y validación del recorrido

**Asignación** Responsable Yokio. Esfuerzo 2 h. Prioridad P1. Depende de E1 T10 y sistema integrado.

Repetir arranque y recorrido docente usando plantilla, pegado y captura directa. Verificar ayuda, registro y seguimiento con Marco y comunicar fallos a Víctor.

**Evidencia** Resultado real del ensayo, capturas sin datos personales y lista de problemas detectados.

**Aceptación** La demostración explica el ingreso sin tecnicismos, diferencia lo ejecutado de lo pendiente y recuerda la revisión humana.

### E1 T12 Comunicación y revisión de datos

**Asignación** Responsable Yokio. Esfuerzo 2 h. Prioridad P1. Depende de E1 T11 y E1 T04.

Preparar un guion breve de problema, ingreso docente, recorrido y límites. Revisar claridad del README y datos de Ismael; apoyar el lenguaje de la futura guía 04.

**Evidencia** Guion de demostración, observaciones de revisión y cambio propio con autoría real.

**Aceptación** El guion coincide con la versión demostrable, reconoce datos sintéticos y no promete precisión o impacto no comprobados.


## Actividades de Salomón y revisión cruzada

Salomón concentra la documentación para esta entrega: convierte el comportamiento comprobado de la aplicación en instrucciones y capturas. Puede contribuir código, como cualquier integrante. Marco coordina las correcciones y Víctor su validación; cada autor aporta las notas técnicas y evidencias de sus cambios.

### E1 T13 Guía de ingreso y manejo de archivos

**Asignación** Responsable Salomón. Esfuerzo 4 h. Prioridad P0. Depende de Contrato E1 T04 y acuerdos E1 T01.

Documentar captura directa, pegado desde Excel, carga CSV y XLSX, descarga de plantilla y mensajes de error. Explicar indicadores, alertas de demostración y ayuda con pasos sencillos en docs/entrega_1/Guia_rapida.md. Usar datos ficticios y capturas de la versión ejecutada.

**Evidencia** Guía de uso con instrucciones y capturas del ingreso docente y recorrido con datos sintéticos.

**Aceptación** Otra persona puede seguir las instrucciones para ingresar datos, corregir un error y solicitar ayuda; la guía coincide con las pantallas existentes y explica cuándo necesita MySQL o el modelo.

### E1 T14 Comprobación de instrucciones y capturas

**Asignación** Responsable Salomón. Esfuerzo 2 h. Prioridad P1. Depende de E1 T13 y casos de Víctor.

Repetir los pasos de la guía con el escenario de Yokio y comprobar que las capturas y explicaciones coincidan con la aplicación. Registrar diferencias o instrucciones confusas; comunicar defectos a Víctor y Marco para su validación y corrección.

**Evidencia** Lista de instrucciones comprobadas, capturas actualizadas y diferencias reportadas con su estado.

**Aceptación** Cada paso documentado corresponde a una acción disponible; los requisitos y problemas pendientes están visibles y las capturas usan datos ficticios.

### E1 T15 Revisión documental y de demostración

**Asignación** Responsable Salomón. Esfuerzo 2 h. Prioridad P1. Depende de E1 T14 y E1 T10.

Revisar la coherencia entre README, guía rápida y guion de Yokio. Preparar el material de la futura guía 04 con lenguaje claro y capturas pertinentes; incorporar las observaciones de Víctor sobre el comportamiento comprobado.

**Evidencia** Guía inicial, observaciones de revisión y cambio propio con autoría real.

**Aceptación** Las instrucciones corresponden a pantallas existentes; el material de entregas posteriores se identifica como preparación, no como entrega terminada.

## Circuito de revisión

| Persona que revisa | Trabajo que verifica | Registro esperado |
| --- | --- | --- |
| Marco | Pruebas de Víctor | Cobertura, resultados y errores relevantes |
| Ismael | Integración de Marco | Contrato, variables y persistencia |
| Víctor | Correcciones de Marco y guía de Salomón | Revalidación de defectos y coherencia entre instrucciones y aplicación |
| Yokio | Datos y documentación de Ismael | Claridad y coherencia de escenarios |
| Salomón | Demostración de Yokio | Correspondencia entre guion y aplicación |

Cada autor atiende las observaciones de sus cambios y aporta sus notas y evidencia. Salomón coordina la guía, Víctor consolida resultados y Marco integra la versión y cierra las correcciones. Todos pueden escribir código y apoyar entregables de otros integrantes, manteniendo la autoría y la revisión de cada aportación.


## Condiciones para cerrar la primera entrega

Tener un esqueleto creado no completa la entrega. El equipo marca cada punto como comprobado sólo cuando exista la evidencia indicada. Una demostración del flujo de apoyos sin IA permite avanzar, pero la rama asignada requiere ejecutar y revisar el componente de redes neuronales antes de declarar lista la entrega.

| Elemento | Responsable y apoyo | Evidencia de cierre |
| --- | --- | --- |
| Documento del proyecto 01 | Marco; todos revisan | Documento existente y coherencia con la versión demostrada; ajustes posteriores sólo cuando se acuerden |
| Prototipo en repositorio | Marco; todos aportan | Código publicado en el repositorio M.E.S.S.I- y recorrido local ejecutado |
| Dependencias y ejecución | Marco y Yokio | Versiones comprobadas, instalación y comandos reproducidos por otra persona |
| Datos de prueba y red MLP | Ismael; Víctor verifica | CSV y plantilla XLSX sintéticos; ingreso equivalente, entrenamiento y predicción ejecutados; resultados documentados |
| Historial de los cinco integrantes | Cada integrante | Commits reales de cambios propios; nombres y cuentas confirmados por sus autores |
| Créditos y licencias README | Marco; Ismael aporta fuentes | Créditos de recursos usados y licencias revisadas de las dependencias |
| Bitácora 06 | Cada integrante aporta su uso posterior | Archivo existente conservado; este prompt de arranque queda excluido |

## Preparación de las entregas siguientes

- Entrega 2: manual del programador 02 a cargo de Marco e Ismael, con Salomón para documentar interfaz y archivos. Informe de pruebas QA 03 a cargo de Víctor; todos aportan casos y evidencias de su módulo.
- Entrega 3: manual de usuario 04 a cargo de Salomón con Yokio para claridad y recorrido. Nota de prueba 05 a cargo de Víctor, con Yokio para coordinar la sesión con una persona ajena real. Registrar lo observado en media página; no fabricar participante ni resultados.
- Entrega 4: reflexión y bitácora 06 con aportaciones individuales de los cinco integrantes y consolidación acordada. Preservar el trabajo existente y registrar sólo el uso posterior que corresponda.

## Fuentes y decisiones vigentes

Los integrantes y el alcance provienen de 01_Documento_del_proyecto_MESSI.docx. La ficha MESSI_Riesgo_Escolar_Ficha_Bloque1_Parte_II.pdf, página 1, conserva los roles iniciales; el usuario ajustó el reparto el 5 de octubre: Salomón concentra documentación, Marco las correcciones y Víctor la validación, y todos pueden aportar código. Las plantillas 01 a 06 orientan los entregables. La carga de ocho horas, las tareas y las sesiones son la propuesta operativa de este mapa.

Repositorio de trabajo: https://github.com/a3524110303-cpu/M.E.S.S.I-.git. Carpeta local destinada al proyecto: C:\Users\user\Desktop\MESSI. La entrega está acordada para el 5 de octubre durante la clase. Los permisos para contribuir al repositorio, las cuentas de los cinco integrantes y el entorno de prueba final deben confirmarse antes del cierre.
