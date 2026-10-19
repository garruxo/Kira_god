# -*- coding: utf-8 -*-
"""
editor_kira.py - EDITOR DE VÍDEO real de Kira (sin Kivy).

Construye órdenes de ffmpeg RESTRINGIDO (ffmpeg_seguro) y las ejecuta con herramientas_kira.Herramientas (aquí si hay
ffmpeg, o en el laboratorio del PC). Todo son datos (tiempos, tamaños…): nunca código.

  - cortar(): quedarte con un trozo de un vídeo (de un tiempo a otro).
  - redimensionar(): cambiar la resolución manteniendo la proporción (con bordes si hace falta).
  - unir(): encadenar varios vídeos (sin sonido; luego puedes poner música).
  - poner_musica(): ponerle a un vídeo una pista de audio (recorta a la duración más corta).
  - quitar_audio() / extraer_audio_video(): quitar o sacar el sonido de un vídeo.
No genera imágenes de IA; trabaja sobre vídeos reales que ya tienes o que creó el motor de Kira.
"""
import os

import ffmpeg_seguro as fs

TAMANOS = {"720p": (1280, 720), "480p": (854, 480), "360p": (640, 360), "vertical": (720, 1280), "cuadrado": (720, 720)}
V_CODEC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
A_CODEC = ["-c:a", "aac", "-b:a", "160k"]


class EditorError(ValueError):
    """Parámetro inválido (mensaje apto para mostrar)."""


def _seg(v, nombre):
    """Admite segundos (12.5) o mm:ss / hh:mm:ss."""
    s = str(v).strip()
    try:
        total, partes = 0.0, s.split(":")
        if len(partes) > 3:
            raise ValueError
        for p in partes:
            total = total * 60 + float(p)
    except ValueError:
        raise EditorError(f"{nombre}: usa segundos (12.5) o mm:ss.")
    if not 0 <= total <= 36000:
        raise EditorError(f"{nombre}: tiempo fuera de rango.")
    return total


def _fmt(t):
    return f"{t:.3f}"


def _dim(tam):
    if tam in TAMANOS:
        return TAMANOS[tam]
    raise EditorError("Tamaño no válido: " + ", ".join(TAMANOS))


# =====================================================================================
#  OPERACIONES (construyen args; no tocan archivos)
# =====================================================================================
def args_cortar(inicio, fin):
    a, b = _seg(inicio, "inicio"), _seg(fin, "fin")
    if b <= a:
        raise EditorError("El fin debe ser mayor que el inicio.")
    return ["-ss", _fmt(a), "-to", _fmt(b)] + V_CODEC + A_CODEC


def args_redimensionar(tam):
    w, h = _dim(tam)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    return ["-vf", vf] + V_CODEC + A_CODEC


def args_unir(n, tam="720p"):
    if not 2 <= n <= 6:
        raise EditorError("Une entre 2 y 6 vídeos.")
    w, h = _dim(tam)
    trozos = [f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]" for i in range(n)]
    cadena = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    return ["-filter_complex", ";".join(trozos) + ";" + cadena, "-map", "[v]"] + V_CODEC


def args_poner_musica():
    return ["-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:v", "copy"] + A_CODEC


def args_quitar_audio():
    return ["-an", "-c:v", "copy"]


# =====================================================================================
#  EJECUCIÓN (importa de la mediateca, ejecuta, deja el resultado en la carpeta de trabajo)
# =====================================================================================
def _salida(base, sufijo, ext=".mp4"):
    return os.path.splitext(os.path.basename(base))[0][:30] + sufijo + ext


def cortar(herr, titulo, inicio, fin, progreso=None):
    e = herr.importar(titulo)
    s = _salida(e, "_corte")
    herr.ffmpeg([e], s, args_cortar(inicio, fin), progreso=progreso)
    return s


def redimensionar(herr, titulo, tam, progreso=None):
    e = herr.importar(titulo)
    s = _salida(e, "_" + tam)
    herr.ffmpeg([e], s, args_redimensionar(tam), progreso=progreso)
    return s


def unir(herr, titulos, tam="720p", salida="union.mp4", progreso=None):
    if not 2 <= len(titulos) <= 6:
        raise EditorError("Une entre 2 y 6 vídeos.")
    entradas = [herr.importar(t) for t in titulos]
    herr.ffmpeg(entradas, salida, args_unir(len(entradas), tam), progreso=progreso)
    return salida


def poner_musica(herr, titulo_video, titulo_audio, salida=None, progreso=None):
    v, a = herr.importar(titulo_video), herr.importar(titulo_audio)
    salida = salida or _salida(v, "_con_musica")
    herr.ffmpeg([v, a], salida, args_poner_musica(), progreso=progreso)
    return salida


def quitar_audio(herr, titulo, progreso=None):
    v = herr.importar(titulo)
    s = _salida(v, "_sin_audio")
    herr.ffmpeg([v], s, args_quitar_audio(), progreso=progreso)
    return s


def extraer_audio_video(herr, titulo, formato="mp3", progreso=None):
    import audio_kira
    return audio_kira.extraer_audio(herr, titulo, formato, progreso=progreso)
