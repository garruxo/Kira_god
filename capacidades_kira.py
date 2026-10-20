# -*- coding: utf-8 -*-
"""
capacidades_kira.py - Qué sabe hacer Kira, qué le falta y cómo puede prepararse (lógica PURA, sin Kivy ni red).

Cada capacidad es una función que se puede PROGRAMAR (Kira escribe un módulo, el laboratorio lo prueba y tú lo apruebas),
que puede necesitar algo DESCARGADO (p. ej. ffmpeg en el PC) o que ya viene INTEGRADA. Este archivo no instala ni ejecuta nada:
solo describe, compara con lo que hay y redacta el pedido que Kira enviará a su proceso de mejoras.

Estados:
  disponible    - ya funciona (integrada o con módulo instalado)
  programable   - el entorno está listo; Kira puede programarla ahora
  falta_entorno - antes hay que conseguir algo (p. ej. ffmpeg); se indica cómo
"""
import re
import unicodedata

USO_API = (
    "El comando recibe dos parámetros: def comando(texto, kira). 'kira' ofrece: kira.medios(tipo=None) -> lista de dicts "
    "(titulo, tipo, ruta); kira.importar(titulo) -> nombre de archivo copiado a la carpeta de trabajo; "
    "kira.ffmpeg(entradas:list[str], salida:str, args:list[str]) -> mensaje (nombres de archivo simples, sin rutas; args solo "
    "opciones, nunca rutas; solo se permiten los filtros de ffmpeg habituales); kira.escribir(nombre, texto) y kira.leer(nombre) "
    "para archivos .txt/.json/.md/.csv; kira.exportar(nombre) -> (ok, mensaje) para entregar el resultado. NO uses subprocess, "
    "os, shutil ni open: usa 'kira'. Si algo falla, devuelve un texto claro (captura kira.HerramientaError si quieres)."
)

CAPACIDADES = [
    {"id": "mesa_mezcla", "abrir": "mezcla", "integrada_si_ffmpeg": True, "nombre": "Mesa de mezcla de audio", "prefijo": "mezclar",
     "palabras": ("mezcla", "mezclar", "mesa de mezcla", "pistas", "mixer", "mezclador"), "ffmpeg": True,
     "pedido": ("Mesa de mezcla de audio. Comando 'mezclar': el usuario escribe por ejemplo «mezclar Canción A:0.8 Voz:1.2 "
                "salida=Mi mezcla». Para cada título de la mediateca usa kira.importar, aplica volumen (filtro volume), opcional "
                "retardo (adelay), panorámica (pan) y fundidos (afade) por pista, mézclalas con amix (normalize=0 si procede) y "
                "guarda un .mp3 con kira.ffmpeg; luego kira.exportar. Máx. 6 pistas. Devuelve un resumen de lo hecho. ")},
    {"id": "editor_video", "abrir": "editor_video", "integrada_si_ffmpeg": True, "nombre": "Editor de vídeo (cortar, unir, redimensionar)", "prefijo": "editar video",
     "palabras": ("editar video", "editor de video", "cortar video", "unir videos", "recortar video", "montaje", "montar video"),
     "ffmpeg": True,
     "pedido": ("Editor de vídeo básico. Comando 'editar video': subcomandos «cortar <título> de <inicio> a <fin>», «unir <título1> "
                "+ <título2>» y «redimensionar <título> a <ancho>x<alto>». Usa kira.importar, trim/setpts o las opciones -ss/-to, "
                "concat (filter_complex con concat=n=2:v=1:a=1) y scale; guarda .mp4 con -c:v libx264 y -c:a aac y entrega con "
                "kira.exportar. ")},
    {"id": "convertidor", "abrir": "editor_video", "integrada_si_ffmpeg": True, "nombre": "Conversor de formatos de audio y vídeo", "prefijo": "convertir",
     "palabras": ("convertir", "conversor", "formato", "pasar a mp3", "pasar a mp4"), "ffmpeg": True,
     "pedido": ("Conversor. Comando 'convertir': «convertir <título> a mp3|wav|ogg|m4a|mp4|webm». Importa el medio, convierte con "
                "kira.ffmpeg eligiendo códecs razonables (libmp3lame, aac, libx264, libvpx-vp9, libopus, pcm_s16le) y exporta. ")},
    {"id": "extraer_audio", "abrir": "editor_video", "integrada_si_ffmpeg": True, "nombre": "Extraer el audio de un vídeo", "prefijo": "extraer audio",
     "palabras": ("extraer audio", "sacar el audio", "audio de un video", "quitar el video"), "ffmpeg": True,
     "pedido": ("Extractor de audio. Comando 'extraer audio': «extraer audio <título del vídeo>». Importa el vídeo, usa -vn y "
                "libmp3lame (-b:a 192k) con kira.ffmpeg, y exporta el .mp3. ")},
    {"id": "efectos_audio", "abrir": "mezcla", "integrada_si_ffmpeg": True, "nombre": "Efectos de audio (eco, graves, normalizar, velocidad)", "prefijo": "efecto",
     "palabras": ("efecto", "efectos de audio", "eco", "graves", "normalizar", "ecualizar", "ecualizador", "velocidad del audio"),
     "ffmpeg": True,
     "pedido": ("Efectos de audio. Comando 'efecto': «efecto eco|graves|agudos|normalizar|rapido|lento <título>». Usa los filtros "
                "aecho, bass, treble, loudnorm y atempo (0.5 a 2.0) con kira.ffmpeg y exporta el resultado. ")},
    {"id": "videoclip_mp4", "abrir": "estudio", "nombre": "Videoclips en MP4 (motor gráfico)", "integrada": True, "palabras": ("videoclip", "crear video")},
    {"id": "web_app", "abrir": "estudio", "nombre": "Webs y maquetas de apps", "integrada": True, "palabras": ("pagina web", "maqueta", "app")},
]

