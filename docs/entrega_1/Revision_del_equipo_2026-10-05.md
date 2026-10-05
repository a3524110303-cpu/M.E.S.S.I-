# Revisión de aportaciones de MESSI

Fecha: 5 de octubre de 2026, America/Mexico_City.

**Registro histórico anterior a las correcciones solicitadas por Marco.**
La integración y las correcciones posteriores están en
[Evidencia de integración de Marco](Evidencia_integracion_Marco.md).
Los pendientes de otros integrantes se conservan; el estado vigente de la
entrega está en [Estado de la entrega](Estado_de_la_entrega.md).

**La primera entrega todavía no está cerrada.** Hay aportaciones publicadas de Marco, Ismael y Víctor. No se encontraron aportaciones de Yokio y Salomón en las ramas, solicitudes de cambios o archivos revisados. Esto significa falta de evidencia accesible; no demuestra que no hayan trabajado fuera del repositorio.

## Evidencia y versión revisada

- Repositorio: https://github.com/a3524110303-cpu/M.E.S.S.I-
- `main`: `9ea0ba176a827623b98d239f4fb7dfae0d32ce60`, consultado directamente mediante Git y GitHub CLI.
- Se revisaron todas las ramas remotas disponibles (`main`, `victor-qa`), todas las solicitudes de cambios disponibles (1 cerrada y 2 integrada), commits, documentos de resultados, pruebas y capturas de Víctor.
- Responsabilidades contrastadas con `Siguientes_pasos_del_equipo.md`, el mapa T01–T15 y los acuerdos del chat «Organiza primera entrega de MESSI».
- Copia independiente usada para ejecutar la versión publicada: `C:/Users/user/Desktop/MESSI/.qa/revision_equipo_2026-10-05`. No se fusionaron cambios sobre la copia de trabajo de Marco.

## Resultado por integrante

| Integrante | Trabajo realmente localizado | Verificación | Estado y pendiente |
| --- | --- | --- | --- |
| Marco, T01–T03 | Base del sistema y documentación, commits `5a2216a` y `f8c49c7`, publicados el 3 de octubre. Captura, CSV, Excel, pegado, solicitudes, apoyos y seguimiento con SQLite en la versión publicada. Hay implementación MySQL en la carpeta de trabajo, todavía sin publicar. | La suite de la versión publicada pasa salvo el fallo esperado. La prueba de Víctor comprueba persistencia de solicitudes, apoyos y seguimiento entre sesiones. Se reprodujo la predicción con el modelo recién entrenado. | **Parcial.** Integrar y volver a probar las correcciones abiertas, actualizar documento 01 y cerrar la bitácora 06. La implementación MySQL local no acredita integración ni publicación; no se ejecutó en esta revisión. |
| Ismael, T04–T06 | Commit `f6bf167`, del 4 de octubre, que añade `resultados_entrenamiento.md` a `main`. Reporta entrenamiento y comparación de los tres métodos. | Se entrenó desde el código publicado con semilla 2026: las divisiones 144/48/48 y cifras de su resumen se reproducen. Se generaron el modelo y los metadatos en la copia de auditoría; las predicciones se comprobaron con AppTest. | **Parcial, con aporte confirmado.** Corregir la interpretación del sobreajuste y de eficacia escolar; enumerar las tres variables y completar matriz de confusión, falsos negativos, evidencia de su ejecución y fuentes. No se encontró registro de su revisión cruzada con Marco. |
| Víctor, T07–T09 | Commit `b785dd2`, integrado mediante PR 2. Informe QA, registro de defectos, ocho capturas, datos válidos e inválidos, logs de instalación y pruebas, ocho pruebas AppTest nuevas y fijación de pyarrow 21.0.0. | La suite se repitió con pyarrow 21.0.0: 59 ejecutadas, **58 aprobadas y 1 fallo esperado**, sin errores ni omisiones. Se inspeccionaron las capturas de QA-03 y QA-04. La ejecución de Actions de `main` confirma el mismo resultado. | **Aporte QA confirmado; cierre parcial.** QA-03, QA-04 y QA-05 siguen abiertos. Repetir pruebas tras las correcciones y revisar los futuros cambios de Salomón. No se acredita aquí la futura prueba con una persona ajena. |
| Yokio, T10–T12 | No se encontró commit, rama o PR atribuible a él, ni `Guion_demostracion.md`, escenario propio de presentación o registro de ensayo. Los datos sintéticos iniciales corresponden a la base de Marco. | Búsqueda en el historial, todas las ramas disponibles, archivos del repositorio y materiales locales de MESSI. Una presentación previa preparada en A.B.R.I.L no acredita por sí sola el trabajo de Yokio en esta entrega. | **No verificable con lo disponible.** Publicar escenario ficticio probado, guion, resultado real del ensayo y observaciones sobre instalación y claridad del resumen de Ismael. |
| Salomón, T13–T15 | No se encontró commit, rama o PR atribuible a él ni `Guia_rapida.md`. La interfaz disponible proviene de la base inicial; no debe atribuirse a Salomón sin evidencia. | Se contrastó el historial y la ausencia de guía con los defectos de interfaz reportados por Víctor. | **No verificable con lo disponible.** Aportar mejoras de interfaz, conservar campos válidos tras un error, comprobar teclado y preparar guía con capturas reales; dejar registrada la revisión del guion de Yokio. |

