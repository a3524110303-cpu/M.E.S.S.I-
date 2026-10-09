# Validación del portal compartido MESSI

Fecha: 9 de octubre de 2026. Esta evidencia corresponde a la implementación
Django de `web/`; el prototipo Streamlit conserva su interfaz y pruebas propias.

## Adaptación para Streamlit Community Cloud

La entrada `cloud/app.py` utiliza los servicios Django con MySQL externo. El
9 de octubre se ejecutaron conjuntamente 125 pruebas de `portal.tests` y
`cloud.tests` contra MySQL 8.0.42: todas aprobadas, ninguna omitida, en 30.293
segundos. Los AppTest verifican los cuatro paneles autenticados, sesiones
independientes, privacidad del estudiante y del tutor, inicio de sesión real,
borrado de contraseña y cierre ante configuración ausente. También se prueba
la administración atómica, el bloqueo compartido y la configuración TLS.

Una prueba adicional del recorrido completo aprobó con MySQL en 4.569 segundos:
envió los formularios reales de captura e inferencia, solicitud, acuerdo y
seguimiento desde sesiones Streamlit distintas. El estudiante visualizó el
acuerdo y el avance sin las notas privadas. La suite contiene ahora 126 pruebas.

Tres pruebas adicionales de Excel verifican que la importación institucional
rechace códigos vacíos, conserve códigos explícitos y mantenga el comportamiento
del prototipo local. El certificado MySQL y Secrets permanecen fuera de Git.

Esta ejecución usa MySQL local de ensayo. La publicación final requiere el
acceso a Community Cloud y la creación de la base MySQL externa; no acredita
todavía una URL pública operativa. Véase [STREAMLIT_CLOUD.md](STREAMLIT_CLOUD.md).

## Pruebas automatizadas verificadas

Se ejecutó la suite completa de 79 pruebas contra MySQL 8.0.42 en una
instancia aislada, puerto local 33307: 79 aprobadas, ninguna omitida,
27.436 segundos y ninguna incidencia del chequeo de Django. Esta ejecución
incluyó los cinco escenarios de concurrencia con bloqueo real de filas.

La misma suite se ejecutó con SQLite en memoria habilitado deliberadamente
para pruebas: 74 aprobadas y 5 omitidas porque requieren bloqueo real
`SELECT FOR UPDATE`. Duración: 22.686 segundos. Esta segunda ejecución sirve
para desarrollo rápido; la evidencia de concurrencia procede de MySQL.

SQLite en estas pruebas no es el motor configurado para el despliegue:
producción exige MySQL y rechaza la opción de pruebas SQLite.

Comando desde la raíz del repositorio, en PowerShell:

```powershell
$env:MESSI_WEB_ENV = 'development'
$env:MESSI_WEB_TEST_SQLITE = '1'
$env:MESSI_WEB_SQLITE_PATH = ':memory:'
.\.venv-web\Scripts\python.exe web/manage.py test portal.tests --verbosity 1
```

La base temporal de Django se elimina al terminar. No se utilizó la base
de datos del prototipo para estas pruebas.

## Alcance comprobado

| Comportamiento | Verificación |
| --- | --- |
| Docente por asignación | Lee, captura, importa y exporta únicamente sus grupos. Cambiar un identificador no habilita grupos ajenos. |
| Estudiante autenticado | La solicitud usa su identidad y exige inscripción al periodo; la página académica contiene sólo sus indicadores. |
| Tutor por alumno y periodo | La asignación se compara por la pareja alumno/periodo; tener un alumno asignado en un periodo no permite consultar otro. |
| Cuentas y organización | La bandera `is_staff` no otorga administración a un docente. La administración no registra indicadores, solicitudes, casos ni notas privadas como modelos editables. |
| Tres sesiones independientes | Docente captura, estudiante solicita y tutor acuerda y registra seguimiento usando sesiones distintas sobre la misma base. El estudiante consulta el acuerdo y el avance. |
| Notas privadas | Ni las notas del caso ni las del seguimiento aparecen en las respuestas HTML del estudiante. El tutor asignado puede leerlas. |
| Entrada y salida seguras | Formularios con CSRF; texto público escapado en HTML; nombres que podrían ejecutarse como fórmulas de Excel se protegen en CSV. |
| Importación | Lote válido completo; fila inválida o versión atrasada revierte el lote. El formulario conserva versiones firmadas y vinculadas a usuario, grupo y corte. |
| Ediciones simultáneas | En MySQL, dos ediciones compiten y una recibe conflicto; dos altas iniciales no duplican indicadores; dos seguimientos no sobrescriben el caso; el bloqueo del inicio de sesión comparte un contador transaccional. |
| Alerta y edición concurrentes | Se obliga al docente a mantener el bloqueo de inscripción mientras el tutor intenta abrir el caso de alerta. La edición termina, el tutor rechaza la alerta desactualizada y no se produce un bloqueo cruzado. |
| Riesgo | El artefacto MLP existente ejecuta inferencia real. Se guardan datos de entrada, versión, hash del modelo, puntuación y umbral. El modelo rechaza cortes distintos del primer parcial. |
| Predicción desactualizada | Editar indicadores vuelve histórico el cálculo previo. Cambiar indicadores o modelo durante la inferencia descarta el resultado. Una alerta histórica no puede originar un caso nuevo. |
| Ausencia del modelo | Solicitudes, acuerdos y seguimiento siguen funcionando aunque la inferencia falle. |
| Duplicados | La misma solicitud no abre casos repetidos; repetir el cálculo de la misma versión no duplica la predicción. |
| Reasignación | Cambiar tutor transfiere casos del mismo alumno y periodo y aumenta la versión; el tutor anterior pierde acceso. |
| Intentos de acceso | Contadores compartidos por cuenta/IP e IP, bloqueo temporal con HTTP 429, desbloqueo después del intervalo y rechazo de cuentas inactivas. También se controla el acceso administrativo. |
| Producción | El arranque rechaza clave débil, hosts comodín, origen CSRF HTTP, falta de credenciales MySQL y SQLite. La configuración correcta activa HTTPS, cookies seguras y HSTS. |

