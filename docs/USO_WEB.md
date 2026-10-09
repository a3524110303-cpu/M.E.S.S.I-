# MESSI web: acceso compartido y despliegue

MESSI web permite que docentes, estudiantes y tutores entren desde sus propios
dispositivos. Una aplicación Django recibe las solicitudes y guarda la información
en MySQL. Cada cuenta tiene un rol y sólo puede acceder a sus registros asignados.
La aplicación de escritorio anterior continúa disponible como prototipo local;
sus archivos SQLite no se convierten ni se importan automáticamente al portal.

## Arquitectura implementada

```text
Navegadores de docente / estudiante / tutor / administrador
                      ↓ HTTPS
                  Proxy Caddy
                      ↓ red privada
                 Django + Gunicorn
                      ↓ red privada
             MySQL 8.4 + volumen persistente
```

El servidor central puede estar en una escuela o en un proveedor de alojamiento.
No se instala Python ni una base de datos en cada dispositivo del usuario.
Windows también puede ejecutar la aplicación mediante Waitress para ensayos.

La red neuronal permanece como componente de demostración. Los indicadores y
predicciones guardan su versión para reconocer una alerta anterior a una edición.
Las solicitudes de apoyo y el seguimiento funcionan aunque el modelo no esté
disponible. Los datos sintéticos y sus métricas no validan eficacia educativa.

## Ensayo con MySQL en Windows

Se necesita Python 3.13 de 64 bits y MySQL 8.0.11 o posterior. Desde PowerShell,
en la raíz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_web.ps1
```

El script crea `.venv-web`, instala `requirements-web.txt`, genera la demostración
si falta y crea `web/.env` con una clave aleatoria si ese archivo no existe. No
reescribe archivos de configuración existentes. La configuración de escritorio
en `.env` es independiente.

Crea una base nueva y una cuenta específica desde MySQL Workbench o el cliente
MySQL, sustituyendo la contraseña del siguiente ejemplo:

```sql
CREATE DATABASE messi_web CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'messi_web'@'localhost' IDENTIFIED BY 'ELIGE_UNA_CLAVE_PRIVADA';
GRANT ALL PRIVILEGES ON messi_web.* TO 'messi_web'@'localhost';
```

Completa `MESSI_WEB_DB_*` en `web/.env`. Usa `MESSI_WEB_ENV=development` para
el ensayo, y agrega a `MESSI_WEB_ALLOWED_HOSTS` la IP del equipo servidor,
por ejemplo `localhost,127.0.0.1,192.168.1.20`. El navegador debe usar esa misma
IP. No uses `*`. En una red escolar controlada, permite el puerto 8000 en el
firewall únicamente en el perfil y la red requeridos.

```powershell
.\.venv-web\Scripts\python.exe web\manage.py check --database default
.\.venv-web\Scripts\python.exe web\manage.py migrate
.\.venv-web\Scripts\python.exe web\manage.py createsuperuser
powershell -ExecutionPolicy Bypass -File scripts\iniciar_web.ps1 -BindAddress 0.0.0.0 -Port 8000
```

`createsuperuser` solicita la contraseña de forma interactiva. El servidor
escucha mientras permanezca abierto el proceso; Ctrl+C lo detiene. Cada equipo
de la red entra a `http://IP_DEL_SERVIDOR:8000`. HTTP de desarrollo sólo sirve
para ensayar con datos ficticios; la configuración de publicación exige HTTPS.
No ejecutes el modo de desarrollo en un servidor público.

En el equipo donde se implementó este cambio también quedó una instancia de
ensayo aislada en `.qa/mysql-web`, puerto `33307`, con su configuración privada
en `web/.env`. Después de reiniciar ese equipo puedes levantarla con
`powershell -ExecutionPolicy Bypass -File scripts\iniciar_mysql_demo.ps1` y luego
ejecutar `scripts\iniciar_web.ps1`. Este auxiliar sólo arranca la instancia
previamente preparada; no crea credenciales y no interviene en el servicio
MySQL80 del equipo. En otro servidor sigue la instalación normal o Compose.

En este equipo también puedes abrir `INICIAR_MESSI_WEB.bat` para arrancar
el ensayo. Usa cuentas ficticias y los hosts permitidos configurados en
`web/.env`. Si cambió la IP del servidor, actualiza esa lista. Si el servidor
ya está abierto en el puerto 8000, usa la página existente.

