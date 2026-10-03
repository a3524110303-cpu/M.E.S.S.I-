# Datos de demostración de MESSI

Todos los registros de esta carpeta son **sintéticos**. Los identificadores no
corresponden a personas y `resultado_final` contiene etiquetas artificiales,
creadas por una fórmula con ruido. No constituyen evidencia de capacidad para
predecir resultados escolares reales.

| Archivo | Uso | Filas por defecto |
| --- | --- | --- |
| `students_demo.csv` | Probar carga y presentación; sin etiqueta final | 8 |
| `training_synthetic.csv` | Probar entrenamiento y comparación didáctica | 240 |

Contrato de entrada:

- `id_estudiante`: identificador anónimo `EST-` seguido de 3 a 8 dígitos, único.
- `nota_parcial`: número entre 0 y 10.
- `asistencia`: porcentaje entre 0 y 100.
- `tareas_entregadas`: porcentaje entre 0 y 100.
- `resultado_final`: sólo entrenamiento; `1` = reprobado, `0` = aprobado.

El lector admite CSV UTF-8 (con o sin BOM) de hasta 5 MB y 10,000 filas. Rechaza
columnas adicionales, nombres, correos u otros datos sensibles, valores vacíos,
identificadores repetidos y números no finitos o fuera de rango. Un CSV de
inferencia no debe incluir `resultado_final` para evitar filtración de la etiqueta.
Los porcentajes deben usar la escala 0–100, no fracciones; el separador es coma y
el separador decimal es punto.

Para regenerar los mismos CSV desde la raíz del proyecto:

```powershell
python scripts/generate_synthetic.py --seed 2026 --rows 240
```

La generación usa únicamente la biblioteca estándar. `--seed` modifica los datos
simulados; el valor predeterminado es 2026. El CSV pequeño contiene ejemplos fijos.

Después de instalar los requisitos, la demostración opcional se entrena con:

```powershell
python scripts/train_demo.py --seed 2026
```

Se separan entrenamiento, validación y prueba (60/20/20) antes de ajustar los
escaladores. Se comparan una regla `nota_parcial < 6`, regresión logística y una
red MLP de una capa oculta con 8 neuronas. `resultado_final` es sólo la etiqueta,
nunca una entrada de los modelos. El umbral 0.5 de la IA es de demostración y no
está validado con datos reales. Las métricas de validación y prueba se guardan
junto con semilla, versiones, distribución de clases y hashes de procedencia en
`models/messi_demo.json`. El MLP se guarda localmente en `models/messi_demo.joblib`.
El artefacto no debe versionarse, enviarse ni cargarse desde fuentes desconocidas.

Cambiar el contenido del CSV artificial no lo convierte en un conjunto real
autorizado. La primera entrega no debe procesar expedientes personales. Una alerta
sirve para mostrar el flujo de acompañamiento y requiere valoración humana.
