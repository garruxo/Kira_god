# -*- coding: utf-8 -*-
"""
audio_kira.py - MESA DE MEZCLA y herramientas de AUDIO reales de Kira (sin Kivy).

Construye órdenes de ffmpeg RESTRINGIDO (ffmpeg_seguro) y las ejecuta con herramientas_kira.Herramientas, que corre
aquí si hay ffmpeg o en el laboratorio del PC si no. Todo son datos (números de volumen, tiempos…): nunca código.

  - mezclar(): varias pistas de la mediateca con volumen, panorámica (izq/der), retardo y fundido de entrada por pista,
               más volumen general; salida a .mp3/.wav/.m4a/.ogg.
  - efecto():  eco, graves, agudos, normalizar, acelerar/ralentizar sobre un audio.
  - convertir(): pasar un audio o vídeo a otro formato de audio.
  - extraer_audio(): sacar la pista de audio de un vídeo.
Son operaciones de AUDIO: no dañan nada y no editan vídeo (eso es editor_kira.py).
"""
import os

import ffmpeg_seguro as fs

FORMATOS_AUDIO = {"mp3": ("libmp3lame", ["-b:a", "192k"]), "m4a": ("aac", ["-b:a", "192k"]),
                  "aac": ("aac", ["-b:a", "192k"]), "ogg": ("libvorbis", ["-q:a", "5"]),
                  "opus": ("libopus", ["-b:a", "128k"]), "wav": ("pcm_s16le", []), "flac": ("flac", [])}
MAX_PISTAS = 6


class AudioError(ValueError):
    """Parámetro inválido (mensaje apto para mostrar)."""


def _num(v, lo, hi, nombre):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise AudioError(f"{nombre}: pon un número.")
    if not (lo <= x <= hi):
        raise AudioError(f"{nombre}: entre {lo} y {hi}.")
    return x


def _codec_salida(salida):
    ext = os.path.splitext(str(salida))[1].lower().lstrip(".")
    if ext not in FORMATOS_AUDIO:
        raise AudioError("Formato de salida de audio no válido (mp3, m4a, aac, ogg, opus, wav, flac).")
    cod, extra = FORMATOS_AUDIO[ext]
    return ["-vn", "-c:a", cod] + extra


# =====================================================================================
#  MESA DE MEZCLA
# =====================================================================================
def normalizar_pista(p):
    """Valida una pista: {titulo, volumen(0-2), pan(-1..1), retardo(s), fundido(s)}."""
    if not isinstance(p, dict) or not str(p.get("titulo", "")).strip():
        raise AudioError("Cada pista necesita el título de un audio de la mediateca.")
    return {"titulo": str(p["titulo"]).strip(),
            "volumen": _num(p.get("volumen", 1.0), 0.0, 2.0, "volumen"),
            "pan": _num(p.get("pan", 0.0), -1.0, 1.0, "panorámica"),
            "retardo": _num(p.get("retardo", 0.0), 0.0, 60.0, "retardo"),
            "fundido": _num(p.get("fundido", 0.0), 0.0, 10.0, "fundido")}


def _cadena_pista(i, p):
    gl = min(1.0, 1.0 - p["pan"])
    gr = min(1.0, 1.0 + p["pan"])
    pasos = ["aformat=channel_layouts=stereo", f"volume={p['volumen']:.3f}",
             f"pan=stereo|c0={gl:.3f}*c0|c1={gr:.3f}*c1"]
    if p["retardo"] > 0:
        ms = int(p["retardo"] * 1000)
        pasos.append(f"adelay={ms}|{ms}")
    if p["fundido"] > 0:
        pasos.append(f"afade=t=in:st=0:d={p['fundido']:.2f}")
    return f"[{i}:a]" + ",".join(pasos) + f"[a{i}]"


def construir_args_mezcla(pistas, salida, volumen_general=1.0):
    """(args de ffmpeg) para mezclar len(pistas) entradas. No toca archivos."""
    pistas = [normalizar_pista(p) for p in pistas]
    if not 1 <= len(pistas) <= MAX_PISTAS:
        raise AudioError(f"Entre 1 y {MAX_PISTAS} pistas.")
    vg = _num(volumen_general, 0.0, 2.0, "volumen general")
    cadenas = [_cadena_pista(i, p) for i, p in enumerate(pistas)]
    etiquetas = "".join(f"[a{i}]" for i in range(len(pistas)))
    mezcla = f"{etiquetas}amix=inputs={len(pistas)}:normalize=0:duration=longest"
    if abs(vg - 1.0) > 1e-3:
        mezcla += f",volume={vg:.3f}"
    fc = ";".join(cadenas) + ";" + mezcla + "[mix]"
    return ["-filter_complex", fc, "-map", "[mix]"] + _codec_salida(salida)


def mezclar(herr, pistas, salida="mezcla.mp3", volumen_general=1.0, progreso=None):
    """Importa cada pista de la mediateca, mezcla y deja el resultado en la carpeta de trabajo. Devuelve el nombre."""
    pistas = [normalizar_pista(p) for p in pistas]
    nombres = []
    for p in pistas:
        nombres.append(herr.importar(p["titulo"]))
    args = construir_args_mezcla(pistas, salida, volumen_general)
    herr.ffmpeg(nombres, salida, args, progreso=progreso)
    return salida


# =====================================================================================
#  EFECTOS
# =====================================================================================
EFECTOS = {
    "eco": lambda: "aecho=0.8:0.9:1000:0.3",
    "graves": lambda: "bass=g=6",
    "agudos": lambda: "treble=g=5",
    "normalizar": lambda: "loudnorm",
    "rapido": lambda: "atempo=1.35",
    "lento": lambda: "atempo=0.75",
    "radio": lambda: "highpass=f=300,lowpass=f=3400",
}


def construir_args_efecto(efecto, salida):
    if efecto not in EFECTOS:
        raise AudioError("Efecto no reconocido: " + ", ".join(EFECTOS))
    return ["-af", EFECTOS[efecto]()] + _codec_salida(salida)


def efecto(herr, titulo, nombre_efecto, salida=None, progreso=None):
    entrada = herr.importar(titulo)
    salida = salida or (os.path.splitext(entrada)[0] + f"_{nombre_efecto}.mp3")
    herr.ffmpeg([entrada], salida, construir_args_efecto(nombre_efecto, salida), progreso=progreso)
    return salida


# =====================================================================================
#  CONVERTIR / EXTRAER
# =====================================================================================
def convertir(herr, titulo, formato, progreso=None):
    formato = str(formato).lower().lstrip(".")
    if formato not in FORMATOS_AUDIO:
        raise AudioError("Formato no válido (mp3, m4a, aac, ogg, opus, wav, flac).")
    entrada = herr.importar(titulo)
    salida = os.path.splitext(os.path.basename(entrada))[0] + "." + formato
    herr.ffmpeg([entrada], salida, _codec_salida(salida), progreso=progreso)
    return salida


def extraer_audio(herr, titulo, formato="mp3", progreso=None):
    return convertir(herr, titulo, formato, progreso=progreso)