PAQUETES_UTILES = {"ffmpeg": ["imageio-ffmpeg"], "dibujo": ["pillow"]}


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def buscar(texto):
    """Capacidad que mejor encaja con un texto libre ('prepárate para mezclar audio'), o None."""
    n = _norm(texto)
    mejor, puntos = None, 0
    for c in CAPACIDADES:
        p = sum(len(k.split()) for k in c.get("palabras", ()) if re.search(r"\b" + re.escape(_norm(k)), n))
        if p > puntos:
            mejor, puntos = c, p
    return mejor


def estado(cap, hechos):
    """hechos: {'prefijos': iterable de prefijos de comandos de módulos, 'ffmpeg': 'local'|'laboratorio'|None,
    'lab': bool (laboratorio alcanzable), 'lab_instalar': bool (el PC permite instalar)}.
    Devuelve {'id','nombre','estado','faltan':[...],'plan':[...]}."""
    r = {"id": cap["id"], "nombre": cap["nombre"], "estado": "", "faltan": [], "plan": []}
    prefijos = {str(p).lower() for p in hechos.get("prefijos", ())}
    if cap.get("integrada"):
        r["estado"] = "disponible"
        r["plan"] = ["Ya viene integrada en Kira."]
        return r
    if cap.get("integrada_si_ffmpeg"):
        if hechos.get("ffmpeg"):
            r["estado"] = "disponible"
            r["plan"] = ["Ya viene integrada en Kira (Mesa de mezcla / Editor de vídeo / audio). Necesita ffmpeg, que ya tienes."]
        else:
            r["estado"] = "falta_entorno"
            r["faltan"] = ["ffmpeg (aquí o en el laboratorio del PC)"]
            r["plan"] = ["Ya viene integrada en Kira, pero necesita ffmpeg.",
                         "En el PC: pip install imageio-ffmpeg y arranca servidor_lab.py, o Taller > Instalar en el PC."]
        return r
    if any(p.startswith(cap["prefijo"]) for p in prefijos):
        r["estado"] = "disponible"
        r["plan"] = [f"Ya está instalada: escribe «{cap['prefijo']} …»."]
        return r
    if cap.get("ffmpeg") and not hechos.get("ffmpeg"):
        r["estado"] = "falta_entorno"
        r["faltan"] = ["ffmpeg (aquí o en el laboratorio del PC)"]
        r["plan"] = ["Necesita ffmpeg y no hay ninguno disponible."]
        if not hechos.get("lab"):
            r["plan"].append("1. En tu PC: doble clic en «Arrancar laboratorio» (carpeta kira_laboratorio) y dile a Kira «conéctate al ordenador».")
        if hechos.get("lab_instalar"):
            r["plan"].append("2. Desde el Taller puedes pedir que el PC instale imageio-ffmpeg (te pido confirmación).")
        else:
            r["plan"].append("2. En el PC: pip install imageio-ffmpeg  (o instala ffmpeg), o arranca el laboratorio con "
                             "--permitir-instalar para que Kira te lo pida desde el móvil.")
        r["plan"].append("3. Después Kira podrá programarla.")
        return r
    r["estado"] = "programable"
    r["plan"] = ["Kira escribe el módulo con tu pedido (Mejoras).",
                 "El laboratorio lo prueba (sintaxis, avisos, carga aislada, tests fijos).",
                 "Tú lo revisas y lo aplicas con doble confirmación."]
    return r


def informe(hechos):
    """Lista de estados de todas las capacidades."""
    return [estado(c, hechos) for c in CAPACIDADES]


ETIQUETA = {"disponible": "[OK]", "programable": "[ ]", "falta_entorno": "[!]"}


def texto_informe(estados):
    l = ["Qué sabe hacer Kira y qué le falta:"]
    for e in estados:
        l.append(f"  {ETIQUETA[e['estado']]} {e['nombre']}  ({e['estado'].replace('_', ' ')})")
    pend = [e for e in estados if e["estado"] != "disponible"]
    if pend:
        l.append("")
        l.append("[ ] se puede programar ahora; [!] necesita algo antes. Di «preparar <nombre>» (p. ej. «preparar mesa de mezcla») "
                 "o abre el Taller.")
    return "\n".join(l)


def texto_plan(cap, hechos):
    e = estado(cap, hechos)
    l = [f"{cap['nombre']}: {e['estado'].replace('_', ' ')}."] + e["plan"]
    if e["estado"] == "programable":
        l.append("Lo siguiente es pedirle a Kira que la programe: en el Taller, «Programarla con Kira».")
    return "\n".join(l)


def pedido_mejora(cap):
    """Texto que se envía a 'mejorar' para que Kira programe esta capacidad (None si es integrada)."""
    return cap.get("pedido")