## Configurar cuentas y escuela

Abre `/admin/` con el administrador creado. Sólo un superusuario o una cuenta
de administrador con permiso de personal puede entrar a esta consola.

1. Crea los usuarios de docente, estudiante y tutor con contraseñas individuales.
   Mantén desactivados sus permisos de personal y superusuario. Crea para cada
   uno su **Perfil** con el rol correspondiente. Comparte sus credenciales por
   un medio privado; pueden cambiar su contraseña desde el portal.
2. Crea el **Estudiante** asociado a su usuario y un código `EST-001` o similar.
3. Crea el **Periodo**, sus fechas y si la captura está abierta.
4. Crea el **Grupo y materia** del periodo y asigna sus docentes.
5. Agrega las **Inscripciones** de los estudiantes a sus grupos y materias.
6. Crea una **Asignación de tutor** para cada estudiante en ese periodo.

El acceso depende de esas asignaciones; una cuenta no puede elegir libremente
otro rol o consultar a otro estudiante usando su código.

Para una exposición con registros ficticios, puedes cargar las cuentas y
asignaciones de ejemplo de forma deliberada:

```powershell
.\.venv-web\Scripts\python.exe web\manage.py seed_demo
```

El comando pide una contraseña; úsala sólo para el ensayo privado. Los usuarios
son `admin_demo`, `docente_demo`, `estudiante_demo` y `tutor_demo`. No existe una
contraseña pública predeterminada. Este comando rechaza producción y no se
ejecuta al levantar el servicio. No publiques una base que conserve cuentas de
demostración; prepara una base de producción nueva.

## Recorrido para la exposición

1. En un navegador, entra con el docente. Selecciona un grupo asignado, registra
   calificación de 0 a 10, asistencia y tareas de 0 a 100 y calcula el riesgo.
2. En otro navegador o dispositivo, entra con el estudiante. Comprueba que ve
   exclusivamente sus datos y envía una solicitud de apoyo.
3. En otro navegador o dispositivo, entra con el tutor. Abre la solicitud de su
   estudiante asignado, registra un acuerdo y agrega un seguimiento.
4. Actualiza la pantalla del estudiante para mostrar el acuerdo y el avance.

Para ensayar tres cuentas en el mismo equipo usa perfiles de navegador
independientes. Varias pestañas del mismo perfil comparten la sesión.
Las notas internas del tutor no se muestran al estudiante. Las operaciones
sensibles requieren POST con CSRF; cerrar sesión también usa un formulario POST.

## Publicar por HTTPS con Docker Compose

Se necesita un servidor con Docker Engine y Compose, un dominio propio y sus
registros DNS dirigidos a la IP del servidor. Los puertos públicos son 80 y 443;
MySQL y Gunicorn no publican sus puertos al equipo host. Caddy gestiona los
certificados y redirige HTTP a HTTPS. Tener el código y los contenedores no
equivale a que el sitio ya esté publicado.

Crea `web/.env` a partir del ejemplo y configura valores privados para:

- `MESSI_WEB_SECRET_KEY`: clave aleatoria de al menos 50 caracteres, nueva para
  producción. Puedes generarla con `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- `MESSI_WEB_DB_NAME`, `MESSI_WEB_DB_USER`, `MESSI_WEB_DB_PASSWORD` y
  `MESSI_WEB_DB_ROOT_PASSWORD`: cuenta de la aplicación y clave root distintas.
- `MESSI_WEB_DOMAIN`: dominio sin protocolo, puerto ni ruta.
- `MESSI_WEB_TLS_EMAIL`: correo del responsable del certificado.
- `MESSI_WEB_ENV=production`, `MESSI_WEB_ALLOWED_HOSTS=tu.dominio` y
  `MESSI_WEB_CSRF_TRUSTED_ORIGINS=https://tu.dominio` para herramientas ejecutadas
  fuera de los contenedores. Compose fija los ajustes de producción en `app`.

No agregues contraseñas a Git. Las variables exportadas en el entorno tienen
prioridad sobre `.env`. El Dockerfile copia exclusivamente código y datos
sintéticos y genera el modelo dentro de la imagen; excluye `.env`, bases locales,
modelos externos y respaldos.

