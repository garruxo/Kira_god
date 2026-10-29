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


def sin_repeticiones(texto, mínimo=2):
    """Quita los solapes de los subtítulos automáticos: si una secuencia de `mínimo` a 10 palabras va pegada a sí misma,
    deja solo una. (Los subtítulos auto de YouTube repiten el final de cada línea al principio de la siguiente.)"""
    palabras = str(texto or "").split()
    if len(palabras) < 6:
        return str(texto or "").strip()
    salida = []
    for w in palabras:
        salida.append(w)
        n = len(salida)
        for L in range(mínimo, 11):
            if n >= 2 * L and salida[-L:] == salida[-2 * L:-L]:
                del salida[-L:]
                break
    return " ".join(salida).strip()


def texto_de_subtitulos(xml):
    """El texto corrido de un subtítulo en formato timedtext (XML) de YouTube, sin los solapes de los automáticos."""
    partes = re.findall(r"<text[^>]*>(.*?)</text>", str(xml or ""), re.S)
    limpio = " ".join(_html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\n", " ") for p in partes)
    return sin_repeticiones(re.sub(r"\s+", " ", limpio).strip())


def _titulo(pagina):
    m = re.search(r'"videoDetails".{0,400}?"title":"((?:[^"\\]|\\.)*)"', pagina, re.S)
    if m:
        try:
            return json.loads('"' + m.group(1) + '"')
        except ValueError:
            pass
    m = re.search(r"<title>(.*?)</title>", pagina, re.S)
    return _html.unescape(m.group(1)).replace(" - YouTube", "").strip() if m else ""


def _bajar_defecto(url, datos=None, cabeceras=None):
    """Baja una página (GET) o, si `datos` no es None, hace un POST (para la API interna de YouTube).
    Mete la cookie de consentimiento para que YouTube no devuelva el muro de cookies de Europa (sin ella, desde España
    el HTML viene «pelado» y sin subtítulos)."""
    import urllib.request
    import red_kira
    agente = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
    cab = {"User-Agent": agente, "Accept-Language": "es-ES,es;q=0.9,en;q=0.5",
           "Cookie": "CONSENT=YES+cb.20210328-17-p0.es+FX+000; SOCS=CAI"}
    if cabeceras:
        cab.update(cabeceras)
    req = urllib.request.Request(url, data=datos, headers=cab)
    with red_kira.abrir(req, timeout=25) as r:
        return r.read(8 * 1024 * 1024)


# La API interna de YouTube (InnerTube): devuelve los datos del vídeo —incluidos los subtítulos— aunque el HTML no los
# traiga. Usamos el cliente ANDROID porque es el que menos pega con el muro de consentimiento de Europa.
_PLAYER_URL = ("https://www.youtube.com/youtubei/v1/player"
               "?key=AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w")
_CLIENTE_ANDROID = {"clientName": "ANDROID", "clientVersion": "19.09.37", "androidSdkVersion": 30,
                    "hl": "es", "gl": "ES"}


def _player_api(vid, bajar):
    """Pregunta a la API interna de YouTube por el vídeo y devuelve su JSON (texto), o '' si no se puede."""
    cuerpo = json.dumps({"context": {"client": _CLIENTE_ANDROID}, "videoId": vid,
                         "contentCheckOk": True, "racyCheckOk": True}).encode("utf-8")
    cab = {"Content-Type": "application/json",
           "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
           "X-Goog-Api-Format-Version": "2"}
    try:
        raw = bajar(_PLAYER_URL, datos=cuerpo, cabeceras=cab)
    except TypeError:
        # El «bajar» inyectado no acepta POST (p. ej. una prueba antigua): no hay reserva por API.
        return ""
    except Exception:
        return ""
    try:
        return raw.decode("utf-8", "replace")
    except Exception:
        return ""


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
    lista = pistas(pagina)
    if not lista:
        # El HTML vino sin subtítulos (muro de Europa o YouTube los escondió): se los pedimos a su API interna.
        api = _player_api(vid, bajar)
        if api:
            lista = pistas(api)
            if (not titulo or titulo == vid):
                t2 = _titulo(api)
                if t2:
                    titulo = t2
    pista = elegir(lista, idioma)
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
