# Registro de errores de Víctor

Fecha: 4 de octubre de 2026. Base: `f6bf167`, rama `codex/victor-entrega-1`.
Revisión asistida por Codex. Sólo se usaron datos ficticios.

| ID | Prioridad | Hallazgo | Estado |
| --- | --- | --- | --- |
| QA-01 | Bloqueante para instalar | El BAT requiere Python 3.13; el equipo tenía 3.14 | Resuelto en este equipo instalando 3.13.16 |
| QA-02 | Bloqueante para tablas e IA | Windows bloquea la DLL de pyarrow 25.0.1 | Resuelto en este equipo y versión 21.0.0 fijada para revisión |
| QA-03 | Menor | Desaparece la confirmación de seguimiento | Abierto, reproducido en navegador y AppTest |
| QA-04 | Media | Un envío inválido borra los campos válidos del formulario | Abierto, reproducido en navegador |
| QA-05 | Mantenimiento | Avisos de Streamlit sobre `use_container_width` | Abierto; no impide la ejecución con 1.50.0 |

## QA-01: versión de Python

Reproducción: ejecutar INSTALAR_MESSI.bat con sólo Python 3.14 instalado.
Observado: “No runtime installed that matches 3.13” y la instalación falla.
Esperado: tener la versión exigida por el proyecto disponible.
Resolución local: `py install 3.13` instaló Python 3.13.16; después el BAT creó
`.venv` correctamente. No se cambió el requisito del proyecto.

## QA-02: importación de pyarrow

Reproducción: instalar los requirements originales en este equipo y ejecutar
PROBAR_MESSI.bat. Abrir Docente y cargar el ejemplo sintético.
Observado: 50 aprobados y un error en `test_local_pipeline_roundtrip`.
También falla `st.dataframe` en el navegador con:

```text
ImportError: DLL load failed while importing lib:
Una directiva de Control de aplicaciones bloqueó este archivo.
```

Esperado: que las tablas y scikit-learn puedan importar las dependencias.
Causa comprobada: la importación de pyarrow 25.0.1 falla en este entorno;
`pip check` no detecta este bloqueo de ejecución. No se determinó qué
componente exacto de la directiva de Windows rechazó la biblioteca.

Resolución comprobada: instalar pyarrow 21.0.0 del registro oficial y fijarlo
en requirements.txt. Repetir INSTALAR, importar pyarrow y sklearn, cargar las
tablas y ejecutar PROBAR. Las 51 pruebas originales aprueban y el navegador
muestra los datos. No se cambiaron ajustes de seguridad de Windows.
La publicación ofrece una rueda para Python 3.13 y Windows x64:
[pyarrow 21.0.0 en PyPI](https://pypi.org/project/pyarrow/21.0.0/).

Evidencia: [captura del fallo](evidencia_victor/01_fallo_pyarrow.png),
[tabla después de la corrección](evidencia_victor/02_excel_valido.png),
[salida inicial](evidencia_victor/pruebas_base.txt) y
[salida final](evidencia_victor/pruebas_finales.txt).
La prueba `test_sample_table_and_missing_model_keep_indicators` usa Streamlit
real y reproduce un error si no se puede mostrar la tabla.

## QA-03: confirmación de seguimiento

Reproducción: en Tutor registrar un apoyo ficticio. Seleccionar
“En seguimiento”, escribir una nota y pulsar “Guardar seguimiento”.
Esperado: historial y estado actualizados con confirmación visible de éxito.
Observado: el historial y SQLite se actualizan correctamente, pero no queda
el mensaje “Seguimiento guardado.”. `show_tutor` muestra el éxito y llama
inmediatamente a `st.rerun()`, que reconstruye la pantalla sin ese mensaje.

Impacto: el tutor puede dudar si se guardó y repetir la operación.
Propuesta para integración/interfaz: conservar una notificación en el estado
de sesión y mostrarla después del rerun. No se modificó app.py en esta rama.

Evidencia: [historial sin confirmación](evidencia_victor/07_seguimiento_sin_confirmacion.png).
Reproducción automática:
`test_qa03_followup_keeps_visible_success_confirmation`, marcado
`expectedFailure`. No es un caso aprobado. Después de corregirlo, retirar
el decorador y comprobar que el test apruebe; un `unexpected success` obliga
a actualizar la marca. Otra prueba independiente confirma que la información
permanece al abrir una sesión nueva.

## QA-04: campos borrados después de un error

Reproducción: en Docente/Captura directa escribir EST-902, nota 6 y asistencia
80; dejar tareas vacías y pulsar “Agregar estudiante”. También se observa
al enviar un mensaje de solicitud vacío con un ID válido.
Esperado: ver el error y conservar los valores válidos para corregir sólo lo
que falta.
Observado: la validación rechaza correctamente, pero `clear_on_submit=True`
vacía el formulario incluso si el envío falló. Las filas previamente
aceptadas en la sesión sí permanecen; el problema es el formulario pendiente.

Impacto: hay que volver a capturar la información.
Propuesta para interfaz: limpiar únicamente después de un envío válido.
Evidencia: [captura del formulario inválido](evidencia_victor/05_captura_invalida_borra_campos.png).
No se agrega una prueba AppTest de limpieza del formulario porque esa API no
comprueba el reinicio de campos que ejecuta el navegador; este caso se debe
repetir visualmente después del cambio de interfaz.

## QA-05: avisos de mantenimiento

Al mostrar tablas, Streamlit imprime avisos para reemplazar
`use_container_width` por `width`. No provocaron excepciones con la versión
1.50.0 fijada en el proyecto. Registrar para la revisión de interfaz y repetir
QA cuando el equipo actualice Streamlit.

## Pendiente de volver a probar

- QA-03 y QA-04 después de la corrección por integración/interfaz.
- Predicción y descarga de reporte con el artefacto local de la demo del equipo.
- Recorrido completo con teclado y cambios de interfaz de Salomón al integrarse.

El documento 01, entrenamiento, guion, guía y bitácora no se alteraron en esta
aportación. El resultado completo está en [Evidencia_pruebas.md](Evidencia_pruebas.md).
