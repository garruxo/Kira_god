# -*- coding: utf-8 -*-
"""Aprender de un vídeo de YouTube (video_kira): reconocer el enlace, sacar las pistas de subtítulos del HTML, elegir
el mejor (español, no automático), leer el texto del subtítulo, y la reserva del oído si no hay subtítulos. Con un
«bajar» de mentira (sin internet)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import video_kira as vk

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# --- reconocer el enlace ---
ok(vk.id_de("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1s") == "dQw4w9WgXcQ", "saca el id de un watch?v=")
ok(vk.id_de("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ", "saca el id de un youtu.be")
ok(vk.id_de("mira esto https://www.youtube.com/shorts/abcdefghijk ok") == "abcdefghijk", "saca el id de un short dentro de una frase")
ok(vk.es_youtube("youtu.be/dQw4w9WgXcQ") and not vk.es_youtube("https://vimeo.com/123"), "distingue YouTube de otros")
ok(vk.id_de("no hay enlace") == "", "si no hay enlace, id vacío")

# --- HTML de mentira con dos pistas de subtítulos (una en inglés auto, otra en español) ---
PAGINA = r'''<html><head><title>Curso de Python - YouTube</title></head><body>
<script>var x = {"videoDetails":{"videoId":"dQw4w9WgXcQ","title":"Curso de Python desde cero","author":"Profe"},
"captions":{"playerCaptionsTracklistRenderer":{"captionTracks":[
{"baseUrl":"https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=en&kind=asr","name":{"simpleText":"Inglés (automático)"},"languageCode":"en","kind":"asr"},
{"baseUrl":"https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=es","name":{"simpleText":"Español"},"languageCode":"es"}
]}}};</script></body></html>'''

ps = vk.pistas(PAGINA)
ok(len(ps) == 2 and all("timedtext" in p["url"] for p in ps), "saca las dos pistas de subtítulos")
ok("&" in ps[0]["url"] and "\\u0026" not in ps[0]["url"], "arregla el \\u0026 de las direcciones")
mejor = vk.elegir(ps, "es")
ok(mejor["idioma"] == "es" and not mejor["auto"], "elige el español de verdad antes que el inglés automático")

ok(vk._titulo(PAGINA) == "Curso de Python desde cero", "saca el título del vídeo")

# --- subtítulos (timedtext XML) ---
XML = '''<?xml version="1.0"?><transcript>
<text start="0" dur="3">Hola, en este tutorial</text>
<text start="3" dur="3">vamos a aprender Python&amp;#39;s básico</text>
<text start="6" dur="3">empezando por las variables</text>
</transcript>'''
t = vk.texto_de_subtitulos(XML)
ok("Hola, en este tutorial" in t and "variables" in t and "<text" not in t, "lee el texto del subtítulo (sin etiquetas)")

# --- subtítulos automáticos con solape (se repite el final de cada línea) ---
XML_SOLAPE = ('<transcript>'
              '<text>vamos a crear una función</text>'
              '<text>crear una función en Python</text>'
              '<text>en Python que sume dos números</text></transcript>')
ts = vk.texto_de_subtitulos(XML_SOLAPE)
ok(ts.count("crear una función") == 1 and ts.count("en Python") == 1 and "sume dos números" in ts,
   "quita el solape de los subtítulos automáticos (cada trozo se queda una vez)")
ok(vk.sin_repeticiones("sí sí sí sí sí sí vale", mínimo=1) == "sí vale", "rompe un bucle de una sola palabra")
ok(vk.sin_repeticiones("hola que tal") == "hola que tal", "no toca un texto normal sin repeticiones")

# --- aprender() entero con un bajar de mentira ---
def bajar_falso(url):
    if "watch?v=" in url:
        return PAGINA.encode("utf-8")
    if "timedtext" in url and "lang=es" in url:
        return XML.encode("utf-8")
    return b"<transcript></transcript>"

r = vk.aprender("https://youtu.be/dQw4w9WgXcQ", bajar=bajar_falso)
ok(r["ok"] and r["fuente"] == "subtitulos" and "Python" in r["texto"] and r["titulo"].startswith("Curso"),
   "aprende del vídeo por los subtítulos (español)")

# --- HTML «pelado» (muro de Europa) pero la API interna de YouTube sí trae los subtítulos ---
PAGINA_PELADA = '<html><head><title>Curso de Python - YouTube</title></head><body>ver antes de aceptar cookies</body></html>'
API_JSON = r'''{"videoDetails":{"title":"Curso de Python desde cero"},
"captions":{"playerCaptionsTracklistRenderer":{"captionTracks":[
{"baseUrl":"https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=es","name":{"simpleText":"Español"},"languageCode":"es"}
]}}}'''

def bajar_con_api(url, datos=None, cabeceras=None):
    if datos is not None:          # POST a la API interna
        return API_JSON.encode("utf-8")
    if "watch?v=" in url:          # el HTML viene sin subtítulos
        return PAGINA_PELADA.encode("utf-8")
    if "timedtext" in url and "lang=es" in url:
        return XML.encode("utf-8")
    return b"<transcript></transcript>"

r_api = vk.aprender("https://youtu.be/dQw4w9WgXcQ", bajar=bajar_con_api)
ok(r_api["ok"] and r_api["fuente"] == "subtitulos" and "Python" in r_api["texto"],
   "si el HTML viene sin subtítulos, los saca de la API interna de YouTube")

# --- sin subtítulos: usa el oído si está; si no, lo dice claro ---
PAGINA_SIN = '<html><head><title>Algo - YouTube</title></head><body><script>{"videoDetails":{"title":"Algo"}}</script></body></html>'
def bajar_sin(url):
    return PAGINA_SIN.encode("utf-8")

r2 = vk.aprender("https://youtu.be/dQw4w9WgXcQ", bajar=bajar_sin)
ok(not r2["ok"] and "oído" in r2["error"], "sin subtítulos y sin oído: lo dice claro")

r3 = vk.aprender("https://youtu.be/dQw4w9WgXcQ", bajar=bajar_sin, transcribir=lambda vid: "esto lo dijo la voz del vídeo")
ok(r3["ok"] and r3["fuente"] == "oido" and "voz del vídeo" in r3["texto"], "sin subtítulos, el oído de Kira lo transcribe")

# enlace que no es de YouTube
r4 = vk.aprender("no hay enlace aquí", bajar=bajar_falso)
ok(not r4["ok"] and "YouTube" in r4["error"], "si no hay enlace de YouTube, avisa")

# reconocedor de la orden
ok(vk.es_orden("Kira, aprende de este vídeo https://youtu.be/dQw4w9WgXcQ"), "reconoce «aprende de este vídeo …»")
ok(vk.es_orden("resume este tutorial de youtube.com/watch?v=dQw4w9WgXcQ"), "reconoce «resume este tutorial de youtube»")
ok(not vk.es_orden("https://youtu.be/dQw4w9WgXcQ"), "un enlace suelto sin «aprende/vídeo» no lo secuestra")
ok(not vk.es_orden("aprende de este pdf"), "sin enlace de YouTube, no es orden de vídeo")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
