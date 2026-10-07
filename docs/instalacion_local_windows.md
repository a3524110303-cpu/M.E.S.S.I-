# MESSI local para Windows 10 y 11

## Qué entregar al cliente

Entrega únicamente `release/MESSI-Setup-Windows-x64.exe`. El cliente pulsa
Siguiente, Instalar y Finalizar. Abre MESSI con su acceso directo; las pantallas
se abren en el navegador de esa computadora. Debe mantener abierta la ventana
de control y usar **Cerrar MESSI** al terminar.

El instalador y su SHA256 también se publican en la
[versión v0.2.0-local de GitHub](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.2.0-local).

El instalador contiene Python, las librerías, el modelo MLP ya entrenado, su
archivo de metadatos, el ejemplo CSV y la plantilla Excel. Funciona sin conexión
para capturar datos, predecir y registrar apoyos. No instala MySQL ni pide claves,
contraseñas, comandos o permisos de administrador.

Destino de la aplicación: `%LOCALAPPDATA%\Programs\MESSI`.
Datos por usuario: `%LOCALAPPDATA%\MESSI\data\messi.sqlite3`.
Registros de problemas: `%LOCALAPPDATA%\MESSI\logs`.

Windows 10 debe ser versión 2004 o posterior; Windows 11 admite esta edición.
El paquete es para Intel/AMD x64. Recomendados: 4 GB de RAM, 1 GB de espacio libre
y un navegador instalado. No requiere GPU. Cada computadora tiene su propia
base; SQLite local no sincroniza los registros entre equipos.

## Qué mover para llevar el sistema a otra computadora

**Instalación nueva:** sólo el instalador. No copies `.venv`, `.env`, el código,
la carpeta MySQL ni tu base personal al paquete del cliente.

**Versión portable:** copia completa `dist/MESSI`, incluido `_internal`, y abre
`MESSI.exe`. Copiar sólo ese ejecutable deja fuera Python, librerías y recursos.

**Conservar registros:** pulsa **Guardar respaldo** en la ventana de control.
El respaldo usa la API SQLite e incluye los cambios pendientes en el WAL.
En el destino, instala MESSI, ciérralo y coloca el respaldo con el nombre
`messi.sqlite3` en `%LOCALAPPDATA%\MESSI\data`. Guarda antes una copia de cualquier
base existente. Los archivos `-wal` y `-shm` de una base activa no son un respaldo.

El instalador crea una base vacía y conserva los datos al actualizar/desinstalar.
Si existía una base SQLite antigua en `data/private`, haz una copia con MESSI
cerrado y colócala en la ruta nueva: la aplicación conserva solicitudes, apoyos,
seguimientos e IDs y añade las tablas de indicadores y predicciones.
El cambio de almacenamiento no importa automáticamente datos de MySQL.

## Qué cambió en el código

- `app.py` usa `SQLiteStore` y la ruta de datos del usuario; ignora la configuración MySQL de `.env`.
- `src/messi/sqlite_storage.py` guarda solicitudes, apoyos, seguimientos, indicadores y predicciones.
- Si cambian los indicadores, se invalida su predicción anterior; los lotes se guardan en una transacción.
- `src/messi/paths.py` separa recursos del paquete y datos que se pueden escribir.
- `src/messi/model.py` encuentra el modelo dentro del paquete y comprueba su hash y metadatos.
- `messi_desktop.py` abre el servidor incluido y el navegador; `desktop.py` selecciona un puerto libre en `127.0.0.1`.
- La telemetría de Streamlit está desactivada; el servidor sólo escucha en esa computadora.
- Windows termina el servidor cuando se cierra la aplicación, incluso tras una terminación inesperada.
- `MESSI.spec` e `installer/MESSI.iss` generan el ejecutable y el instalador.

El MLP conserva su arquitectura de tres entradas y ocho neuronas ocultas. El
modelo incluido sigue siendo una demostración sintética. El empaquetado no
convierte esa red en un modelo escolar validado ni añade autenticación a los roles.

## Reconstruir después de modificar el programa

Sólo en la computadora de desarrollo: Python 3.13 x64 e Inno Setup 6.
Internet se usa para instalar las dependencias de construcción; el cliente no
lo necesita para usar el paquete terminado.

```powershell
Set-Location 'C:\Users\user\Desktop\MESSI'
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Si Python o Inno Setup están en otra ruta, pasa `-Python` y `-ISCC`.
`-SoloPortable` genera y comprueba la carpeta portable sin compilar el instalador.
El script entrena el modelo, ejecuta las pruebas y comprueba el ejecutable desde
otra carpeta con un PATH sin Python. Las comprobaciones están en
`release/verificacion-self-test.json` y `release/verificacion-smoke-server.json`.
Al modificar código o modelo, vuelve a construir y entrega el nuevo instalador.
Usa el mismo AppId para actualizar sin perder la carpeta de datos.

## Diagnóstico y alcance de la comprobación

La ventana permite **Guardar diagnóstico**; revisa SQLite e inferencia sin
incluir solicitudes ni notas en el reporte. También se puede ejecutar:

```powershell
MESSI.exe --diagnostico
MESSI.exe --self-test
MESSI.exe --smoke-server
```

`--self-test` prueba el flujo de persistencia, un respaldo y las tres pantallas;
`--smoke-server` abre y cierra el servidor real del paquete. Las escrituras de
prueba se hacen en una base temporal.

La evidencia local distingue las pruebas ejecutadas en Windows 11 de la
comprobación todavía pendiente en una computadora Windows 10 o en el equipo
específico del cliente.

Comprobación realizada el 6 de octubre de 2026 en Windows 11 x64:

- Suite: 144 pruebas aprobadas y 7 pruebas de MySQL omitidas porque requieren servidor.
- Ejecutable desde otra carpeta, con PATH sin Python: inferencia, persistencia,
  respaldo, pantallas Docente/Tutor/Estudiante y servidor HTTP comprobados.
- Instalador real sin permisos de administrador: instalación, actualización y
  desinstalación comprobadas; los datos sobrevivieron a ambas últimas operaciones.
- Informe de instalación: `release/verificacion-instalacion.json`.
- Instalador generado: 109 468 172 bytes. Su SHA256 está en
  `release/MESSI-Setup-Windows-x64.sha256`.

Windows 10 x64 (2004 o posterior) es el destino configurado junto con Windows 11;
la ejecución en una computadora Windows 10 sigue pendiente de comprobación.

Referencias: [configuración Streamlit](https://docs.streamlit.io/develop/api-reference/configuration/config.toml),
[PyInstaller](https://pyinstaller.org/en/stable/spec-files.html),
[respaldo SQLite](https://www.sqlite.org/backup.html).
