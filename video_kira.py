# -*- coding: utf-8 -*-
"""
video_kira.py - Que Kira aprenda de un vídeo tutorial de YouTube.

Saca lo que DICE el vídeo y lo devuelve como texto, para que el núcleo lo resuma y lo guarde en el baúl (igual que un
PDF o una página). Primero prueba los SUBTÍTULOS (rápido y fiable, la mayoría de tutoriales los tienen, aunque sean
automáticos); si no hay, usa el OÍDO de Kira (Vosk) para transcribir el audio (más lento; ese «oído» se le pasa de
fuera porque solo funciona en el móvil).

  aprender("https://youtu.be/XXXX", bajar=…, transcribir=…)
    -> {"ok", "titulo", "texto", "fuente": "subtitulos"|"oido", "idioma"}  o  {"ok": False, "error": …}

Lógica pura (sin Kivy): se prueba con un «bajar» de mentira. El bajador de verdad (internet) y el oído los pone el
núcleo.
"""
import html as _html
import json
import re

_IDRX = (r"[?&]v=([\w-]{11})", r"youtu\.be/([\w-]{11})", r"/shorts/([\w-]{11})", r"/embed/([\w-]{11})",
         r"/live/([\w-]{11})")


def id_de(texto):
    """El identificador (11 caracteres) del vídeo de YouTube que haya en el texto, o ''."""
    t = str(texto or "").strip()
    for rx in _IDRX:
        m = re.search(rx, t)
        if m:
            return m.group(1)
    return t if re.fullmatch(r"[\w-]{11}", t) else ""


def es_youtube(texto):
    t = str(texto or "").lower()
    return bool(id_de(texto)) or "youtube.com" in t or "youtu.be" in t


_ORDEN = re.compile(r"\b(aprende|apr[eé]ndete|estudia|estudi[aá]te|resume|res[uú]meme|mira)\b", re.I)


def es_orden(texto):
    """¿Es un «aprende de este vídeo …» con un enlace de YouTube? (para que el núcleo lo mande aquí)."""
    t = str(texto or "")
    if not es_youtube(t):
        return False
    low = t.lower()
    return bool(_ORDEN.search(low)) or "video" in low or "vídeo" in low or "tutorial" in low or "youtube" in low


def _bloque_json(texto, clave):
    """Saca el array/objeto JSON que va tras «"clave":» equilibrando los corchetes (aguanta corchetes dentro de
    cadenas). Devuelve el trozo de texto JSON o ''."""
    i = texto.find('"' + clave + '"')
    if i < 0:
        return ""
    j = texto.find(":", i)
    if j < 0:
        return ""
    j += 1
    while j < len(texto) and texto[j] in " \t\r\n":
        j += 1
    if j >= len(texto) or texto[j] not in "[{":
        return ""
    abre = texto[j]
    cierra = "]" if abre == "[" else "}"
    prof, k, en_cadena, escape = 0, j, False, False
    while k < len(texto):
        c = texto[k]
        if en_cadena:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                en_cadena = False
        else:
            if c == '"':
                en_cadena = True
            elif c == abre:
                prof += 1
            elif c == cierra:
                prof -= 1
                if prof == 0:
                    return texto[j:k + 1]
        k += 1
    return ""


def pistas(pagina):
    """Las pistas de subtítulos del HTML de la página del vídeo: [{url, idioma, nombre, auto}]."""
    bloque = _bloque_json(pagina, "captionTracks")
    if not bloque:
        return []
    try:
        arr = json.loads(bloque)
    except ValueError:
        return []
    out = []
    for t in arr:
        base = (t.get("baseUrl") or "").replace("\\u0026", "&")
        nombre = (t.get("name") or {}).get("simpleText", "")
        if not nombre:
            runs = (t.get("name") or {}).get("runs") or []
            nombre = runs[0].get("text", "") if runs else ""
        out.append({"url": base, "idioma": t.get("languageCode", ""), "nombre": nombre,
                    "auto": t.get("kind") == "asr"})
    return out


def elegir(lista, idioma="es"):
    """La mejor pista: el idioma pedido antes que otros, y los subtítulos de verdad antes que los automáticos."""
    if not lista:
        return None

    def punt(p):
        return (0 if (p["idioma"] or "").startswith(idioma) else 2, 1 if p["auto"] else 0)

    return sorted(lista, key=punt)[0]


def texto_de_subtitulos(xml):
    """El texto corrido de un subtítulo en formato timedtext (XML) de YouTube."""
    partes = re.findall(r"<text[^>]*>(.*?)</text>", str(xml or ""), re.S)
    limpio = " ".join(_html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\n", " ") for p in partes)
    return re.sub(r"\s+", " ", limpio).strip()


def _titulo(pagina):
    m = re.search(r'"videoDetails".{0,400}?"title":"((?:[^"\\]|\\.)*)"', pagina, re.S)
    if m:
        try:
            return json.loads('"' + m.group(1) + '"')
        except ValueError:
            pass
    m = re.search(r"<title>(.*?)</title>", pagina, re.S)
    return _html.unescape(m.group(1)).replace(" - YouTube", "").strip() if m else ""


def _bajar_defecto(url):
    import urllib.request
    import red_kira
    agente = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
    req = urllib.request.Request(url, headers={"User-Agent": agente, "Accept-Language": "es-ES,es;q=0.9,en;q=0.5"})
    with red_kira.abrir(req, timeout=25) as r:
        return r.read(8 * 1024 * 1024)


def aprender(texto, bajar=None, transcribir=None, idioma="es"):
    """Saca lo que dice un vídeo de YouTube. `bajar(url)->bytes` (internet) y `transcribir(id)->texto` (el oído) se
    inyectan. Devuelve el texto del vídeo para que el núcleo lo resuma/estudie."""
    bajar = bajar or _bajar_defecto
    vid = id_de(texto)
    if not vid:
        return {"ok": False, "error": "No reconozco el enlace de YouTube. Pásame uno como youtu.be/… o youtube.com/watch?v=…"}
    try:
        pagina = bajar(f"https://www.youtube.com/watch?v={vid}&hl=es").decode("utf-8", "replace")
    except Exception as e:
        return {"ok": False, "error": f"No pude abrir el vídeo (¿hay internet?): {e}"}
    titulo = _titulo(pagina) or vid
    pista = elegir(pistas(pagina), idioma)
    if pista and pista["url"]:
        try:
            xml = bajar(pista["url"]).decode("utf-8", "replace")
            cuerpo = texto_de_subtitulos(xml)
        except Exception:
            cuerpo = ""
        if cuerpo and len(cuerpo) > 40:
            return {"ok": True, "titulo": titulo, "texto": cuerpo, "fuente": "subtitulos",
                    "idioma": pista["idioma"], "auto": pista["auto"]}
    # sin subtítulos: el oído de Kira (si está disponible)
    if transcribir is not None:
        try:
            cuerpo = transcribir(vid) or ""
        except Exception as e:
            return {"ok": False, "titulo": titulo, "error": f"No pude transcribir el audio con el oído: {e}"}
        if cuerpo:
            return {"ok": True, "titulo": titulo, "texto": cuerpo, "fuente": "oido"}
    return {"ok": False, "titulo": titulo,
            "error": "Este vídeo no tiene subtítulos. Puedo transcribirlo con mi oído, pero eso aún no está listo en el móvil."}
