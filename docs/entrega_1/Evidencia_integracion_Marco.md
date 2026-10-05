# Evidencia de integración de Marco

Fecha: 5 de octubre de 2026. Responsable: Marco Antonio Osorio Hernandez. Implementación y verificación asistidas por Codex.

## Cambios

- Integración de la versión publicada `9ea0ba1`, conservando los aportes de Ismael y Víctor y los cambios locales anteriores.
- MySQL como almacenamiento del runtime: estudiantes, indicadores, predicciones, solicitudes, apoyos y seguimiento; esquema explícito, transacciones y migración opcional de SQLite.
- QA-03: confirmación del seguimiento conservada después de actualizar la pantalla. Se retiró `expectedFailure`; el caso ahora aprueba.
- QA-04: formularios conservan campos cuando falla la validación o la escritura; se limpian sólo tras una operación confirmada.
- QA-05: tablas utilizan `width="stretch"` en lugar del parámetro obsoleto.
- Adaptación de las pruebas de Víctor al contrato MySQL. Las pruebas UI utilizan un adaptador temporal para aislar el estado; la persistencia MySQL se comprueba por separado contra un servidor real.
- CI incluye Windows y una comprobación completa sobre Linux con servicio MySQL 8.0.

## Resultado local

Windows, Python 3.13.13, Streamlit 1.50.0, scikit-learn 1.7.2, pyarrow 21.0.0, mysql-connector-python 9.4.0. Servicio MySQL de prueba 8.0.42 en 127.0.0.1:13307; base `messi_marco_revision_test`.

| Comprobación | Resultado |
| --- | --- |
| Suite completa con MESSI_TEST_MYSQL=1 | **138 aprobadas, 0 fallos, 0 errores, 0 omisiones, 0 fallos esperados** |
| Interacciones Streamlit | Diez casos aprobados, incluida confirmación tras rerun y conservación de campos inválidos |
| MySQL real | Cinco casos de persistencia, concurrencia, invalidación de predicciones y rollback aprobados |
| Migración real | Importación exacta e idempotencia aprobadas en destino aislado |
| Permisos reales | Cambio editor/lector, bloqueo y rechazo de permisos ajenos comprobados |
| pip check | Sin incompatibilidades |
| compileall | Sin errores de sintaxis |
| git diff --check | Sin errores de espacios ni marcadores de conflicto |
| Recorrido en navegador | Captura inválida conserva campos; captura válida los limpia; solicitud, apoyo y seguimiento guardados en MySQL; confirmación visible tras rerun |

La evidencia completa de tests se conserva en [pruebas_integracion.txt](evidencia_marco/pruebas_integracion.txt).

Capturas del recorrido real con el servidor aislado:
[campos conservados](evidencia_marco/campos_conservados.png),
[captura confirmada](evidencia_marco/captura_confirmada.png) y
[seguimiento confirmado](evidencia_marco/seguimiento_confirmado.png).
Se utilizó exclusivamente el estudiante ficticio EST-906.

## Reproducción

Ejecutar `INSTALAR_MESSI.bat`, después `PROBAR_MESSI.bat`. Sin configuración de prueba MySQL se ejecutan las pruebas unitarias y UI y se omiten explícitamente siete pruebas de servidor real.

Para verificar esas siete pruebas, preparar un servidor y una cuenta administrativa exclusivos de prueba, y configurar las variables MESSI_MYSQL_HOST, MESSI_MYSQL_PORT, MESSI_MYSQL_USER, MESSI_MYSQL_PASSWORD y MESSI_MYSQL_DATABASE. La base debe terminar en `_test`. Activar MESSI_TEST_MYSQL=1 y ejecutar:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas de integración generan registros propios y eliminan sólo sus registros y cuentas de prueba. La migración utiliza un destino de prueba vacío y conserva su fuente SQLite.

La prueba de permisos usa cuentas temporales con origen 127.0.0.1 localmente.
CI configura MESSI_TEST_MYSQL_USER_HOST=% para alcanzar el contenedor desde
la red interna del runner. Cada cuenta conserva permisos sólo en la base de
prueba y se elimina al terminar. El origen predeterminado del script de
administración de la aplicación permanece en 127.0.0.1.

## Límites y pendientes

La conexión del archivo .env habitual fue rechazada por MySQL; el usuario debe corregir sus credenciales y permisos siguiendo [Base de datos](../base_de_datos.md). No se declara verificada esa conexión, ni migrados los registros habituales.

AppTest verifica las interacciones y el estado de la interfaz. La revisión de una sesión exclusiva con teclado y las futuras aportaciones de Salomón requieren sus propias evidencias. Las capturas de Víctor se conservan como historial de la versión anterior.

El documento 01 actualizado es [01_Documento_del_proyecto_MESSI.md](01_Documento_del_proyecto_MESSI.md). Se conserva el DOCX de diseño original sin modificar. La bitácora [06_Bitacora_de_prompts_Marco.md](06_Bitacora_de_prompts_Marco.md) registra las solicitudes de esta sesión; la consolidación del equipo sigue pendiente.
