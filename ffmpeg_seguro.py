# -*- coding: utf-8 -*-
"""
ffmpeg_seguro.py - ffmpeg RESTRINGIDO para los módulos que Kira programa (solo librería estándar; APK y laboratorio).

Idea: mezclar audio y editar vídeo se reduce casi siempre a una llamada a ffmpeg. En vez de dejar que un módulo
use subprocess (y arrastre todos sus riesgos), los módulos piden el trabajo aquí y este archivo:
  - acepta solo OPCIONES de una lista blanca, con el formato de valor que corresponde a cada una;
  - acepta solo FILTROS de una lista blanca (nada que lea archivos o red: movie, subtitles, drawtext, sendcmd…);
  - recibe las entradas y la salida como rutas ya validadas por quien llama (carpeta de trabajo), nunca desde los args;
  - lanza ffmpeg sin shell, sin red (-protocol_whitelist file), sin stdin, con límite de tiempo, de duración y de tamaño.
No es una caja de seguridad perfecta (ffmpeg es un programa enorme), pero reduce la superficie a lo necesario.
"""
import os
import re
import subprocess

EXT_ENTRADA = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac", ".opus", ".mp4", ".mkv", ".webm", ".3gp", ".mov", ".avi", ".m4v")
EXT_SALIDA = (".mp4", ".webm", ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus")
MAX_ARGS, MAX_ENTRADAS, MAX_LARGO_ARG = 60, 8, 600
MAX_SEGUNDOS_SALIDA, MAX_BYTES_SALIDA = 3600, 500 * 1024 * 1024
TIMEOUT = 900

CODECS = {"libx264", "libx265", "mpeg4", "libvpx-vp9", "aac", "libmp3lame", "libopus", "libvorbis", "pcm_s16le", "flac", "copy"}
PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"}
PIXFMT = {"yuv420p", "yuv444p", "rgb24", "gray"}

FILTROS_OK = {
    # vídeo
    "scale", "crop", "pad", "trim", "setpts", "fps", "fade", "hflip", "vflip", "transpose", "rotate", "format", "overlay",
    "concat", "null", "eq", "hue", "colorchannelmixer", "gblur", "boxblur", "unsharp", "setsar", "setdar", "split",
    "xfade", "zoompan", "drawbox", "vignette", "negate", "reverse", "tpad", "loop",
    # audio
    "volume", "afade", "atrim", "asetpts", "amix", "amerge", "aresample", "pan", "adelay", "atempo", "aformat", "anull",
    "areverse", "aecho", "equalizer", "highpass", "lowpass", "bass", "treble", "loudnorm", "acompressor", "alimiter",
    "dynaudnorm", "apad", "channelsplit", "channelmap", "join", "asplit", "silenceremove", "asetrate", "volumedetect",
    "acrossfade",
}

_NUM = r"\d+(?:\.\d+)?"
VALOR_RE = {
    "-ss": re.compile(r"^[0-9:.]{1,12}$"), "-t": re.compile(r"^[0-9:.]{1,12}$"), "-to": re.compile(r"^[0-9:.]{1,12}$"),
    "-r": re.compile(rf"^{_NUM}$"), "-s": re.compile(r"^\d{2,4}x\d{2,4}$"), "-aspect": re.compile(r"^\d{1,3}:\d{1,3}$"),
    "-crf": re.compile(r"^\d{1,2}$"), "-q:v": re.compile(r"^\d{1,2}$"), "-q:a": re.compile(r"^\d{1,2}$"),
    "-b:a": re.compile(r"^\d{2,4}[kK]$"), "-b:v": re.compile(r"^\d{2,5}[kKmM]$"),
    "-ar": re.compile(r"^\d{4,6}$"), "-ac": re.compile(r"^[1-8]$"),
    "-map": re.compile(r"^\[?[0-9a-z_:\-]{1,24}\]?\??$"),
}
SIN_VALOR = {"-an", "-vn", "-sn", "-shortest"}
CON_VALOR_ESPECIAL = {"-c:v", "-c:a", "-preset", "-pix_fmt", "-vf", "-af", "-filter_complex"}


class FfmpegError(ValueError):
    """Petición no permitida o inválida (mensaje apto para mostrar)."""


def _segundos(valor):
    """'90', '1:30', '00:01:30.5' -> segundos (float)."""
    try:
        total = 0.0
        for p in str(valor).split(":"):
            total = total * 60 + float(p)
        return total
    except ValueError:
        raise FfmpegError(f"Tiempo no válido: {valor}")


def _trozos_filtro(texto):
    """Divide una cadena de filtros en (nombre, opciones) cuidando paréntesis y etiquetas [x]. Rechaza comillas y escapes."""
    if re.search(r"[\"'\\`$\n\r\x00]", texto):
        raise FfmpegError("Los filtros no pueden llevar comillas, barras invertidas ni caracteres de control.")
    res, actual, prof, dentro_etq = [], "", 0, False
    for c in texto:
        if c == "[":
            dentro_etq = True
        elif c == "]":
            dentro_etq = False
        elif c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
        if prof < 0:
            raise FfmpegError("Paréntesis desbalanceados en el filtro.")
        if c in ",;" and prof == 0 and not dentro_etq:
            res.append(actual)
            actual = ""
        else:
            actual += c
    if prof != 0:
        raise FfmpegError("Paréntesis desbalanceados en el filtro.")
    res.append(actual)
    salida = []
    for t in res:
        t = re.sub(r"^(?:\s*\[[^\]]*\])+", "", t)          # etiquetas de entrada
        t = re.sub(r"(?:\[[^\]]*\]\s*)+$", "", t).strip()   # etiquetas de salida
        if not t:
            continue
        nombre, _, opciones = t.partition("=")
        salida.append((nombre.strip(), opciones))
    return salida


def validar_filtros(texto):
    if len(texto) > MAX_LARGO_ARG:
        raise FfmpegError("Filtro demasiado largo.")
    trozos = _trozos_filtro(texto)
    if not trozos:
        raise FfmpegError("Filtro vacío.")
    for nombre, opciones in trozos:
        if nombre not in FILTROS_OK:
            raise FfmpegError(f"Filtro no permitido: '{nombre}'.")
        if re.search(r"(?i)(file|http|ftp|tcp|udp|pipe|://|concat:|subfile|/dev/|\.\.|~)", opciones):
            raise FfmpegError(f"Opción no permitida en el filtro '{nombre}'.")
    return texto


def validar_args(args, n_entradas):
    """Comprueba la lista de opciones. Devuelve una copia limpia (lista de str) o lanza FfmpegError."""
    if not isinstance(args, (list, tuple)) or len(args) > MAX_ARGS:
        raise FfmpegError(f"Las opciones deben ser una lista de hasta {MAX_ARGS} elementos.")
    args = [str(a) for a in args]
    limpio, i = [], 0
    while i < len(args):
        a = args[i]
        if not a.startswith("-"):
            raise FfmpegError(f"Se esperaba una opción y llegó '{a[:30]}'. Las rutas no se pasan aquí.")
        if a in SIN_VALOR:
            limpio.append(a)
            i += 1
            continue
        if a not in VALOR_RE and a not in CON_VALOR_ESPECIAL:
            raise FfmpegError(f"Opción no permitida: {a}")
        if i + 1 >= len(args):
            raise FfmpegError(f"Falta el valor de {a}.")
        v = args[i + 1]
        if len(v) > MAX_LARGO_ARG or re.search(r"[\x00\n\r]", v):
            raise FfmpegError(f"Valor no válido para {a}.")
        if a in ("-vf", "-af", "-filter_complex"):
            validar_filtros(v)
        elif a in ("-c:v", "-c:a"):
            if v not in CODECS:
                raise FfmpegError(f"Códec no permitido: {v}")
        elif a == "-preset":
            if v not in PRESETS:
                raise FfmpegError(f"Preset no permitido: {v}")
        elif a == "-pix_fmt":
            if v not in PIXFMT:
                raise FfmpegError(f"Formato de píxel no permitido: {v}")
        else:
            if not VALOR_RE[a].match(v):
                raise FfmpegError(f"Valor no válido para {a}: '{v[:30]}'")
            if a in ("-t", "-to") and _segundos(v) > MAX_SEGUNDOS_SALIDA:
                raise FfmpegError(f"{a} no puede superar {MAX_SEGUNDOS_SALIDA} s.")
            if a == "-map":
                m = re.match(r"^(\d+):", v)
                if m and int(m.group(1)) >= n_entradas:
                    raise FfmpegError(f"-map {v} apunta a una entrada que no existe.")
        limpio += [a, v]
        i += 2
    return limpio


def construir_comando(ffmpeg, entradas, salida, args):
    """Lista de argumentos lista para subprocess. 'entradas' y 'salida' son rutas ya validadas por el que llama."""
    if not 1 <= len(entradas) <= MAX_ENTRADAS:
        raise FfmpegError(f"Entre 1 y {MAX_ENTRADAS} entradas.")
    for e in entradas:
        if os.path.splitext(str(e))[1].lower() not in EXT_ENTRADA:
            raise FfmpegError(f"Formato de entrada no permitido: {os.path.basename(str(e))}")
    if os.path.splitext(str(salida))[1].lower() not in EXT_SALIDA:
        raise FfmpegError("Formato de salida no permitido (mp4, webm, mp3, wav, m4a, ogg, flac, aac, opus).")
    opciones = validar_args(args, len(entradas))
    cmd = [ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file"]
    for e in entradas:
        cmd += ["-i", str(e)]
    if "-t" not in opciones and "-to" not in opciones:
        cmd += ["-t", str(MAX_SEGUNDOS_SALIDA)]
    cmd += opciones + ["-fs", str(MAX_BYTES_SALIDA), "-map_metadata", "-1", str(salida)]
    return cmd


def ejecutar(ffmpeg, entradas, salida, args, timeout=TIMEOUT):
    """(ok, mensaje). Escribe en 'salida' de forma atómica (.part) y borra restos si falla."""
    cmd = construir_comando(ffmpeg, entradas, salida, args)
    base, ext = os.path.splitext(str(salida))
    parcial = base + ".part" + ext
    cmd[-1] = parcial
    try:
        p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _borrar(parcial)
        return False, f"ffmpeg tardó más de {timeout} s y se detuvo."
    except OSError as e:
        return False, f"No se pudo lanzar ffmpeg: {e}"
    if p.returncode != 0 or not os.path.isfile(parcial) or os.path.getsize(parcial) == 0:
        _borrar(parcial)
        return False, "ffmpeg falló: " + (p.stderr.strip()[-400:] or "sin detalle")
    os.replace(parcial, str(salida))
    return True, f"Creado {os.path.basename(str(salida))} ({os.path.getsize(str(salida)) // 1024} KB)"


def _borrar(ruta):
    try:
        os.remove(ruta)
    except OSError:
        pass
