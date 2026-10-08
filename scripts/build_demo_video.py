"""Build a narrated MESSI walkthrough from verified screenshots and synthetic speech.

Use the bundled Python runtime. Extra video dependencies can live in
.qa/video-tools; the source screenshots must already exist before video assembly.
No UI is reconstructed: screenshots are scaled proportionally and letterboxed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".qa" / "video-tools"))
DOCS = ROOT / "docs" / "entrega_3"
WORK = ROOT / ".qa" / "demo_video"
RELEASE = ROOT / "release"
SIZE = (1920, 1080)
VOICE = "es-MX-DaliaNeural"

SCENES = [
    {
        "id": "01", "section": "Problema y caso", "title": "Acompañamiento desde el primer parcial",
        "screen": "01_docente_inicio.png",
        "text": "Presentamos MESSI, una aplicación local de alerta y acompañamiento escolar. El problema es que las dificultades pueden detectarse tarde, cuando ya se acumuló una baja calificación o pocas entregas. Este proyecto reúne indicadores del primer parcial para orientar una revisión del tutor. El recorrido utiliza capturas reales de la aplicación y narración sintética, con información completamente ficticia.",
    },
    {
        "id": "02", "section": "Problema y caso", "title": "Un caso ficticio y tres indicadores",
        "screen": "03_datos_validados.png",
        "text": "Nuestro caso de demostración es un grupo ficticio. Cada estudiante se identifica con un código, sin nombre ni expediente. Se registran la nota parcial, la asistencia y las tareas entregadas. Una nota baja o pocos porcentajes pueden motivar una conversación de apoyo. La decisión corresponde al tutor; la aplicación no modifica calificaciones ni aplica sanciones.",
    },
    {
        "id": "03", "section": "Demostración entrada", "title": "Ingresar y revisar los datos",
        "screen": "02_entrada_tabla.png",
        "text": "En la vista Docente elegimos cómo ingresar los datos. MESSI admite una plantilla de Excel, un CSV, una tabla pegada, captura directa y un ejemplo sintético. La nota debe estar entre cero y diez, y los porcentajes entre cero y cien. La pantalla confirma cuántos registros son válidos y permite comprobarlos antes de continuar. Los códigos enlazan después los apoyos.",
    },
    {
        "id": "04", "section": "Demostración entrada", "title": "Rechazar datos fuera de rango",
        "screen": "09_validacion_invalida.png",
        "text": "La validación rechaza valores fuera de rango, identificadores duplicados, datos faltantes y fórmulas en Excel. Aquí pegamos una fila ficticia con nota doce, que supera el máximo de diez. La aplicación señala el campo que debe corregirse. Para continuar hay que corregir el dato y volver a revisar la tabla. Esta entrada inválida no genera una predicción.",
    },
    {
        "id": "05", "section": "Demostración proceso", "title": "Calcular la puntuación de demostración",
        "screen": "04_resultado_modelo.png",
        "text": "Al pulsar Calcular riesgo de demostración, el programa usa una red neuronal con una capa de ocho neuronas y un escalador. El modelo recibe únicamente los tres indicadores. No recibe el código del estudiante ni la etiqueta final usada al entrenar. La alerta se activa cuando la puntuación es mayor o igual a cero punto cinco, el umbral de esta demostración.",
    },
    {
        "id": "06", "section": "Demostración salida", "title": "Interpretar la salida y descargar el reporte",
        "screen": "04_resultado_modelo.png",
        "text": "La salida conserva los indicadores y añade una puntuación entre cero y uno y una marca para revisar el caso con un tutor. El botón Descargar reporte genera un CSV. Los indicadores y predicciones se guardan en la base local SQLite. Si cambian los indicadores, una predicción anterior debe recalcularse. La puntuación orienta esta simulación; no es una probabilidad escolar validada.",
    },
    {
        "id": "07", "section": "Demostración acompañamiento", "title": "Solicitar apoyo aunque no haya alerta",
        "screen": "06_solicitud_registrada.png",
        "text": "En la vista Estudiante registramos una solicitud ficticia de ayuda. Esta función está disponible aunque no exista alerta ni predicción. El mensaje se valida y, al guardarse, la pantalla muestra una confirmación. Así, la búsqueda de apoyo no depende de que la inteligencia artificial identifique primero un riesgo. En este recorrido sólo se utilizan códigos y mensajes de demostración.",
    },
    {
        "id": "08", "section": "Demostración acompañamiento", "title": "Acordar un apoyo y conservar su seguimiento",
        "screen": "08_seguimiento_guardado.png",
        "text": "El tutor consulta las solicitudes, registra un acuerdo y selecciona el apoyo para agregar seguimiento. Los estados permiten distinguir pendiente, en seguimiento y cerrado. La captura muestra el historial y el estado de seguimiento guardado. SQLite conserva solicitudes, acuerdos y seguimiento al volver a abrir la aplicación. Esta persistencia permite revisar qué se acordó, sin depender de una sola sesión del navegador.",
    },
    {
        "id": "09", "section": "Resultados e interpretación", "title": "Qué demuestran los resultados sintéticos",
        "screen": "04_resultado_modelo.png",
        "text": "El entrenamiento separó ciento cuarenta y cuatro registros para ajuste, cuarenta y ocho para validación y cuarenta y ocho para prueba. En prueba, la red detectó veintiséis de veintisiete riesgos artificiales, pero produjo catorce falsas alarmas. Su exactitud fue de sesenta y ocho punto setenta y cinco por ciento. El recall alto no prueba eficacia real, y el MLP se conserva por el alcance didáctico.",
    },
    {
        "id": "10", "section": "Limitaciones y mejoras", "title": "Alcance de la entrega y próximos pasos",
        "screen": "15_control_messi.png",
        "text": "MESSI se entrega como demostración local para Windows, con aplicación, ejecutable, instalador y manuales. El selector de roles no autentica usuarios y los datos son sintéticos. Las mejoras futuras requieren datos reales autorizados, validación, calibración y control de acceso. Este video documenta el recorrido mediante capturas reales; no sustituye una prueba con persona ajena al equipo ni inventa su opinión o conformidad.",
    },
]


def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args[0]}\n{result.stderr[-5000:]}")
    return result


def duration(ffmpeg: str, path: Path) -> float:
    result = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"No measurable duration for {path}: {result.stderr[-2000:]}")
    h, m, s = map(float, match.groups())
    return h * 3600 + m * 60 + s


def write_prepare(scenes: list[dict]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "Narracion_video_demo.json").write_text(json.dumps({"voice": VOICE, "voice_kind": "generic_synthetic", "language": "es-MX", "visual_source": "real_application_screenshots", "scenes": scenes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    transcript = ["# Transcripción del video de demostración de MESSI", "", "Recorrido narrado con capturas reales de la aplicación y voz sintética genérica. No es una grabación de una persona ni una prueba externa.", ""]
    for scene in scenes:
        transcript.extend([f"## {scene['id']} {scene['title']}", "", scene["text"], ""])
    (DOCS / "Transcripcion_video_demo.md").write_text("\n".join(transcript), encoding="utf-8")


async def edge_audio(scene: dict, voice: str) -> Path:
    import edge_tts

    output = WORK / f"audio_{scene['id']}.mp3"
    boundary_path = output.with_suffix(".json")
    cache = hashlib.sha256((voice + "|-5%|" + scene["text"]).encode()).hexdigest()
    if output.exists() and boundary_path.exists():
        existing = json.loads(boundary_path.read_text(encoding="utf-8"))
        if existing.get("cache") == cache:
            return output
    communicator = edge_tts.Communicate(scene["text"], voice, rate="-5%", boundary="WordBoundary", connect_timeout=10, receive_timeout=25)
    boundaries = []
    with output.open("wb") as audio:
        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({"text": chunk["text"], "start": chunk["offset"] / 10_000_000, "end": (chunk["offset"] + chunk["duration"]) / 10_000_000})
    if output.stat().st_size < 1000:
        raise RuntimeError("Speech synthesis returned empty audio")
    boundary_path.write_text(json.dumps({"cache": cache, "boundaries": boundaries}, ensure_ascii=False), encoding="utf-8")
    return output


def sapi_audio(scene: dict) -> Path:
    """Fallback to an installed generic Spanish Windows voice, never a real person."""
    output = WORK / f"audio_{scene['id']}.wav"
    text_path = WORK / f"text_{scene['id']}.txt"
    text_path.write_text(scene["text"], encoding="utf-8")
    ps_script = WORK / "synthesize_sapi.ps1"
    ps_script.write_text("""param([string]$TextPath, [string]$OutPath)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$spanishVoice = $speaker.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es-*' } | Select-Object -First 1
