# MESSI Alerta y acompañamiento escolar

Versión local **0.4.0** preparada para las entregas 2 y 3 del equipo MESSI.
El docente ingresa indicadores del
primer parcial; el tutor revisa los casos y registra apoyos y seguimiento; el
estudiante puede solicitar ayuda aunque no haya alerta ni modelo disponible.

La navegación lateral organiza las vistas Docente, Tutor y Estudiante. El
docente ve pasos de carga, guardado y cálculo que reflejan el estado de sus
datos; el tutor consulta cifras de solicitudes, apoyos activos y casos para
revisar, con tablas en español y fechas locales. Puede leer una solicitud por
folio y usar su código para preparar el acuerdo; el apoyo se guarda al enviarlo.
La ventana de escritorio
agrupa apertura, respaldo, diagnóstico y cierre.

Documento de alcance de la primera entrega:
[Documento del proyecto 01](docs/entrega_1/01_Documento_del_proyecto_MESSI.md).
La copia DOCX anterior conserva el diseño original como referencia histórica.
La descripción de los roles, los datos y el flujo funcional está en
[Funcionalidad del proyecto](docs/funcionalidad.md).

Los manuales y formatos del profesor están en
[entrega 2](docs/entrega_2/README.md) y [entrega 3](docs/entrega_3/README.md).
La [lista de cotejo](docs/entrega_3/Verificacion_de_entregas_2_y_3.md) relaciona
cada requisito del examen con su archivo y evidencia. **La prueba con una persona
ajena sigue pendiente:** el equipo confirmó el 8 de octubre que aún no la ha
realizado. El formato 05 contiene un protocolo preparado, sin resultados inventados.
El [video de MESSI 0.4.0, de 4:25](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/download/v0.4.0-interfaz/MESSI_Demo_Entrega_3.mp4)
ya está generado y validado con capturas de la interfaz actual, narración
sintética y subtítulos. El instalador y portable están publicados en la
[versión 0.4.0](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.4.0-interfaz).
La página y descargas principales respondieron HTTP 200 sin autenticación;
el hash del video descargado coincide con el archivo final.
[Comprobación de acceso público](docs/entrega_3/evidencias/publicacion_0.4.0.json).
La
[versión 0.3.0](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.3.0-entregas)
se conserva como historial, con acceso HTTP 200 comprobado.

El prototipo es una demostración local con datos sintéticos. El selector de
roles sirve para demostrar los flujos; la autenticación y los permisos de un
piloto escolar están pendientes. No usar datos de estudiantes reales en esta
versión. Una alerta no cambia calificaciones ni aplica sanciones.

## Usar MESSI en Windows 10 y 11

Para el cliente, entrega **`release/MESSI-Setup-Windows-x64.exe`**. El instalador
[se descarga de la versión 0.4.0 de GitHub](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.4.0-interfaz).
El instalador
incluye Python, librerías, SQLite y el modelo neuronal ya entrenado. Basta con
Siguiente, Instalar y Finalizar; después abrir MESSI desde el acceso directo.
Funciona sin internet, MySQL ni configuración de contraseñas. La aplicación
se abre en el navegador local y la ventana de control permite cerrarla,
guardar un respaldo o generar un diagnóstico.

La base se crea automáticamente en
`%LOCALAPPDATA%\MESSI\data\messi.sqlite3`, separada de la instalación.
Se conservan los datos al actualizar o desinstalar. Cada equipo y usuario tienen
su propia base; no hay sincronización automática entre computadoras.

El paquete es para Intel/AMD x64 con Windows 10 versión 2004 o posterior,
o Windows 11. Se recomiendan 4 GB de RAM, 1 GB libre y un navegador instalado.
No requiere GPU dedicada.
La interfaz y el paquete 0.4.0 se comprobaron en Windows 11 x64, con ejecución
instalada sin Python en `PATH` y conservación de la base al actualizar. Windows
10 y una segunda computadora aún requieren una prueba física.

Para reconstruir el instalador en desarrollo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Esta computadora necesita Python 3.13 x64 e Inno Setup 6. El cliente no necesita
instalarlos. La versión portable requiere copiar **toda** `dist/MESSI`.

Para ejecutar desde el código: `INSTALAR_MESSI.bat` instala dependencias y genera
el modelo si falta; `INICIAR_MESSI.bat` abre MESSI. `PROBAR_MESSI.bat` ejecuta las
pruebas. La IA usa únicamente datos y librerías locales.

[Guía de instalación, archivos que mover y cambios de código](docs/instalacion_local_windows.md).
La [guía MySQL](docs/base_de_datos.md) y sus scripts quedan como documentación de
la versión anterior; la interfaz actual usa SQLite e ignora las credenciales MySQL.

