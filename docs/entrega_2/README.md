# Entrega 2

**Fecha: 8 de octubre de 2026, durante la hora de clase.**

[Reparto del trabajo por integrante y rol](Reparto_del_equipo.md).

Marco coordina la arquitectura, la integración y las instrucciones de modificación;
Ismael explica datos y modelo; Salomón integra el manual en la plantilla;
Víctor consolida QA; Yokio comprueba la instalación y prepara la demostración.
Todos documentan su aportación y entregan evidencia.

Archivos preparados sobre las plantillas originales del profesor:

- [02_Manual_del_programador.docx](02_Manual_del_programador.docx): arquitectura
  y diagrama, módulos, modelo y parámetros, datos, extensión y licencias, en ese orden.
- [03_Informe_de_pruebas_QA.docx](03_Informe_de_pruebas_QA.docx): entradas,
  resultados esperados y reales, defectos corregidos y límites de la comprobación.
- Código documentado y [evidencias/](evidencias/) de MESSI 0.4.0.

La suite actual tiene **161 casos: 154 aprobados, siete MySQL omitidos y cero
fallidos**. La interfaz guía carga, guardado y cálculo con progreso real, muestra
resúmenes del conjunto visible y presenta las tablas de Tutor en español sin
modificar SQLite. Leer una solicitud y copiar su código conserva el acuerdo
preparado y no crea un apoyo hasta enviarlo. El self-test de fuente 0.4.0 comprobó inferencia, persistencia,
respaldo y las tres vistas; `pip check` no encontró conflictos.
[Registro actual](evidencias/pruebas_actuales.txt).

El CI del commit `dd4a001` aprobó 154 de 161 pruebas en Windows, con siete
MySQL omitidas, y las 161 en Ubuntu con MySQL real, sin fallos.
[Resultados y logs actuales](evidencias/ci_github_0.4.0.json).
El ZIP portable 0.4.0 conserva los 3 355 archivos de la carpeta completa,
comprobados mediante inventario, CRC y hash.
[Verificación del portable](evidencias/paquete_portable.json).
La [actualización instalada 0.4.0](evidencias/actualizacion_instalador.json)
terminó con código 0 y conservó el hash de la base, con lectura/copia de
solicitudes y contraste final incluidos. El self-test y servidor instalados
pasaron sin Python en `PATH`; las comprobaciones CI de 0.3.0 se conservan como
historial. Windows 10 y una segunda computadora no se han probado en esta sesión.
[Comprobación final de fuente e instalación idénticas](evidencias/verificacion_instalado_final.json).
El instalador y portable están preparados para la
[versión 0.4.0](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.4.0-interfaz)
y la carpeta `MESSI_0.4.0` del escritorio.
[Revisión de Ismael y Víctor](Revision_Ismael_y_Victor_2026-10-08.md).

La entrega describe la versión actual con SQLite, MLP local e instalador Windows.
Consultar [instalación local](../instalacion_local_windows.md). Los requisitos
MySQL de la primera entrega son históricos.
La [lista de cotejo](../entrega_3/Verificacion_de_entregas_2_y_3.md) registra la
correspondencia con el examen y el pendiente humano de la entrega 3.
