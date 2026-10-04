# Análisis de los Resultados de Entrenamiento (Demo M.E.S.S.I.)
Fecha: 4 de octubre de 2026

1. Actividades Realizadas
Se ejecutó el script ENTRENAR_DEMO.bat para entrenar la red neuronal. Con esto se procesaron los datos de prueba y se generó exitosamente el modelo de demostración del sistema.

2. Datos y Variables Analizadas
Se utilizó un set de datos sintéticos (datos simulados para esta fase), dividido en: 144 registros para entrenamiento, 48 para validación y 48 para pruebas. 
* **Regla básica:** Toma únicamente la variable de la calificación (`nota_parcial`) y asume que cualquier valor menor a 6 representa un riesgo.
* **Red Neuronal (IA):** Analiza múltiples variables internas al mismo tiempo para calcular la probabilidad de que un alumno repruebe. Para esta demostración, el sistema usó un umbral fijo de 0.5; es decir, si la red calcula un 50% o más de probabilidad de fracaso, lanza la alerta de riesgo.

3. Resultados de los Entrenamientos
Al comparar los distintos métodos, la consola arrojó los siguientes resultados:
* **Regla básica (Nota < 6):** Alcanzó un 87.5% de exactitud. Funciona bien como un filtro rápido y tradicional, pero no es capaz de predecir a futuro ni analizar el contexto del alumno.
* **Regresión Logística:** Obtuvo un 100% de exactitud perfecta. Aunque suena positivo, en inteligencia artificial esto es un claro caso de "sobreajuste". Como los datos simulados son demasiado predecibles, el modelo simplemente memorizó las respuestas en lugar de aprender a encontrar patrones reales.
* **Red Neuronal (MLP_8):** Tuvo una exactitud general del 68.8%, pero lo más destacado es que logró un Recall de riesgo del 96.3%. 
*¿Qué significa este Recall tan alto?* Significa que la red neuronal es sumamente preventiva. El modelo prefiere equivocarse lanzando una "falsa alarma" (marcando a un estudiante seguro como si estuviera en riesgo), antes que cometer el grave error de ignorar a un alumno que realmente va a reprobar y necesita ayuda. Para nuestro objetivo de alertas tempranas, esta alta sensibilidad es exactamente lo que buscamos.

4. Conclusión
El proceso de entrenamiento funciona de manera correcta y el modelo se genera sin fallas. La prueba demuestra que la red neuronal cumple su propósito principal: detectar a la gran mayoría de los alumnos vulnerables (alto Recall). Sin embargo, para comprobar la verdadera utilidad del sistema y evitar que los modelos solo memoricen información (como ocurrió con la regresión logística), el siguiente paso indispensable será reemplazar esta información simulada por el historial de calificaciones reales de los estudiantes.