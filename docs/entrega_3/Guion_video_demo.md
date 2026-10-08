# Guion del video de demostración de MESSI

Recorrido de aproximadamente cuatro minutos para la entrega 3. El orden es problema y caso, demostración de entrada proceso y salida, resultados e interpretación, limitaciones y mejoras. Se utilizan capturas reales del funcionamiento de MESSI, acompañadas de voz sintética genérica en español de México y subtítulos.

Este material no presenta una persona ficticia como integrante del equipo, no imita la voz de una persona y no acredita una prueba con persona ajena. Las acciones representadas deben haber sido realizadas en la aplicación antes de incorporar sus capturas. El video se etiqueta como recorrido narrado mediante capturas reales.

| Escena | Contenido mostrado | Narración y propósito |
| --- | --- | --- |
| 1 | Inicio de la vista Docente | Presentar el problema de detectar dificultades tarde y el propósito de acompañamiento. |
| 2 | Tabla de un grupo ficticio | Explicar códigos anónimos, nota, asistencia y tareas. |
| 3 | Datos válidos ingresados | Describir Excel, CSV, pegado y captura; rangos y confirmación antes de procesar. |
| 4 | Pegado con nota 12 y mensaje de rechazo | Mostrar validación de rango. Esta captura no comprueba retención de filas ni la corrección QA-04 de captura directa. |
| 5 | Predicción real de la demo | Explicar escalador, red de ocho neuronas, tres indicadores y umbral inclusivo 0.5. |
| 6 | Resultado y botón de reporte | Interpretar puntuación, alerta, CSV y conservación local. |
| 7 | Solicitud del estudiante registrada | Mostrar acceso al apoyo sin exigir alerta ni predicción. |
| 8 | Seguimiento del tutor guardado | Mostrar acuerdo, estado de seguimiento e historial conservado. |
| 9 | Resultado real de predicción | Interpretar la evaluación sintética: 26 TP, 1 FN, 14 FP y 7 TN en 48 casos. |
| 10 | Ventana real de control de MESSI local | Cerrar con el paquete Windows, límites, validación futura y control de acceso. |

La narración completa está en `Transcripcion_video_demo.md`; su estructura reproducible está en `Narracion_video_demo.json`. Los subtítulos finales se generan como `MESSI_Demo_Entrega_3.srt`, además de incrustarse en el video.

## Producción y verificación

Ejecutar `scripts/build_demo_video.py` con el Python bundled de Codex y dependencias `Pillow`, `edge_tts` e `imageio_ffmpeg`. `--prepare` genera narración y transcripción; `--audio-only` sintetiza la voz. La generación del MP4 exige que existan todas las capturas referidas. `--screens archivo.json` permite mapear cada ID de escena a un nombre de captura real sin reconstruir la interfaz.

Las capturas se escalan conservando proporción y se centran en un lienzo Full HD. Los títulos y subtítulos ocupan bandas independientes de la interfaz. El audio usa una voz genérica de síntesis; si el servicio no está disponible, el script intenta una voz española genérica instalada de Windows SAPI. Se registra el motor utilizado por escena.

La salida es `release/MESSI_Demo_Entrega_3.mp4`, H.264 con audio AAC. El script mide la duración con FFmpeg y exige entre 180 y 300 segundos. El archivo `evidencias/verificacion_video_demo.json` registra duración, resolución, hashes del video y capturas, escenas y tipo de voz. La revisión final debe comprobar reproducción con audio, legibilidad de las capturas y subtítulos, y coherencia de las acciones narradas con las imágenes reales.
