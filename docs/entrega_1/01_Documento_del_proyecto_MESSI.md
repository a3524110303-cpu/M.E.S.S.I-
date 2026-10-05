# Documento del proyecto MESSI

Entrega 1: prototipo funcional y repositorio. Actualización del 5 de octubre de 2026.

MESSI permite ingresar indicadores del primer parcial, calcular una puntuación de demostración y registrar solicitudes, apoyos y seguimiento. El prototipo está publicado y sus módulos se verificaron con datos sintéticos. La entrega del equipo requiere todavía reunir todas las aportaciones y completar la bitácora conjunta.

| Dato | Valor |
| --- | --- |
| Proyecto | MESSI Alerta y acompañamiento escolar |
| Integrantes | Marco Antonio Osorio Hernandez; Ismael Hernández Jiménez; Víctor Manuel Jiménez Suárez; Yokio Yosafat Vazquez Carrillo; Salomón Alvarez Gomez |
| Rama de IA | Redes neuronales |
| Repositorio | https://github.com/a3524110303-cpu/M.E.S.S.I- |
| Ejecución | Aplicación web local mediante Streamlit y MySQL |

## Responsabilidades del equipo para esta entrega

| Integrante | Responsabilidad principal |
| --- | --- |
| Marco Antonio Osorio Hernandez | Integración, almacenamiento y correcciones QA-03 a QA-05 |
| Ismael Hernández Jiménez | Datos sintéticos, modelo y evaluación de demostración |
| Víctor Manuel Jiménez Suárez | Pruebas, registro de defectos, evidencias y revalidación |
| Yokio Yosafat Vazquez Carrillo | Escenario, guion y demostración |
| Salomón Alvarez Gomez | Guía, instrucciones y capturas de la versión comprobada |

Todos pueden aportar código. Este reparto organiza el cierre de los entregables;
cada autor revisa y comprueba sus cambios y Marco integra las aportaciones revisadas.

## 1 Problemática a resolver

Al terminar el primer parcial, docentes y tutores necesitan reconocer qué estudiantes podrían requerir apoyo antes del cierre del curso. Revisar por separado calificación, asistencia y tareas dificulta organizar el seguimiento oportuno.

Una evaluación también puede reflejar barreras de acceso. Por eso, MESSI combina indicadores académicos con revisión humana y permite solicitar ayuda aunque no exista una alerta. La discapacidad y las notas personales del tutor no se utilizan para determinar automáticamente el riesgo.

## 2 Descripción del proyecto

El docente puede cargar Excel o CSV, pegar una tabla o capturar datos directamente. En captura puede ingresar porcentajes o cantidades de asistencias y tareas; el sistema convierte las cantidades a porcentajes y aplica las mismas validaciones.

Se utilizan un código ficticio de estudiante, nota del primer parcial de 0 a 10 y porcentajes de asistencia y tareas de 0 a 100. El código identifica los registros y no entra al modelo. La aplicación rechaza valores incompletos, códigos duplicados, fórmulas de Excel y totales inválidos.

La red utiliza las tres variables académicas. Muestra una puntuación y una alerta con umbral fijo 0.5 de demostración. El tutor revisa los indicadores, recibe solicitudes y registra tutorías, apoyos accesibles o contacto con orientación y su seguimiento. Las solicitudes y apoyos funcionan sin modelo entrenado cuando MySQL está configurado.

MySQL conserva estudiantes, indicadores por periodo, predicciones, solicitudes, apoyos y seguimiento. La creación del esquema es explícita; la cuenta de ejecución sólo necesita permisos de datos. SQLite se conserva para migrar el almacenamiento anterior y para pruebas.

El selector Docente/Tutor/Estudiante demuestra los flujos y no autentica personas. La versión utiliza datos sintéticos; no acredita eficacia escolar, precisión con estudiantes reales ni probabilidades calibradas.

## 3 Rama de IA

Se implementó una MLP supervisada con tres entradas y una capa oculta de ocho neuronas, precedida por StandardScaler. El escalador se ajusta con entrenamiento. `resultado_final` es la etiqueta de aprendizaje: 1 corresponde a reprobado y 0 a aprobado; nunca es una entrada de predicción.

El script `scripts/train_demo.py`, con semilla 2026, divide 240 registros sintéticos en 144 de entrenamiento, 48 de validación y 48 de prueba. Compara la MLP con la regla de nota menor que 6 y una regresión logística. La ejecución reproducida obtuvo 68.75 % de exactitud y 96.30 % de recall de riesgo para la MLP; estas cifras describen exclusivamente el conjunto sintético. No se ha demostrado superioridad de la red ni utilidad en un piloto escolar.

El modelo y sus metadatos se generan localmente en `models/messi_demo.joblib` y `models/messi_demo.json`. Se comprueban sus hashes y procedencia al cargarlo. No se publican los binarios en Git.

## 4 Caso de uso

**Usuarios:** docentes y tutores; estudiantes que solicitan apoyo.