## Equipo y actividades

**Entrega 2 — 8 de octubre de 2026, durante la hora de clase:**
[reparto del código documentado, manual 02 e informe QA 03](docs/entrega_2/Reparto_del_equipo.md).

El reparto para cerrar esta entrega se actualizó el 5 de octubre de 2026.
Todos pueden aportar código; los roles indican la responsabilidad principal
de cada integrante para reunir y revisar los entregables.
El mapa completo contiene tareas, dependencias, revisores, criterios de aceptación
y una estimación orientativa equivalente por integrante:
[Mapa de actividades](docs/planificacion/Mapa_de_actividades_MESSI.md).
Para continuar sobre la base existente, consultar
[Siguientes pasos de cada integrante](docs/entrega_1/Siguientes_pasos_del_equipo.md).

| Integrante | Rol confirmado | Trabajo inmediato |
| --- | --- | --- |
| Marco Antonio Osorio Hernandez | Líder técnico y desarrollador | Integración, almacenamiento y correcciones QA-03 a QA-05 |
| Ismael Hernández Jiménez | Investigador y analista | Datos sintéticos, fuentes, modelo y comparación con métodos base |
| Víctor Manuel Jiménez Suárez | QA y pruebas | Casos válidos e inválidos, evidencia y revisión del flujo completo |
| Yokio Yosafat Vazquez Carrillo | Vocero principal | Guion y escenarios de demostración, comprobación de instrucciones |
| Salomón Alvarez Gomez | Documentación | Guía del flujo, instrucciones y capturas de la versión comprobada |

## Estructura

```text
app.py                         Interfaz Streamlit con tres vistas de demostración
src/messi/presentation.py      Navegación, pasos, presentación y tablas en español
src/messi/data.py              Validación de Excel, CSV, pegado y captura
src/messi/model.py             Inferencia opcional y comprobación de metadatos
src/messi/paths.py             Recursos incluidos y datos por usuario
src/messi/sqlite_storage.py    Persistencia local completa y respaldos
src/messi/desktop.py           Ventana de control y servidor local incluido
messi_desktop.py              Entrada del ejecutable y diagnóstico
MESSI.spec                    Empaquetado de Python, recursos y modelo
installer/MESSI.iss            Instalador Windows 10/11
scripts/build_windows.ps1     Construcción y comprobación del paquete
src/messi/database.py          Herramientas históricas MySQL
src/messi/mysql_storage.py     Adaptador histórico MySQL opcional
src/messi/esquema_mysql.sql    Tablas, índices, restricciones y relaciones
src/messi/storage.py           Contrato base de solicitudes, apoyos y seguimientos
scripts/init_database.py      Inicialización explícita del esquema MySQL
scripts/migrate_sqlite.py      Importación opcional del almacenamiento legado
scripts/manage_mysql_users.py Administración de cuentas y permisos de MySQL
scripts/generate_synthetic.py  Generador reproducible de datos ficticios
scripts/train_demo.py          Entrenamiento opcional y evaluación sintética
data/synthetic/                Datos ficticios para carga y entrenamiento
data/private/                  Archivos privados y SQLite legado, ignorados por Git
.env.example                   Plantilla sin credenciales reales
docs/base_de_datos.md          Configuración, esquema y migración a MySQL
models/                        Modelo local, incluido al construir el instalador
tests/                         Pruebas automatizadas
docs/planificacion/            Mapa de actividades del equipo
docs/entrega_1/                Documento 1 existente y estado de la entrega
docs/entrega_2/                Manual del programador, QA y evidencias actuales
docs/entrega_3/                Manual de usuario, nota pendiente, guion y capturas
docs/referencias/              Copias intactas de documentos y referencias
```

## Ingreso para docentes

Tres pasos visibles separan **cargar y revisar**, **guardar indicadores** y
**calcular y descargar**. El paso de guardado se confirma cuando SQLite acepta
el conjunto o cuando se recupera de la base. Un resultado disponible en sesión
se distingue de un resultado guardado; un error de escritura mantiene el aviso
de que no se guardó. Cambiar datos o rechazar un pegado invalida el progreso
correspondiente y los resultados anteriores.

Las cifras muestran estudiantes, nota y asistencia promedio y casos marcados
para revisar. Se calculan a partir de los indicadores visibles; no representan
eficacia escolar ni decisiones tomadas por una persona.

