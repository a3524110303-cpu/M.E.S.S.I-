# Reparto de trabajo: Entrega 2 de MESSI

Preparado el 6 de octubre de 2026. **Entrega: 8 de octubre de 2026, durante la hora de clase.**

Objetivo: que otra persona pueda comprender y modificar MESSI con el código
documentado y el manual, y comprobar sus resultados con el informe de QA.
Las tareas siguientes están asignadas; no se consideran realizadas hasta
que cada responsable entregue su aportación y evidencia.

## Versión común que se documentará

La versión actual funciona con Streamlit, una MLP local y SQLite. Incluye
instalador para Windows 10/11 Intel/AMD x64. MySQL es una implementación
histórica y opcional, no un requisito del funcionamiento actual.

Marco coordina una misma versión del código y el instalador antes de que los
demás documenten o prueben. La preparación está en `codex/messi-local-windows`;
al integrarse en `main`, todos deben actualizar su copia desde esa versión.
Registrar el commit compartido y usarlo en ambos documentos y en las evidencias
de QA. La publicación no acredita que cada integrante ya haya actualizado su copia.

## Responsabilidad de cada integrante

| Integrante y rol confirmado | Trabajo concreto | Producto que entrega | Revisión |
| --- | --- | --- | --- |
| **Marco Antonio Osorio Hernandez — líder técnico y desarrollador** | Elaborar la arquitectura y el diagrama entrada/procesamiento/salida; describir interfaz, SQLite, arranque y empaquetado; redactar cómo modificar y reconstruir el sistema. Documentar clases y funciones de sus módulos y coordinar las correcciones. | Contenido de secciones **1 y 5**, parte técnica de **2**; código documentado; versión común para probar y entregar. | Ismael revisa contratos e integración; Víctor revalida correcciones. |
| **Ismael Hernández Jiménez — investigador y analista** | Explicar la elección de la MLP frente a los métodos base, parámetros reales, entrenamiento y límites; describir origen sintético, campos, rangos y separación de datos. Documentar funciones de datos y modelo y reunir las fuentes de sus dependencias. | Contenido de secciones **3 y 4**, módulos de datos/modelo para **2**, fuentes para **6** y evidencia de entrenamiento. | Yokio revisa claridad; Marco comprueba correspondencia con el código. |
| **Víctor Manuel Jiménez Suárez — QA y pruebas** | Diseñar y ejecutar casos; registrar entradas, resultados esperados y obtenidos, errores, correcciones y repetición de pruebas. Consolidar evidencias de todos y verificar que las instrucciones del manual funcionen. Documentar las pruebas para que puedan repetirse. | **03_Informe_de_prueba.docx** completo con sus cinco secciones, logs y casos trazables. | Marco revisa cobertura técnica; Salomón revisa plantilla y coherencia documental. |
| **Yokio Yosafat Vazquez Carrillo — vocero principal** | Preparar un escenario ficticio reproducible; probar el instalador y recorrido en otra computadora disponible; comprobar cierre, reapertura y recuperación de registros. Ensayar una explicación breve de arquitectura, IA y resultados de QA. | Evidencia de instalación/recorrido para Víctor; observaciones de claridad para Salomón; guion breve de presentación. | Víctor valida sus resultados; Salomón comprueba que el guion corresponda al manual. |
| **Salomón Alvarez Gomez — documentación** | Integrar los aportes en la plantilla original del manual; mantener títulos y orden; completar portada, versiones y créditos. Revisar nombres, comentarios y docstrings con los autores, referencias, tablas y diagrama. Comprobar formato del informe de QA sin alterar resultados. | **02_Manual_del_programador.docx** completo; revisión de formato de **03_Informe_de_prueba.docx**; lista final de archivos. | Víctor sigue las instrucciones; Marco confirma la exactitud técnica. |

Salomón integra el manual, pero cada autor entrega la descripción y documentación
de su componente. Víctor consolida QA, pero todos aportan las pruebas y evidencias
de su trabajo. Yokio participa desde la instalación y la comprobación; su aporte
no se limita a exponer.

## Manual 02: reparto en el orden obligatorio

Usar una copia de `docs/referencias/02_Manual_del_programador.docx`.
Conservar sus títulos, subsecciones, tablas y orden. Completar los datos de
portada y eliminar las instrucciones y filas de ejemplo al cerrar el documento.

