# MESSI Alerta y acompañamiento escolar

Base de la primera entrega del equipo MESSI. El docente ingresa indicadores del
primer parcial; el tutor revisa los casos y registra apoyos y seguimiento; el
estudiante puede solicitar ayuda aunque no haya alerta ni modelo disponible.

El prototipo es una demostración local con datos sintéticos. El selector de
roles sirve para demostrar los flujos; la autenticación y los permisos de un
piloto escolar están pendientes. No usar datos de estudiantes reales en esta
versión. Una alerta no cambia calificaciones ni aplica sanciones.

## Empezar en Windows

1. Abre esta carpeta del escritorio: `C:\Users\user\Desktop\MESSI`.
2. Ejecuta `INSTALAR_MESSI.bat` una vez. Crea un entorno privado `.venv` e
   instala las versiones de `requirements.txt`. Requiere internet.
3. Ejecuta `INICIAR_MESSI.bat`. Abre `http://127.0.0.1:8501` en el navegador.
4. En Docente, elige **Ejemplo sintético** y pulsa **Cargar ejemplo sintético**.
   También puedes descargar la plantilla Excel, capturar datos directamente o
   pegar una tabla. En Estudiante, registra una solicitud ficticia. En Tutor,
   registra un apoyo y su seguimiento.
5. Para activar la IA de demostración, ejecuta `ENTRENAR_DEMO.bat`; vuelve a la
   vista Docente y pulsa **Calcular riesgo de demostración**.
6. Ejecuta `PROBAR_MESSI.bat` para comprobar todos los módulos instalados.

Python 3.13 ya se encontró en este equipo. Faltan Streamlit y scikit-learn;
la instalación de paquetes queda a cargo del usuario mediante el primer paso.
La versión admite Python 3.11 a 3.13; los accesos de Windows seleccionan 3.13.

También se puede ejecutar desde PowerShell:

```powershell
Set-Location 'C:\Users\user\Desktop\MESSI'
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No hace falta instalar Node, Docker ni un motor externo de base de datos.
SQLite viene con Python. La aplicación sólo escucha en el equipo local.

## Equipo y actividades

Se conservan los roles confirmados de la ficha del Bloque 1 Parte II.
El mapa completo contiene tareas, dependencias, revisores, criterios de aceptación
y una estimación orientativa equivalente por integrante:
[Mapa de actividades](docs/planificacion/Mapa_de_actividades_MESSI.md).
Para continuar sobre la base existente, consultar
[Siguientes pasos de cada integrante](docs/entrega_1/Siguientes_pasos_del_equipo.md).

| Integrante | Rol confirmado | Trabajo inmediato |
| --- | --- | --- |
| Marco Antonio Osorio Hernandez | Líder técnico y desarrollador | Integración, almacenamiento y revisión del contrato de IA |
| Ismael Hernández Jiménez | Investigador y analista | Datos sintéticos, fuentes, modelo y comparación con métodos base |
| Víctor Manuel Jiménez Suárez | QA y pruebas | Casos válidos e inválidos, evidencia y revisión del flujo completo |
| Yokio Yosafat Vazquez Carrillo | Vocero principal | Guion y escenarios de demostración, comprobación de instrucciones |
| Salomón Alvarez Gomez | Desarrollo y documentación | Interfaz, mensajes de ayuda y guía del flujo |

## Estructura

```text
app.py                         Interfaz Streamlit con tres vistas de demostración
src/messi/data.py              Validación de Excel, CSV, pegado y captura
src/messi/model.py             Inferencia opcional y comprobación de metadatos
src/messi/storage.py           Solicitudes, apoyos y seguimiento SQLite
scripts/generate_synthetic.py  Generador reproducible de datos ficticios
scripts/train_demo.py          Entrenamiento opcional y evaluación sintética
data/synthetic/                Datos ficticios para carga y entrenamiento
data/private/                  Base local ignorada por Git
models/                        Modelo local ignorado por Git
tests/                         Pruebas automatizadas
docs/planificacion/            Mapa de actividades del equipo
docs/entrega_1/                Documento 1 existente y estado de la entrega
docs/entrega_2/                Espacio para manual del programador y QA
docs/entrega_3/                Espacio para manual y prueba con persona ajena
docs/referencias/              Copias intactas de documentos y referencias
```

## Ingreso para docentes

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

Las solicitudes y las notas del tutor se almacenan por separado en SQLite y no
forman parte de las variables del modelo. El contexto sensible y la discapacidad
no determinan automáticamente el riesgo. Los indicadores observados no son una
explicación causal de una predicción.

## Validación y estado real

Verificación inicial: 50 casos aprobados, ninguno fallido y una integración
MLP omitida por dependencias faltantes. Excel, CSV, pegado y conteos manuales
produjeron registros equivalentes sobre la plantilla real. La interfaz real
todavía está pendiente de instalar y ejecutar. Detalle en
[Verificación inicial](docs/entrega_1/Verificacion_inicial.md).

Las pruebas de contrato y almacenamiento pueden ejecutarse sin instalar la
interfaz ni IA:

```powershell
py -3.13 -m unittest discover -s tests -v
```

Las pruebas que necesitan scikit-learn o Streamlit deben ejecutarse después de
instalar dependencias; un caso omitido no cuenta como aprobado.
El estado y pendientes de la primera entrega están en
[Estado de la entrega](docs/entrega_1/Estado_de_la_entrega.md).
La instalación completa, la ejecución visual y el entrenamiento todavía requieren
verificación en el entorno `.venv`. No hay un modelo escolar validado ni una URL
pública. La base del repositorio sirve para iniciar las contribuciones y reunir
las evidencias de la primera entrega.

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

Equipo: Marco Antonio Osorio Hernandez, Ismael Hernández Jiménez, Víctor Manuel
Jiménez Suárez, Yokio Yosafat Vazquez Carrillo y Salomón Alvarez Gomez.
Herramienta de asistencia para preparar esta base: Codex. Cada responsable debe
comprender, revisar y comprobar el código asignado antes de entregar.

## Dependencias y licencias

Versiones directas fijadas y publicaciones comprobadas en PyPI. La instalación
conjunta se comprobó en GitHub Actions con Windows y Python 3.13; la instalación
en el equipo local sigue pendiente. Las licencias de dependencias no otorgan
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

La propuesta de microservicios encontrada en las referencias queda como línea
de evolución. Esta base implementa el stack de la entrega 1 adjunta; no presenta
gRPC, RBAC, concurrencia institucional ni explicaciones XAI como funciones hechas.
