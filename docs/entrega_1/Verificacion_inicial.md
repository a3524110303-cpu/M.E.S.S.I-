# Verificación inicial de MESSI

Fecha: 3 de octubre de 2026. Alcance: esqueleto local de la primera entrega.

Se ejecutó `python -m unittest discover -s tests` en Windows con el Python 3.13.13
existente y con Python 3.12.14 del entorno de herramientas. En ambos entornos
hubo **51 casos: 50 aprobados, 0 fallidos y 1 omitido**. El omitido corresponde
a la integración real de la MLP, porque no está instalado scikit-learn.

Los casos aprobados comprueban el contrato de CSV, Excel, pegado y captura,
rangos, valores vacíos y no finitos, duplicados, rechazo de fórmulas y columnas
extra, conversión de conteos, metadatos del modelo, persistencia SQLite y
transacciones de seguimiento. Las regresiones de la interfaz se probaron con
controles simulados; esa ejecución no comprueba el comportamiento visual de
Streamlit ni sus interacciones reales.

La plantilla Excel final se abrió con el lector del sistema: sus tres filas
produjeron los mismos registros que CSV y tabla pegada; el primer registro
también coincidió con la conversión de conteos manuales. Las dos hojas de la
plantilla se renderizaron y revisaron visualmente. Se comprobó que sus valores
son numéricos, el encabezado está congelado y no contiene fórmulas.

La comprobación de sintaxis de app.py, src, scripts y tests terminó sin errores.
Las copias de los documentos 01 de MESSI y 06 adjunto coinciden byte por byte
con sus originales de Descargas. No se agregó una entrada a la bitácora.

## Comprobaciones pendientes

Ejecutar INSTALAR_MESSI.bat para instalar las versiones fijadas en un entorno
privado. Después comprobar la interfaz real, teclado y mensajes; ejecutar
ENTRENAR_DEMO.bat y PROBAR_MESSI.bat; registrar las métricas sintéticas y el
recorrido completo. La instalación conjunta, la MLP real, el piloto escolar
y la publicación en GitHub no se presentan como verificados.

Este registro prepara evidencia de la primera entrega. El informe QA 03 se
elaborará siguiendo su plantilla y reflejará las ejecuciones de la versión
que el equipo decida entregar.