**Situación:** revisión al terminar el primer parcial de una asignatura. En la demostración se utilizan ejemplos ficticios.

1. El docente carga datos, corrige los errores señalados y guarda los indicadores.
2. Con el modelo disponible, calcula la puntuación de demostración y obtiene el reporte CSV.
3. El tutor revisa indicadores y alertas; la decisión de apoyo corresponde a una persona.
4. El estudiante puede enviar una solicitud aunque no haya predicción o alerta.
5. El tutor registra el apoyo y su seguimiento. MySQL conserva la información al abrir otra sesión.

Facilitar apoyo oportuno es una meta por comprobar. La alerta no modifica calificaciones ni aplica sanciones.

## 5 Requisitos

| Componente | Requisito |
| --- | --- |
| Equipo | Windows para los accesos BAT; navegador y servicio MySQL local |
| Python | 3.11 a 3.13; los BAT seleccionan 3.13 |
| Base de datos | MySQL 8.0.16 o posterior; se probó MySQL 8.0.42 |
| Interfaz | Streamlit 1.50.0 |
| Datos | pandas 2.3.3, NumPy 2.3.3, openpyxl 3.1.5, pyarrow 21.0.0 |
| IA | scikit-learn 1.7.2, SciPy 1.16.2, joblib 1.5.2 |
| Conexión y configuración | mysql-connector-python 9.4.0, python-dotenv 1.1.1 |
| Instalación | Internet para descargar las dependencias fijadas en requirements.txt |

Las instrucciones detalladas de usuarios, permisos, esquema y migración están en [Base de datos](../base_de_datos.md).

## 6 Instalación y ejecución

La aplicación se abre en el navegador del equipo que inicia Streamlit. La dirección `http://127.0.0.1:8501` es local; no existe una URL pública ni un ejecutable `.exe`.

### 6.1 Instalación

1. Obtener una copia del repositorio y abrir su carpeta.
2. Instalar Python 3.13 y ejecutar `INSTALAR_MESSI.bat`.
3. Iniciar MySQL. Crear una base `messi` y una cuenta de aplicación conforme a la guía de base de datos.
4. Copiar `.env.example` a `.env` si todavía no existe y configurar host, puerto, usuario, contraseña y base. No publicar `.env`.
5. Ejecutar `scripts/init_database.py` con la cuenta autorizada para instalar el esquema. La base debe existir; `--create-database` autoriza expresamente su creación.
6. Utilizar después una cuenta con SELECT, INSERT, UPDATE y DELETE, sin permisos administrativos ni creación de tablas.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\init_database.py
```

La conexión habitual configurada en esta computadora fue rechazada al verificar el inicializador. Deben ajustarse sus credenciales y permisos localmente antes de usar esa base. La persistencia del código se comprobó en un servidor aislado y no sustituye esa configuración.

### 6.2 Ejecución

1. Ejecutar `ENTRENAR_DEMO.bat` para generar el modelo local con los datos sintéticos incluidos.
2. Ejecutar `INICIAR_MESSI.bat` y abrir `http://127.0.0.1:8501`.
3. En Docente, seleccionar Ejemplo sintético y cargarlo; también se puede usar la plantilla Excel, CSV, pegado o captura directa.
4. Guardar los indicadores y calcular el riesgo de demostración. Descargar el reporte si se necesita.
5. En Estudiante, enviar una solicitud ficticia. En Tutor, registrar un apoyo y un seguimiento.
6. Ejecutar `PROBAR_MESSI.bat`. Las siete pruebas MySQL reales requieren el servidor aislado y la configuración opt-in descrita en la evidencia de integración; sin ella se omiten expresamente.

Un envío inválido conserva los campos para corregirlos. Un envío válido limpia el formulario y mantiene visible la confirmación en la pantalla actualizada.

## 7 Lista de verificación

| Entregable | Ubicación | Estado |
| --- | --- | --- |
| Código y prototipo | app.py, src/messi y repositorio | Integración corregida; configuración habitual de MySQL pendiente |
| Documento del proyecto | Este documento | Actualizado con el funcionamiento real |
| Dependencias | requirements.txt | Versiones fijadas, instalación y pip check comprobados |
| Datos de prueba | data/synthetic | Excel y CSV ficticios incluidos |
| Pruebas | tests y Evidencia_integracion_Marco.md | 138 aprobadas con MySQL real; sin fallos esperados ni omisiones en esa ejecución |
| Historial compartido | GitHub | Aportaciones de Marco, Ismael y Víctor; faltan evidencias de Yokio y Salomón |
| Créditos y fuentes | README.md | Herramientas, datos sintéticos y asistencia de IA declarados; licencia del código del equipo pendiente de acuerdo |
| Bitácora | 06_Bitacora_de_prompts_Marco.md | Registro de Marco; pendiente consolidación con los registros reales del equipo |

La copia DOCX anterior y los documentos originales se conservan como referencias históricas. Este Markdown es la versión actualizada del documento 01 para la primera entrega.