| Orden y tema | Autor principal / integración | Contenido y criterio de terminación |
| --- | --- | --- |
| **1. Arquitectura general** | Marco / Salomón | Diagrama de entrada → validación/normalización → MLP → salida, con SQLite para indicadores, predicciones, solicitudes, apoyos y seguimiento. Mostrar que solicitar ayuda funciona sin modelo. Explicar recursos del instalador frente a datos del usuario y ejecución en navegador local. |
| **2. Descripción de módulos y funciones principales** | Marco e Ismael; todos describen sus archivos / Salomón | Completar la tabla de módulo/archivo, función/clase, descripción, entradas y salidas. Incluir interfaz, datos, modelo, persistencia, arranque, diagnóstico y construcción; indicar dónde están las pruebas. Los nombres deben coincidir con el código actual. |
| **3. Explicación del algoritmo o modelo** | Ismael / Salomón | Respetar **3.1 Por qué se eligió** y **3.2 Parámetros que se ajustan**. Describir StandardScaler y MLP, tres variables y ocho neuronas ocultas; verificar en el código semilla, entrenamiento, iteraciones y umbral. Distinguir pesos aprendidos de hiperparámetros configurados. Comparar con regla de nota y regresión logística sin afirmar superioridad no demostrada. |
| **4. Formato y origen de los datos** | Ismael / Salomón | Tabla de archivo/dataset, origen o autor, formato y campos. ID seudónimo; nota 0–10; asistencia y tareas 0–100; `resultado_final` sólo en entrenamiento. Explicar captura por conteos, CSV, XLSX y pegado, generación sintética y división entrenamiento/validación/prueba. |
| **5. Cómo extender o modificar el proyecto** | Marco con Ismael / Salomón | Pasos para preparar el entorno de desarrollo, agregar una función, añadir o cambiar un campo con su validación y almacenamiento, cambiar/reentrenar el modelo, ejecutar pruebas y reconstruir el instalador. Explicar respaldo y evolución de SQLite sin pérdida de registros. |
| **6. Créditos y licencias de las dependencias** | Salomón; Marco e Ismael aportan fuentes | Completar dependencia, versión real, licencia y fuente oficial. Revisar `requirements.txt`, `requirements-build.txt` e `installer/TERCEROS.md`; incluir Python, Streamlit, scikit-learn, pandas, NumPy, SciPy, joblib, openpyxl, pyarrow, python-dotenv, PyInstaller, Inno Setup y Tcl/Tk según su uso. Separar herramientas de construcción de dependencias del cliente. Declarar origen sintético, aportes reales y asistencia de IA; la licencia del código propio requiere acuerdo del equipo. |

El documento describe el sistema implementado. No presentar como implementados
los microservicios del diseño de referencia ni como vigente el requisito MySQL
de la primera entrega. El selector de roles no autentica personas y el modelo
sintético no acredita eficacia escolar.

## Código documentado: tarea de todos

| Responsable | Archivos principales que revisará |
| --- | --- |
| Marco | `app.py`, `messi_desktop.py`, `src/messi/sqlite_storage.py`, `storage.py`, `storage_validation.py`, `paths.py`, `desktop.py`, `windows_process.py`, `MESSI.spec` y `scripts/build_windows.ps1`. |
| Ismael | `src/messi/data.py`, `model.py`, `scripts/generate_synthetic.py` y `scripts/train_demo.py`. |
| Víctor | `src/messi/diagnostics.py` y pruebas en `tests/`; aclarar preparaciones, propósito de casos y condiciones para omitir pruebas históricas de MySQL. |
| Yokio | Escenario y procedimiento de comprobación: pasos, datos de entrada y resultados esperados, revisados con Víctor. Si aporta un script, documentarlo también. |
| Salomón | Auditar consistencia entre docstrings, nombres del código y tablas del manual; devolver faltantes al autor y reunir la revisión final. |

Para funciones y clases Python, revisar o completar docstrings que expliquen
propósito, argumentos, unidades/rangos, retorno, errores y efectos persistentes
cuando corresponda. Comentar decisiones que no sean evidentes: invalidación de
predicciones, transacciones, respaldo WAL, verificación del modelo y cierre del
servidor. Mantener nombres claros; evitar comentarios que sólo repitan una línea.
Si se modifica código además de documentarlo, repetir las pruebas afectadas.

## Informe 03: trabajo de Víctor con evidencias del equipo

Usar una copia de `docs/referencias/03_Informe_de_pruebas_QA.docx` y guardar el
resultado con el nombre solicitado **03_Informe_de_prueba.docx**. Conservar:

1. **Alcance y entorno de pruebas:** versión/commit, sistema operativo, Python
   y dependencias o instalador, navegador usado y alcance realmente ejecutado.