Las pruebas de inferencia acreditan integración del modelo sintético con el
portal. No acreditan precisión con estudiantes reales ni superioridad frente
a otros métodos.

## Recorrido comprobado en el navegador

Con datos ficticios y cuentas diferenciadas se capturaron indicadores,
se ejecutó el MLP mediante el botón de la interfaz y se guardó una puntuación
demostrativa de 59.9 / 100. El estudiante envió una solicitud; el tutor creó
el caso y un seguimiento. Al volver a la cuenta del estudiante se visualizaron
el acuerdo y el avance y se comprobó la ausencia de la nota privada.

El navegador accedió al servidor HTTP de desarrollo. Esto acredita que las
pantallas ejecutan el flujo sobre MySQL compartido; no constituye una prueba
de publicación en internet ni de dispositivos físicos distintos.

## Respaldo y restauración comprobados

Se generó un respaldo MySQL real con `scripts/respaldo_web.py --local`
en `.qa/messi-web-final.sql`. Se restauró en el esquema independiente
`test_messi_web_20261009` y se compararon todas las filas y columnas de sus
24 tablas con el esquema de origen: coincidencia exacta.

El conjunto restaurado incluía un estudiante, indicador, predicción,
solicitud, caso y seguimiento, además de la estructura escolar, cuentas,
asignaciones y tablas de Django. El respaldo permanece fuera de Git.
Los comandos de validación no imprimieron contraseñas de la base.

## Configuración de producción comprobada

La imagen `Dockerfile.web` se construyó correctamente en Docker Desktop. Dentro
de Linux con MySQL 8.4, las mismas 79 pruebas aprobaron sin omisiones en
21.369 segundos y las migraciones se aplicaron correctamente. El chequeo de
producción dentro de la imagen tampoco reportó incidencias.

Se arrancó Gunicorn con dos trabajadores y configuración de producción en un
entorno aislado de validación. El acceso HTTP devolvió redirección 301; al
simular desde localhost la petición del proxy HTTPS, el formulario de acceso
y los estilos devolvieron 200. Esto verifica aplicación y recursos estáticos,
sin acreditar un certificado público ni una conexión HTTPS externa.

La configuración de Caddy también se validó con su imagen oficial: válida.
Los contenedores y volúmenes de validación se retiraron después de comprobar
el despliegue. El ensayo Windows/MySQL de la aplicación permanece disponible.

El ensayo de Windows escucha ahora en la red local. La página de acceso
respondió 200 por la IP Wi-Fi del servidor desde el propio equipo. Queda
pendiente comprobar un dispositivo físico diferente y su acceso por firewall.

Se ejecutó `manage.py check --deploy --database default` con configuración de
producción y un dominio de prueba: ninguna incidencia. También se probaron
rechazos de configuración incompleta y débil desde procesos independientes,
sin leer secretos de los archivos `.env` reales.

El chequeo verifica ajustes de Django y conexión a MySQL. No prueba emisión
de un certificado, resolución DNS ni conectividad pública.

## Comprobaciones pendientes fuera de las pruebas

- Publicar el despliegue con un dominio y certificado HTTPS y comprobarlo
  desde computadoras o teléfonos de personas distintas.
- Medir latencia, CPU, memoria y errores con una carga y concurrencia
  acordadas antes de afirmar capacidad institucional o ahorro de recursos.
- Definir los procedimientos institucionales de cuentas, acceso y atención;
  validar el modelo con datos reales autorizados antes de usar sus alertas
  como evidencia académica.

Las sesiones independientes automatizadas prueban el flujo compartido del
servidor. La accesibilidad desde internet, los certificados y la capacidad
bajo carga necesitan verificación en el alojamiento final.
