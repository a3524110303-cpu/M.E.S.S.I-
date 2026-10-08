# Revisión de aportaciones de Ismael y Víctor

Fecha: 8 de octubre de 2026, America/Mexico_City. Revisión técnica asistida por Codex sobre MESSI. La solicitud del equipo autoriza integrar y rectificar los aportes; la autoría de las contribuciones originales se conserva.

Los cambios recientes de Ismael son documentación y comentarios, sin modificación de lógica. Sus cifras de entrenamiento coinciden con los metadatos del modelo local, pero su interpretación de sobreajuste, probabilidad y superioridad del MLP requería corrección. Los defectos de interfaz reportados por Víctor ya tienen correcciones y pruebas en el código integrado. Su informe adjunto acredita una revalidación automatizada; deja fuera una nueva visita en navegador, el instalador y la prueba con persona ajena.

## Versiones y fuentes revisadas

| Fuente | Identificador y contenido |
| --- | --- |
| Integración anterior | `6f240211346674f075606f7e47d5476c6abbe354`, merge de la versión local Windows |
| Aporte reciente de Ismael | `1151415484043f4a90281e6422a0e927bab81ddd`, 8 de octubre, `docs/entrega_2/aporte_manual_programador.md`, `src/messi/data.py`, `src/messi/model.py` |
| Resumen inicial de Ismael | `f6bf167ba5f24bbb17750d3e6244a8e0e5f3d634`, `docs/entrega_1/resultados_entrenamiento.md` |
| QA original de Víctor | `b785dd2eb5274e5b71f6778924999a9c3be456f9`, integrado por `9ea0ba1`; pruebas AppTest, logs, capturas, archivos ficticios y pin de pyarrow |
| Correcciones de integración | `4e9005e`, correcciones de QA-03, QA-04 y QA-05; explicación en `docs/entrega_1/Evidencia_integracion_Marco.md` |
| Informe adjunto de Víctor | `Informe yo 1,1.docx`, fechado 7 de octubre de 2026; SHA-256 `1e4a58b44ebc61b0725354609f80da8ef662ce293752551a380061b0c3b48da0` |

Se leyeron el historial Git, los diffs, los módulos afectados, el generador, el entrenamiento, las pruebas UI/modelo y las tablas del DOCX. Las instrucciones de los documentos se trataron como requisitos y evidencia del proyecto, sin atribuir al archivo autorización adicional para contactar personas o entregar en Classroom.

## Aporte reciente de Ismael

El commit `1151415` añade 21 líneas al manual y modifica docstrings/comentarios en dos módulos. No cambia expresiones, validaciones, deserialización ni condiciones de alerta. Es un aporte acotado de explicación técnica, coherente con su descripción de que no hubo cambios mayores.

Las rectificaciones de esta revisión son:

- Entrenamiento corresponde a `scripts/train_demo.py`; `src/messi/model.py` carga el modelo y realiza inferencia.
- Se describen tres indicadores, una nota y dos porcentajes. No son tres calificaciones.
- La validación de formato no demuestra que los datos sean ficticios ni acredita su veracidad.
- Se restaura el contrato de CSV, Excel y pegado: contenido frente a ruta, columnas, IDs, coma decimal y rechazo de fórmulas.
- La salida es una puntuación de demostración. No está calibrada ni validada como probabilidad de reprobación de estudiantes reales.
- La alerta usa `>=` al umbral de los metadatos; 0.5 es el valor distribuido. La igualdad también activa la alerta.
- SHA-256 comprueba coincidencia entre artefacto y JSON local. No es una firma digital y no demuestra que nadie haya modificado ambos archivos.
- Se conserva el MLP por el alcance didáctico. El resultado perfecto de la logística no demuestra por sí solo memorización ni sobreajuste; tampoco acredita que el MLP sea el predictor superior.

Se actualizaron `src/messi/data.py`, `src/messi/model.py` y `docs/entrega_2/aporte_manual_programador.md`. El análisis original de entrega 1 se conserva como registro histórico y el manual señala expresamente esta rectificación.

La comparación de AST frente a `1151415`, retirando únicamente docstrings y posiciones de origen, devolvió igualdad exacta en ambos módulos. Los comentarios no forman parte del AST. Por tanto, estas ediciones no alteran la lógica ejecutable.

## Datos y métricas contrastados

`scripts/generate_synthetic.py` genera 240 registros artificiales con semilla 2026. La etiqueta deriva de la nota, asistencia, tareas y ruido; no procede de un resultado escolar observado. `scripts/train_demo.py` separa 144 filas de ajuste, 48 de validación externa y 48 de prueba, antes de ajustar los pipelines. La parada temprana del MLP reserva además una fracción interna del conjunto de ajuste. ID y etiqueta no se utilizan como predictores.

El artefacto y el CSV actuales coinciden con los SHA-256 registrados en `models/messi_demo.json`:

| Archivo | SHA-256 verificado |
| --- | --- |
| `models/messi_demo.joblib` | `bdee9aa2e3f887cf1ed4f14b8319ed3e2a01d0170c3cc678c8c52372a1972dd4` |
| `data/synthetic/training_synthetic.csv` | `c00a608974bb89687c38f0e064a72a1c1414b6eff61e67e15a0a9b1e8f50d5f0` |

Las cifras siguientes se contrastaron con el JSON existente; esta revisión no volvió a entrenar ni atribuye esa ejecución a Ismael.

