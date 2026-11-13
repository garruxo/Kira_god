# -*- coding: utf-8 -*-
"""
accesos_kira.py — v3.26: los ACCESOS DIRECTOS de los programas que Kira crea (solo KiraOS, el portátil).

Lo pidió el dueño: «cuando cree un programa nuevo, que lo cree con un acceso directo con un icono en el escritorio, y
que se pueda desinstalar con el botón derecho del ratón, como en Windows».

Cada acceso directo guarda el programa como una APP WEB (Brython, con `app_web_kira`) para poder ABRIRLO y verlo/
manejarlo de forma SEGURA (corre en el navegador/pywebview, aislado; NO ejecuta Python nativo con permisos), y se
apunta para que salga como un ICONO en el escritorio de KiraOS. «Desinstalar» quita el icono y su .html.

Lógica pura (sin Kivy ni red): se prueba en el PC. El registro vive en `<dir>/accesos.json` y los .html en `<dir>/apps/`.
"""
import json
import os
import re
import time

REGISTRO = "accesos.json"
CARPETA = "apps"
TOPE = 200


def _ruta(dir_):
    return os.path.join(dir_, REGISTRO)


def _leer(dir_):
    try:
        with open(_ruta(dir_), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _guardar(dir_, lista):
    try:
        tmp = _ruta(dir_) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(lista[-TOPE:], f, ensure_ascii=False)
        os.replace(tmp, _ruta(dir_))
        os.chmod(_ruta(dir_), 0o600)
    except OSError:
        pass


def _id(titulo):
    base = re.sub(r"[^a-z0-9]+", "_", str(titulo or "").lower()).strip("_")[:40]
    return base or "programa"


def listar(dir_):
    """Los accesos directos, del más nuevo al más viejo (para pintar los iconos del escritorio). A igualdad de instante
    (mismo segundo), el apuntado después va primero."""
    pares = list(enumerate(_leer(dir_)))
    pares.sort(key=lambda kv: (-kv[1].get("cuando", 0), -kv[0]))
    return [a for _i, a in pares]


def existe(dir_, titulo):
    t = str(titulo or "").strip().lower()
    return any(str(a.get("titulo", "")).strip().lower() == t for a in _leer(dir_))


def anadir(dir_, titulo, codigo="", tipo="programa", icono="programa"):
    """Crea el acceso directo de un programa recién hecho. Lo guarda como app web (si hay código) para poder abrirlo, y
    lo apunta como icono del escritorio. Deduplicado por título. Devuelve el id (o None si ya existía o no hay título)."""
    titulo = (str(titulo or "").strip() or "Programa de Kira")[:60]
    if existe(dir_, titulo):
        return None
    lista = _leer(dir_)
    usados = {a.get("id") for a in lista}
    iid = base = _id(titulo)
    k = 2
    while iid in usados:
        iid = f"{base}_{k}"
        k += 1
    tiene_html = False
    if codigo:
        try:
            import app_web_kira as aw
            html = aw.html_app(codigo, titulo=titulo)
            carpeta = os.path.join(dir_, CARPETA)
            os.makedirs(carpeta, exist_ok=True)
            ruta = os.path.join(carpeta, iid + ".html")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(html)
            os.chmod(ruta, 0o600)
            tiene_html = True
        except Exception:
            tiene_html = False
    lista.append({"id": iid, "titulo": titulo, "tipo": tipo, "icono": icono or "programa",
                  "cuando": int(time.time()), "tiene_html": tiene_html})
    _guardar(dir_, lista)
    return iid


def uno(dir_, iid):
    for a in _leer(dir_):
        if a.get("id") == iid:
            return a
    return None


def html_de(dir_, iid):
    """El .html de la app web del acceso (para abrirla en una ventana). Cadena vacía si no hay."""
    if not uno(dir_, iid):
        return ""
    try:
        with open(os.path.join(dir_, CARPETA, str(iid) + ".html"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def quitar(dir_, iid):
    """DESINSTALAR el acceso directo (clic derecho ▸ Desinstalar): quita el icono y borra su .html. True si existía."""
    lista = _leer(dir_)
    quedan = [a for a in lista if a.get("id") != iid]
    quitado = len(quedan) != len(lista)
    if quitado:
        _guardar(dir_, quedan)
        try:
            os.remove(os.path.join(dir_, CARPETA, str(iid) + ".html"))
        except OSError:
            pass
    return quitado
