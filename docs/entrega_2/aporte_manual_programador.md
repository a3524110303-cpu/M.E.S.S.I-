# Aportes para el Manual del Programador

**Aporte original:** Ismael Hernández Jiménez, commit `1151415`.
**Rectificación técnica:** 8 de octubre de 2026, revisión del código y los metadatos asistida por Codex. Se conserva la autoría del aporte; las aclaraciones siguientes corrigen su interpretación y distinguen entrenamiento de inferencia.

## Sección 2 Descripción de módulos principales

`scripts/train_demo.py` valida el CSV sintético, separa entrenamiento, validación y prueba, ajusta los modelos y genera `models/messi_demo.joblib` junto con el reporte `models/messi_demo.json`. El escalador se ajusta dentro del pipeline con el conjunto de entrenamiento.

`src/messi/model.py` carga el artefacto local y realiza la inferencia. Antes de `joblib.load` revisa ruta, metadatos, tamaño y coincidencia SHA-256. Esta comprobación detecta discrepancias entre el modelo y el JSON local; no constituye firma digital ni acredita autoría si alguien altera ambos archivos. No se deben abrir artefactos de terceros.

`src/messi/data.py` valida CSV, Excel, pegado y captura. Revisa esquema, valores finitos, rangos, IDs únicos y límites de 5 MB y 10,000 registros. La nota va de 0 a 10 y asistencia/tareas de 0 a 100. Excel y pegado pueden generar IDs temporales; las fórmulas Excel se rechazan. Validar el formato no demuestra que un dato sea sintético o verdadero.

## Sección 3 Explicación del modelo y parámetros

El modelo de la demo es `StandardScaler + MLPClassifier`, con una capa oculta de ocho neuronas, `max_iter=1000`, `early_stopping=True`, `validation_fraction=0.15`, `n_iter_no_change=30` y semilla 2026. La parada temprana reserva una parte del conjunto de ajuste; es distinta del conjunto externo de validación.

El MLP se conserva por el alcance didáctico del proyecto. En los 48 casos sintéticos de prueba obtuvo exactitud de 68.75%, recall de 96.30%, precisión de 65.00%, F1 de 77.61% y ROC AUC de 0.6067. Su matriz `[[7, 14], [1, 26]]`, con filas reales 0/1 y columnas predichas 0/1, representa siete verdaderos negativos, 14 falsos positivos, un falso negativo y 26 verdaderos positivos. El recall expresa 26 de 27 casos artificiales de riesgo detectados; no demuestra eficacia con alumnos reales.

Se compararon una regla `nota_parcial < 6` y regresión logística. La regla obtuvo 87.5% de exactitud y la logística 100% en este conjunto de prueba. Ese 100% por sí solo no acredita sobreajuste ni memorización. No hay evidencia para afirmar que la logística se descartó por ese motivo ni que el MLP sea el mejor predictor. El generador construye la etiqueta a partir de los tres indicadores y ruido, por lo que esta comparación evalúa una simulación pequeña.

El umbral distribuido es 0.5. Inferencia lee el umbral de los metadatos y activa la alerta si `puntuacion_riesgo >= threshold`, incluyendo la igualdad. La puntuación no está calibrada ni validada como probabilidad de reprobación en estudiantes reales.

## Sección 4 Formato y origen de los datos

Los 240 registros de `data/synthetic/training_synthetic.csv` son totalmente ficticios, generados con semilla 2026. La separación externa consta de 144 registros para ajuste, 48 para validación y 48 reservados para prueba. La clase 0 significa aprobado y la clase 1 reprobado en la simulación.

Las entradas son `nota_parcial`, `asistencia` y `tareas_entregadas`. Cada fila tiene un `id_estudiante` anónimo; el ID no se pasa al modelo. `resultado_final` es la etiqueta de entrenamiento y se rechaza como entrada de inferencia. La demo no utiliza expedientes escolares reales.

## Sección 6 Fuentes y créditos

Las cifras proceden de `models/messi_demo.json`; el procedimiento está en `scripts/train_demo.py` y el origen artificial en `scripts/generate_synthetic.py`. El resumen original de Ismael se conserva en `docs/entrega_1/resultados_entrenamiento.md` como aporte histórico; su interpretación de sobreajuste debe leerse con esta rectificación.

- [MLPClassifier en scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html).
- [Curvas de validación y diagnóstico de sobreajuste](https://scikit-learn.org/stable/modules/learning_curve.html).
- [Calibración de probabilidades](https://scikit-learn.org/stable/modules/calibration.html).
- [Persistencia y confianza en archivos de modelos](https://scikit-learn.org/stable/model_persistence.html).
