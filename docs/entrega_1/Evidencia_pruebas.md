# Evidencia de pruebas de Víctor

Fecha: 4 de octubre de 2026 (America/Mexico_City).
Responsable de QA: Víctor Manuel Jiménez Suárez, cuenta GitHub `Vixman128`.
Ejecución, diagnóstico y redacción asistidos por Codex; Víctor debe revisar
los resultados y comprender los casos antes de presentar su aportación.

## Alcance y versión

Se actualizó la copia local de VS Code desde `main`, incluyendo el análisis
de Ismael (`f6bf167ba5f24bbb17750d3e6244a8e0e5f3d634`). La aportación de QA se
preparó en `codex/victor-entrega-1`: instalación, pruebas automatizadas,
recorrido en navegador y registro de defectos. El documento 01, el análisis
de entrenamiento, el guion, la guía y la bitácora 06 corresponden a sus
respectivos responsables y no se modificaron en esta aportación.

## Entorno comprobado

- Windows 11, compilación 26300, arquitectura x64.
- VS Code 1.140.0, carpeta local del repositorio M.E.S.S.I-.
- Python 3.13.16, entorno privado `.venv` creado con `INSTALAR_MESSI.bat`.
- Streamlit 1.50.0, pandas 2.3.3, scikit-learn 1.7.2, NumPy 2.3.3,
  SciPy 1.16.2, joblib 1.5.2, openpyxl 3.1.5 y pyarrow 21.0.0.
- Aplicación iniciada mediante `INICIAR_MESSI.bat` en `http://127.0.0.1:8501`.
- Navegador integrado de Codex; datos ficticios EST-901, EST-902 y EST-903.

Python 3.14 ya estaba instalado. Se agregó 3.13 porque los archivos BAT lo
seleccionan explícitamente. La primera instalación completa descargó pyarrow
25.0.1 y Windows bloqueó su biblioteca nativa; la pantalla de tablas y la
prueba MLP fallaron. Se comprobó pyarrow 21.0.0, se fijó en requirements.txt y
se repitió el instalador. Este resultado corresponde a este equipo, no
demuestra un fallo general de pyarrow 25.0.1 en otros equipos.

## Resultados automatizados

| Ejecución | Resultado |
| --- | --- |
| INSTALAR antes de agregar Python 3.13 | Falló; faltaba la versión requerida |
| PROBAR con pyarrow 25.0.1 | 51 casos: 50 aprobados y 1 error de importación, 0 omitidos |
| INSTALAR con requirements corregido | Terminó con código 0 |
| PROBAR final | 59 casos: **58 aprobados, 1 fallo esperado, 0 errores inesperados, 0 omitidos**; código 0 |
| `python -m pip check` | Sin incompatibilidades de dependencias |
| `python -m compileall -q app.py src scripts tests` | Sin errores de sintaxis |

El fallo esperado reproduce QA-03: el mensaje de éxito del seguimiento
desaparece por un `st.rerun()` inmediato. **No cuenta como prueba aprobada ni
como defecto corregido**, aunque unittest devuelva `OK (expected failures=1)`.
Las 51 pruebas originales, incluida la integración MLP real, aprobaron tras
corregir la dependencia. Las ocho pruebas nuevas usan Streamlit AppTest real,
con SQLite y datos temporales, y añaden siete aprobados y el fallo esperado.
AppTest comprueba interacciones y estado; la apariencia se revisó aparte en
el navegador. [Referencia oficial de AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).

## Recorrido en navegador