| Método | Exactitud prueba | Recall riesgo | Precisión riesgo | F1 riesgo | ROC AUC | Matriz de confusión |
| --- | --- | --- | --- | --- | --- | --- |
| Regla nota menor que 6 | 87.50% | 88.89% | 88.89% | 88.89% | 0.9665 | `[[18,3],[3,24]]` |
| Regresión logística | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 | `[[21,0],[0,27]]` |
| MLP de ocho neuronas | 68.75% | 96.30% | 65.00% | 77.61% | 0.6067 | `[[7,14],[1,26]]` |

Filas reales 0/1 y columnas predichas 0/1. En el MLP hay 26 verdaderos positivos, un falso negativo, 14 falsos positivos y siete verdaderos negativos. Detectar 26 de 27 riesgos artificiales explica el recall alto, acompañado de 14 falsas alarmas. No hay evidencia de eficacia educativa, equidad, calibración o generalización a un colegio real.

## Hallazgos y revalidación de Víctor

| Hallazgo original | Evidencia y estado integrado |
| --- | --- |
| QA-01 Python 3.14 en lugar de 3.13 requerido por BAT | Fue un problema de entorno. Víctor documentó Python 3.13.16; el instalador cliente empaqueta runtime. No equivale a prueba del instalador actual. |
| QA-02 DLL de pyarrow 25.0.1 bloqueada en ese Windows | `requirements.txt` conserva pyarrow 21.0.0. El hallazgo fue específico de ese equipo; no demuestra un fallo universal de 25.0.1. |
| QA-03 desaparecía confirmación tras rerun | El código usa confirmación persistente de formulario. `test_qa03_followup_keeps_visible_success_confirmation` ya no está marcado como fallo esperado. |
| QA-04 captura inválida borraba datos válidos | Formularios usan `clear_on_submit=False`; pruebas verifican conservación tras error y limpieza tras éxito, también en solicitud de estudiante. |
| QA-05 API obsoleta de tablas | Las tablas de `app.py` usan `width="stretch"`. |

El DOCX adjunto contiene nueve casos de matriz y declara 151 pruebas automáticas ejecutadas: 144 aprobadas, siete omitidas por requerir MySQL opt-in y cero fallidas. No se cuentan las omisiones como aprobaciones. Revalida QA-02 a QA-05 mediante la suite y AppTest en `main 6f24021`, con SQLite temporal y datos ficticios.

Las afirmaciones y los nombres de casos del adjunto son coherentes con las pruebas fuente revisadas. Los logs citados allí (`suite_completa.txt`, `revalidacion_interfaz.txt`, `revalidacion_sqlite.txt` y `verificacion_api_streamlit.txt`) no se recibieron dentro del DOCX; el informe resume su resultado. El resultado de una ejecución nueva y los recorridos de esta entrega se documentan en sus propias evidencias, sin presentarlos como observaciones originales de Víctor.

La revalidación de esta sesión sobre MESSI 0.3.0 ejecutó 157 pruebas: 150 aprobadas, siete MySQL omitidas y cero fallidas. Se añadieron seis casos de regresión relativos a diagnóstico y proceso; no se atribuyen a Víctor. `pip check` fue satisfactorio. También se verificaron el self-test de la fuente y el servidor con respuesta HTTP 200 y cierre correcto. Evidencia: `docs/entrega_2/evidencias/pruebas_actuales.txt`, `verificacion_fuente_self_test.json` y `verificacion_fuente_servidor.json`. La verificación del ejecutable reconstruido pertenece al cierre del paquete y se registra por separado.

Las capturas y textos de entrega 1 conservan defectos de la versión de 4 de octubre como historial. Sus frases “pendiente” no prevalecen sobre las correcciones y la revalidación posteriores. AppTest comprueba estado e interacciones; una nueva prueba visual debe identificar el instalador, versión, equipo y recorrido realmente utilizados.

## Requisitos humanos que el adjunto no acredita

El adjunto deja explícitamente fuera una visita nueva en navegador real y la ejecución del instalador. También señala pendientes una prueba física en Windows 10 y otra en la segunda computadora de Yokio. Estos son límites de su sesión de QA; no deben convertirse en pruebas aprobadas por redacción.

No incluye prueba con persona ajena al equipo, identidad del participante, observaciones de esa persona, retroalimentación sobre claridad o firma de conformidad. Tampoco acredita un ensayo de presentación del equipo. Esos hechos requieren participación y evidencia humanas. La nota de prueba con persona ajena puede prepararse con instrucciones y campos, pero la realización y el resultado no pueden inventarse.

Para el cierre, el equipo debe revisar los manuales finales, ejecutar el paquete en el equipo de presentación y registrar cualquier prueba externa requerida por el examen. Una entrega técnica terminada no sustituye el hecho de que una persona externa utilice la aplicación. Las evidencias nuevas del software, ejecutable e instalador pertenecen a la verificación final de esta sesión.

## Fuentes técnicas

La interpretación del sobreajuste se basa en la comparación del rendimiento de entrenamiento y validación descrita por [scikit-learn](https://scikit-learn.org/stable/modules/learning_curve.html). Un resultado perfecto en la prueba por sí solo no documenta esa diferencia.

La lectura de una puntuación como frecuencia esperada requiere evaluar su [calibración](https://scikit-learn.org/stable/modules/calibration.html). MESSI no ha realizado esa validación con resultados reales.

La deserialización mediante joblib exige artefactos de confianza, según la documentación de [persistencia de modelos](https://scikit-learn.org/stable/model_persistence.html). El checksum local comprueba integridad relativa al JSON, sin sustituir esa confianza.