Desde la raíz del repositorio en el servidor:

```bash
docker compose --env-file web/.env -f compose.web.yaml build
docker compose --env-file web/.env -f compose.web.yaml up -d db
docker compose --env-file web/.env -f compose.web.yaml run --rm app python manage.py migrate
docker compose --env-file web/.env -f compose.web.yaml run --rm app python manage.py createsuperuser
docker compose --env-file web/.env -f compose.web.yaml run --rm app python manage.py check --deploy --database default
docker compose --env-file web/.env -f compose.web.yaml up -d
```

Las migraciones y el administrador se crean explícitamente, antes de abrir el
servicio. La imagen ya contiene los archivos estáticos. Configura entonces los
usuarios y asignaciones en `https://tu.dominio/admin/`. Verifica el recorrido
desde dos dispositivos y confirma que una cuenta ajena recibe acceso denegado.

El volumen `mysql_data` conserva los datos al recrear contenedores. Cambiar una
contraseña en `.env` no modifica una cuenta existente dentro de ese volumen:
rota las credenciales en MySQL y la aplicación de forma coordinada. No uses
`docker compose down -v` sobre una instancia que tenga registros que conservar.

## Respaldar, recuperar y mantener

El script de respaldo utiliza `mysqldump --single-transaction` dentro del
contenedor; no imprime ni pasa contraseñas como argumentos. Requiere Python en
el equipo administrador. Guarda los respaldos fuera del servidor y protege sus
accesos: contienen información privada.

```bash
python scripts/respaldo_web.py backup
```

Para MySQL instalado en el equipo, ejecuta
`.\.venv-web\Scripts\python.exe scripts\respaldo_web.py backup --local`.
Lee únicamente `web/.env` y usa los clientes MySQL del equipo; si no están en
PATH, indica `--mysql-bin-dir "C:\ruta\MySQL\bin"`. El modo `--local` también
se admite al restaurar y debe apuntar a una instancia de ensayo independiente.

Para comprobar recuperación en un entorno de ensayo independiente, configura
su propio `web/.env`, detén la aplicación y el proxy y restaura un respaldo:

```bash
docker compose --env-file web/.env -f compose.web.yaml stop app caddy
python scripts/respaldo_web.py restore --file /ruta/al/respaldo.sql --confirm-replace
docker compose --env-file web/.env -f compose.web.yaml run --rm app python manage.py migrate
docker compose --env-file web/.env -f compose.web.yaml up -d
```

La restauración reemplaza tablas y registros de la base configurada. Comprueba
que coincidan alumnos, indicadores, solicitudes y seguimientos con el respaldo.
No hagas el primer ensayo de restauración sobre la única base de producción.

Limpia periódicamente las sesiones vencidas con `python manage.py clearsessions`
dentro del contenedor `app`, revisa el espacio de los volúmenes y aplica parches
de dependencias. El bloqueo de acceso después de intentos fallidos se guarda en
MySQL y se comparte entre trabajadores; en desarrollo no confía en encabezados
de IP enviados por el navegador. En producción sólo acepta la IP que Caddy
reescribe mediante el puerto privado de la aplicación.

## Verificación de desarrollo

La aplicación no cambia a SQLite si MySQL no responde. Para pruebas automáticas
sin MySQL, habilita deliberadamente `MESSI_WEB_ENV=development` y
`MESSI_WEB_TEST_SQLITE=1`; nunca deben estar habilitados al publicar.

```powershell
$env:MESSI_WEB_ENV = 'development'
$env:MESSI_WEB_TEST_SQLITE = '1'
.\.venv-web\Scripts\python.exe web\manage.py test portal
Remove-Item Env:\MESSI_WEB_TEST_SQLITE
Remove-Item Env:\MESSI_WEB_ENV
```

SQLite de pruebas no acredita concurrencia en MySQL. Ejecuta también la suite
con una base MySQL de ensayo y una cuenta con permiso de crear su base temporal
`test_*`; nunca la ejecutes apuntando a producción. Usa `check --deploy` contra
la configuración final y verifica respaldos y accesos desde varios dispositivos.

Fuentes de implementación: [Django 5.2, despliegue](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[Django y MySQL](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes),
[actualización Django 5.2.18](https://www.djangoproject.com/weblog/2026/oct/06/security-releases/).
