# -*- coding: utf-8 -*-
"""
recetas_programas_kira.py - v3.77: RECETAS probadas para manejar por órdenes programas que normalmente son de
ventana (LibreOffice, GIMP, Inkscape, ImageMagick) y algunos de órdenes muy usados (ffmpeg, pandoc).

Lo pidió el dueño: «los programas que solo funcionan con ventana… cómo podemos hacer que lo haga». Muchos de esos
programas tienen un modo «sin ventana» (por lotes). El cerebro pequeño del portátil no se sabe esos guiones de
memoria, así que aquí van las recetas ya escritas: si la tarea encaja con una receta, el plan del Taller sale de
aquí TAL CUAL (sin que el cerebro lo invente); si no encaja, las recetas se le dan al cerebro como ejemplos.

Todo es puro (sin ejecutar nada): devuelve las órdenes en texto. Las ejecuta el Taller con sus candados de siempre
y SOLO tras tu «Hazlo» (dos toques).
"""
import os
import re
import shutil
import unicodedata

# nombre que dices → posibles programas instalados (el primero que exista)
ALIAS = {
    "libreoffice": ["soffice", "libreoffice"], "soffice": ["soffice", "libreoffice"],
    "writer": ["soffice", "libreoffice"], "calc": ["soffice", "libreoffice"], "impress": ["soffice", "libreoffice"],
    "lowriter": ["soffice", "libreoffice"], "localc": ["soffice", "libreoffice"], "office": ["soffice", "libreoffice"],
    "gimp": ["gimp", "gimp-console"], "gimp-console": ["gimp-console", "gimp"],
    "inkscape": ["inkscape"],
    "imagemagick": ["magick", "convert"], "magick": ["magick", "convert"], "convert": ["convert", "magick"],
    "ffmpeg": ["ffmpeg"], "pandoc": ["pandoc"],
}
FAMILIA = {"soffice": "office", "libreoffice": "office", "gimp": "gimp", "gimp-console": "gimp",
           "inkscape": "inkscape", "magick": "magick", "convert": "magick", "ffmpeg": "ffmpeg", "pandoc": "pandoc"}

