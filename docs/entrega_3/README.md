# Entrega 3

**Fecha: 9 de octubre de 2026, durante la hora de clase.**

- [04_Manual_de_usuario.docx](04_Manual_de_usuario.docx): descripción sencilla,
  instalación, uso de Docente/Estudiante/Tutor, interpretación, FAQ y solución
  de problemas. Listo y revisado: 11 páginas, 12 capturas únicas de MESSI 0.4.0
  y 20 figuras con recortes dentro de Word.
- [05_Nota_de_prueba_con_persona_ajena.docx](05_Nota_de_prueba_con_persona_ajena.docx):
  protocolo preparado de máximo media página, **pendiente de realizar la prueba**.
- [Video público de 0.4.0, de 4:25](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/download/v0.4.0-interfaz/MESSI_Demo_Entrega_3.mp4), con capturas actuales, narración sintética y
  [subtítulos](MESSI_Demo_Entrega_3.srt). Sigue el orden exigido: problema,
  entrada/proceso/salida, resultados e interpretación, limitaciones y mejoras.
  [Guion](Guion_video_demo.md), [transcripción](Transcripcion_video_demo.md) y
  [verificación técnica](evidencias/verificacion_video_demo.json).
  Archivo validado: 265.23 segundos, 1920×1080, H.264/AAC y 6 402 163 bytes.
  [Acceso HTTP 200 sin autenticación y hash de descarga comprobados](evidencias/publicacion_0.4.0.json).

MESSI 0.4.0 organiza las vistas mediante navegación lateral, pasos de Docente,
resúmenes de estudiantes/solicitudes/apoyos y tablas de Tutor en español. Permite
leer una solicitud por folio y copiar su código al acuerdo sin guardar el apoyo
hasta enviarlo. La ventana de escritorio agrupa apertura, respaldo, diagnóstico
y cierre. Las [capturas actuales](evidencias/capturas_interfaz_04/) ilustran el
manual y el video de esta versión. La suite de
fuente tiene **161 pruebas: 154 aprobadas, siete MySQL omitidas y cero fallidas**.
El [CI de la versión actual](../entrega_2/evidencias/ci_github_0.4.0.json) confirma
esas cifras en Windows y 161 aprobadas en Ubuntu con MySQL real. El
[ZIP portable](../entrega_2/evidencias/paquete_portable.json) conserva la carpeta
completa; se debe extraer todo su contenido para abrir `MESSI.exe`.
La [actualización instalada 0.4.0](../entrega_2/evidencias/actualizacion_instalador.json)
terminó con código 0, conservó la base y pasó self-test y servidor sin Python
en `PATH`.
La [comprobación final](../entrega_2/evidencias/verificacion_instalado_final.json)
confirma `app.py` instalado idéntico a la fuente.

El equipo confirmó el 8 de octubre que aún no realizó la prueba externa.
Una persona ajena debe usar el manual sin ayuda; Víctor observa sin intervenir.
Después se sustituyen los campos pendientes del 05 por dificultades observadas
y cambios reales al manual, sin superar media página. La verificación de Codex
y el video no sustituyen esa prueba.

La [lista de cotejo de entregas 2 y 3](Verificacion_de_entregas_2_y_3.md) muestra
la evidencia de cada requisito. Las copias DOCX, el instalador y el video se
reúnen en `MESSI_0.4.0` en el escritorio; los binarios están publicados en
la [versión 0.4.0 de GitHub](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.4.0-interfaz),
fuera del historial Git. La [publicación 0.3.0](https://github.com/a3524110303-cpu/M.E.S.S.I-/releases/tag/v0.3.0-entregas)
se conserva como historial; su acceso público se comprobó en la revisión anterior.
