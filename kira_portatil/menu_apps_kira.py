# -*- coding: utf-8 -*-
"""
menu_apps_kira.py — v3.45 (SOLO KiraOS): TODAS LAS APLICACIONES de Xubuntu dentro de KiraOS, como su menú.

Lo pidió el dueño (con una foto del menú de Xubuntu): «poner en ajustes un apartado para entrar, con esas funciones».
Lee los mismos lanzadores que el menú de Xubuntu (los .desktop), los ordena por las mismas categorías (Accesorios,
Configuración, Desarrollo, Gráficos, Internet, Juegos, Multimedia, Oficina, Sistema…) con su icono de verdad, y los
abre con `manejo_apps_kira.Manejo` (lista de argumentos, sin shell). Solo abre apps que están en esa lista: la pantalla
manda un id, nunca una orden.
"""
import os

import fondos_kira as fk
import manejo_apps_kira as ma

# categoría oficial (freedesktop) → nombre del menú de Xubuntu
CATEGORIAS = [("Configuración", ("Settings", "DesktopSettings", "HardwareSettings", "X-XFCE-SettingsDialog")),
              ("Internet", ("Network", "WebBrowser", "Email", "Chat", "P2P")),
              ("Multimedia", ("AudioVideo", "Audio", "Video", "Player", "Recorder")),
              ("Gráficos", ("Graphics", "Photography", "Viewer")),
              ("Oficina", ("Office", "WordProcessor", "Spreadsheet", "Presentation")),
              ("Desarrollo", ("Development", "IDE")),
              ("Juegos", ("Game",)),
              ("Educación", ("Education", "Science")),
              ("Sistema", ("System", "Monitor", "Security", "PackageManager", "TerminalEmulator", "FileManager")),
              ("Accesorios", ("Utility", "Accessibility", "TextEditor", "Archiving", "Calculator"))]
ORDEN = [c for c, _ in CATEGORIAS] + ["Otras"]

TEMAS_ICONOS = ("elementary-xfce-darker", "elementary-xfce-dark", "elementary-xfce", "Papirus", "Adwaita", "hicolor")
TAMANOS = ("48", "64", "32", "128", "256", "scalable")
_cache_icono = {}


def categoria_de(cats):
    cs = set(cats or [])
    for nombre, claves in CATEGORIAS:
        if cs & set(claves):
            return nombre
    return "Otras"


def ruta_icono(nombre, raiz="/usr/share"):
    """Busca el archivo del icono (png o svg) como lo hace el menú: tema → tamaño → apps; luego pixmaps."""
    if not nombre:
        return ""
    if os.path.isabs(nombre):
        return nombre if os.path.isfile(nombre) and nombre.lower().endswith((".png", ".svg")) else ""
    clave = (nombre, raiz)
    if clave in _cache_icono:
        return _cache_icono[clave]
    base = nombre[:-4] if nombre.lower().endswith((".png", ".svg", ".xpm")) else nombre
    hallado = ""
    for tema in TEMAS_ICONOS:
        for tam in TAMANOS:
            carpetas = (os.path.join(raiz, "icons", tema, f"{tam}x{tam}" if tam != "scalable" else tam, "apps"),
                        os.path.join(raiz, "icons", tema, "apps", tam))       # elementary: apps/48/
            for c in carpetas:
                for ext in (".png", ".svg"):
                    r = os.path.join(c, base + ext)
                    if os.path.isfile(r):
                        hallado = r
                        break
                if hallado:
                    break
            if hallado:
                break
        if hallado:
            break
    if not hallado:
        for ext in (".png", ".svg"):
            r = os.path.join(raiz, "pixmaps", base + ext)
            if os.path.isfile(r):
                hallado = r
                break
    _cache_icono[clave] = hallado
    return hallado


def icono_datos(nombre, raiz="/usr/share", maximo=160_000):
    r = ruta_icono(nombre, raiz)
    if not r:
        return ""
    try:
        if os.path.getsize(r) > maximo:
            return fk.miniatura(r, 64) if r.endswith(".png") else ""
        with open(r, "rb") as f:
            datos = f.read()
    except OSError:
        return ""
    return fk._data("image/svg+xml" if r.endswith(".svg") else "image/png", datos)


def menu(dirs=None, raiz_iconos="/usr/share", con_iconos=True):
    """{"categorias": [...], "apps": [{id, titulo, generico, categoria, icono}]} ordenadas por nombre."""
    apps = []
    for a in ma.apps_del_sistema(dirs):
        apps.append({"id": os.path.basename(a.get("archivo") or ""), "titulo": a["titulo"][:60],
                     "generico": (a.get("generico") or "")[:80], "categoria": categoria_de(a.get("categorias")),
                     "icono": icono_datos(a.get("icono"), raiz_iconos) if con_iconos else ""})
    apps.sort(key=lambda x: fk._plano(x["titulo"]))
    hay = {a["categoria"] for a in apps}
    return {"categorias": [c for c in ORDEN if c in hay], "apps": apps}


def app_por_id(ident, dirs=None):
    ident = os.path.basename(str(ident or ""))
    if not ident.endswith(".desktop"):
        return None
    for a in ma.apps_del_sistema(dirs):
        if os.path.basename(a.get("archivo") or "") == ident:
            return a
    return None


def abrir(ident, dirs=None, manejo=None):
    a = app_por_id(ident, dirs)
    if a is None:
        return {"ok": False, "texto": "Esa aplicación ya no está en el menú."}
    return (manejo or ma.Manejo(dirs=dirs)).abrir(a)
