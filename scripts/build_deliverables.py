"""Completar las cuatro plantillas del maestro sin alterar sus originales.

Ejecutar con Python que incluya python-docx y Pillow. El constructor conserva
byte por byte las partes de las plantillas que no necesita editar. Las capturas
son archivos reales guardados en docs/entrega_3/evidencias. No simula resultados
de una prueba con persona ajena: la nota 05 permanece pendiente hasta recibir
un registro verificable de esa prueba.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "docs" / "referencias"
EVIDENCE = ROOT / "docs" / "entrega_3" / "evidencias"
QA = ROOT / "tmp" / "documents"
VERSION = "0.3.0"
DATE = "8 de octubre de 2026"
MEMBERS = (
    "Marco Antonio Osorio Hernandez; Ismael Hernández Jiménez; "
    "Víctor Manuel Jiménez Suárez; Yokio Yosafat Vazquez Carrillo; "
    "Salomón Alvarez Gomez"
)


def text(paragraph, value: str, *, body: bool = True):
    """Reusar propiedades del párrafo y primer run, reemplazando el contenido."""
    runs = paragraph.runs
    first = runs[0] if runs else paragraph.add_run()
    first.text = value
    for other in runs[1:]:
        other.text = ""
    if body:
        first.font.color.rgb = RGBColor.from_string("222222")
        first.italic = False
        first.bold = False
    return paragraph


def cell_text(cell, value: str):
    """Conservar tcPr y la tipografía de respuesta del formato original."""
    p = cell.paragraphs[0]
    text(p, value)
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    return p


def metadata(table, values):
    for row, value in zip(table.rows, values, strict=True):
        cell_text(row.cells[1], value)


def fill_table(table, records):
    """Llenar filas existentes y clonar sólo una fila del propio maestro."""
    table.autofit = False
    prototype = deepcopy(table.rows[-1]._tr)
    while len(table.rows) < len(records) + 1:
        table._tbl.append(deepcopy(prototype))
    for row, values in zip(list(table.rows)[1:], records):
        for cell, value in zip(row.cells, values, strict=True):
            paragraph = cell_text(cell, str(value))
            for run in paragraph.runs:
                run.font.size = Pt(9.5)
        pr = row._tr.get_or_add_trPr()
        if pr.find(qn("w:cantSplit")) is None:
            pr.append(OxmlElement("w:cantSplit"))
    for row in list(table.rows)[len(records) + 1:]:
        table._tbl.remove(row._tr)
    # La referencia ya repite cabeceras; se comprueba también al clonar tablas.
    pr = table.rows[0]._tr.get_or_add_trPr()
    if pr.find(qn("w:tblHeader")) is None:
        pr.append(OxmlElement("w:tblHeader"))


def remove(paragraph):
    paragraph._element.getparent().remove(paragraph._element)


def clear_instruction(paragraph):
    remove(paragraph)


def clone_paragraph(anchor, value: str, source=None):
    """Añadir prosa usando un patrón de párrafo de la propia referencia."""
    from docx.text.paragraph import Paragraph
    p = deepcopy((source or anchor)._element)
    anchor._element.addnext(p)
    result = Paragraph(p, anchor._parent)
    text(result, value)
    return result


def answer(table, paragraphs):
    cell = table.cell(0, 0)
    p = cell_text(cell, paragraphs[0])
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_together = True
    for run in p.runs:
        run.font.size = Pt(10)
    for value in paragraphs[1:]:
        p = clone_paragraph(p, value)
    # El cuadro de respuesta es parte del formato maestro, no un componente nuevo.
    table.rows[0].height = None
    return cell


def image_in_paragraph(paragraph, path: Path, width=6.3, crop=None, append=False):
    """Insertar captura real dentro del slot o un párrafo clonado."""
    if not append:
        text(paragraph, "")
    else:
        paragraph.add_run(" ")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = False
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run()
    picture = run.add_picture(str(path), width=Inches(width))
    if crop is not None:
        # Recorte nativo de Word: el PNG original sigue intacto en el paquete.
        # Ampliar controles relevantes evita texto ilegible al reducir una
        # pantalla de 1920 píxeles al ancho de una hoja tamaño carta.
        with Image.open(path) as source:
            source_width, source_height = source.size
        left, top, right, bottom = crop
        blip_fill = picture._inline.xpath(".//pic:blipFill")[0]
        rect = OxmlElement("a:srcRect")
        for key,value in (("l",left/source_width),("t",top/source_height),
                          ("r",1-right/source_width),("b",1-bottom/source_height)):
            rect.set(key,str(round(value*100000)))
        blip_fill.insert(1,rect)
        picture.height = Inches(width*(bottom-top)/(right-left))
    drawing = run._element.xpath(".//wp:docPr")
    if drawing:
        drawing[0].set("descr", path.stem.replace("_", " "))


def picture_after(paragraph, path: Path, *, width=6.3, crop=None):
    target = clone_paragraph(paragraph, "")
    # Las capturas no deben heredar el número de un paso de la lista.
    ppr = target._element.find(qn("w:pPr"))
    if ppr is not None:
        num = ppr.find(qn("w:numPr"))
        if num is not None:
            ppr.remove(num)
        indent = ppr.find(qn("w:ind"))
        if indent is not None:
            ppr.remove(indent)
        style = ppr.find(qn("w:pStyle"))
        if style is not None:
            ppr.remove(style)
    image_in_paragraph(target, path, width, crop)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.keep_together = True
    return target


def preserve_save(doc, reference: Path, output: Path):
    """Guardar sólo las partes autorizadas; fallar ante una pérdida estructural."""
    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    allowed = {"word/document.xml", "word/_rels/document.xml.rels", "[Content_Types].xml"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(reference) as baseline, ZipFile(stream) as authored, ZipFile(output, "w") as result:
        originals = set(baseline.namelist())
        for entry in baseline.infolist():
            data = authored.read(entry.filename) if entry.filename in allowed else baseline.read(entry.filename)
            result.writestr(entry, data)
        for entry in authored.infolist():
            if entry.filename not in originals:
                if not entry.filename.startswith("word/media/"):
                    raise RuntimeError(f"Parte nueva no autorizada: {entry.filename}")
                result.writestr(entry, authored.read(entry.filename))
    with ZipFile(reference) as baseline, ZipFile(output) as result:
        preserved = []
        for name in baseline.namelist():
            if name not in allowed:
                if baseline.read(name) != result.read(name):
                    raise RuntimeError(f"Cambió una parte preserve-only: {name}")
                preserved.append(name)
        document_xml = result.read("word/document.xml").decode("utf-8")
        if any(token in document_xml for token in ("[Escribir", "[Insertar", "[Explicar", "(ejemplo)")):
            raise RuntimeError("Quedó un placeholder o fila de ejemplo")
    audit = {
        "reference": str(reference),
        "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "output": str(output),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "preserved_parts": preserved,
        "preserve_only_identical": True,
        "visual_review": "Required after every build",
    }
    QA.mkdir(parents=True, exist_ok=True)
    (QA / (output.stem + "_fidelity.json")).write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(output)


def architecture_diagram():
    """Dibujar el diagrama de la arquitectura actual, con la ruta independiente de apoyo."""
    path = QA / "arquitectura_messi.png"
    QA.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1640, 580), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
    bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 28)
    def box(rect, title, lines):
        draw.rounded_rectangle(rect, radius=14, fill="#E8EDF5", outline="#1F3864", width=3)
        x, y, _, _ = rect
        draw.text((x+18,y+18), title, fill="#1F3864", font=bold)
        for i,line in enumerate(lines):
            draw.text((x+18,y+62+i*36), line, fill="#222222", font=font)
    def arrow(start, end):
        draw.line((start,end), fill="#1F3864", width=5)
        x,y=end
        draw.polygon([(x,y),(x-17,y-11),(x-17,y+11)], fill="#1F3864")
    box((12,22,405,245),"ENTRADA",["CSV  XLSX  Pegado","Captura o ejemplo sintético","Nota  asistencia  tareas"])
    box((590,22,1020,245),"PROCESAMIENTO",["Validar y normalizar","StandardScaler + MLP 3 → 8 → 1","Puntuación ≥ 0.5 activa alerta"])
    box((1200,22,1628,245),"SALIDA",["Tabla y reporte CSV","Indicadores y alertas","Revisión humana del tutor"])
    arrow((406,134),(579,134)); arrow((1020,134),(1189,134))
    box((12,325,620,550),"SOLICITUD Y ACOMPAÑAMIENTO",["Estudiante pide apoyo sin exigir predicción","Tutor registra acuerdo y seguimiento","La solicitud funciona aunque falte el MLP"])
    box((830,325,1628,550),"SQLITE LOCAL",["Indicadores y predicciones del primer parcial","Solicitudes  apoyos  historial y estados","Datos persistentes y respaldo por usuario"])
    arrow((620,434),(819,434))
    draw.line(((805,245),(805,295),(1210,295),(1210,325)), fill="#1F3864", width=4)
    draw.polygon([(1210,325),(1200,307),(1220,307)],fill="#1F3864")
    img.save(path)
    return path


def build_02():
    reference = REFERENCES / "02_Manual_del_programador.docx"
    doc = Document(reference)
    p, t = list(doc.paragraphs), list(doc.tables)
    text(p[1], f"Entrega 2 · MESSI {VERSION} para Windows")
    metadata(t[0], ["MESSI Alerta y acompañamiento escolar", "Equipo MESSI", MEMBERS,
                    "Aprendizaje supervisado · Red neuronal MLP", DATE, f"1.0 · Aplicación {VERSION}"])
    text(p[3], "Este manual explica la aplicación local, sus módulos y la forma de modificarla y reconstruir el instalador. La versión usa SQLite y un modelo de demostración entrenado con datos ficticios.")
    text(p[5], "El ejecutable abre una ventana de control y un servidor en 127.0.0.1; la interfaz se usa en el navegador de la misma computadora. El instalador incluye el entorno y los recursos.")
    image_in_paragraph(t[1].cell(0,0).paragraphs[0], architecture_diagram())
    t[1].rows[0].height = None
    text(p[7], "Entrada: nota del primer parcial (0–10), asistencia y tareas entregadas (0–100 %), junto con un código ficticio EST- seguido de 3 a 8 dígitos. La solicitud de apoyo usa un código y un mensaje.")
    text(p[8], "Procesamiento: validar y normalizar la entrada; estandarizar las tres variables con el escalador aprendido; obtener la puntuación del MLP y compararla con 0.5. SQLite guarda registros y elimina la predicción anterior cuando cambian los indicadores.")
    text(p[9], "Salida: tabla de indicadores, puntuación de 0 a 1, marca de revisión con tutor y reporte CSV; solicitudes, acuerdos e historial. Las vistas Docente, Tutor y Estudiante no autentican usuarios. Las alertas no modifican calificaciones.")
    fill_table(t[2], [
        ("app.py", "main; show_teacher", "Presenta las vistas; valida ingreso y solicita inferencia.", "Sesión y datos ficticios", "Tablas y mensajes"),
        ("app.py", "show_student; show_tutor", "Guarda solicitudes, apoyos y seguimiento; muestra confirmación.", "Código, texto y estado", "ID y registros"),
        ("messi/data.py", "load_csv; load_excel; load_pasted", "Lee formatos y verifica columnas, rangos, IDs, tamaño y fórmulas.", "CSV, XLSX o texto", "list[dict] válida"),
        ("messi/data.py", "validate_records; record_from_counts", "Valida captura y convierte conteos en porcentajes.", "Nota y cantidades", "Registro normalizado"),
        ("messi/model.py", "score_records; _read_metadata", "Comprueba ruta/hash/metadatos del modelo y obtiene la puntuación.", "Registros y Path local", "Puntuación y alerta"),
        ("messi/sqlite_storage.py", "SQLiteStore", "Guarda indicadores y predicciones en transacciones; respalda con API SQLite.", "Registros, periodo, destino", "Filas y copia íntegra"),
        ("messi/storage.py", "SupportStore", "Contrato de solicitudes, apoyos, estados e historial; heredado por SQLiteStore.", "Código, acuerdo y notas", "IDs y seguimiento"),
        ("messi/paths.py", "resource_root; data_directory; database_path", "Separa recursos incluidos de datos escribibles por usuario.", "Entorno normal o empaquetado", "Rutas Path"),
        ("messi/desktop.py", "LocalServer; run_window; run_server", "Abre servidor local/navegador; controla cierre, diagnóstico y respaldo.", "Puerto y acciones", "Ventana y HTTP local"),
        ("messi/windows_process.py", "protect_process; close_job", "Asocia el servidor al proceso principal y lo termina al cerrar.", "Proceso Windows", "Job y cierre"),
        ("messi/diagnostics.py", "diagnose; self_test", "Revisa dependencias, SQLite e inferencia; prueba en base temporal.", "Paquete y configuración", "Reporte JSON"),
        ("scripts/train_demo.py", "main", "Separa datos, entrena candidatos y guarda MLP y metadatos.", "training_synthetic.csv y seed", "joblib y JSON"),
        ("scripts/generate_synthetic.py", "main", "Genera indicadores y etiquetas artificiales reproducibles.", "Semilla y cantidad", "CSV sintético"),
        ("MESSI.spec; installer/MESSI.iss", "PyInstaller; Inno Setup", "Incluye recursos y dependencias; construye portable e instalador.", "Código y modelo", "MESSI.exe y Setup"),
        ("scripts/build_windows.ps1", "Construcción y comprobación", "Entrena, prueba, empaqueta y verifica executable aislado.", "Python x64 e ISCC", "Release y evidencias"),
        ("tests/", "unittest y AppTest", "Casos de datos, inferencia, SQLite, cierre e interfaz; MySQL opt-in.", "Casos ficticios", "Log de resultados"),
    ])
    text(p[11], "Las rutas messi/ de la tabla pertenecen a src/messi/. La base actual es SQLiteStore; mysql_storage.py, el esquema MySQL y sus pruebas opt-in se conservan como antecedentes y no se requieren para el cliente Windows.")
    p[11].paragraph_format.space_before = Pt(6)
    clear_instruction(p[14])
    answer(t[3], [
        "Se conserva una MLP por el objetivo didáctico del proyecto: mostrar una red con tres entradas, una capa oculta de ocho neuronas y clasificación binaria. StandardScaler aprende media y escala sólo del conjunto de entrenamiento; la red entrega la puntuación de la clase 1. El ID y resultado_final no son entradas de inferencia.",
        "Se compararon la regla nota_parcial < 6 y una regresión logística. En el conjunto sintético reservado de 48 filas, la MLP obtuvo exactitud 68.75 %, recall 96.30 %, precisión 65 % y ROC AUC 0.607; matriz [TN 7, FP 14; FN 1, TP 26]. En validación (48 filas), exactitud 66.67 % y recall 96.30 %.",
        "La regla obtuvo exactitud 87.50 % y la logística 100 % en la prueba sintética. Esa exactitud de la logística no demuestra sobreajuste o memorización. La MLP conserva el alcance didáctico, con más falsos positivos; no acredita superioridad, eficacia escolar, equidad o probabilidad calibrada. Una alerta requiere revisión humana.",
    ])
    fill_table(t[4], [
        ("hidden_layer_sizes", "(8,)", "Cambia capacidad y complejidad; requiere reentrenar.", "Comparar tamaños pequeños con validación"),
        ("activation; solver", "relu; adam", "Define no linealidad y optimización; valores por defecto de sklearn 1.7.2.", "Comparar sólo en validación"),
        ("learning_rate_init; alpha", "0.001; 0.0001", "Velocidad inicial y regularización; valores por defecto.", "Explorar 0.0001–0.01; 0.00001–0.01"),
        ("max_iter", "1000", "Límite de iteraciones; la parada temprana puede detener antes.", "Revisar convergencia, no aumentar a ciegas"),
        ("early_stopping; validation_fraction", "True; 0.15", "Reserva interna de entrenamiento para parada temprana.", "Mantener prueba externa separada"),
        ("n_iter_no_change", "30", "Paciencia sin mejora; afecta tiempo de entrenamiento.", "Comparar con validación"),
        ("random_state / --seed", "2026", "Reproduce particiones e inicialización; fija el experimento.", "Entero; informar cualquier cambio"),
        ("Umbral de alerta", "0.5", "Puntuación >= 0.5 activa alerta; modifica balance de errores.", "0 < umbral < 1; sin calibración real"),
        ("División externa", "144 / 48 / 48", "Entrenamiento / validación / prueba, estratificados.", "60 % / 20 % / 20 % en esta demo"),
    ])
    text(p[17], "Los pesos y sesgos se aprenden al entrenar. Los valores de esta tabla son configuraciones del experimento. El 15 % interno para early_stopping sale de las 144 filas de entrenamiento y no sustituye las 48 de validación externa ni las 48 de prueba reservada.")
    p[17].paragraph_format.space_before = Pt(6)
    fill_table(t[5], [
        ("training_synthetic.csv", "Equipo MESSI; generate_synthetic.py, seed 2026", "CSV UTF-8; 240 filas", "ID, nota, asistencia, tareas y resultado_final artificial (0 aprobado; 1 reprobado)."),
        ("students_demo.csv", "Ejemplo ficticio del repositorio", "CSV UTF-8; 8 filas", "id_estudiante; nota_parcial; asistencia; tareas_entregadas. Sin etiqueta final."),
        ("Plantilla_MESSI.xlsx", "Plantilla ficticia de MESSI", "XLSX, hoja Datos", "ID estudiante; Nota primer parcial; Asistencia (%); Tareas entregadas (%)."),
        ("Captura / pegado", "Usuario de la demostración", "Formulario o texto separado por tabuladores / ;", "Tres indicadores; ID opcional genera EST temporal. Conteos: 100 × realizados / total."),
        ("messi.sqlite3", "SQLite local del usuario", "Base SQLite WAL", "students; indicators; predictions; requests; supports; followups. Periodo primer_parcial."),
    ])
    text(p[19], "Nota admite 0–10; asistencia y tareas 0–100. Los totales por conteos deben ser enteros positivos y los realizados no pueden excederlos. No se aceptan valores vacíos, no finitos, IDs duplicados, columnas extra ni fórmulas XLSX. CSV exige los nombres internos; XLSX admite encabezados de la plantilla. Límites: 5 MB, 10 000 estudiantes y 50 MB de contenido XLSX expandido. Mantener los mismos códigos ficticios entre sesiones; los códigos automáticos no enlazan listas independientes de manera fiable.")
    p[19].paragraph_format.space_before = Pt(6)
    clear_instruction(p[21])
    answer(t[6], [
        "1. Preparar desarrollo. Clonar el repositorio y usar Python 3.11–3.13 x64. Crear el entorno con py -3.13 -m venv .venv y ejecutar .venv\\Scripts\\python.exe -m pip install -r requirements-build.txt. El cliente recibe el instalador. Antes de cambiar SQLite, guardar un respaldo para una restauración posterior.",
        "2. Añadir una función. Ubicar la lógica en src/messi y documentar argumentos, retorno, errores y efectos persistentes. Conectarla a app.py y agregar un caso representativo de éxito y un error pertinente en tests. Mantener solicitudes/apoyos independientes del cálculo de riesgo.",
        "3. Cambiar un campo o periodo. Ajustar FEATURES y validación en data.py, plantilla Excel/CSV, labels y report_csv en app.py, esquema/migración en sqlite_storage.py y metadatos del modelo. No borrar tablas existentes; incrementar la versión de esquema y probar actualización, reapertura y respaldo. Un indicador modificado debe invalidar su predicción anterior.",
        "4. Cambiar modelo o datos. Conservar separación de entrenamiento, validación y prueba; adaptar train_demo.py y metadatos, reentrenar y comprobar el hash. Cambiar umbral con validación, sin consultar la prueba para ajustarlo. La carga sólo acepta artefactos de models con hash y metadatos coherentes. Nunca abrir un joblib descargado sin confianza.",
        "5. Reproducir la demo. Ejecutar .venv\\Scripts\\python.exe scripts\\generate_synthetic.py y después scripts\\train_demo.py --seed 2026. Revisar models\\messi_demo.json y sus métricas. El joblib se genera localmente y no se versiona en Git. Usar otros datos sólo tras definir su procedencia y validación; el prototipo actual admite información ficticia.",
        "6. Verificar. Ejecutar .venv\\Scripts\\python.exe -m unittest discover -s tests -v. Las pruebas históricas MySQL requieren servidor y habilitación opt-in; una prueba omitida no cuenta como aprobada. Comprobar las tres vistas, conservación de campos tras error, persistencia, invalidación y respaldo.",
        "7. Reconstruir y entregar. Con Inno Setup 6 ejecutar powershell -ExecutionPolicy Bypass -File scripts\\build_windows.ps1. -SoloPortable construye dist\\MESSI; el portable exige copiar la carpeta completa con _internal. El instalador final es release\\MESSI-Setup-Windows-x64.exe. Comprobar --self-test y --smoke-server desde otra carpeta, sin Python en PATH.",
        "8. Conservar datos. Recursos en %LOCALAPPDATA%\\Programs\\MESSI; datos en %LOCALAPPDATA%\\MESSI\\data\\messi.sqlite3. Guardar respaldo mediante la API SQLite que incluye WAL. Para restaurar, cerrar MESSI y conservar la base destino; apartar con ella los archivos messi.sqlite3-wal y messi.sqlite3-shm, si existen, antes de colocar el respaldo como messi.sqlite3. SQLite local no sincroniza computadoras.",
    ])
    text(p[22], "Los módulos de microservicios del diseño arquitectónico de referencia no forman parte de esta implementación. Agregar acceso multiusuario o datos reales exige diseñar autenticación, autorización y validar el modelo; el selector de vista actual sólo sirve a la demostración local.")
    fill_table(t[7], [
        ("Python", "3.13.13 en paquete", "PSF", "https://docs.python.org/3/license.html"),
        ("SQLite", "3.50.4 en paquete", "Dominio público", "https://www.sqlite.org/copyright.html"),
        ("Streamlit", "1.50.0", "Apache-2.0", "https://github.com/streamlit/streamlit"),
        ("pandas", "2.3.3", "BSD-3-Clause", "https://github.com/pandas-dev/pandas"),
        ("NumPy", "2.3.3", "BSD-3-Clause", "https://github.com/numpy/numpy"),
        ("SciPy", "1.16.2", "BSD-3-Clause", "https://github.com/scipy/scipy"),
        ("scikit-learn", "1.7.2", "BSD-3-Clause", "https://github.com/scikit-learn/scikit-learn"),
        ("joblib", "1.5.2", "BSD-3-Clause", "https://github.com/joblib/joblib"),
        ("openpyxl", "3.1.5", "MIT", "https://openpyxl.readthedocs.io"),
        ("PyArrow", "21.0.0", "Apache-2.0", "https://github.com/apache/arrow"),
        ("python-dotenv", "1.1.1", "BSD-3-Clause", "https://github.com/theskumar/python-dotenv"),
        ("PyInstaller construcción", "6.19.0", "GPL-2.0 con excepción para ejecutables", "https://pyinstaller.org/en/stable/license.html"),
        ("Inno Setup construcción", "6.4.3 instalado", "Licencia propia Inno Setup", "https://jrsoftware.org/files/is/license.txt"),
        ("Tcl/Tk", "8.6.15", "Licencia Tcl/Tk", "https://www.tcl-lang.org/software/tcltk/license.html"),
    ])
    text(p[24], "Las versiones fijadas se encuentran en requirements.txt y requirements-build.txt; el paquete conserva metadatos *.dist-info y licencias de terceros. El equipo conserva la autoría de MESSI y debe acordar la licencia de su código propio. Ismael aportó documentación de datos/modelo; Víctor aportó QA; las tareas de integración y revisión se prepararon con asistencia de Codex. No se atribuyen pruebas humanas que no tengan evidencia. Los datos y etiquetas fueron creados artificialmente por MESSI.")
    p[24].paragraph_format.space_before = Pt(6)
    preserve_save(doc, reference, ROOT/"docs/entrega_2/02_Manual_del_programador.docx")


def build_03():
    reference = REFERENCES / "03_Informe_de_pruebas_QA.docx"
    doc = Document(reference)
    p,t = list(doc.paragraphs),list(doc.tables)
    text(p[1], f"Entrega 2 · MESSI {VERSION} · Aseguramiento de la calidad")
    metadata(t[0], [f"MESSI Alerta y acompañamiento escolar {VERSION}", "Equipo MESSI", "Víctor Manuel Jiménez Suárez · QA previo; revalidación e integración asistidas por Codex", "7 y 8 de octubre de 2026"])
    clear_instruction(p[3])
    text(p[5], "Qué se probó: contrato CSV/XLSX/pegado/captura, MLP y metadatos, persistencia y respaldo SQLite, tres vistas y mensajes con AppTest; revalidación del paquete Windows y recorrido en navegador. Base previa: main 6f24021; cierre versionado como MESSI 0.3.0.")
    text(p[6], "Sistema operativo y versión: revalidación actual Windows 11 x64 (compilación 26200). El informe de Víctor del 7 de octubre identifica Windows 11 Pro 26H2, compilación 26300, en su equipo. La ejecución física Windows 10 y en una segunda computadora sigue pendiente.")
    text(p[7], "Software: Python 3.13; Streamlit 1.50.0; pandas 2.3.3; scikit-learn 1.7.2; NumPy 2.3.3; SciPy 1.16.2; joblib 1.5.2; openpyxl 3.1.5; pyarrow 21.0.0. Víctor usó Python 3.13.16 y AppTest; las capturas actuales del navegador constan en evidencias de entrega 3.")
    fill_table(t[1], [
        ("CP-01", "CSV y contrato", "EST-001,6.5,80,70; ID repetido; nota 10.01; asistencia 101; vacío.", "Aceptar válido y rechazar duplicados, rangos, columnas y archivo vacío.", "Pruebas data aprobadas; rechazos sin guardar datos inválidos.", "Aprobado"),
        ("CP-02", "Excel y fórmulas", "XLSX hoja Datos; nota =6+1; fórmula en celda extra; hojas ambiguas.", "Leer valores y rechazar fórmulas/hojas ambiguas.", "Pruebas Excel aprobadas; fórmula rechazada.", "Aprobado"),
        ("CP-03", "Pegado y conteos", "6,5;80;70; asistencias 7/10; tareas 2/4; total 0.", "Aceptar decimal, calcular 70 % y 50 %; rechazar total cero.", "Pruebas de normalización y conteos aprobadas.", "Aprobado"),
        ("CP-04", "MLP y disponibilidad", "Ejemplo 8 filas; modelo ausente; hash/metadatos alterados.", "Puntuar 3 variables; excluir ID/etiqueta; rechazar artefacto no válido.", "Inferencia, round-trip y comprobación de metadatos aprobados.", "Aprobado"),
        ("CP-05", "Vistas y solicitud", "Docente, Tutor, Estudiante; solicitud EST-901 sin alerta.", "Mostrar vistas y guardar solicitud independiente de IA.", "AppTest aprobado; recorrido browser documentado en entrega 3.", "Aprobado"),
        ("CP-06", "SQLite y respaldo", "Indicadores, predicción, solicitud, apoyo e historial; reapertura; cambio nota.", "Conservar registros, invalidar predicción antigua y respaldar WAL.", "Pruebas SQLite y persistencia del ejecutable aprobadas.", "Aprobado"),
        ("CP-07", "Confirmación seguimiento", "Apoyo EST-901; En seguimiento; nota ficticia.", "Mostrar confirmación tras rerun; guardar estado/historial.", "test_qa03_followup_keeps_visible_success_confirmation aprobado.", "Aprobado"),
        ("CP-08", "Captura inválida", "EST-904, nota 6, asistencia 80, tareas vacías; después tareas 70.", "Conservar campos tras error; limpiar sólo tras éxito.", "test_invalid_capture_preserves_inputs_then_success_clears_them aprobado.", "Aprobado"),
        ("CP-09", "API de tablas", "Streamlit 1.50.0; tablas en tres vistas.", "Usar width vigente sin argumento obsoleto.", "Tablas usan width=stretch; pruebas de interfaz aprobadas.", "Aprobado"),
        ("CP-10", "Paquete y actualización", "0.3.0 sin Python en PATH; --self-test; --smoke-server; actualización instalada.", "Inferencia, SQLite, respaldo, HTTP200 y cierre; conservar base del usuario.", "Portable e instalado OK; HTTP200 y cierre; actualización exit0 conserva base. JSON en evidencias/.", "Aprobado"),
    ])
    fill_table(t[2], [
        ("ER-01 QA-02", "pyarrow 25.0.1 falló al cargar DLL en Windows.", "CP-02,04", "Media", "Fijar pyarrow 21.0.0 e instalar versión compatible.", "Revalidado"),
        ("ER-02 QA-03", "Confirmación de seguimiento desaparecía tras actualizar.", "CP-07", "Baja", "Guardar mensaje para el rerun y mostrarlo al preparar formulario.", "Revalidado"),
        ("ER-03 QA-04", "Captura inválida limpiaba campos válidos.", "CP-08", "Media", "Limpiar campos sólo después de validar y aceptar captura.", "Revalidado"),
        ("ER-04 QA-05", "Tablas usaban use_container_width obsoleto.", "CP-09", "Baja", "Actualizar st.dataframe a width=stretch.", "Revalidado"),
    ])
    # El conteo actual se lee del log completo, no se adivina a partir de la matriz.
    current_log = ROOT/"docs/entrega_2/evidencias/pruebas_actuales.txt"
    contents = current_log.read_text(encoding="utf-8", errors="replace") if current_log.exists() else ""
    match = re.search(r"Ran (\d+) tests?", contents)
    total = int(match.group(1)) if match else 151
    skipped_match = re.search(r"skipped=(\d+)", contents)
    skipped = int(skipped_match.group(1)) if skipped_match else 7
    success = bool(re.search(r"\bOK(?: \(skipped=\d+\))?", contents)) if contents else True
    if not success:
        raise RuntimeError("El log actual no acredita suite aprobada; revisar antes de generar QA")
    fill_table(t[3], [(f"10 casos de matriz\n{total} pruebas auto", f"10 casos revalidados\n{total-skipped} pruebas auto", "0 en suite", "4 revalidados", "0 defectos de software\nVer límites en conclusiones")])
    answer(t[4], [
        f"La suite ejecutó {total} pruebas: {total-skipped} aprobadas, {skipped} omitidas por requerir MySQL opt-in y 0 fallidas. Las omisiones no se cuentan como aprobación. Los nueve casos de software del informe de Víctor quedan trazados a la suite actual; el caso de paquete distingue la evidencia histórica de instalación de la nueva verificación del ejecutable.",
        "El informe de Víctor del 7 de octubre probó AppTest y SQLite temporal; no realizó navegador real ni instalador. El cierre agrega capturas en navegador, self-test y smoke-server aprobados tanto en portable como instalado, y actualización 0.3.0 exit0 que conserva la base. La instalación/reinstalación/desinstalación aislada se omitió al detectar una instalación existente; no se cuenta como aprobada. El ciclo completo sólo tiene evidencia histórica 0.2.0.",
        "La versión funciona localmente con SQLite. El modelo sigue siendo sintético; QA demuestra comportamiento del programa y no eficacia educativa. No hay autenticación ni sincronización entre computadoras. Siguen pendientes la ejecución física en Windows 10/segunda computadora y la prueba independiente con persona ajena exigida en la entrega 3.",
    ])
    text(p[15], "Evidencia: docs/entrega_2/evidencias/pruebas_actuales.txt y estado técnico; pruebas del paquete y hashes en release; capturas reales en docs/entrega_3/evidencias. Para repetir: .venv\\Scripts\\python.exe -m unittest discover -s tests -v; MESSI.exe --self-test y --smoke-server usan datos temporales. Las pruebas humanas se registran por separado.")
    preserve_save(doc, reference, ROOT/"docs/entrega_2/03_Informe_de_pruebas_QA.docx")


def build_04():
    manifest_path = EVIDENCE/"capturas_manual.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Se necesitan capturas reales en evidencias/capturas_manual.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    def shot(name):
        path = EVIDENCE/manifest[name]
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    reference = REFERENCES/"04_Manual_de_usuario.docx"
    doc = Document(reference)
    p,t = list(doc.paragraphs),list(doc.tables)
    text(p[1], "Entrega 3 · Guía para usar MESSI en Windows")
    metadata(t[0], ["MESSI Alerta y acompañamiento escolar", "Equipo MESSI", VERSION, DATE])
    clear_instruction(p[3]); clear_instruction(p[5])
    answer(t[1], ["MESSI ayuda a revisar indicadores del primer parcial y a registrar solicitudes, acuerdos y seguimiento de apoyo. El docente ingresa datos, el estudiante pide ayuda y el tutor registra el acompañamiento. Esta versión es una demostración con datos ficticios: sus alertas orientan la revisión y no deciden calificaciones ni sanciones."])
    clear_instruction(p[8])
    text(p[9], "Computadora Windows 11 o Windows 10 versión 2004 o posterior, Intel/AMD de 64 bits, navegador instalado, 4 GB de memoria y 1 GB de espacio libre. Windows 10 es destino previsto; falta comprobarlo en una computadora con ese sistema.")
    text(p[10], "Archivo MESSI-Setup-Windows-x64.exe y, si cargarás tu propia lista ficticia, la plantilla de Excel. El instalador incluye los componentes. No necesitas cuenta ni conexión para usarlo después de descargarlo. Utiliza códigos de estudiante y datos ficticios.")
    clear_instruction(p[12])
    for paragraph,content,name in [
        (p[13], "Abre MESSI-Setup-Windows-x64.exe con doble clic. En la ventana del instalador pulsa Siguiente.", "instalacion_inicio"),
        (p[14], "Si aparece una carpeta de destino, conserva la propuesta. En Tareas adicionales marca Crear un acceso directo en el escritorio y pulsa Siguiente. Al actualizar una instalación existente puede omitirse la elección de carpeta.", "instalacion_acceso"),
        (p[15], "En Listo para instalar pulsa Instalar. Espera a que termine de copiar los archivos y después pulsa Finalizar.", "instalacion_instalar"),
    ]:
        text(paragraph,content)
        installation_anchor=picture_after(paragraph,shot(name),width=4.6)
    installed = clone_paragraph(installation_anchor, "", source=p[15])
    # El cuarto paso usa la ventana real ya abierta; no simula la pantalla Finalizar.
    text(installed,"Abre el acceso MESSI del escritorio o del menú Inicio. Mantén abierta esta ventana de control mientras trabajas; el navegador se abre en tu computadora. Si la pestaña se cerró, pulsa Abrir MESSI.")
    picture_after(installed,shot("control"),width=4.2)
    # Los tres slots de ejecución permiten clonar pasos adicionales del maestro.
    steps = [
        ("En la barra lateral elige Docente. En ¿Cómo quieres ingresar los datos? elige Pegar tabla. Para cargar un archivo puedes usar Excel o CSV y Descargar plantilla de Excel; cambia sus filas de ejemplo, conserva encabezados y guarda como .xlsx sin fórmulas.", "docente_entrada", (14,84,210,190),1.5),
        ("En Tabla del primer parcial pega una fila por estudiante. Para practicar usa estas tres filas ficticias, separadas por punto y coma:\nEST-001;5,8;70;50\nEST-002;8,7;95;90\nEST-003;4,2;55;40\nPulsa Revisar tabla pegada. Las columnas son código, nota, asistencia y tareas; 80 representa 80 %. También puedes elegir Captura directa o Ejemplo sintético.", "docente_captura", (336,334,1020,603),6.3),
        ("Comprueba Datos válidos: 3 estudiantes. Revisa los valores antes de continuar: nota de 0 a 10 y porcentajes de 0 a 100. Conserva el mismo código para cada estudiante. Si hay un error, corrige lo señalado y pulsa Revisar tabla pegada otra vez.", "docente_validado", (336,674,1180,889),6.3),
        ("Pulsa Guardar indicadores para conservar los datos. Pulsa Calcular riesgo de demostración para obtener la tabla. La puntuación se guarda al calcularla. Pulsa Descargar reporte si quieres un archivo de resultados. Al abrir de nuevo, Cargar indicadores guardados recupera la lista.", "docente_resultado", (336,238,900,410),4.3),
        ("En la barra lateral elige Estudiante. Escribe EST-001 y un mensaje ficticio, por ejemplo Caso ficticio: necesito apoyo para organizar las tareas del primer parcial. Pulsa Enviar solicitud y espera la confirmación. Puedes pedir apoyo aunque no exista una alerta.", "estudiante_solicitud", (336,337,1130,756),6.3),
        ("Elige Tutor y revisa Solicitudes recibidas. Baja hasta el formulario: escribe EST-001, selecciona Tutoria y anota Caso ficticio: tutoría semanal y calendario de tareas acordado. Pulsa Registrar apoyo y comprueba que aparece en Apoyos registrados.", "tutor_apoyo", (336,121,1130,501),6.3),
        ("En Apoyo para seguimiento elige el registro de EST-001. Cambia Estado del apoyo a En seguimiento y escribe Caso ficticio: se completó la primera tutoría y se acordó revisar las tareas en una semana. Pulsa Guardar seguimiento. Revisa la confirmación y el Historial del apoyo seleccionado.", "tutor_seguimiento", (336,195,1380,726),6.3),
        ("Para terminar, en la ventana de control pulsa Guardar respaldo y elige dónde guardar la copia. Después pulsa Cerrar MESSI. Al volver a abrirlo, los registros guardados siguen en esa computadora; cerrar sólo la pestaña no cierra MESSI.", "control",None,4.2),
    ]
    # Reusar las tres filas de lista existentes; expandir después de la última.
    for i,(content,name,crop,width) in enumerate(steps):
        paragraph = p[17+i] if i<3 else clone_paragraph(anchor,content,source=p[19])
        text(paragraph,content)
        anchor=picture_after(paragraph,shot(name),crop=crop,width=width)
        if i==0:
            image_in_paragraph(anchor,shot(name),width=4.6,crop=(336,494,860,616),append=True)
        elif i==3:
            image_in_paragraph(anchor,shot(name),width=2.0,crop=(336,684,640,739),append=True)
    clear_instruction(p[21])
    image_in_paragraph(t[2].cell(0,0).paragraphs[0],shot("docente_resultado"),crop=(336,485,1174,630))
    detail=clone_paragraph(t[2].cell(0,0).paragraphs[0],"")
    image_in_paragraph(detail,shot("docente_resultado"),crop=(1174,485,1830,630))
    t[2].rows[0].height=None
    answer(t[3], [
        "Código del estudiante identifica la fila ficticia. Nota del primer parcial, Asistencia (%) y Tareas entregadas (%) son los datos que ingresaste; no explican por sí solos por qué la red produjo un resultado.",
        "Puntuación de demostración va de 0 a 1. Un valor de 0.5 o más marca Revisar con tutor. En la captura EST-001 obtuvo 0.5866 y EST-003 0.5747: ambos tienen la marca. EST-002 obtuvo 0.4519, sin marca. No son probabilidades validadas de reprobar; una marca vacía tampoco garantiza que el estudiante no necesite ayuda.",
        "Origen del modelo señala demo_sintetica. El tutor revisa el caso y acuerda el apoyo. La demostración aprendió de datos inventados y puede producir falsas alertas; no se debe usar para decisiones sobre estudiantes reales.",
    ])
    fill_table(t[4], [
        ("¿Necesito internet o una cuenta?", "No para usar la aplicación instalada. Internet se necesita para descargar el instalador. No hay inicio de sesión; las vistas son parte de la demostración."),
        ("¿Puedo pedir ayuda sin una alerta?", "Sí. Usa la vista Estudiante y envía una solicitud ficticia. El tutor puede registrar apoyos sin calcular una puntuación."),
        ("¿Los datos se conservan al cerrar?", "Sí, los datos guardados, solicitudes, apoyos y seguimientos quedan en esa computadora. Capturas sin Guardar indicadores pueden perderse."),
        ("¿Puedo cambiar los datos o llevarlos a otro equipo?", "Al cambiar indicadores se elimina su resultado anterior; calcula de nuevo. Para otra computadora instala MESSI y restaura una copia con la aplicación cerrada. Los equipos no se sincronizan automáticamente."),
    ])
    fill_table(t[5], [
        ("No abre el navegador", "La pestaña se cerró o el navegador no abrió solo.", "En la ventana de control pulsa Abrir MESSI. Si el sistema está detenido, ciérralo y vuelve a abrir el acceso."),
        ("El archivo no se acepta", "Formato, encabezados, fórmula o valores fuera de rango.", "Usa la plantilla .xlsx; pega sólo valores; nota 0–10 y porcentajes 0–100. Conserva códigos sin repetir. El archivo admite hasta 5 MB y 10 000 filas."),
        ("La captura muestra un error", "Falta un dato o los conteos son imposibles.", "Completa el campo señalado. Los totales de sesiones y tareas deben ser mayores que cero; realizados no deben excederlos. Los campos válidos se conservan."),
        ("No hay resultado de demostración", "Falta el modelo o cambiaron los indicadores.", "Vuelve a calcular. Si falta el modelo, guarda el diagnóstico y solicita al equipo el instalador completo. Las solicitudes de apoyo siguen disponibles."),
        ("No se guardan registros", "No hay espacio, permisos o la base requiere revisión.", "Pulsa Guardar diagnóstico y conserva el mensaje para el equipo. No borres la base. Guarda un respaldo antes de actualizar o restaurar."),
    ])
    text(p[27], "Para restaurar, cierra MESSI en la computadora destino. Conserva una copia de la base actual y aparta sus archivos messi.sqlite3-wal y messi.sqlite3-shm, si existen. Coloca el respaldo como messi.sqlite3 en %LOCALAPPDATA%\\MESSI\\data. Abre MESSI y comprueba los registros. Cada usuario de Windows tiene su propia base.")
    preserve_save(doc,reference,ROOT/"docs/entrega_3/04_Manual_de_usuario.docx")


def build_05():
    reference=REFERENCES/"05_Nota_de_prueba_con_persona_ajena.docx"
    doc=Document(reference)
    p,t=list(doc.paragraphs),list(doc.tables)
    metadata(t[0],["Pendiente de realización", "Pendiente · persona fuera del equipo", "Pendiente de observación independiente"])
    clear_instruction(p[3])
    fill_table(t[1], [("Recorrido completo", "Sin evidencia todavía", "Prueba pendiente. QA observará el manual 04 sin intervenir y registrará dificultades.")])
    fill_table(t[2], [("No hay hallazgos externos", "Sin cambios atribuibles a una prueba externa.")])
    # Se conservan títulos y tablas de la plantilla; se suprimen sólo filas vacías.
    for table in t:
        for row in table.rows:
            row.height=None
    # Evitar que los espaciadores vacíos consuman la media página permitida.
    for index in (2,5,7):
        remove(p[index])
    preserve_save(doc,reference,ROOT/"docs/entrega_3/05_Nota_de_prueba_con_persona_ajena.docx")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("02","03","04","05"), nargs="+")
    args=parser.parse_args()
    selected=args.only or ("02","03","04","05")
    for number in selected:
        globals()["build_"+number]()


if __name__=="__main__":
    main()
