# Transcripción del video de demostración de MESSI

Recorrido narrado con capturas reales de la aplicación y voz sintética genérica. No es una grabación de una persona ni una prueba externa.

## 01 Acompañamiento desde el primer parcial

Presentamos MESSI, una aplicación local de alerta y acompañamiento escolar. El problema es que las dificultades pueden detectarse tarde, cuando ya se acumuló una baja calificación o pocas entregas. Este proyecto reúne indicadores del primer parcial para orientar una revisión del tutor. El recorrido utiliza capturas reales de la aplicación y narración sintética, con información completamente ficticia.

## 02 Un caso ficticio y tres indicadores

Nuestro caso de demostración es un grupo ficticio. Cada estudiante se identifica con un código, sin nombre ni expediente. Se registran la nota parcial, la asistencia y las tareas entregadas. Una nota baja o pocos porcentajes pueden motivar una conversación de apoyo. La decisión corresponde al tutor; la aplicación no modifica calificaciones ni aplica sanciones.

## 03 Ingresar y revisar los datos

En la vista Docente elegimos cómo ingresar los datos. MESSI admite una plantilla de Excel, un CSV, una tabla pegada, captura directa y un ejemplo sintético. La nota debe estar entre cero y diez, y los porcentajes entre cero y cien. La pantalla confirma cuántos registros son válidos y permite comprobarlos antes de continuar. Los códigos enlazan después los apoyos.

## 04 Rechazar datos fuera de rango

La validación rechaza valores fuera de rango, identificadores duplicados, datos faltantes y fórmulas en Excel. Aquí pegamos una fila ficticia con nota doce, que supera el máximo de diez. La aplicación señala el campo que debe corregirse. Para continuar hay que corregir el dato y volver a revisar la tabla. Esta entrada inválida no genera una predicción.

## 05 Calcular la puntuación de demostración

Al pulsar Calcular riesgo de demostración, el programa usa una red neuronal con una capa de ocho neuronas y un escalador. El modelo recibe únicamente los tres indicadores. No recibe el código del estudiante ni la etiqueta final usada al entrenar. La alerta se activa cuando la puntuación es mayor o igual a cero punto cinco, el umbral de esta demostración.

## 06 Interpretar la salida y descargar el reporte

La salida conserva los indicadores y añade una puntuación entre cero y uno y una marca para revisar el caso con un tutor. El botón Descargar reporte genera un CSV. Los indicadores y predicciones se guardan en la base local SQLite. Si cambian los indicadores, una predicción anterior debe recalcularse. La puntuación orienta esta simulación; no es una probabilidad escolar validada.

## 07 Solicitar apoyo aunque no haya alerta

En la vista Estudiante registramos una solicitud ficticia de ayuda. Esta función está disponible aunque no exista alerta ni predicción. El mensaje se valida y, al guardarse, la pantalla muestra una confirmación. Así, la búsqueda de apoyo no depende de que la inteligencia artificial identifique primero un riesgo. En este recorrido sólo se utilizan códigos y mensajes de demostración.

## 08 Acordar un apoyo y conservar su seguimiento

El tutor consulta las solicitudes, registra un acuerdo y selecciona el apoyo para agregar seguimiento. Los estados permiten distinguir pendiente, en seguimiento y cerrado. La captura muestra el historial y el estado de seguimiento guardado. SQLite conserva solicitudes, acuerdos y seguimiento al volver a abrir la aplicación. Esta persistencia permite revisar qué se acordó, sin depender de una sola sesión del navegador.

## 09 Qué demuestran los resultados sintéticos

El entrenamiento separó ciento cuarenta y cuatro registros para ajuste, cuarenta y ocho para validación y cuarenta y ocho para prueba. En prueba, la red detectó veintiséis de veintisiete riesgos artificiales, pero produjo catorce falsas alarmas. Su exactitud fue de sesenta y ocho punto setenta y cinco por ciento. El recall alto no prueba eficacia real, y el MLP se conserva por el alcance didáctico.

## 10 Alcance de la entrega y próximos pasos

MESSI se entrega como demostración local para Windows, con aplicación, ejecutable, instalador y manuales. El selector de roles no autentica usuarios y los datos son sintéticos. Las mejoras futuras requieren datos reales autorizados, validación, calibración y control de acceso. Este video documenta el recorrido mediante capturas reales; no sustituye una prueba con persona ajena al equipo ni inventa su opinión o conformidad.