| Caso | Acción y resultado observado | Estado |
| --- | --- | --- |
| NAV-01 | Abrir Docente, Estudiante y Tutor; se muestran sus formularios | Aprobado |
| ING-01 | Subir Excel válido con EST-901, nota 5.8, asistencia 70 y tareas 50; carga una fila | Aprobado |
| ING-02 | Subir CSV equivalente; acepta los mismos indicadores | Aprobado |
| ING-03 | Subir Excel con `=5+1` en la nota; rechaza fórmulas y retira la tabla anterior | Aprobado |
| ING-04 | Subir CSV con nota vacía; muestra el campo que falta | Aprobado |
| ING-05 | Subir CSV con ID repetido; muestra identificador duplicado | Aprobado |
| ING-06 | Subir CSV con nota 11; rechaza el valor fuera de 0 a 10 | Aprobado |
| ING-07 | Subir CSV con asistencia 101; rechaza el valor fuera de 0 a 100 | Aprobado |
| ING-08 | En captura manual omitir tareas; rechaza la fila, pero borra campos válidos ya escritos | Validación aprobada; usabilidad QA-04 abierta |
| ING-09 | Captura por cantidades con cero sesiones impartidas; rechaza el total cero | Aprobado |
| ING-10 | Capturar 7/10 sesiones y 2/4 tareas con nota 5.8; calcula 70 % y 50 % | Aprobado |
| IA-01 | Calcular riesgo sin modelo local; muestra “Modelo pendiente” y conserva indicadores | Aprobado |
| EST-01 | Enviar solicitud sin mensaje; rechaza y no la guarda | Aprobado |
| EST-02 | Enviar solicitud ficticia sin alerta ni modelo; confirma su registro | Aprobado |
| TUT-01 | Tutor recibe la solicitud y registra un apoyo ficticio | Aprobado |
| TUT-02 | Registrar seguimiento “En seguimiento”; aparece en el historial y en SQLite, sin confirmación visible | Persistencia aprobada; QA-03 abierta |
| TUT-03 | Reiniciar el servidor y abrir una sesión nueva; solicitud, apoyo e historial permanecen | Aprobado |

Además, AppTest comprobó pegado con coma decimal, datos pegados inválidos,
ID duplicado en captura conservando las filas previas y persistencia entre
sesiones. Los casos Excel se comprueban también con la suite original.

## Evidencia y reproducción

- [Salida inicial de PROBAR](evidencia_victor/pruebas_base.txt).
- [Salida final completa de PROBAR](evidencia_victor/pruebas_finales.txt).
- [Salida de instalación final](evidencia_victor/instalacion_final.txt).
- [Versiones completas del entorno](evidencia_victor/entorno.txt).
- [Capturas del navegador](evidencia_victor/).
- [Archivos ficticios válidos e inválidos](evidencia_victor/inputs/).
- [Pruebas de interacción nuevas](../../tests/test_streamlit_ui.py).
- [Registro de errores y pendientes](Registro_errores_Victor.md).

Desde la raíz de la rama, ejecutar:

```powershell
.\INSTALAR_MESSI.bat
.\PROBAR_MESSI.bat
.\INICIAR_MESSI.bat
```

Para repetir sólo las pruebas nuevas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_streamlit_ui.py -v
```

Las pruebas nuevas crean datos temporales y no escriben en la base habitual.
El recorrido manual sí dejó un ejemplo ficticio EST-903 en la base local,
que está excluida de Git. No se publican `.venv`, SQLite ni modelos binarios.

## Límites y entrega al equipo

El modelo entrenado por Ismael no está incluido en Git: el repositorio ignora
los artefactos de models. Se comprobó el comportamiento sin modelo y la
integración MLP de la suite; no se ejecutó ENTRENAR_DEMO.bat ni se evaluaron
nuevamente las métricas de Ismael. Queda pendiente probar visualmente el
reporte de predicción con el artefacto que el equipo vaya a demostrar.

QA-03 y QA-04 siguen abiertos para revisión de integración e interfaz.
No se comprobó una sesión completa exclusivamente con teclado, otro navegador,
otro sistema operativo, autenticación institucional ni un piloto escolar.
La revisión de futuros cambios de Salomón debe repetirse sobre su versión
integrada. Esta evidencia sirve como insumo para el informe QA 03 posterior.