if (-not $spanishVoice) { throw 'No installed Spanish SAPI voice found' }
$speaker.SelectVoice($spanishVoice.VoiceInfo.Name)
$speaker.Rate = -1
$speaker.SetOutputToWaveFile($OutPath)
$speaker.Speak([System.IO.File]::ReadAllText($TextPath, [System.Text.Encoding]::UTF8))
$speaker.Dispose()
""", encoding="utf-8")
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script), "-TextPath", str(text_path), "-OutPath", str(output)])
    return output


async def synthesize(scenes: list[dict], voice: str) -> list[Path]:
    WORK.mkdir(parents=True, exist_ok=True)
    audio_paths = []
    for scene in scenes:
        print(f"Synthesizing scene {scene['id']}: {scene['title']}", flush=True)
        try:
            path = await edge_audio(scene, voice)
            scene["actual_voice"] = voice
            scene["speech_engine"] = "edge-tts"
        except Exception as exc:
            print(f"Edge speech unavailable ({type(exc).__name__}); trying Spanish SAPI.", flush=True)
            path = sapi_audio(scene)
            scene["actual_voice"] = "installed_generic_Spanish_SAPI"
            scene["speech_engine"] = "Windows SAPI"
        audio_paths.append(path)
    return audio_paths


def font(size: int, *, bold: bool = False):
    from PIL import ImageFont

    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", size)


def compose_frame(scene: dict, source: Path, output: Path) -> None:
    from PIL import Image, ImageDraw, ImageOps

    canvas = Image.new("RGB", SIZE, "#101b2b")
    draw = ImageDraw.Draw(canvas)
    draw.text((35, 12), f"MESSI  /  {scene['section']}", font=font(22), fill="#bbcfdf")
    draw.text((35, 40), scene["title"], font=font(35, bold=True), fill="white")
    draw.text((1810, 40), f"{int(scene['id'])}/10", font=font(26), fill="#bbcfdf")
    with Image.open(source) as original:
        image = ImageOps.contain(original.convert("RGB"), (1900, 825), Image.Resampling.LANCZOS)
        canvas.paste(image, ((SIZE[0] - image.width) // 2, 90 + (825 - image.height) // 2))
    draw.text((35, 925), "Captura real de MESSI  ·  Datos ficticios  ·  Voz sintética", font=font(19), fill="#aebfcc")
    canvas.save(output)


def time_srt(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    h, remain = divmod(milliseconds, 3_600_000)
    m, remain = divmod(remain, 60_000)
    s, ms = divmod(remain, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def time_ass(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, remain = divmod(cs, 360_000)
    m, remain = divmod(remain, 6000)
    s, remain = divmod(remain, 100)
    return f"{h}:{m:02d}:{s:02d}.{remain:02d}"


def subtitles(scene: dict, audio: Path, audio_duration: float, tempo: float) -> list[dict]:
    boundary_file = audio.with_suffix(".json")
    groups = []
    if boundary_file.exists():
        words = json.loads(boundary_file.read_text(encoding="utf-8")).get("boundaries", [])
        original_words = scene["text"].split()
        normalize = lambda value: re.sub(r"[^\w]", "", value).casefold()
        if len(words) == len(original_words) and all(normalize(word["text"]) == normalize(original) for word, original in zip(words, original_words, strict=True)):
            # Preserve written accents/punctuation while retaining exact TTS timing.
            words = [{**word, "text": original} for word, original in zip(words, original_words, strict=True)]
        current = []
        for word in words:
            current.append(word)
            content = " ".join(w["text"] for w in current)
            if len(content) >= 75 or len(current) >= 13 or word["text"].endswith((".", "?", "!")):
                groups.append({"start": current[0]["start"] / tempo, "end": current[-1]["end"] / tempo + 0.15, "text": content})
                current = []
        if current:
            groups.append({"start": current[0]["start"] / tempo, "end": current[-1]["end"] / tempo + 0.15, "text": " ".join(w["text"] for w in current)})
    if not groups:
        words = scene["text"].split()
        for start in range(0, len(words), 12):
            selected = words[start:start + 12]
            groups.append({"start": audio_duration * start / len(words) / tempo, "end": audio_duration * min(start + 12, len(words)) / len(words) / tempo, "text": " ".join(selected)})
    return groups


def write_ass(path: Path, cues: list[dict]) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,32,&H00FFFFFF,&H00FFFFFF,&H00101B2B,&H00101B2B,0,0,0,0,100,100,0,0,1,1,0,2,90,90,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for cue in cues:
        text = cue["text"].replace("{", "").replace("}", "").replace("\n", " ")
        lines.append(f"Dialogue: 0,{time_ass(cue['start'])},{time_ass(cue['end'])},Default,,0,0,0,,{text}\n")
    path.write_text("".join(lines), encoding="utf-8-sig")


def build(scenes: list[dict], paths: list[Path], ffmpeg: str) -> None:
    missing = [scene["screen"] for scene in scenes if not (DOCS / "evidencias" / scene["screen"]).is_file()]
    if missing:
        raise RuntimeError("Screenshots missing; video assembly refused: " + ", ".join(sorted(set(missing))))
    durations = [duration(ffmpeg, path) for path in paths]
    spoken_total = sum(durations)
    # Keep narration natural while ensuring the assessment's 3–5 minute length.
    tempo = spoken_total / 225 if spoken_total < 205 else spoken_total / 255 if spoken_total > 265 else 1.0
    if not 0.5 <= tempo <= 2.0:
        raise RuntimeError(f"Narration duration unsuitable for natural tempo: {spoken_total:.1f}s")
    parts = []
    global_cues = []
    offset = 0.0
    for scene, audio, original_duration in zip(scenes, paths, durations, strict=True):
        frame = WORK / f"frame_{scene['id']}.png"
        compose_frame(scene, DOCS / "evidencias" / scene["screen"], frame)
        cues = subtitles(scene, audio, original_duration, tempo)
        ass = WORK / f"captions_{scene['id']}.ass"
        write_ass(ass, cues)
        length = original_duration / tempo + 1.0
        part = WORK / f"part_{scene['id']}.mp4"
        print(f"Encoding scene {scene['id']} ({length:.2f}s)", flush=True)
        run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", "15", "-i", frame.name, "-i", str(audio), "-vf", f"subtitles={ass.name}", "-af", f"atempo={tempo:.8f},apad", "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "15", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(part)], cwd=WORK)
        actual = duration(ffmpeg, part)
        scene["start_seconds"] = round(offset, 3)
        scene["duration_seconds"] = round(actual, 3)
        scene["screenshot_sha256"] = hashlib.sha256((DOCS / "evidencias" / scene["screen"]).read_bytes()).hexdigest()
        for cue in cues:
            global_cues.append({**cue, "start": cue["start"] + offset, "end": cue["end"] + offset})
        offset += actual
        parts.append(part)
    concat_file = WORK / "parts.txt"
    concat_file.write_text("\n".join(f"file '{part.name}'" for part in parts) + "\n", encoding="utf-8")
    RELEASE.mkdir(parents=True, exist_ok=True)
    output = RELEASE / "MESSI_Demo_Entrega_3.mp4"
    concatenated = WORK / "concatenated.mp4"
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_file.name, "-c", "copy", str(concatenated)], cwd=WORK)
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(concatenated), "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", str(output)])
    measured = duration(ffmpeg, output)
    if not 180 <= measured <= 300:
        raise RuntimeError(f"Video duration {measured:.2f}s does not satisfy 180–300s")
    srt = "\n\n".join(f"{i}\n{time_srt(cue['start'])} --> {time_srt(cue['end'])}\n{cue['text']}" for i, cue in enumerate(global_cues, 1)) + "\n"
    (DOCS / "MESSI_Demo_Entrega_3.srt").write_text(srt, encoding="utf-8-sig")
    write_prepare(scenes)
    report = {"file": output.name, "duration_seconds": measured, "resolution": list(SIZE), "fps": 15, "video_codec": "H.264", "audio_codec": "AAC", "audio_normalization": "loudnorm I=-16 LUFS, TP=-1.5 dBTP, LRA=11", "voice_kind": "generic_synthetic", "screen_origin": "real_MESSI_application_captures", "human_external_test": False, "tempo_factor": round(tempo, 8), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "scenes": scenes}
    (DOCS / "evidencias" / "verificacion_video_demo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audio_check = run([ffmpeg, "-hide_banner", "-i", str(output), "-af", "volumedetect", "-vn", "-f", "null", "NUL" if sys.platform == "win32" else "/dev/null"])
    (DOCS / "evidencias" / "verificacion_video_ffmpeg.txt").write_text(audio_check.stderr, encoding="utf-8")
    print(json.dumps({"output": str(output), "duration_seconds": measured, "size_bytes": output.stat().st_size, "sha256": report["sha256"]}, indent=2), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Write narration and transcript without rendering")
    parser.add_argument("--audio-only", action="store_true", help="Generate synthetic narration before screenshots exist")
    parser.add_argument("--screens", type=Path, help="JSON object mapping scene IDs to real screenshot filenames")
    parser.add_argument("--voice", default=VOICE)
    args = parser.parse_args()
    scenes = [dict(scene) for scene in SCENES]
    if args.screens:
        mapping = json.loads(args.screens.read_text(encoding="utf-8"))
        for scene in scenes:
            scene["screen"] = mapping.get(scene["id"], scene["screen"])
    write_prepare(scenes)
    if args.prepare:
        print(f"Prepared {len(scenes)} scenes, {sum(len(scene['text'].split()) for scene in scenes)} spoken words.")
        return 0
    paths = asyncio.run(synthesize(scenes, args.voice))
    if args.audio_only:
        write_prepare(scenes)
        print("Synthetic narration ready; screenshots still required for assembly.")
        return 0
    import imageio_ffmpeg

    build(scenes, paths, imageio_ffmpeg.get_ffmpeg_exe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
