# -*- coding: utf-8 -*-
"""
fondos_kira.py — v3.45 (SOLO KiraOS): las IMÁGENES que KiraOS puede usar de FONDO DE PANTALLA y como ICONOS.

Lo pidió el dueño: «que pueda poner imágenes de fondo de pantalla, o crear en el pintor del móvil para cambiar todas
las imágenes de Kira, incluso nuevos iconos».

De dónde salen (solo LEE, no cambia nada):
  * las que pinta el PINTOR DEL MÓVIL: viajan solas a KiraOS al sincronizar (`<datos>/imagenes_movil`);
  * tus carpetas de imágenes (Imágenes, Descargas, Escritorio…) y ~/kira_portatil/fondos;
  * los fondos que trae Xubuntu (/usr/share/backgrounds, /usr/share/xfce4/backdrops).
Elegir una se hace SIEMPRE por su número (id) de esta lista: la pantalla nunca puede pedir un archivo cualquiera.
Para la pantalla se mandan como «data:» (la ventana no lee archivos sueltos); si hay Pillow se achican.
"""
import base64
import hashlib
import io
import os
import time

EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
        ".gif": "image/gif", ".bmp": "image/bmp"}
MAX_LISTA = 300
MAX_BRUTO_MINI = 400_000            # sin Pillow, una miniatura «en bruto» solo si el archivo es pequeño
MAX_BRUTO_FONDO = 12_000_000
_cache_mini = {}


def datos_nucleo():
    return os.environ.get("KIRA_DATOS_NUCLEO") or os.path.expanduser("~/kira_portatil/kira_datos")


def carpetas():
    """[(carpeta, origen)] en el orden en que se enseñan."""
    casa = os.path.expanduser("~")
    return [(os.path.join(datos_nucleo(), "imagenes_movil"), "pintado en el móvil"),
            (os.path.join(casa, "kira_portatil", "fondos"), "fondos de Kira"),
            (os.path.join(casa, "Imágenes"), "Imágenes"), (os.path.join(casa, "Pictures"), "Imágenes"),
            (os.path.join(casa, "Escritorio"), "Escritorio"), (os.path.join(casa, "Desktop"), "Escritorio"),
            (os.path.join(casa, "Descargas"), "Descargas"), (os.path.join(casa, "Downloads"), "Descargas"),
            ("/usr/share/backgrounds", "de Xubuntu"), ("/usr/share/xfce4/backdrops", "de Xubuntu")]


def _id(ruta):
    return hashlib.sha1(os.path.abspath(ruta).encode("utf-8", "replace")).hexdigest()[:12]


def listar(lista_carpetas=None, maximo=MAX_LISTA):
    """[{id, nombre, ruta, origen, cuando}] — las del móvil primero, luego lo más nuevo."""
    vistos, fuera = set(), []
    for orden_c, (carpeta, origen) in enumerate(lista_carpetas or carpetas()):
        if not os.path.isdir(carpeta):
            continue
        base_prof = carpeta.rstrip(os.sep).count(os.sep)
        for raiz, dirs, archivos in os.walk(carpeta):
            if raiz.count(os.sep) - base_prof >= 2:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for a in archivos:
                if not a.lower().endswith(EXT) or a.startswith("."):
                    continue
                r = os.path.realpath(os.path.join(raiz, a))
                if r in vistos or not os.path.isfile(r):
                    continue
                vistos.add(r)
                try:
                    cuando = os.path.getmtime(r)
                except OSError:
                    cuando = 0
                fuera.append({"id": _id(r), "nombre": os.path.splitext(a)[0][:80], "ruta": r, "origen": origen,
                              "cuando": cuando, "_orden": 0 if origen == "pintado en el móvil" else 1})
                if len(fuera) >= maximo * 3:
                    break
    fuera.sort(key=lambda x: (x["_orden"], -x["cuando"]))
    for x in fuera:
        x.pop("_orden", None)
    return fuera[:maximo]


def por_id(ident, lista=None):
    for x in lista if lista is not None else listar():
        if x["id"] == str(ident):
            return x
    return None


def _plano(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def buscar(texto, lista=None):
    """«la última del móvil / del pintor», «la última», o por palabras del nombre."""
    lista = lista if lista is not None else listar()
    t = _plano(texto).strip(" .")
    t = t.replace("_", " ")
    if not lista:
        return None
    if "ultima" in t or "nueva" in t or "reciente" in t:
        movil = [x for x in lista if x["origen"] == "pintado en el móvil"]
        if movil and ("movil" in t or "pintor" in t or "pintad" in t):
            return max(movil, key=lambda x: x["cuando"])
        return max(lista, key=lambda x: x["cuando"])
    palabras = [p for p in t.replace("-", " ").split() if len(p) > 2 and p not in ("imagen", "foto", "del", "las", "los")]
    mejor, puntos = None, 0
    for x in lista:
        n = _plano(x["nombre"]).replace("_", " ").replace("-", " ")
        p = sum(1 for w in palabras if w in n)
        if p > puntos:
            mejor, puntos = x, p
    return mejor


def mime(ruta):
    return MIME.get(os.path.splitext(ruta)[1].lower(), "image/png")


def _data(mime_, datos):
    return f"data:{mime_};base64," + base64.b64encode(datos).decode("ascii")


def _achicar(ruta, lado, calidad=78):
    """Con Pillow: la imagen achicada a `lado` píxeles (el mayor) en JPEG/PNG. None si no hay Pillow."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(ruta) as im:
            im.thumbnail((lado, lado))
            buf = io.BytesIO()
            if im.mode in ("RGBA", "LA", "P"):
                im.save(buf, "PNG", optimize=True)
                return _data("image/png", buf.getvalue())
            im.convert("RGB").save(buf, "JPEG", quality=calidad)
            return _data("image/jpeg", buf.getvalue())
    except Exception:
        return ""


def miniatura(ruta, lado=220):
    """La imagen pequeña para la galería o un icono. '' si no se puede (se enseña solo el nombre)."""
    try:
        clave = (ruta, lado, os.path.getmtime(ruta))
    except OSError:
        return ""
    if clave in _cache_mini:
        return _cache_mini[clave]
    d = _achicar(ruta, lado)
    if d is None:                                     # sin Pillow: en bruto si es pequeña
        try:
            d = _data(mime(ruta), open(ruta, "rb").read()) if os.path.getsize(ruta) <= MAX_BRUTO_MINI else ""
        except OSError:
            d = ""
    if len(_cache_mini) > 400:
        _cache_mini.clear()
    _cache_mini[clave] = d
    return d


def fondo(ruta, ancho=1920):
    """El fondo para la pantalla (achicado al ancho de la pantalla si hay Pillow)."""
    if not ruta or not os.path.isfile(ruta) or not ruta.lower().endswith(EXT):
        return ""
    d = _achicar(ruta, ancho, calidad=85)
    if d:
        return d
    try:
        if os.path.getsize(ruta) <= MAX_BRUTO_FONDO:
            return _data(mime(ruta), open(ruta, "rb").read())
    except OSError:
        pass
    return ""


def galeria(lista=None, maximo=60):
    """Para la ventana «Fondo de pantalla»: [{id, nombre, origen, mini}] (las primeras con miniatura)."""
    lista = lista if lista is not None else listar()
    fuera = []
    t0 = time.time()
    for i, x in enumerate(lista[:maximo]):
        mini = miniatura(x["ruta"]) if time.time() - t0 < 6 else ""
        fuera.append({"id": x["id"], "nombre": x["nombre"], "origen": x["origen"], "mini": mini})
    return fuera
