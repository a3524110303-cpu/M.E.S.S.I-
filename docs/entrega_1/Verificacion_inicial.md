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
recorrido completo. La instalación en el equipo local, la ejecución visual,
el entrenamiento local de la demostración y el piloto escolar siguen pendientes.

## Comprobación de la base publicada

La base se publicó en main mediante el commit
5a2216a851319586bebb89996ac626fa4ee39bde. La ejecución de
[GitHub Actions](https://github.com/a3524110303-cpu/M.E.S.S.I-/actions/runs/37148971608)
terminó correctamente: instaló requirements.txt en Windows con Python 3.13,
ejecutó la suite automatizada y comprobó la sintaxis. Esta comprobación confirma
la instalación conjunta en ese entorno; no sustituye el recorrido visual ni
la evaluación escolar del modelo.

Este registro prepara evidencia de la primera entrega. El informe QA 03 se
elaborará siguiendo su plantilla y reflejará las ejecuciones de la versión
que el equipo decida entregar.
