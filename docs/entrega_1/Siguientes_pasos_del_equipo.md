# Siguientes pasos del equipo para la primera entrega

Fecha: 3 de octubre de 2026. La base ya incluye los módulos de ingreso, el
entrenamiento de demostración, la interfaz y el almacenamiento. Las actividades
de esta etapa consisten en revisar esa base, ejecutarla, corregir los problemas
observados y completar las evidencias de la primera entrega. El mapa general
mantiene las estimaciones y la revisión cruzada acordadas.

## Inicio común para los cinco integrantes

Marco comprueba que todos tengan acceso para contribuir al repositorio. Cada
integrante obtiene la base de main, configura Git con su nombre y correo reales
y trabaja en su propia rama. En otro equipo se puede comenzar así, sustituyendo
la rama del ejemplo por la asignada en la tabla:

```powershell
git clone https://github.com/a3524110303-cpu/M.E.S.S.I-.git MESSI
Set-Location MESSI
git switch -c codex/ismael-entrega-1
```

En Windows, ejecutar INSTALAR_MESSI.bat una vez e INICIAR_MESSI.bat para abrir
el prototipo. Leer el README y recorrer las vistas con información ficticia.
Cada persona realiza un cambio útil en su responsabilidad, guarda su evidencia
de ejecución y solicita revisión. Un commit debe representar trabajo propio
revisado; no se crean contribuciones de relleno para completar la lista.

| Integrante | Rama sugerida | Revisor |
| --- | --- | --- |
| Marco Antonio Osorio Hernandez | codex/marco-entrega-1 | Ismael |
| Ismael Hernández Jiménez | codex/ismael-entrega-1 | Yokio |
| Víctor Manuel Jiménez Suárez | codex/victor-entrega-1 | Marco |
| Yokio Yosafat Vazquez Carrillo | codex/yokio-entrega-1 | Salomón |
| Salomón Alvarez Gomez | codex/salomon-entrega-1 | Víctor |

## Marco líder técnico y desarrollador

Revisar la conexión entre app.py, data.py, model.py y storage.py. Ejecutar el
recorrido de ingreso docente, solicitud de ayuda, registro de apoyo y
seguimiento; comprobar que un apoyo siga disponible después de reiniciar y
que se pueda pedir ayuda antes de entrenar la red. Corregir los fallos de
integración observados y revisar las aportaciones que se incorporan a main.

Actualizar el documento 01 y el README con el enlace del repositorio y los
pasos realmente comprobados de instalación y ejecución. El documento actual
todavía describe el estado anterior al prototipo. Incorporar la versión
completada de la bitácora 06 que el equipo ya tiene; el adjunto conservado es
una plantilla. Acordar con el equipo la licencia del código propio.

**Aporte esperado:** corrección o mejora de integración revisada, documento 01
actualizado y recorrido reproducible en una versión común.

## Ismael investigador y analista

Revisar el contrato de ingreso y el generador de datos sintéticos. Comprobar
que los datos de Excel, pegado, CSV y captura equivalente den los mismos
indicadores. Verificar que el ID y resultado_final nunca sean entradas del
modelo y que las notas de apoyo permanezcan fuera de la IA.

Tras instalar dependencias, ejecutar ENTRENAR_DEMO.bat. Revisar los resultados
de models/messi_demo.json: separación de entrenamiento, validación y prueba,
MLP de ocho neuronas, regla de nota y regresión logística. Registrar métricas,
límites y la condición sintética en un resumen legible dentro de
docs/entrega_1/Evaluacion_demo.md. Mantener la revisión humana y el umbral de
demostración sin atribuirle validez escolar.

**Aporte esperado:** mejora revisada en datos o entrenamiento y resumen de
una ejecución real de la demostración, con sus fuentes y limitaciones.

## Víctor QA y pruebas

Ejecutar PROBAR_MESSI.bat después de instalar dependencias y registrar la
salida y el entorno en docs/entrega_1/Evidencia_pruebas.md. La comprobación
inicial obtuvo 50 aprobados y una integración MLP omitida; al instalar IA
esa prueba debe ejecutarse. Un caso omitido sigue pendiente.

Comprobar también la interfaz real: archivo válido, Excel con fórmula, campo
vacío, ID duplicado, nota o porcentaje fuera de rango, conteos con total cero,
modelo ausente y solicitud sin alerta. Si encuentra un error, añadir una
prueba que lo reproduzca, registrar el defecto y repetir el caso después de
la corrección. Revisar los cambios de interfaz de Salomón.

**Aporte esperado:** casos nuevos o mejoras de pruebas a partir de fallos
reales, resultados ejecutados y defectos con su estado. Esta evidencia servirá
después para el informe QA 03.

## Yokio vocero principal

Seguir la instalación desde una copia del repositorio y anotar cualquier paso
confuso. Preparar un escenario pequeño en la plantilla Excel con estudiantes
ficticios y conservarlo como data/synthetic/escenario_presentacion.xlsx o CSV.
Comprobar su ingreso, el caso de ayuda sin alerta y el seguimiento.

Escribir docs/entrega_1/Guion_demostracion.md con el recorrido que realmente
funcione: problema, ingreso sencillo, alerta de demostración, revisión del
tutor y apoyo. Explicar que la red usa datos sintéticos y no se ha probado
su eficacia escolar. Revisar la claridad del material de Ismael.

**Aporte esperado:** escenario probado, guion y mejoras concretas de
instrucciones. La preparación técnica de la demostración cuenta como aporte;
el rol de vocero no se limita a hablar durante la exposición.

## Salomón desarrollo y documentación

Recorrer la interfaz con el escenario de Yokio. Comprobar carga de Excel,
captura directa por porcentajes o conteos y pegado de tabla. Revisar etiquetas,
mensajes, navegación con teclado y corrección de datos. Implementar mejoras
que permitan usar los flujos sin conocimientos de programación y sin perder
filas capturadas al introducir una fila inválida.

Completar docs/entrega_1/Guia_rapida.md con los pasos y capturas de la versión
que haya ejecutado: abrir, ingresar datos, interpretar el resultado ficticio,
solicitar ayuda y registrar seguimiento. Revisar el guion de Yokio. Ese material
servirá para el futuro manual 04.

**Aporte esperado:** mejora revisada de interfaz y guía basada en pantallas
existentes y comprobadas.

## Incorporar cada aporte

Guardar y subir los cambios de la rama con la identidad propia. Ejemplo para
Ismael; se deben seleccionar los archivos que efectivamente modificó:

```powershell
git add src/messi/data.py docs/entrega_1/Evaluacion_demo.md
git commit -m "Revisar datos y documentar evaluacion sintetica"
git push -u origin codex/ismael-entrega-1
```

Abrir una solicitud de cambios hacia main en GitHub, adjuntar el resultado de
las pruebas y pedir revisión a la persona indicada. Marco integra los cambios
revisados; cada autor atiende las observaciones de su aportación.

## Cierre de la primera entrega

Confirmar en una misma versión: documento 01 coherente, prototipo ejecutado,
red de demostración entrenada y probada, dependencias instaladas, ejemplos de
datos, resultados de pruebas, créditos y licencias, bitácora existente y
contribuciones reales de los cinco integrantes. El equipo confirma la fecha
límite y decide la versión de main que presentará.

Los manuales 02 y 03 corresponden a la entrega 2; el manual 04 y la prueba
con persona ajena 05 corresponden a la entrega 3. Se conserva el trabajo
existente del 06 y su reflexión final se completa en la entrega 4.