La vista Docente ofrece cuatro opciones. **Excel o CSV** permite descargar
`data/synthetic/Plantilla_MESSI.xlsx`, reemplazar sus ejemplos, guardar y cargar
el archivo. La hoja Datos tiene los encabezados Código del estudiante (en la
plantilla, ID estudiante), Nota primer parcial, Asistencia (%) y Tareas
entregadas (%). Escribe valores numéricos y usa 80 para 80 %, sin fórmulas.
La hoja Instrucciones explica los pasos. Los archivos .xls deben guardarse
como .xlsx antes de cargarlos.

**Captura directa** permite agregar un estudiante por vez. Puedes escribir
porcentajes o cantidades registradas: sesiones asistidas e impartidas y tareas
entregadas y solicitadas. MESSI calcula los porcentajes; los totales deben ser
mayores que cero y las cantidades no pueden superarlos. La nota sigue siendo
la calificación del primer parcial, en escala de 0 a 10.

**Pegar tabla** admite filas copiadas desde Excel. Puedes pegar los cuatro
encabezados de la plantilla, cuatro columnas sin encabezados o sólo tres
columnas de nota, asistencia y tareas. También admite punto y coma como
separador, por ejemplo `5,8;70;50`. Permite coma decimal en texto pegado.
Excel y pegado reciben porcentajes; la entrada por conteos se realiza en
Captura directa.

En Excel, pegado y captura se asigna un código temporal cuando falta el ID.
Conserva códigos estables como EST-001 para el seguimiento; los códigos
automáticos no enlazan listas distintas de forma fiable.

**Guardar indicadores** conserva la lista validada en SQLite para el periodo
`primer_parcial`; **Cargar indicadores guardados** recupera los datos persistidos.
Importar o capturar una lista sólo la coloca en la sesión hasta guardarla. Al
calcular el riesgo se intenta conservar también la predicción: si falla la
escritura en SQLite, el resultado calculado permanece en la sesión y la aplicación avisa
que no se guardó. La vista Tutor puede recuperar indicadores y predicciones
guardados cuando la sesión está vacía.

## Contrato de datos

El CSV de predicción contiene exactamente estas cuatro columnas:

```csv
id_estudiante,nota_parcial,asistencia,tareas_entregadas
EST-001,5.8,70,50
```

La nota se expresa de 0 a 10 y los porcentajes de 0 a 100. Se admite punto
decimal. El identificador ficticio usa `EST-` seguido de 3 a 8 dígitos; no entra
al modelo. La escala de nota es una decisión inicial a verificar con la escuela.
El entrenamiento añade `resultado_final`: **1 = reprobado, 0 = aprobado**.
Esa etiqueta nunca se usa como entrada de predicción. Se rechazan registros
vacíos, identificadores repetidos, campos adicionales y valores fuera de rango.

La red MLP propuesta tiene tres entradas y ocho neuronas ocultas. El escalado se
ajusta sólo con entrenamiento. La demostración separa entrenamiento, validación
y prueba, y compara MLP, regresión logística y una regla basada en nota.
El umbral sintético no acredita validez escolar. El documento técnico del modelo
se genera al ejecutar el entrenamiento y registra su procedencia sintética.

SQLite relaciona estudiantes, indicadores y predicciones, y conserva solicitudes,
apoyos y seguimientos. Las solicitudes y las notas del tutor no forman parte de
las variables del modelo. El contexto sensible y la discapacidad
no determinan automáticamente el riesgo. Los indicadores observados no son una
explicación causal de una predicción.

## Validación y estado real

La versión **0.4.0** mejora la jerarquía de tareas, el progreso de Docente, los
resúmenes de datos, las tablas de Tutor y la ventana de control. Conserva el
modelo, SQLite y los contratos de captura, validación y acompañamiento. Una
regresión nueva confirma que el progreso se restablece al rechazar datos; otra
comprueba que las tablas en español conservan intactos los registros de SQLite.
Las mejoras de aislamiento y cierre del servidor introducidas en 0.3.0 se
mantienen.
La revisión de Ismael confirmó aportes de comentarios y manual, sin cambios de
lógica; se precisó la interpretación de métricas, puntuación y checksum.
El informe de Víctor se contrastó con su commit y con una ejecución nueva.
[Revisión de ambos aportes](docs/entrega_2/Revision_Ismael_y_Victor_2026-10-08.md).

