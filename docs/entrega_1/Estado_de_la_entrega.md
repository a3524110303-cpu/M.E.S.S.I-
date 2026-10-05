# Estado de la primera entrega MESSI

Actualización: 5 de octubre de 2026. Fecha de entrega acordada: 5 de octubre durante la clase.

| Requisito | Evidencia | Estado |
| --- | --- | --- |
| Documento 01 | [Documento actualizado](01_Documento_del_proyecto_MESSI.md) | Funcionamiento, instalación y requisitos actualizados; DOCX anterior conservado como referencia |
| Código | app.py y src/messi | MySQL y correcciones integrados; configuración habitual de .env todavía rechaza el acceso |
| Dependencias | requirements.txt | Instaladas y comprobadas, incluida pyarrow 21.0.0; pip check correcto |
| Datos de prueba | data/synthetic | Excel y CSV ficticios incluidos |
| Pruebas | [Integración de Marco](Evidencia_integracion_Marco.md) | 138 aprobadas contra MySQL aislado, sin errores, omisiones ni fallos esperados |
| QA-03 a QA-05 | app.py y tests/test_streamlit_ui.py | Corregidos por Marco; las capturas de Víctor conservan la observación inicial |
| Entrenamiento | resultados_entrenamiento.md y scripts/train_demo.py | Cifras reproducidas; interpretación y evidencia completa de Ismael pendientes |
| Historial compartido | Git y [revisión inicial](Revision_del_equipo_2026-10-05.md) | Marco, Ismael y Víctor con aportación; Yokio y Salomón sin evidencia publicada localizada |
| Guion y escenario | Responsabilidad de Yokio | Pendientes de evidencia |
| Guía, instrucciones y capturas | Responsabilidad principal de Salomón | Pendientes de evidencia; correcciones de Marco no sustituyen su contribución documental |
| Créditos y licencias | README.md | Dependencias y asistencia de IA declaradas; licencia del código del equipo por acordar |
| Bitácora 06 | [Registro de Marco](06_Bitacora_de_prompts_Marco.md) | Registro real de esta sesión preparado; falta consolidar las bitácoras existentes del equipo |

## Responsabilidades para esta entrega

Marco cierra la integración y las correcciones QA-03 a QA-05; Víctor registra
defectos, evidencias y su revalidación; Salomón concentra la guía, las
instrucciones y las capturas. Ismael conserva datos y modelo; Yokio prepara
el escenario y el guion de demostración. Todos pueden aportar código y cada
autor debe revisar y comprobar sus cambios. El reparto indica quién coordina
el cierre de cada entregable; los pendientes de la tabla requieren evidencia.

## Cierre

Antes de presentar, configurar la cuenta y los permisos MySQL del equipo de demostración y repetir el recorrido con esa instalación. El servidor aislado de pruebas confirma el código y no acredita el acceso con las credenciales habituales. La migración de los registros habituales de SQLite es opcional y no se declara realizada.

El documento 01 ya refleja el prototipo. El registro de Marco reúne sus prompts reales de revisión y corrección; no se inventaron los de otras personas. Faltan aportes y revisiones cruzadas del equipo para considerar cerrada la entrega conjunta.

Los manuales 02 y 03 corresponden a la entrega 2; el 04 y la prueba con una persona ajena del 05 corresponden a la entrega 3. Las plantillas originales se conservan en docs/referencias.
