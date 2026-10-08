# MESSI — Alerta y acompañamiento escolar

MESSI 0.4.0 es una aplicación local para registrar indicadores académicos,
solicitudes de apoyo, acuerdos y seguimiento. Cuenta con vistas para Docente,
Estudiante y Tutor.

## Instalar y abrir en Windows

Requiere Windows 10 versión 2004 o posterior, o Windows 11, en un equipo
Intel/AMD de 64 bits y con navegador instalado.

1. Descarga [MESSI-Setup-Windows-x64.exe](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/download/v0.4.0-interfaz/MESSI-Setup-Windows-x64.exe).
2. Ejecuta el instalador y sigue **Siguiente → Instalar → Finalizar**.
3. Abre **MESSI** desde Inicio o desde el acceso directo del escritorio, si lo creaste.
4. Trabaja en la página que se abre en tu navegador. Mantén abierta la ventana
   de control de MESSI y pulsa **Cerrar MESSI** al terminar.

**Si ya instalaste la aplicación, basta con abrirla desde su acceso directo.**
El instalador incluye Python, las librerías, SQLite y el modelo entrenado.
Para usarla no necesitas ejecutar los `.bat` del repositorio, instalar MySQL
ni tener conexión a internet.

También puedes usar la [versión portable](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/download/v0.4.0-interfaz/MESSI-Portable-Windows-x64.zip):
extrae todo el ZIP y abre `MESSI.exe` dentro de la carpeta extraída.
Conserva junto al ejecutable la carpeta `_internal` y los demás archivos.

## Usar la aplicación

1. **Docente:** selecciona **Ejemplo sintético** y pulsa **Cargar ejemplo sintético**.
   También puedes cargar un Excel o CSV, pegar una tabla o capturar los datos.
   Usa un código estable, como `EST-001`, nota del primer parcial de 0 a 10,
   asistencia y tareas entregadas de 0 a 100; escribe `80` para 80 %.
2. Revisa los datos y pulsa **Guardar indicadores**. Después pulsa
   **Calcular riesgo de demostración** para consultar las puntuaciones y alertas.
   **Descargar reporte** genera un CSV con los resultados.
3. **Estudiante:** escribe el mismo código y una solicitud ficticia; pulsa
   **Enviar solicitud**. Puede pedir apoyo aunque no exista una alerta.
4. **Tutor:** consulta las solicitudes, completa el acuerdo y pulsa
   **Registrar apoyo**. Selecciona el apoyo, escribe una nota, elige su estado
   y pulsa **Guardar seguimiento**.

Comprueba la confirmación de guardado al enviar cada formulario.
El modelo es una demostración con datos sintéticos; sus puntuaciones requieren
revisión humana. Usa datos ficticios. El selector de roles no tiene autenticación.

## Guardar datos y resolver problemas

Los registros se guardan por usuario en
`%LOCALAPPDATA%\MESSI\data\messi.sqlite3`. Se conservan al cerrar, actualizar
o desinstalar MESSI. Cada computadora tiene su propia base de datos.

En la ventana de control, **Guardar respaldo** crea una copia de los registros.
Si ocurre un error, **Guardar diagnóstico** genera un reporte para revisarlo.

## Ejecutar desde el código del repositorio

Esta opción sirve para modificar o revisar el programa. Requiere Python 3.13
de 64 bits con el lanzador `py`, e internet para instalar las dependencias.

Clona o descarga el repositorio, abre PowerShell en su carpeta y ejecuta:

```powershell
.\INSTALAR_MESSI.bat
.\INICIAR_MESSI.bat
```

`INSTALAR_MESSI.bat` crea `.venv`, instala las dependencias y genera el modelo
si falta. Ejecútalo la primera vez o cuando cambien las dependencias.
En las siguientes ocasiones, usa únicamente `INICIAR_MESSI.bat` para abrir
la aplicación desde el código.

Herramientas adicionales de desarrollo:

| Archivo | Cuándo usarlo |
| --- | --- |
| `PROBAR_MESSI.bat` | Para ejecutar las pruebas después de modificar el código. |
| `ENTRENAR_DEMO.bat` | Para regenerar el modelo con datos sintéticos. |

Los cambios en el código del repositorio no actualizan la aplicación instalada.
Para distribuir una versión modificada, instala Inno Setup 6 y reconstruye
el paquete desde PowerShell en la carpeta del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

El instalador resultante queda en `release/MESSI-Setup-Windows-x64.exe`.

## Documentación

- [Manual de usuario](docs/entrega_3/04_Manual_de_usuario.docx).
- [Manual del programador](docs/entrega_2/02_Manual_del_programador.docx).
- [Informe de pruebas](docs/entrega_2/03_Informe_de_pruebas_QA.docx).
- [Lista de cotejo de las entregas 2 y 3](docs/entrega_3/Verificacion_de_entregas_2_y_3.md).

## Créditos y fuentes

- Los datos de demostración se generan con [generate_synthetic.py](scripts/generate_synthetic.py),
  con semilla 2026. Son artificiales, sin registros de alumnos reales.
- Las versiones de las librerías están en [requirements.txt](requirements.txt) y
  [requirements-build.txt](requirements-build.txt). Sus licencias y fuentes se
  citan en la sección 6 del [manual del programador](docs/entrega_2/02_Manual_del_programador.docx).
- Codex asistió en la generación de partes del código, documentos, pruebas y
  video de demostración. Los aportes y correcciones del equipo se registran en
  el [historial de commits](https://github.com/a3524110303-cpu/M.E.S.S.I-/commits/main/)
  y en la [revisión de aportes](docs/entrega_2/Revision_Ismael_y_Victor_2026-10-08.md).

Proyecto del equipo MESSI: Marco Antonio Osorio Hernandez, Ismael Hernández
Jiménez, Víctor Manuel Jiménez Suárez, Yokio Yosafat Vazquez Carrillo y
Salomón Alvarez Gomez.