2. **Casos de prueba:** ID, caso, entradas concretas, resultado esperado,
   resultado obtenido y estado. Vincular log, captura o reporte de la ejecución.
3. **Errores encontrados y corregidos:** ID, descripción, caso relacionado,
   gravedad, corrección realizada, responsable y estado; incluir revalidación.
4. **Resumen de resultados:** totales coherentes con la matriz; separar casos
   aprobados, fallidos y no ejecutados, y errores corregidos y pendientes.
5. **Conclusiones:** qué se comprobó, límites y pendientes de la versión entregada.

| Grupo de casos mínimos | Quién ejecuta y aporta evidencia | Qué comprobar |
| --- | --- | --- |
| Captura, CSV, XLSX y pegado | Víctor con Ismael | Equivalencia entre entradas válidas; límites, faltantes, duplicados, fórmulas y conteos con total cero. |
| Modelo | Ismael; Víctor contrasta | Entrenamiento reproducible; predicción y umbral; ID/etiqueta fuera de las entradas; error útil con modelo ausente o inválido. |
| SQLite y flujos | Víctor con Marco | Guardar/reabrir indicadores y predicciones; invalidar predicciones al cambiar indicadores; solicitar ayuda sin modelo; apoyo, seguimiento y respaldo/restauración en una base de prueba. |
| Interfaz y defectos anteriores | Víctor | Confirmación visible, campos conservados ante entrada inválida y revalidación de QA-03 a QA-05 contra la versión actual. |
| Instalador y otra computadora | Yokio con Víctor | Instalación, arranque sin Python/MySQL/internet, recorrido completo, cierre y reapertura. Actualización y conservación de datos; registrar Windows, arquitectura y navegador reales. |
| Manual reproducible | Yokio y Víctor con Salomón | Seguir instrucciones sin ayuda del autor; anotar pasos ambiguos y comprobar las correcciones antes del cierre. |

Hay evidencia previa disponible en `docs/instalacion_local_windows.md` y en
`release/verificacion-*.json`: 151 pruebas automatizadas, 144 aprobadas y 7 de
MySQL omitidas; comprobaciones del paquete y de instalación/actualización/
desinstalación en Windows 11. Víctor debe identificar la fecha, autor/origen y
versión de esas ejecuciones; no atribuirlas a una ejecución propia. Una prueba
omitida no cuenta como aprobada. Windows 10 y la computadora del cliente siguen
pendientes hasta ejecutar allí los casos. No inventar resultados ni capturas.

## Secuencia de trabajo hasta la entrega

| Fecha | Trabajo de cada responsable | Resultado necesario |
| --- | --- | --- |
| **6 de octubre** | Marco comparte la versión común y prepara secciones 1/5; Ismael 3/4; Víctor prepara la matriz; Yokio reúne equipo/escenario; Salomón prepara copias de plantillas y portada. | Versión identificada y borradores con responsables. |
| **7 de octubre** | Todos completan docstrings/notas; Víctor e Ismael ejecutan casos; Yokio prueba la instalación en otro equipo; Marco corrige; Salomón integra 02 y revisa el formato de 03. | Código documentado, documentos completos y evidencia real. |
| **8 de octubre, antes de clase** | Revisión cruzada, repetición de casos corregidos y ensayo de Yokio; Marco comprueba la versión final; Salomón revisa nombres/portadas; Víctor confirma totales. | Carpeta final lista para entregar en la hora clase. |

Carga orientativa: **4 horas por integrante** (2 de preparación, 1 de
comprobación y 1 de revisión/integración), ajustable a disponibilidad y fallos
encontrados. Si una tarea se extiende, Marco redistribuye el apoyo con el equipo.
No medir la contribución sólo por cantidad de commits.

## Lista de cierre

- Código documentado de la misma versión descrita y probada, sin contraseñas,
  `.env`, entornos virtuales ni datos personales en la entrega.
- `docs/entrega_2/02_Manual_del_programador.docx`, requisitado con los seis temas
  y la estructura de la plantilla original.
- `docs/entrega_2/03_Informe_de_prueba.docx`, requisitado con resultados,
  correcciones y pendientes trazables a evidencias.
- Evidencias en `docs/entrega_2/evidencias/`, con fecha, entorno y versión.
- Revisión técnica de Marco e Ismael, validación de Víctor, comprobación del
  recorrido de Yokio y revisión documental de Salomón registradas.
- Cada autor aporta sus cambios con su identidad real. Marco integra la versión
  revisada; este reparto no publica archivos ni envía mensajes al equipo.