La suite actual descubrió **161 pruebas: 154 aprobadas, siete MySQL omitidas y
cero fallidas**. Las omisiones requieren un servidor MySQL y no se cuentan como
aprobaciones. La aplicación cliente usa SQLite.
[Registro de pruebas](docs/entrega_2/evidencias/pruebas_actuales.txt).
El registro histórico de **0.3.0** incluye GitHub Actions en Windows (150
aprobadas, siete MySQL omitidas) y Linux con MySQL real (157 aprobadas, ninguna
omitida). Se corrigió una comparación de alias temporales de Windows en una
prueba, sin cambiar la app. [Ejecución CI de 0.3.0](https://github.com/a3524110303-cpu/M.E.S.S.I-/actions/runs/37753609896).
El CI de **0.4.0**, commit `dd4a001`, también terminó correctamente: Windows
descubrió 161 pruebas, con 154 aprobadas y siete MySQL omitidas; Ubuntu con
MySQL real aprobó las 161, sin omisiones ni fallos.
[Ejecución actual](https://github.com/a3524110303-cpu/M.E.S.S.I-/actions/runs/37763609648)
y [evidencia con logs reales](docs/entrega_2/evidencias/ci_github_0.4.0.json).

El self-test de fuente **0.4.0** comprobó ocho predicciones sintéticas,
persistencia, respaldo, tres vistas y reapertura.
[Verificación de fuente](docs/entrega_2/evidencias/verificacion_fuente_self_test.json).
El ejecutable y la actualización instalada **0.4.0** se comprobaron sin Python
en `PATH`. La actualización terminó con código 0 y conservó el hash de la base;
incluye lectura/copia de solicitudes y el contraste final del detalle.
[Actualización instalada](docs/entrega_2/evidencias/actualizacion_instalador.json),
[self-test instalado](docs/entrega_2/evidencias/instalado-self-test.json) y
[servidor instalado](docs/entrega_2/evidencias/instalado-smoke-server.json).
La [comprobación final](docs/entrega_2/evidencias/verificacion_instalado_final.json)
confirma que la copia instalada de `app.py` es idéntica a la fuente final.
El `release/MESSI-Portable-Windows-x64.zip` conserva los 3 355 archivos de
`dist/MESSI`, con inventario, CRC y SHA-256 comprobados. Extrae la carpeta
completa antes de abrir `MESSI.exe`.
[Verificación del portable](docs/entrega_2/evidencias/paquete_portable.json).
La prueba aislada de instalar y desinstalar abortó de forma segura al detectar
la instalación habitual; no se presenta como ejecutada en esta versión.

El recorrido manual en navegador incluye entrada, validación, cálculo, solicitud,
apoyo y seguimiento con información ficticia. La actualización 0.4.0 reúne
[capturas de la interfaz](docs/entrega_3/evidencias/capturas_interfaz_04/), los
formatos del profesor y el video del diseño actual. Los archivos se reúnen en
`MESSI_0.4.0` en el escritorio. El video dura 265.23 segundos, es Full HD con
H.264/AAC y conserva el orden de problema, demostración, resultados y límites.
[Verificación del video](docs/entrega_3/evidencias/verificacion_video_demo.json).
Las pruebas anteriores se conservan
como historial y no sustituyen la evidencia de la versión nueva.


El 5 de octubre se integraron las aportaciones de Ismael y Víctor con la
persistencia MySQL de Marco y las correcciones QA-03, QA-04 y QA-05.
La ejecución local con servidor MySQL aislado aprobó **138 pruebas**, sin
errores, omisiones ni fallos esperados. Se verificaron también instalación,
`pip check` y sintaxis. Evidencia y límites en
[Integración de Marco](docs/entrega_1/Evidencia_integracion_Marco.md).
GitHub Actions comprueba además Windows y MySQL 8.0 en Linux.

Los formularios conservan los valores cuando falla un envío y se limpian
únicamente después de guardarlo o aceptar la fila. La confirmación del
seguimiento permanece después de actualizar la pantalla. Los cambios de
interfaz se registran como aportación de integración de Marco.

La verificación inicial registró 50 casos aprobados, ninguno fallido y una
integración MLP omitida por dependencias faltantes. Excel, CSV, pegado y conteos manuales
produjeron registros equivalentes sobre la plantilla real. La interfaz no se
ejecutó en esa comprobación inicial. Detalle en
[Verificación inicial](docs/entrega_1/Verificacion_inicial.md).

Las pruebas de contrato y almacenamiento pueden ejecutarse sin instalar la
interfaz ni IA. Los casos del adaptador MySQL que usan conexiones simuladas
comprueban el contrato, pero no acreditan una conexión al servidor:

```powershell
py -3.13 -m unittest discover -s tests -v
```

Las pruebas que necesitan scikit-learn o Streamlit deben ejecutarse después de
instalar dependencias; un caso omitido no cuenta como aprobado.
El estado y pendientes de la primera entrega están en
[Estado de la entrega](docs/entrega_1/Estado_de_la_entrega.md).
El modelo se entrenó y evaluó con datos sintéticos reproducibles. No hay un
modelo validado para un colegio real; el servidor de la aplicación es local.

La puesta en marcha de MySQL se comprueba por separado con las credenciales de
esta instalación, el inicializador y un recorrido de guardar y recuperar datos.
La existencia del servicio MySQL no demuestra que la base esté inicializada.
Si hay un SQLite anterior de MESSI, su importación es explícita; no se declara
migrado hasta ejecutar el procedimiento de la guía y verificar sus conteos.

El adaptador MySQL se verificó con cinco pruebas reales en un servidor aislado
MySQL 8.0.42, puerto 13307; también se comprobó el cambio entre permisos de
edición y lectura y el bloqueo de cuentas. La conexión del servidor principal
en 3306 continúa pendiente de su configuración local. Esta validación no
declara realizada la importación del SQLite anterior.

## Colaboración y créditos

[Repositorio del equipo](https://github.com/a3524110303-cpu/M.E.S.S.I-).
La base compartida se publica en `main`; el trabajo local inicial se preparó
en `codex/entrega-1`. Cada integrante debe
realizar y revisar sus contribuciones usando su identidad real de Git; se debe
conservar evidencia del trabajo y sus pruebas. No atribuir a los integrantes
commits de código que todavía no han revisado o desarrollado.

La primera entrega exige documento del proyecto, código, dependencias, datos de
prueba, historial de contribuciones de todos, créditos y bitácora. Las plantillas
02 y 03 corresponden a la entrega 2; las 04 y 05 a la entrega 3. La reflexión del
06 se completa en la entrega 4. Los documentos existentes se conservan intactos.
La versión completada de la bitácora 6 mencionada por el equipo debe colocarse
cuando esté disponible; el adjunto 6 es una plantilla sin llenar.
Los prompts reales de esta revisión y corrección de Marco están en
[Bitácora de Marco](docs/entrega_1/06_Bitacora_de_prompts_Marco.md).
Ese registro no sustituye los aportes individuales pendientes del equipo.

Equipo: Marco Antonio Osorio Hernandez, Ismael Hernández Jiménez, Víctor Manuel
Jiménez Suárez, Yokio Yosafat Vazquez Carrillo y Salomón Alvarez Gomez.
Herramienta de asistencia para preparar esta base: Codex. Cada responsable debe
comprender, revisar y comprobar el código asignado antes de entregar.
La integración, los formatos y el video del 8 de octubre fueron preparados con
asistencia de Codex. Las pruebas nuevas pertenecen a esta sesión técnica; no se
atribuyen como observaciones humanas de Víctor ni como prueba de una persona externa.

## Dependencias y licencias

Versiones directas fijadas y publicaciones comprobadas en PyPI. La comprobación
inicial en GitHub Actions utilizó Windows y Python 3.13; la incorporación de
MySQL tiene las verificaciones separadas descritas arriba. Las licencias de dependencias no otorgan
automáticamente una licencia al código del equipo; ésta queda por acordar.

| Dependencia | Versión | Licencia | Fuente |
| --- | --- | --- | --- |
| Streamlit | 1.50.0 | Apache 2.0 | [Publicación oficial](https://pypi.org/project/streamlit/1.50.0/) |
| pandas | 2.3.3 | BSD 3 Clause | [Publicación oficial](https://pypi.org/project/pandas/2.3.3/) |
| scikit-learn | 1.7.2 | BSD 3 Clause | [Publicación oficial](https://pypi.org/project/scikit-learn/1.7.2/) |
| NumPy | 2.3.3 | BSD 3 Clause | [Publicación oficial](https://pypi.org/project/numpy/2.3.3/) |
| SciPy | 1.16.2 | BSD 3 Clause | [Publicación oficial](https://pypi.org/project/scipy/1.16.2/) |
| joblib | 1.5.2 | BSD 3 Clause | [Publicación oficial](https://pypi.org/project/joblib/1.5.2/) |
| openpyxl | 3.1.5 | MIT | [Publicación oficial](https://pypi.org/project/openpyxl/3.1.5/) |
| pyarrow | 21.0.0 | Apache 2.0 | [Publicación oficial](https://pypi.org/project/pyarrow/21.0.0/) |
| python-dotenv | 1.1.1 | BSD 3 Clause | [Publicación oficial](https://pypi.org/project/python-dotenv/1.1.1/) |

La propuesta de microservicios encontrada en las referencias queda como línea
de evolución. Esta base implementa el stack de la entrega 1 adjunta; no presenta
gRPC, RBAC, concurrencia institucional ni explicaciones XAI como funciones hechas.
