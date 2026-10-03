# Modelos locales de demostración

`scripts/train_demo.py` generará aquí el modelo de demostración y sus metadatos,
después de instalar las dependencias. Estos archivos no se publican en Git.
La aplicación muestra que la predicción está pendiente cuando no hay modelo.

El entrenamiento usa datos sintéticos. Sus métricas no prueban eficacia en una
escuela. No cargar archivos joblib de terceros: su deserialización ejecuta código.
La aplicación sólo debe usar el artefacto producido por el script local.

Antes de un piloto hacen falta datos escolares autorizados, separación por
estudiante y periodo, umbral validado, comparación con métodos base y evaluación
del desempeño. Los tres indicadores observados no explican causalmente la red.