## Ejecuciones realizadas en esta revisión

Entorno: Windows, Python 3.13.13, Streamlit 1.50.0, scikit-learn 1.7.2. Se instaló pyarrow 21.0.0 exclusivamente en `.qa/deps` de la copia de auditoría y se cargó mediante `PYTHONPATH`; la instalación habitual del proyecto se conservó.

1. `python -m unittest discover -s tests -v`: código 0, 59 casos, 58 aprobados y 1 fallo esperado. Log: `.qa/revision_equipo_2026-10-05/.qa/pruebas_revision_pyarrow21.txt`.
2. `python scripts/train_demo.py`: código 0; modelo y metadatos generados en la copia independiente. Log: `.qa/revision_equipo_2026-10-05/.qa/entrenamiento_revision.txt`.
3. Streamlit AppTest: cargar ejemplo sintético, calcular predicción para ocho estudiantes y generar CSV con ocho filas. Log: `.qa/revision_equipo_2026-10-05/.qa/prediccion_revision.txt`. Se verifica interacción y contenido; no se presenta como nuevo recorrido visual en navegador ni como descarga manual del archivo.
4. GitHub Actions sobre el mismo `main`: https://github.com/a3524110303-cpu/M.E.S.S.I-/actions/runs/37244821170. También informa `OK (expected failures=1)`; el indicador verde no significa que todos los defectos estén corregidos.

## Resultados del entrenamiento contrastados

Datos sintéticos, semilla 2026, 144 registros de entrenamiento, 48 de validación y 48 de prueba. Variables utilizadas: `nota_parcial`, `asistencia`, `tareas_entregadas`. El ID y la etiqueta `resultado_final` no son predictores.

| Método | Exactitud de prueba | Recall de riesgo | Matriz de confusión, filas reales 0/1 y columnas predichas 0/1 |
| --- | --- | --- | --- |
| Regla nota menor que 6 | 87.5 % | 88.9 % | `[[18, 3], [3, 24]]` |
| Regresión logística | 100 % | 100 % | `[[21, 0], [0, 27]]` |
| MLP de ocho neuronas | 68.75 % | 96.30 % | `[[7, 14], [1, 26]]` |

**Correcciones necesarias en el análisis de Ismael:**

- Un 100 % en un conjunto de prueba separado no demuestra memorización ni sobreajuste por sí solo. El reporte no aporta comparación de rendimiento de entrenamiento frente a validación que sostenga ese diagnóstico. Puede describirse el conjunto sintético y su simplicidad, pero no afirmar una causa no demostrada. Referencia oficial: https://scikit-learn.org/stable/modules/learning_curve.html.
- El recall de 96.3 % corresponde a 26 de 27 casos sintéticos de riesgo detectados. Hay **14 falsas alarmas y 1 falso negativo**. No equivale a demostrar detección de estudiantes vulnerables reales ni eficacia escolar.
- La puntuación del modelo y el umbral 0.5 no están calibrados para interpretar probabilidades de reprobación en estudiantes reales. El propio código y sus metadatos declaran este límite.
- Su resumen reproduce las cifras, pero no contiene captura o log propio, matriz de confusión ni fuentes. La repetición de esta auditoría confirma reproducibilidad, no quién ejecutó originalmente el entrenamiento.

## Pendientes de la entrega

1. **Historial de los cinco:** hay identidades confirmadas de Marco, Ismael y Víctor; faltan evidencias publicadas de Yokio y Salomón. El número de commits no se usa para medir esfuerzo.
2. **Documento 01:** la copia publicada en `docs/entrega_1` tiene el mismo objeto Git que la referencia original (`cc7f7d61f4caa82aab7cb8325e4d53c015a1f077`). No se encontró la actualización de instalación y funcionamiento solicitada después de crear el prototipo.
3. **Bitácora 06:** sigue localizada como plantilla de referencia. No se encontró una versión completada de la primera entrega. Este informe no reemplaza esa bitácora ni modifica su contenido.
4. **QA-03:** el seguimiento persiste, pero su confirmación desaparece tras `st.rerun()`. Existe una prueba marcada como fallo esperado; sigue siendo un defecto abierto.
5. **QA-04:** `clear_on_submit=True` borra campos del formulario incluso cuando la validación rechaza el envío. Las filas ya aceptadas sí se conservan. Pendiente de corregir y repetir visualmente.
6. **QA-05:** avisos de mantenimiento por `use_container_width`; no impiden ejecutar esta versión, pero siguen registrados.
7. **Integración local:** la carpeta de Marco está en `codex/entrega-1`, con cambios MySQL sin commit, y no contiene todavía los nuevos archivos de Ismael y Víctor en su árbol de trabajo. `git fetch` actualizó las referencias, sin fusionar los cambios. No presentar esa carpeta como idéntica a `main`.
8. **Revisión conjunta:** no se encontraron registros completos de las cinco revisiones cruzadas. Falta comprobar una versión común en el equipo de presentación, resolver los errores de interfaz y reunir los documentos y guías pendientes.

Este resultado evalúa evidencias disponibles al momento de la consulta. No asigna autoría a documentos genéricos ni a trabajo preparado por otra persona. No se enviaron mensajes al equipo, no se publicó este informe y no se corrigió código como parte de esta revisión.
