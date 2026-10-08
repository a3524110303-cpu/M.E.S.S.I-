# Aportes para el Manual del Programador
**Por:** Ismael Hernández Jiménez

## Sección 2: Descripción de módulos principales
* **Módulo de Entrenamiento (`model.py` / `train_demo.py`):** Se encarga de preparar los datos, dividirlos en grupos (para entrenamiento, validación y prueba final), y generar el archivo del modelo de inteligencia artificial listo para usarse (`messi_demo.joblib`).
* **Módulo de Validación de Datos (`data.py`):** Revisa que toda la información ingresada tenga el formato correcto, no contenga errores y respete los límites (como calificaciones de 0 a 10) antes de enviarla a la red neuronal.

## Sección 3: Explicación del modelo y parámetros
* **Modelo elegido:** Usamos una red neuronal artificial (Perceptrón Multicapa o MLP_8).
* **Por qué se eligió:** Porque tiene una sensibilidad altísima (96.3% de Recall). En pocas palabras, el sistema es muy preventivo: prefiere lanzar una alerta preventiva sobre un alumno seguro, antes que cometer el error de ignorar a un estudiante que realmente va a reprobar.
* **Alternativas descartadas:** Probamos una regla básica (pero no predice a futuro) y un modelo de Regresión Logística (lo descartamos porque solo "memorizó" las respuestas en lugar de aprender, un error llamado sobreajuste).
* **Parámetro principal:** Usamos un umbral fijo de 0.5. Si la red neuronal calcula un 50% o más de probabilidad de reprobar, lanza la alerta.

## Sección 4: Formato y origen de los datos
* **Origen:** Por ahora, usamos datos totalmente ficticios (sintéticos) solo para demostrar que la arquitectura y el código funcionan.
* **Distribución:** La información se divide en 144 registros para enseñar al modelo, 48 para validarlo y 48 para la prueba final.
* **Formato y variables:** Cada estudiante tiene un `id_estudiante` anónimo. Para calcular el riesgo, el modelo cruza la `nota_parcial` (de 0 a 10), el porcentaje de `asistencia` (0 a 100%) y las `tareas_entregadas` (0 a 100%).

## 6. Fuentes y Créditos
* La red neuronal (MLP_8) se programó usando la documentación oficial de la librería de Machine Learning `scikit-learn` para Python (clase `MLPClassifier`).
* La evidencia del entrenamiento y métricas ya se subió al repositorio en el archivo `resultados_entrenamiento.md`.