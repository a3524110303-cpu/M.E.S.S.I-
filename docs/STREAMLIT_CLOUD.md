# Publicar MESSI en Streamlit Community Cloud

Selecciona **`cloud/app.py`** como archivo de entrada. Esta interfaz usa las
mismas cuentas, permisos, expedientes y servicios Django del portal web y guarda
los datos en **MySQL externo**. `app.py` en la raíz conserva el prototipo local
anterior y no es la entrada de esta publicación.

Community Cloud ejecuta Streamlit; no inicia el servidor Django/Gunicorn ni
MySQL de Compose. Django se utiliza como ORM y capa de permisos dentro del
proceso. Los archivos de la instancia Cloud no se usan como base persistente.

## 1. Preparar una base MySQL en línea

Necesitas un servicio MySQL accesible desde Community Cloud y una cuenta con
permiso sobre una base dedicada a MESSI. Una opción para ensayar es el
[plan gratuito de Aiven para MySQL](https://aiven.io/docs/products/mysql/concepts/mysql-free-tier),
que su documentación ofrece sin tarjeta. Comprueba los límites y condiciones
que muestre el proveedor al crear el servicio.

En la consola del proveedor crea el servicio y espera a que esté disponible.
Copia de forma privada **host, puerto, usuario, contraseña y nombre de base**,
y descarga su certificado **CA**. Si el plan sólo ofrece `defaultdb`, usa ese
nombre; no hace falta crear otra base para que Django cree sus tablas ahí.
Usa una instancia dedicada para evitar mezclar tablas con otro proyecto.

La aplicación verifica el certificado y el nombre del servidor mediante TLS.
No se conecta a `localhost` desde Cloud ni cambia a SQLite ante un error.
Configura la lista de redes permitidas del proveedor para aceptar las conexiones
de tu instancia Cloud conforme a sus instrucciones.

## 2. Preparar Secrets y el administrador

Instala las dependencias de Cloud en el entorno separado:

```powershell
.\.venv-web\Scripts\python.exe -m pip install -r cloud\requirements.txt
```

Copia `cloud/secrets.example.toml` a **`.streamlit/secrets.toml`**, archivo
ignorado por Git. Completa los datos MySQL y tu dominio Cloud definitivo en
`allowed_hosts` y `csrf_trusted_origins`. Genera `secret_key` con:

```powershell
.\.venv-web\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

En `ssl_ca_pem` pega el contenido completo del CA del proveedor entre triples
comillas, incluyendo `-----BEGIN CERTIFICATE-----` y
`-----END CERTIFICATE-----`. No pegues una clave privada ni un certificado de
cliente. El ejemplo del repositorio siempre debe conservar sus marcadores;
los valores reales van exclusivamente en el archivo privado y en Cloud Secrets.

Inicializa la base de forma explícita desde tu equipo:

```powershell
.\.venv-web\Scripts\python.exe cloud\runtime.py migrate
.\.venv-web\Scripts\python.exe cloud\runtime.py createsuperuser
.\.venv-web\Scripts\python.exe cloud\runtime.py check
```

Estos comandos leen el TOML privado, preparan el CA y usan los valores remotos
sin sobrescribir `web/.env` del ensayo local. La contraseña del administrador
se solicita con entrada oculta. Para usar otro archivo privado agrega
`--secrets C:\ruta\privada.toml` a cada comando. La interfaz pública no crea
tablas, administradores ni cuentas de demostración al abrirse.

## 3. Desplegar desde GitHub

Con el código actualizado en GitHub, abre
[Streamlit Community Cloud](https://share.streamlit.io/), elige **Create app**
y completa:

| Campo | Valor |
| --- | --- |
| Repository | El repositorio GitHub de MESSI |
| Branch | La rama que contiene esta versión |
| Main file path | `cloud/app.py` |
| App URL | El nombre elegido para MESSI |
| Python | `3.13` |

En **Advanced settings → Secrets**, pega el contenido privado de
`.streamlit/secrets.toml`. `cloud/requirements.txt` proporciona las dependencias
Python; `packages.txt` en la raíz proporciona los compiladores y la biblioteca
de MySQL para Linux. Conserva las opciones de CORS y protección XSRF de
Streamlit activadas.

Pulsa **Deploy** y espera a que termine la instalación. Si falta una
configuración, falla MySQL o quedan migraciones pendientes, la aplicación
muestra un mensaje y detiene la entrada sin imprimir secretos ni trazas SQL.
Después de modificar Secrets, reinicia la aplicación; la configuración Django
es única para cada proceso y no cambia de base entre usuarios.

## 4. Configurar escuela y probar

Entra con el administrador y crea cuentas individuales con su rol, estudiantes,
periodos, grupos/materias, inscripciones y asignaciones de tutores. Revisa el
orden de configuración en [USO_WEB.md](USO_WEB.md). El acceso Cloud usa los
mismos servicios de autorización del portal Django.

Comprueba el recorrido con navegadores o dispositivos independientes:

1. **Docente:** capturar indicadores de un grupo asignado y calcular riesgo.
2. **Estudiante:** consultar únicamente sus indicadores y enviar una solicitud.
3. **Tutor:** abrir un acuerdo y registrar seguimiento para su alumno asignado.
4. **Estudiante:** actualizar y comprobar el acuerdo y avance publicados.
5. Verificar que otra cuenta no pueda consultar registros ajenos y que cerrar
   sesión borre los formularios y resultados de la cuenta anterior.

Las sesiones duran hasta ocho horas y se invalidan al cambiar contraseña,
desactivar la cuenta o cambiar su rol. Las contraseñas se comprueban mediante
Django y no se conservan en el estado autenticado de Streamlit. Los intentos
fallidos se cuentan en MySQL por cuenta, para compartir el bloqueo entre
sesiones. La IP aportada por Streamlit no se utiliza como garantía de identidad.

El modelo demostrativo se genera una vez por proceso, si falta, a partir del
CSV sintético y del código de entrenamiento del repositorio. No se aceptan
modelos binarios enviados por visitantes. Si ese análisis falla, solicitudes y
seguimiento permanecen disponibles. Sus métricas no validan eficacia educativa.

Programa respaldos en el proveedor y comprueba restauración en otra base antes
de trabajar con registros que debas conservar. Usa contraseñas individuales;
el despliegue no incluye contraseñas públicas de demostración.

## Ensayo local de la interfaz Cloud

Para pruebas deliberadas con MySQL local, el proceso puede usar
`MESSI_CLOUD_LOCAL_TEST=1`, con Secrets que apunten a la base de ensayo y orígenes
HTTP locales. Nunca guardes esta variable en el despliegue Cloud. Este modo
conserva MySQL y no admite SQLite; sirve para AppTest y desarrollo controlado.

Fuentes: [dependencias de Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies),
[Secrets de Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management),
[estado de sesión](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
y [límites de la IP de Streamlit](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.context#contextip_address).