EXT = {
    "office": {"docx", "doc", "odt", "rtf", "txt", "xlsx", "xls", "ods", "csv", "pptx", "ppt", "odp", "html"},
    "gimp": {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "xcf"},
    "magick": {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp"},
    "inkscape": {"svg"},
    "ffmpeg": {"mp4", "mkv", "avi", "mov", "webm", "mp3", "wav", "ogg", "flac", "m4a"},
    "pandoc": {"md", "markdown", "txt", "html", "docx", "odt", "rst"},
}
SALIDAS = {
    "office": {"pdf", "docx", "odt", "txt", "html", "xlsx", "ods", "csv", "pptx", "odp", "rtf"},
    "gimp": {"png", "jpg", "jpeg", "gif", "bmp", "tif", "webp"},
    "magick": {"png", "jpg", "jpeg", "gif", "bmp", "tif", "webp", "pdf"},
    "inkscape": {"png", "pdf", "eps", "ps"},
    "ffmpeg": {"mp3", "wav", "ogg", "mp4", "webm", "gif", "m4a", "flac", "mkv"},
    "pandoc": {"docx", "odt", "html", "epub", "md", "rst"},
}
_NOMBRE_SEGURO = re.compile(r"^[\w][\w .+-]{0,120}$", re.UNICODE)


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def canonico(prog, which=None):
    """El programa de verdad que hay instalado para lo que dices («libreoffice» → soffice…). Si no hay alias, igual."""
    which = which or shutil.which
    p = os.path.basename(str(prog or "")).lower()
    for c in ALIAS.get(p, []):
        if which(c):
            return c
    return p


def familia(prog):
    return FAMILIA.get(os.path.basename(str(prog or "")).lower())


def nombre_seguro(n):
    """Un nombre de archivo que se puede meter en una receta (sin comillas, barras ni «..»)."""
    n = str(n or "")
    return bool(_NOMBRE_SEGURO.match(n)) and ".." not in n and "/" not in n and "\\" not in n


# ------------------------------------------------------------------ entender la TAREA
def archivos_de(tarea, ext=None):
    """Nombres de archivo que aparecen en la tarea («informe.docx», «foto 1.jpg» no: sin espacios)."""
    out = []
    for m in re.finditer(r"[\w][\w.+-]*\.([A-Za-z0-9]{2,5})\b", str(tarea or ""), re.UNICODE):
        n, e = m.group(0), m.group(1).lower()
        if (ext is None or e in ext) and nombre_seguro(n) and n not in out:
            out.append(n)
    return out


def formato_destino(tarea, posibles):
    """El formato al que quieres llegar: «a pdf», «en png», «como mp3», «pdf»…"""
    t = _plano(tarea)
    m = re.search(r"\b(?:a|en|como|para|al formato|formato)\s+(?:un\s+|una\s+)?(?:archivo\s+)?\.?([a-z0-9]{2,5})\b", t)
    if m and m.group(1) in posibles:
        return "jpg" if m.group(1) == "jpeg" else m.group(1)
    for f in posibles:
        if re.search(r"(?<![\w.])" + re.escape(f) + r"\b", t):
            return "jpg" if f == "jpeg" else f
    if re.search(r"\baudio\b|\bmusica\b|\bsonido\b", t) and "mp3" in posibles:
        return "mp3"
    return None


def porcentaje(tarea):
    t = _plano(tarea)
    m = re.search(r"(\d{1,3})\s*(?:%|por ?ciento)", t)
    if m and 1 <= int(m.group(1)) <= 400:
        return int(m.group(1))
    if re.search(r"\bmitad\b", t):
        return 50
    if re.search(r"\b(?:pequen|achica|reduce|reducir|menos pesad|que pesen? menos)", t):
        return 50
    return None


def ancho(tarea):
    t = _plano(tarea)
    m = re.search(r"\b(\d{2,5})\s*(?:px|pixeles|pixels|puntos)\b", t) or re.search(r"\ba\s+(\d{2,5})\s+de\s+ancho", t)
    if m and 16 <= int(m.group(1)) <= 10000:
        return int(m.group(1))
    return None


def giro(tarea):
    t = _plano(tarea)
    if not re.search(r"\b(gira|girar|rota|rotar|voltea|dale la vuelta)", t):
        return None
    m = re.search(r"\b(90|180|270)\b", t)
    if m:
        return int(m.group(1))
    if "izquierda" in t:
        return 270
    return 90


def accion_de(tarea):
    t = _plano(tarea)
    if re.search(r"blanco y negro|escala de grises|\bgris(es)?\b|byn\b", t):
        return "gris"
    if giro(tarea):
        return "girar"
    if ancho(tarea) or re.search(r"\b(redimension|escala|cambia(r)? el tamano|tamano|pequen|achica|reduce|mitad|amplia|agranda)", t) \
            or porcentaje(tarea):
        return "tamano"
    if re.search(r"\b(extrae|saca|quita)\b.*\b(audio|sonido|musica)\b", t):
        return "audio"
    if re.search(r"\bgif\b", t):
        return "gif"
    if re.search(r"\b(convierte|convertir|pasa|pasar|exporta|exportar|transforma|guarda como|cambia el formato)", t) \
            or formato_destino(tarea, set().union(*SALIDAS.values())):
        return "convertir"
    return None


# ------------------------------------------------------------------ las RECETAS (texto de órdenes)
def _base(n):
    return os.path.splitext(n)[0]


def _sf_cadena(n):
    return '"' + n + '"'


def _gimp(prog, entrada, salida, pasos):
    """Una orden de GIMP por lotes (Script-Fu, GIMP 2.10): abre, hace los pasos, aplana, guarda y sale."""
    e, s = _sf_cadena(entrada), _sf_cadena(salida)
    script = ("(let* ((img (car (gimp-file-load RUN-NONINTERACTIVE " + e + " " + e + "))))"
              + "".join(" " + p for p in pasos)
              + " (gimp-file-save RUN-NONINTERACTIVE img (car (gimp-image-flatten img)) " + s + " " + s + ")"
              + " (gimp-image-delete img))")
    return f"{prog} -i -b '{script}' -b '(gimp-quit 0)'"


def _orden_una(fam, prog, entrada, accion, tarea, fmt):
    b = _base(entrada)
    ext_in = os.path.splitext(entrada)[1].lstrip(".").lower()
    if fam == "office":
        f = fmt or "pdf"
        return (f"{prog} -env:UserInstallation=file:///tmp/kira_lo --headless --convert-to {f} --outdir . {entrada}",
                f"{b}.{f}")
    if fam == "pandoc":
        f = fmt or "docx"
        return f"{prog} {entrada} -o {b}.{f}", f"{b}.{f}"
    if fam == "inkscape":
        f = fmt or "png"
        extra = f" -w {ancho(tarea)}" if ancho(tarea) and f == "png" else ""
        return f"{prog} {entrada} --export-type={f} --export-filename={b}.{f}{extra}", f"{b}.{f}"
    if fam == "ffmpeg":
        if accion == "audio" or (fmt in ("mp3", "wav", "ogg", "m4a", "flac") and ext_in not in ("mp3", "wav", "ogg", "m4a", "flac")):
            f = fmt if fmt in ("mp3", "wav", "ogg", "m4a", "flac") else "mp3"
            return f"{prog} -nostdin -y -i {entrada} -vn {b}.{f}", f"{b}.{f}"
        if accion == "gif" or fmt == "gif":
            w = ancho(tarea) or 480
            return f"{prog} -nostdin -y -i {entrada} -vf fps=10,scale={w}:-1 {b}.gif", f"{b}.gif"
        f = fmt or "mp4"
        if f == ext_in:
            f = "webm" if f == "mp4" else "mp4"
        return f"{prog} -nostdin -y -i {entrada} {b}.{f}", f"{b}.{f}"
    # imágenes: GIMP o ImageMagick
    f = fmt or ("jpg" if ext_in in ("jpeg", "jpg") else (ext_in if ext_in in SALIDAS[fam] else "png"))
    sufijo = {"gris": "_gris", "girar": "_girada", "tamano": "_peq"}.get(accion, "")
    salida = f"{b}{sufijo}.{f}"
    if salida == entrada:
        salida = f"{b}_nueva.{f}"
    if fam == "magick":
        op = ""
        if accion == "gris":
            op = " -colorspace Gray"
        elif accion == "girar":
            op = f" -rotate {giro(tarea)}"
        elif accion == "tamano":
            op = f" -resize {ancho(tarea)}x" if ancho(tarea) else f" -resize {porcentaje(tarea) or 50}%"
        return f"{prog} {entrada}{op} {salida}", salida
    pasos = []
    if accion == "gris":
        pasos.append("(gimp-image-convert-grayscale img)")
    elif accion == "girar":
        pasos.append("(gimp-image-rotate img " + {90: "ROTATE-90", 180: "ROTATE-180", 270: "ROTATE-270"}[giro(tarea)] + ")")
    elif accion == "tamano":
        if ancho(tarea):
            w = ancho(tarea)
            pasos.append(f"(gimp-image-scale img {w} (/ (* {w} (car (gimp-image-height img))) (car (gimp-image-width img))))")
        else:
            p = (porcentaje(tarea) or 50) / 100
            pasos.append(f"(gimp-image-scale img (* (car (gimp-image-width img)) {p}) (* (car (gimp-image-height img)) {p}))")
    return _gimp(prog, entrada, salida, pasos), salida


def plan(prog, tarea, archivos_carpeta=()):
    """(órdenes, notas) si la tarea encaja con una receta de este programa; None si no hay receta para eso.
    Si encaja pero falta el archivo, devuelve ([], [nota que dice dónde ponerlo])."""
    fam = familia(prog)
    if not fam:
        return None
    accion = accion_de(tarea)
    if accion is None:
        return None
    if fam in ("office", "pandoc", "inkscape") and accion not in ("convertir",):
        if not (fam == "inkscape" and accion == "tamano"):
            return None
    fmt = formato_destino(tarea, SALIDAS[fam])
    entradas = archivos_de(tarea, EXT[fam])
    if not entradas:
        t = _plano(tarea)
        todas = re.search(r"\b(todas|todos|las fotos|los documentos|los archivos|las imagenes|los videos|cada)\b", t)
        candidatos = [n for n in archivos_carpeta if os.path.splitext(n)[1].lstrip(".").lower() in EXT[fam]
                      and nombre_seguro(n) and (not fmt or os.path.splitext(n)[1].lstrip(".").lower() != fmt
                                                or accion != "convertir")]
        entradas = candidatos if todas else candidatos[:1]
    if not entradas:
        tipos = ", ".join(sorted(EXT[fam])[:8])
        return [], [f"Pon el archivo ({tipos}) en la carpeta del taller y dime su nombre."]
    ordenes, notas = [], []
    for n in entradas[:8]:
        if not nombre_seguro(n):
            notas.append(f"«{n}» tiene un nombre raro (comillas o barras): cámbialo de nombre.")
            continue
        o, sal = _orden_una(fam, prog, n, accion, tarea, fmt)
        ordenes.append(o)
        notas.append(f"{n} → {sal}")
    if fam == "office":
        notas.append("Si tienes LibreOffice abierto con ventana, ciérralo antes (si no, no convierte).")
    return ordenes, notas[:8]


def ejemplos(prog):
    """Texto con ejemplos de órdenes que funcionan, para darle al cerebro cuando ninguna receta encaja."""
    fam = familia(prog)
    if not fam:
        return ""
    muestras = {
        "office": ["convierte informe.docx a pdf", "pasa datos.xlsx a csv"],
        "gimp": ["haz foto.jpg más pequeña al 50%", "pon foto.jpg en blanco y negro"],
        "magick": ["haz foto.jpg de 800 px", "gira foto.jpg 90", "convierte dibujo.png a jpg"],
        "inkscape": ["exporta logo.svg a png de 512 px"],
        "ffmpeg": ["saca el audio de video.mp4 a mp3", "haz un gif de video.mp4"],
        "pandoc": ["convierte notas.md a docx"],
    }[fam]
    lin = []
    for m in muestras:
        r = plan(prog, m, ())
        if r and r[0]:
            lin.append(f"$ {r[0][0]}")
    return "Ejemplos que funcionan:\n" + "\n".join(lin) if lin else ""


def es_guion(prog, arg):
    """¿Es un argumento que lleva un GUION dentro (Script-Fu de GIMP, macros de LibreOffice, acciones de Inkscape)?
    Esos solo se aceptan cuando salen de una receta, nunca escritos por el cerebro."""
    fam = familia(prog)
    a = str(arg or "")
    if fam == "gimp":
        return a.startswith("(") or a in ("-b", "--batch", "--batch-interpreter")
    if fam == "office":
        return a.lower().startswith(("macro:", "vnd.sun.star.script")) or "macro:" in a.lower()
    if fam == "inkscape":
        return a.startswith(("--actions", "--shell", "--action"))
    return False
