# Tareas de Yokio: Entrega 2 de MESSI

Basado en el reparto de trabajo de `Reparto_del_equipo.md`. Fecha de entrega indicada por el equipo: **8 de octubre de 2026, durante la hora de clase**.

## Checklist

- [T] **Usar la versión común del equipo.** Obtener de Marco el commit integrado y actualizar la copia de trabajo antes de probar. Registrar el commit usado en la evidencia.
- [T] **Usar la versión común del equipo.** Obtener de Marco el commit integrado y actualizar la copia de trabajo antes de probar. Registrar el commit usado en la evidencia.
- [T] **Preparar un escenario ficticio reproducible.** Definir los datos de entrada y los pasos del recorrido, usando únicamente códigos y datos sintéticos; acordar con Víctor los resultados que se esperan.
- [T] **Probar la instalación en otra computadora disponible.** Registrar el sistema operativo, arquitectura y navegador reales. Verificar instalación y arranque con el instalador, sin depender de Python, MySQL o internet.

<!-- NOtas -->
Se realizaron pruebas en 3 entornos reprducibles, las maquinas utilizadas para la pruebas usaron una arquitectura de 32 y 64 bits, todas con el SO de windows 10. con las isguientes especificaciones para cada equipo

Windows 10 32bits - 4GB de RAM
Windows 10 64bits - 2GB de RAM 
Windows 10 64bits - 5GB de RAM

- [T] **Completar el recorrido funcional.** Cargar el escenario, recorrer las vistas y funciones pertinentes, cerrar MESSI, volver a abrirlo y comprobar que los registros se recuperan.
- [T] **Comprobar actualización y conservación de datos.** Seguir el procedimiento disponible, confirmar que los registros de prueba se conservan y anotar cualquier problema o paso que no pueda verificarse.
- [T] **Entregar evidencia a Víctor para el informe de QA.** Incluir commit/versión, entorno, pasos, entradas, resultados esperados y obtenidos, estado de cada caso y capturas o logs con fecha. Reportar fallos; no marcar como aprobado lo que no se ejecutó.
- [T] **Probar la claridad del manual.** Con Víctor y Salomón, seguir las instrucciones sin ayuda de quien las escribió; anotar pasos ambiguos o incompletos y comprobar las correcciones antes del cierre.
- [T] **Enviar observaciones de claridad a Salomón.** Confirmar que el lenguaje, el orden y los pasos del manual se entienden durante la prueba.
- [T] **Preparar y ensayar una explicación breve.** Explicar la arquitectura general, qué hace y cuáles son los límites de la IA, y qué resultados de QA se comprobaron. Ajustar el guion a la versión y evidencias reales.
- [T] **Documentar cualquier script aportado.** Si para el escenario se crea un script, describir su propósito, uso, entradas y salidas.

## Pruebas con datos ficticios

Ejecutar estos casos en la versión común y registrar el resultado real. Los IDs son códigos de prueba, no identifican personas. Para CSV, guardar el bloque indicado como UTF-8 `.csv`; para la tabla pegada, copiar las filas al control de pegado.

| ID | Prueba y datos a ingresar | Resultado esperado |
| --- | --- | --- |
| D-01 | **CSV válido, varias filas:**<br>`id_estudiante,nota_parcial,asistencia,tareas_entregadas`<br>`EST-901,5.8,70,50`<br>`EST-902,8.7,95,90`<br>`EST-903,4.2,55,40` | Se aceptan 3 estudiantes y la tabla conserva cada código y valor. |
| D-02 | **Captura directa por porcentajes:** ID `EST-904`, nota `6`, asistencia `80`, tareas `70`. | Se agrega un estudiante con asistencia 80% y tareas 70%. |
| D-03 | **Captura directa por cantidades:** ID `EST-905`, nota `5.8`, 8 asistencias de 10 sesiones, 7 tareas entregadas de 10 solicitadas. | Se agrega el registro con asistencia 80% y tareas 70%. |
| D-04 | **Tabla pegada con punto y coma:**<br>`id_estudiante;nota_parcial;asistencia;tareas_entregadas`<br>`EST-906;6,5;80;70`<br>`EST-907;8;95;100` | Se aceptan 2 filas; la coma decimal se interpreta como 6.5 y 8, sin confundirla con el separador de columnas. |
| D-05 | **Límites permitidos:** dos filas CSV: `EST-908,0,0,0` y `EST-909,10,100,100`. | Se aceptan ambas filas; los extremos 0 y 10 para nota, y 0 y 100 para porcentajes, son válidos. |
| D-06 | **Valor fuera de rango:** intentar cargar `EST-910,10.1,80,70`; repetir con asistencia `101` y tareas `-1`. | Se rechaza cada entrada inválida y se identifica la fila/campo con error; no se presenta como lista válida. |
| D-07 | **Dato faltante o no numérico:** probar `EST-911,,80,70` y `EST-912,abc,80,70`. | Se rechazan los dos casos indicando el campo incompleto o no numérico. |
| D-08 | **ID duplicado o formato incorrecto:** dos filas con `EST-913`; después probar el ID `Ana`. | Se rechaza el duplicado y se rechaza el identificador que no cumple `EST-` más 3–8 dígitos. |
| D-09 | **Columna no permitida:** agregar una columna `nombre` a la cabecera CSV, por ejemplo `...,nombre` y un valor ficticio. | Se rechaza la columna adicional. No usar ni introducir nombres, correos u otros datos personales durante las pruebas reales. |
| D-10 | **Fórmula en Excel:** en una copia de la plantilla `.xlsx`, ingresar `=6+1` en la celda de nota de una fila. | Se rechaza el archivo indicando que no se admiten fórmulas; no se usa el valor calculado que muestre Excel. |
| D-11 | **Predicción de demostración:** cargar D-01 y calcular si el modelo está disponible. | Se muestran resultados para las filas aceptadas y los puntajes quedan entre 0 y 1. No exigir puntajes exactos: dependen del artefacto instalado. Si el modelo no está disponible, los indicadores siguen visibles y la predicción queda pendiente. |
| D-12 | **Solicitud y apoyo:** en vista Estudiante, enviar ID `EST-901` y mensaje `Solicitud ficticia: necesito organizar mis tareas.`; en vista Tutor, revisar la solicitud y registrar una tutoría con nota `Acuerdo ficticio: revisar tareas la próxima semana.` | La solicitud aparece asociada a `EST-901`; el tutor puede registrar el apoyo y su seguimiento sin depender de una alerta de IA. |
| D-13 | **Persistencia del recorrido:** después de D-12, cerrar y volver a abrir MESSI; consultar los registros guardados. | Los registros que la instalación indique como guardados siguen disponibles. Anotar qué se conservó y cualquier fallo; no asumir que una acción no guardada debe persistir. |



## Evidencia mínima de la prueba en otro equipo

- Identificación de la versión y commit probado.
- Fecha, sistema operativo, arquitectura y navegador utilizados.
- Pasos ejecutados y datos sintéticos usados.
- Resultado esperado y obtenido de cada paso, con estado aprobado, fallido o no ejecutado.
- Evidencia asociada (captura, log o reporte) y descripción de errores encontrados.
- Resultado de cierre/reapertura y recuperación de registros; resultado de actualización si se ejecutó.

## Coordinación

- **Víctor:** acordar casos, resultados esperados y formato de evidencias; pasarle los resultados para que los incorpore al informe de QA.
- **Salomón:** compartir observaciones sobre la claridad del manual y validar que el guion de presentación corresponda con él.
- **Marco:** solicitar la versión común y confirmar cualquier duda sobre instalación o actualización.
